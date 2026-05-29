from typing import Optional

from pydantic import BaseModel


class AuditLogEntry(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource: str
    resource_id: Optional[str]
    ip: Optional[str]
    ua: Optional[str]
    created_at: str


class AuditLogsResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    pageSize: int
    sort: str = "created_at:desc"
    filters: dict[str, str] = {}
