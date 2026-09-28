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


class MfaCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=20)  # 6-digit TOTP or a recovery code


class MfaSetupIn(BaseModel):
    password: str | None = Field(default=None, max_length=128)  # step-up: re-enter the password


class MfaSetupOut(BaseModel):
    secret: str  # shown once so it can be typed into an authenticator app
    uri: str


class RecoveryCodesOut(BaseModel):
    recovery_codes: list[str]  # shown once


class MfaChallengeOut(BaseModel):
    mfa_required: bool = True


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    locale: Locale
    organization_id: uuid.UUID | None
    has_password: bool
    created_at: datetime
    mfa_enabled: bool = False
    mfa_verified: bool = False  # this session passed the second factor

    @classmethod
    def of(cls, user: User, mfa_verified: bool = False) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            locale=user.locale,
            organization_id=user.organization_id,
            has_password=user.password_hash is not None,
            created_at=user.created_at,
            mfa_enabled=user.totp_enabled_at is not None,
            mfa_verified=mfa_verified,
        )
