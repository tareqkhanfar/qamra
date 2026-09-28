import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from qamra_core.db.models import Locale, User, UserRole


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    locale: Locale = Locale.ar

    @field_validator("full_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("empty name")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    locale: Locale
    organization_id: uuid.UUID | None
    has_password: bool
    created_at: datetime

    @classmethod
    def of(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            locale=user.locale,
            organization_id=user.organization_id,
            has_password=user.password_hash is not None,
            created_at=user.created_at,
        )
