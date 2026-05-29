import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.domains.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.user import (
    AdminCreateUser,
    AdminUpdateUser,
    OnboardingStepUpdate,
    UserOut,
    UserPrefsUpdate,
    UserUpdate,
    UsersListResponse,
)

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_role(UserRole.CEO, UserRole.ADMIN))]


@router.get("/me", response_model=UserOut)
async def get_me(current: CurrentUser) -> User:
    return current


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    current: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    if body.name is not None:
        current.name = body.name
    if body.email is not None:
        existing = await db.scalar(select(User).where(User.email == body.email))
        if existing and existing.id != current.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already taken")
        current.email = body.email
    await db.commit()
    await db.refresh(current)
    return current


@router.patch("/me/prefs", response_model=UserOut)
async def update_my_prefs(
    body: UserPrefsUpdate,
    current: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> "User":
    patch = body.to_patch()
    if patch:
        existing = current.prefs or {}
        current.prefs = {**existing, **patch}
        await db.commit()
        await db.refresh(current)
    return current


@router.patch("/me/onboarding-step", response_model=UserOut)
async def update_onboarding_step(
    body: OnboardingStepUpdate,
    current: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    current.onboarding_step = body.step
    await db.commit()
    await db.refresh(current)
    return current


@router.get("", response_model=UsersListResponse)
async def list_users(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at:desc"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> UsersListResponse:
    base_q = select(User).where(User.company_id == admin.company_id)
    if role:
        base_q = base_q.where(User.role == role)
    if is_active is not None:
        base_q = base_q.where(User.is_active == is_active)

    total = await db.scalar(
        select(func.count()).select_from(base_q.subquery())
    )

    sort_key, _, sort_dir = sort.partition(":")
    allowed = {"created_at", "name", "email", "role"}
    col = getattr(User, sort_key if sort_key in allowed else "created_at")
    order = asc(col) if sort_dir == "asc" else desc(col)

    result = await db.execute(
        base_q.order_by(order).offset((page - 1) * size).limit(size)
    )
    return UsersListResponse(items=list(result.scalars().all()), total=total or 0, page=page, pageSize=size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: AdminCreateUser,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    if await db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
        company_id=admin.company_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUpdateUser,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.scalar(
        select(User).where(User.id == user_id, User.company_id == admin.company_id)
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and body.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    if body.role is not None:
        user.role = body.role.value
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)
    return user
