"""Schemas for attendance + sessions."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AttendanceMethod, AttendanceStatus, SessionStatus


# ── Session management ──
class SessionOpenResponse(BaseModel):
    """Returned to the instructor when they open a session.

    The QR payload is computed locally on the instructor's phone every
    `window_s` seconds using `secret` + `window_index`. The instructor
    must NOT transmit the secret over the wire again — students verify
    via HMAC against it.
    """
    session_id: uuid.UUID
    secret: str
    window_s: int = 20
    late_threshold_minutes: int = 15
    status: SessionStatus
    offering_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime


class SessionLiveResponse(BaseModel):
    """Live roster snapshot (polled every 5 s by instructor app)."""
    session_id: uuid.UUID
    offering_id: uuid.UUID
    status: SessionStatus
    present_count: int
    late_count: int
    absent_count: int  # zero while open; filled after close
    flagged_count: int
    enrolled_count: int
    records: list["LiveRecord"]


class LiveRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: uuid.UUID
    full_name_ar: str
    status: AttendanceStatus
    method: AttendanceMethod
    scanned_at: datetime | None
    flagged: bool
    flag_reason: str | None


class SessionCloseResponse(BaseModel):
    session_id: uuid.UUID
    closed_at: datetime
    present_count: int
    late_count: int
    absent_count: int
    flagged_count: int
    enrolled_count: int


# ── Attendance scan ──
class LocationPayload(BaseModel):
    lat: float
    lng: float
    accuracy_m: float | None = None


class AttendanceScanRequest(BaseModel):
    session_id: uuid.UUID
    token: str = Field(min_length=10, max_length=2048)
    device_id: uuid.UUID | None = None
    location: LocationPayload | None = None


class AttendanceScanResponse(BaseModel):
    status: AttendanceStatus
    method: AttendanceMethod
    scanned_at: datetime
    flagged: bool = False
    flag_reason: str | None = None
    message_ar: str


    # Mapping of status code → meaning for client UX
    # 200 = present | late | flagged (already recorded, just informational)
    # 403 = NOT_ENROLLED / DEVICE_NOT_BOUND / NOT_SESSION_INSTRUCTOR (caller lacks scope)
    # 409 = SESSION_NOT_OPEN / SESSION_CLOSED / ALREADY_RECORDED
    # 410 = SESSION_EXPIRED / QR_WINDOW_INVALID (token expired)


class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    status: AttendanceStatus
    method: AttendanceMethod
    scanned_at: datetime | None
    flagged: bool
    flag_reason: str | None
    note: str | None


class AttendancePatchRequest(BaseModel):
    """Instructor manual edit (within 24h of session close)."""
    status: AttendanceStatus
    reason: str = Field(min_length=3, max_length=500)


class AttendanceSummaryRow(BaseModel):
    offering_id: uuid.UUID
    total_sessions: int
    present: int
    late: int
    absent: int
    excused: int
    attendance_percent: float
    is_warning: bool


class AttendanceSummaryResponse(BaseModel):
    student_id: uuid.UUID
    rows: list[AttendanceSummaryRow]


# Forward refs
SessionLiveResponse.model_rebuild()
