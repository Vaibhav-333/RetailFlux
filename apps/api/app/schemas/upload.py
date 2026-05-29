import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    dept: str
    original_name: str
    storage_key: str
    status: str
    rows_total: int | None
    rows_clean: int | None
    rows_rejected: int | None
    schema_version: int
    ge_report_id: str | None
    created_at: datetime
    updated_at: datetime


class UploadListResponse(BaseModel):
    items: list[UploadOut]
    total: int
