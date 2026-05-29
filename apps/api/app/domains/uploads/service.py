import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import get_minio_client, upload_bytes
from app.models.upload import Upload, UploadStatus
from app.models.user import User
from app.workers.celery_app import celery_app

_ALLOWED_EXT = {".csv", ".xlsx", ".xls"}
_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
_VALID_DEPTS = {"sales", "marketing", "operations", "finance", "procurement"}
_CONTENT_TYPES = {
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}

# Path traversal: characters that must never appear in a safe filename
_UNSAFE_FILENAME_CHARS = re.compile(r'[^\w\s\-.]')


def _secure_filename(raw: str) -> str:
    """Return a safe filename, preventing path traversal attacks.

    - Strips directory components (``../../etc/passwd`` → ``passwd``).
    - Removes any character that is not alphanumeric, whitespace, hyphen, or dot.
    - Collapses multiple dots to prevent extension spoofing (``foo..exe``).
    - Raises 400 if the result is empty or the extension is not in _ALLOWED_EXT.
    """
    # 1. Strip directory separators — take only the final component
    name = Path(raw).name  # "../../etc/passwd" → "passwd"; "../.." → ".."

    # 2. Reject names that are still traversal-like after stripping
    if name in (".", "..") or name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    # 3. Remove characters that should not appear in a filename
    name = _UNSAFE_FILENAME_CHARS.sub("", name)

    # 4. Collapse multiple dots (prevent ``foo..php.csv`` tricks)
    name = re.sub(r'\.{2,}', '.', name)

    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Filename is empty after sanitisation.")

    return name


async def create_upload(
    db: AsyncSession,
    file: UploadFile,
    dept: str,
    user: User,
) -> Upload:
    if dept not in _VALID_DEPTS:
        raise HTTPException(status_code=422, detail=f"Invalid department: {dept}")

    raw_filename = file.filename or "upload.csv"
    filename = _secure_filename(raw_filename)  # path-traversal safe
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=422, detail=f"Unsupported file type '{ext}'. Use CSV or Excel.")

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 50 MB size limit.")

    upload_id = uuid.uuid4()
    storage_key = f"{user.company_id}/{dept}/{upload_id}/{filename}"

    client = get_minio_client()
    upload_bytes(client, settings.MINIO_BUCKET_UPLOADS, storage_key, data, _CONTENT_TYPES[ext])

    record = Upload(
        id=upload_id,
        company_id=user.company_id,
        user_id=user.id,
        dept=dept,
        original_name=filename,
        storage_key=storage_key,
        status=UploadStatus.QUEUED.value,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    celery_app.send_task(
        "app.workers.tasks.process_upload.run",
        args=[str(upload_id)],
    )

    return record


async def get_upload(
    db: AsyncSession,
    upload_id: uuid.UUID,
    company_id: uuid.UUID,
) -> Upload:
    record = await db.scalar(
        select(Upload).where(Upload.id == upload_id, Upload.company_id == company_id)
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return record


async def list_uploads(
    db: AsyncSession,
    company_id: uuid.UUID,
    dept: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Upload], int]:
    q = select(Upload).where(Upload.company_id == company_id)
    if dept:
        q = q.where(Upload.dept == dept)

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    result = await db.execute(
        q.order_by(Upload.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    return list(result.scalars().all()), total or 0
