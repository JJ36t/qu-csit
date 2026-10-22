"""Attendance + session endpoints.

Implements brief §5.2 + §6 attendance group:

- POST /sessions/{id}/open   (instructor of the offering)
- POST /sessions/{id}/close  (instructor of the offering)
- GET  /sessions/{id}/live   (instructor of the offering)
- POST /attendance/scan       (student)
- PATCH /attendance/{id}     (instructor, within 24h of close)
- GET  /attendance/summary    (student — own summary)
- GET  /offerings/{id}/attendance/report  (instructor — per-student summary)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import CourseOffering, Enrollment, User, UserRole
from app.schemas.attendance import (
    AttendancePatchRequest,
    AttendanceRecordOut,
    AttendanceScanRequest,
    AttendanceScanResponse,
    AttendanceSummaryResponse,
    SessionCloseResponse,
    SessionLiveResponse,
    SessionOpenResponse,
)
from app.services.attendance import (
    close_session,
    live_session,
    open_session,
    patch_record,
    process_scan,
    student_summary,
)
from app.services.audit import write_audit

router = APIRouter()


@router.post("/sessions/{session_id}/open", response_model=SessionOpenResponse)
async def open_session_endpoint(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    data = open_session(db, session_id=session_id, instructor=user)
    write_audit(db, actor_id=user.id, action="open_session", entity="lecture_session",
                entity_id=str(session_id), after={"status": data["status"].value if hasattr(data["status"], "value") else data["status"]},
                request=request)
    db.commit()
    return SessionOpenResponse(**data)


@router.post("/sessions/{session_id}/close", response_model=SessionCloseResponse)
async def close_session_endpoint(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    data = close_session(db, session_id=session_id, instructor=user)
    write_audit(db, actor_id=user.id, action="close_session", entity="lecture_session",
                entity_id=str(session_id),
                after={"present": data["present_count"], "late": data["late_count"], "absent": data["absent_count"]},
                request=request)
    return SessionCloseResponse(**data)


@router.get("/sessions/{session_id}/live", response_model=SessionLiveResponse)
async def live_session_endpoint(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = live_session(db, session_id=session_id, instructor=user)
    return SessionLiveResponse(**data)


@router.post("/attendance/scan", response_model=AttendanceScanResponse)
async def scan_endpoint(
    payload: AttendanceScanRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Student scans a QR; server validates + records.

    Status codes:
      200 = present / late / flagged (recorded)
      403 = NOT_ENROLLED / DEVICE_NOT_BOUND / NOT_SESSION_INSTRUCTOR
      409 = SESSION_NOT_OPEN / SESSION_CLOSED / ALREADY_RECORDED
      410 = QR_WINDOW_INVALID (token expired)
    """
    if user.role != UserRole.student:
        raise APIError("ROLE_NOT_ALLOWED", 403)
    return process_scan(db, payload=payload, student=user)


@router.patch("/attendance/{record_id}", response_model=AttendanceRecordOut)
async def patch_attendance_endpoint(
    record_id: uuid.UUID,
    payload: AttendancePatchRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = patch_record(
        db,
        record_id=record_id,
        new_status=payload.status,
        reason=payload.reason,
        editor=user,
    )
    return AttendanceRecordOut.model_validate(record)


@router.get("/attendance/summary", response_model=AttendanceSummaryResponse)
async def summary_endpoint(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-student attendance summary across all their offerings."""
    if user.role != UserRole.student:
        # Instructors/admins can pass ?student_id=...
        raise APIError("ROLE_NOT_ALLOWED", 403, {"hint": "students see their own summary"})
    data = student_summary(db, student_id=user.id)
    return AttendanceSummaryResponse(**data)


@router.get("/offerings/{offering_id}/attendance/report")
async def offering_report_endpoint(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-student attendance report for an offering (instructor only)."""
    offering = db.get(CourseOffering, offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404, {"offering_id": str(offering_id)})
    if user.role == UserRole.instructor:
        if not user.staff or offering.instructor_id != user.staff.user_id:
            raise APIError("NOT_SESSION_INSTRUCTOR", 403)
    elif user.role not in (UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin):
        raise APIError("ROLE_NOT_ALLOWED", 403)

    enrollments = db.scalars(
        select(Enrollment).where(Enrollment.offering_id == offering_id)
    ).all()
    out = []
    for e in enrollments:
        s_data = student_summary(db, student_id=e.student_id)
        # Filter to this offering only
        matching = [r for r in s_data["rows"] if r["offering_id"] == offering_id]
        out.append({
            "student_id": str(e.student_id),
            "student_name": db.get(User, e.student_id).full_name_ar if db.get(User, e.student_id) else None,
            "summary": matching[0] if matching else None,
        })
    return {"offering_id": str(offering_id), "students": out}
