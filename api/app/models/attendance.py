"""Attendance: attendance_records + absence_excuses (V2 table only)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin
from app.models.enums import AttendanceMethod, AttendanceStatus


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance_session_student"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("lecture_sessions.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("students.user_id", ondelete="CASCADE"), index=True
    )
    status: Mapped[AttendanceStatus] = mapped_column(
        default=AttendanceStatus.present, index=True
    )
    method: Mapped[AttendanceMethod] = mapped_column(default=AttendanceMethod.qr)
    scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flag_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    marked_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("staff.user_id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("LectureSession", back_populates="attendance")
    student = relationship("Student")


class AbsenceExcuse(Base, TimestampMixin):
    """V2 — table created for migration stability, no endpoints."""

    __tablename__ = "absence_excuses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("students.user_id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("lecture_sessions.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(Text)
    attachment_file_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("files.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("staff.user_id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    student = relationship("Student")
    attachment = relationship("File")
