"""Identity & devices: users, students, staff, devices, refresh_tokens, fcm_tokens."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin
from app.models.enums import (
    DeviceStatus,
    EnrollmentSource,
    UserStatus,
    UserRole,
    StudyType,
    StudentStatus,
)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    role: Mapped[UserRole] = mapped_column(default=UserRole.student)
    university_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    full_name_ar: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[UserStatus] = mapped_column(default=UserStatus.pending)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 2FA (Phase 2)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    student: Mapped["Student | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    staff: Mapped["Staff | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    fcm_tokens: Mapped[list["FcmToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("departments.id"), index=True
    )
    stage: Mapped[int] = mapped_column(Integer, index=True)
    study_type: Mapped[StudyType] = mapped_column(default=StudyType.morning)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("groups.id"), nullable=True, index=True
    )
    enrollment_year: Mapped[int] = mapped_column(Integer)
    status: Mapped[StudentStatus] = mapped_column(default=StudentStatus.active)

    user: Mapped["User"] = relationship(back_populates="student")
    department = relationship("Department")
    group = relationship("Group")


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("departments.id"), nullable=True, index=True
    )
    academic_title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    office: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="staff")
    department = relationship("Department")


class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("user_id", "device_fingerprint", name="uq_devices_user_fp"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    device_fingerprint: Mapped[str] = mapped_column(String(255), index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    status: Mapped[DeviceStatus] = mapped_column(default=DeviceStatus.active)

    user: Mapped["User"] = relationship(back_populates="devices")


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class FcmToken(Base, TimestampMixin):
    __tablename__ = "fcm_tokens"
    __table_args__ = (UniqueConstraint("user_id", "device_id", "token", name="uq_fcm_user_dev_token"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    token: Mapped[str] = mapped_column(String(512), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="fcm_tokens")


# Re-export to satisfy flake8 forward refs used by enrollments referencing EnrollmentSource.
_ = EnrollmentSource
