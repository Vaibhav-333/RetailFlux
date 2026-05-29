import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import Company
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)
_DENYLIST = "jwt:denylist:"


async def register(
    db: AsyncSession,
    company_name: str,
    email: str,
    password: str,
    name: str,
) -> tuple[User, str, str]:
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    company = Company(name=company_name)
    db.add(company)
    await db.flush()

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        role=UserRole.CEO,
        company_id=company.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id), extra={"company_id": str(user.company_id)})
    refresh_token, _ = create_refresh_token(str(user.id), extra={"company_id": str(user.company_id)})
    return user, access_token, refresh_token


async def login(
    db: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, str, str]:
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id), extra={"company_id": str(user.company_id)})
    refresh_token, _ = create_refresh_token(str(user.id), extra={"company_id": str(user.company_id)})
    return user, access_token, refresh_token


async def refresh_tokens(token: str) -> str:
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")

    jti = payload.get("jti")
    if jti:
        try:
            redis = await get_redis()
            if await redis.get(f"{_DENYLIST}{jti}"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        except HTTPException:
            raise
        except Exception:
            logger.warning("Redis unavailable — skipping denylist check")

    extra: dict[str, str] | None = None
    if company_id := payload.get("company_id"):
        extra = {"company_id": company_id}
    return create_access_token(payload["sub"], extra=extra)


async def logout(token: str) -> None:
    try:
        payload = decode_token(token)
    except JWTError:
        return

    jti = payload.get("jti")
    if not jti:
        return

    from datetime import datetime as _dt
    exp = payload.get("exp", 0)
    ttl = max(int(exp - _dt.now(timezone.utc).timestamp()), 1)
    try:
        redis = await get_redis()
        await redis.setex(f"{_DENYLIST}{jti}", ttl, "1")
    except Exception:
        logger.warning("Redis unavailable — token not added to denylist")
