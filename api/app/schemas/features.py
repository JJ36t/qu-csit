"""Schemas for timetable, announcements, notifications."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    AnnouncementScope,
    SlotKind,
    TimetableChangeType,
)


# ── Timetable ──
class TimetableSlotCreate(BaseModel):
    offering_id: uuid.UUID
    weekday: int = Field(ge=0, le=6)  # 0=Sunday..4=Thursday by default; configurable
    start_time: time
    end_time: time
    room_id: uuid.UUID | None = None
    kind: SlotKind = SlotKind.theory

    @model_validator(mode="after")
    def _check_times(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class TimetableSlotUpdate(BaseModel):
    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    room_id: uuid.UUID | None = None
    kind: SlotKind | None = None


class TimetableSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    offering_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time
    room_id: uuid.UUID | None = None
    kind: SlotKind


class TimetableChangeCreate(BaseModel):
    slot_id: uuid.UUID
    date: date
    type: TimetableChangeType = TimetableChangeType.move
    new_start: time | None = None
    new_end: time | None = None
    new_room_id: uuid.UUID | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _check_cancel(self):
        if self.type == TimetableChangeType.cancel:
            # cancel doesn't need new times
            return self
        if self.type == TimetableChangeType.move and not (self.new_start or self.new_end):
            raise ValueError("move requires new_start or new_end")
        return self


class TimetableChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slot_id: uuid.UUID
    date: date
    type: TimetableChangeType
    new_start: time | None
    new_end: time | None
    new_room_id: uuid.UUID | None
    reason: str | None
    created_by: uuid.UUID | None


class TimetableEntry(BaseModel):
    """A combined view: weekly slot + any dated change for a specific date."""
    slot: TimetableSlotOut
    changes: list[TimetableChangeOut] = Field(default_factory=list)
    # Resolved view for the given date (after applying changes)
    effective_start: time | None = None
    effective_end: time | None = None
    effective_room_id: uuid.UUID | None = None
    is_cancelled: bool = False


class TimetableResponse(BaseModel):
    """Grouped by date."""
    date: date
    entries: list[TimetableEntry]


# ── Announcements ──
class AnnouncementCreate(BaseModel):
    scope: AnnouncementScope = AnnouncementScope.college
    scope_id: str | None = None  # department_id, stage, group_id, offering_id (as string)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    priority: int = Field(default=0, ge=0, le=10)
    pinned: bool = False
    publish_at: datetime | None = None
    expires_at: datetime | None = None
    attachment_file_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _check_scope(self):
        if self.scope != AnnouncementScope.college and not self.scope_id:
            raise ValueError(f"scope={self.scope.value} requires scope_id")
        if self.expires_at and self.publish_at and self.expires_at < self.publish_at:
            raise ValueError("expires_at must be after publish_at")
        return self


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    scope: AnnouncementScope
    scope_id: str | None
    title: str
    body: str
    priority: int
    pinned: bool
    publish_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    created_by: uuid.UUID | None
    is_read: bool = False  # filled in per-viewer


class PublicNewsOut(BaseModel):
    """Subset for the unauthenticated /public/news endpoint."""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
    pinned: bool
    publish_at: datetime | None
    created_at: datetime


# ── Notifications ──
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    data: dict[str, Any] | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationOut]
    total: int
    unread: int


# ── Audit log (admin read-only) ──
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    actor_id: uuid.UUID | None
    action: str
    entity: str
    entity_id: str | None
    ip: str | None
