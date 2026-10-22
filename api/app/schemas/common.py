"""Pydantic v2 schemas — API request/response shapes."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    StudyType,
    StudentStatus,
    UserRole,
    UserStatus,
)


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Auth ──
class LoginRequest(BaseModel):
    university_id: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    device_fingerprint: str | None = Field(default=None, max_length=255)
    device_model: str | None = Field(default=None, max_length=255)
    fcm_token: str | None = Field(default=None, max_length=512)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    must_change_password: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class FcmTokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    device_fingerprint: str | None = None


class UserOut(ORMBase):
    id: uuid.UUID
    role: UserRole
    university_id: str
    full_name_ar: str
    email: str | None = None
    phone: str | None = None
    status: UserStatus
    must_change_password: bool
    last_login_at: datetime | None = None


class StudentOut(ORMBase):
    user_id: uuid.UUID
    department_id: uuid.UUID
    stage: int
    study_type: StudyType
    group_id: uuid.UUID | None
    enrollment_year: int
    status: StudentStatus


class AuthMeOut(ORMBase):
    user: UserOut
    student: StudentOut | None = None
    staff: "StaffOut | None" = None


class StaffOut(ORMBase):
    user_id: uuid.UUID
    department_id: uuid.UUID | None
    academic_title: str | None = None
    office: str | None = None


# ── Public config (no auth) ──
class PublicConfig(BaseModel):
    app_name: str
    package_id: str
    timezone: str
    week_start: str
    maintenance: bool = False
    min_app_version: str = "0.1.0"


# ── Generic helpers ──
class ErrorResponse(BaseModel):
    code: str
    message_ar: str
    details: dict = Field(default_factory=dict)


class PaginatedMeta(BaseModel):
    page: int
    limit: int
    total: int


class OkResponse(BaseModel):
    ok: bool = True


# Forward refs
AuthMeOut.model_rebuild()
