"""Celery task: validate an uploaded file and load clean rows into MongoDB staging."""
import io
import uuid

import pandas as pd
from celery.exceptions import SoftTimeLimitExceeded
from pandera.errors import SchemaErrors
from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.cache import invalidate_company_sync
from app.core.config import settings
from app.core.storage import download_bytes, get_minio_client
from app.domains.uploads.pandera_schemas import DEPT_SCHEMAS
from app.models.notification import Notification
from app.models.upload import Upload, UploadStatus
from app.workers.celery_app import celery_app

# Convert async URL to sync for Celery workers
_SYNC_DB_URL = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


def _get_session() -> Session:
    return Session(_engine)


@celery_app.task(
    name="app.workers.tasks.process_upload.run",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=120,
    time_limit=180,
)
def run(self, upload_id: str) -> dict:  # type: ignore[return]
    uid = uuid.UUID(upload_id)

    with _get_session() as session:
        upload = session.get(Upload, uid)
        if not upload:
            return {"error": f"Upload {upload_id} not found"}

        # Mark as processing
        upload.status = UploadStatus.PROCESSING.value
        session.commit()

        try:
            # ── 1. Download from MinIO ────────────────────────────────────────
            client = get_minio_client()
            raw = download_bytes(client, settings.MINIO_BUCKET_UPLOADS, upload.storage_key)

            # ── 2. Parse ──────────────────────────────────────────────────────
            buf = io.BytesIO(raw)
            if upload.original_name.lower().endswith(".csv"):
                df = pd.read_csv(buf)
            else:
                df = pd.read_excel(buf)

            rows_total = len(df)

            if rows_total == 0:
                upload.status = UploadStatus.REJECTED.value
                upload.rows_total = 0
                upload.rows_clean = 0
                upload.rows_rejected = 0
                session.commit()
                return {"status": "rejected", "reason": "empty file"}

            # ── 3. Pandera validation ─────────────────────────────────────────
            schema = DEPT_SCHEMAS.get(upload.dept)
            if schema is None:
                upload.status = UploadStatus.REJECTED.value
                upload.rows_total = rows_total
                upload.rows_clean = 0
                upload.rows_rejected = rows_total
                session.commit()
                return {"status": "rejected", "reason": f"no schema for dept '{upload.dept}'"}

            rejected_indices: set[int] = set()
            try:
                schema.validate(df, lazy=True)
            except SchemaErrors as exc:
                fc = exc.failure_cases
                if "index" in fc.columns:
                    rejected_indices = set(
                        int(i) for i in fc["index"].dropna().tolist()
                    )
                else:
                    # Column-level error: entire file is invalid
                    rejected_indices = set(range(rows_total))

            rows_rejected = len(rejected_indices)
            rows_clean = rows_total - rows_rejected
            clean_df = df.drop(index=list(rejected_indices)) if rejected_indices else df

            # ── 4. Store clean rows in MongoDB staging ────────────────────────
            if not clean_df.empty:
                mongo = MongoClient(settings.MONGODB_URL)
                mongo_db = mongo[settings.MONGODB_DATABASE]
                collection = mongo_db[f"staging_{upload.dept}"]

                records = (
                    clean_df.where(pd.notnull(clean_df), None)
                    .to_dict(orient="records")
                )
                for rec in records:
                    rec["_upload_id"] = upload_id
                    rec["_company_id"] = str(upload.company_id)

                collection.insert_many(records)
                mongo.close()
                # Bust the analytics cache so fresh data is served immediately
                invalidate_company_sync(str(upload.company_id))

            # ── 5. Finalise upload record ─────────────────────────────────────
            final_status = (
                UploadStatus.COMPLETE
                if rows_rejected < rows_total
                else UploadStatus.REJECTED
            )
            upload.status = final_status.value
            upload.rows_total = rows_total
            upload.rows_clean = rows_clean
            upload.rows_rejected = rows_rejected

            # ── 6. Create upload completion notification ──────────────────────
            is_complete = final_status == UploadStatus.COMPLETE
            notif = Notification(
                id=uuid.uuid4(),
                user_id=upload.user_id,
                type="info" if is_complete else "warning",
                payload={
                    "title": f"{upload.dept.capitalize()} upload {'completed' if is_complete else 'rejected'}",
                    "message": f"{rows_clean} rows loaded successfully, {rows_rejected} rejected.",
                    "dept": upload.dept,
                },
            )
            session.add(notif)
            session.commit()

            return {
                "status": final_status.value,
                "rows_total": rows_total,
                "rows_clean": rows_clean,
                "rows_rejected": rows_rejected,
            }

        except SoftTimeLimitExceeded:
            upload.status = UploadStatus.ERROR.value
            session.commit()
            return {"error": "Task timed out", "upload_id": upload_id}

        except Exception as exc:
            upload.status = UploadStatus.ERROR.value
            session.commit()
            raise self.retry(exc=exc)
