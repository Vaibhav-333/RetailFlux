import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    role: UserRole
    company_id: uuid.UUID
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None
    prefs: dict[str, Any] | None = None
    onboarding_step: int = 0


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None


class AdminCreateUser(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.SALES


class AdminUpdateUser(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class UserPrefsUpdate(BaseModel):
    density: Literal["comfortable", "compact"] | None = None
    theme: Literal["dark", "light"] | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _no_nulls(cls, v: Any) -> Any:
        return v

    def to_patch(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class OnboardingStepUpdate(BaseModel):
    step: int = Field(..., ge=0, le=10)


class UsersListResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int = 1
    pageSize: int = 20
