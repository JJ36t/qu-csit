"""Schedule: rooms, timetable_slots, timetable_changes, lecture_sessions."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin
from app.models.enums import SessionStatus, SlotKind, TimetableChangeType


# JSON type that resolves to JSONB on PostgreSQL and JSON on SQLite.
class JSONType(JSON):
    pass


try:
    from sqlalchemy import TypeDecorator as _TD  # noqa
except Exception:  # pragma: no cover
    _TD = None


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), index=True)
    building: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    slots = relationship("TimetableSlot", back_populates="room")


class TimetableSlot(Base, TimestampMixin):
    """Weekly recurring slot for an offering."""

    __tablename__ = "timetable_slots"
    __table_args__ = (
        UniqueConstraint("offering_id", "weekday", "start_time", name="uq_slot_offering_day_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    offering_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("course_offerings.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, index=True)  # 0=Sunday..4=Thursday (configurable)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("rooms.id"), nullable=True, index=True
    )
    kind: Mapped[SlotKind] = mapped_column(default=SlotKind.theory)

    offering = relationship("CourseOffering", back_populates="slots")
    room = relationship("Room", back_populates="slots")
    changes = relationship("TimetableChange", back_populates="slot", cascade="all, delete-orphan")
    sessions = relationship("LectureSession", back_populates="slot")


class TimetableChange(Base, TimestampMixin):
    """Dated exception to a weekly slot (cancel / move / extra)."""

    __tablename__ = "timetable_changes"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    slot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("timetable_slots.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    type: Mapped[TimetableChangeType] = mapped_column(default=TimetableChangeType.move)
    new_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    new_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    new_room_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("rooms.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )

    slot = relationship("TimetableSlot", back_populates="changes")
    new_room = relationship("Room")


class LectureSession(Base, TimestampMixin):
    """One concrete session per slot per week."""

    __tablename__ = "lecture_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    offering_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("course_offerings.id", ondelete="CASCADE"), index=True
    )
    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("timetable_slots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[SessionStatus] = mapped_column(
        default=SessionStatus.scheduled, index=True
    )
    opened_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("staff.user_id"), nullable=True
    )
    secret: Mapped[str | None] = mapped_column(String(128), nullable=True)
    window_s: Mapped[int] = mapped_column(Integer, default=20)
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    offering = relationship("CourseOffering", back_populates="sessions")
    slot = relationship("TimetableSlot", back_populates="sessions")
    attendance = relationship(
        "AttendanceRecord", back_populates="session", cascade="all, delete-orphan"
    )


# Silence unused-import warnings when JSON is used via JSONType only.
_ = (JSONB, Any)
