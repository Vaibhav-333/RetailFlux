from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.domains.auth import service as auth_service
from app.schemas.auth import LoginRequest, RefreshResponse, RegisterRequest, TokenResponse

router = APIRouter()

_COOKIE = "refresh_token"
_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_COOKIE,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE, path="/api/v1/auth")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, access_token, refresh_token = await auth_service.register(
        db, body.company_name, body.email, body.password, body.name
    )
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token, user=user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    user, access_token, refresh_token = await auth_service.login(db, body.email, body.password)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token, user=user)


# Origins allowed to call the cookie-based refresh endpoint.
# Empty Origin header (server-to-server, tests) is always permitted.
_CSRF_ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://localhost:5173",
    "https://retailflux.app",
    "https://retailflux.vercel.app",
}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE),
) -> RefreshResponse:
    # CSRF guard: if the browser sends an Origin/Referer it must match an
    # allowed origin. Requests without an Origin header (tests, curl, server)
    # are unconditionally permitted — the httpOnly cookie already prevents
    # JavaScript-based theft.
    origin = request.headers.get("origin") or request.headers.get("referer", "")
    if origin and not any(origin.startswith(o) for o in _CSRF_ALLOWED_ORIGINS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF check failed",
        )

    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    access_token = await auth_service.refresh_tokens(refresh_token)
    return RefreshResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE),
) -> None:
    if refresh_token:
        await auth_service.logout(refresh_token)
    _clear_refresh_cookie(response)
