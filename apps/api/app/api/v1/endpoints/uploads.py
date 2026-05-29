import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.domains.auth.dependencies import get_current_user
from app.domains.uploads import service as upload_service
from app.models.user import User
from app.schemas.upload import UploadListResponse, UploadOut

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def create_upload(
    request: Request,  # required by SlowAPI for rate-limit key extraction
    current: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(..., description="CSV or Excel file"),
    dept: str = Form(..., description="Department: sales|marketing|operations|finance|procurement"),
) -> UploadOut:
    return await upload_service.create_upload(db, file, dept, current)


@router.get("", response_model=UploadListResponse)
async def list_uploads(
    current: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    dept: str | None = None,
    page: int = 1,
    size: int = 20,
) -> UploadListResponse:
    items, total = await upload_service.list_uploads(db, current.company_id, dept, page, size)
    return UploadListResponse(items=items, total=total)


@router.get("/{upload_id}", response_model=UploadOut)
async def get_upload(
    upload_id: uuid.UUID,
    current: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UploadOut:
    return await upload_service.get_upload(db, upload_id, current.company_id)
