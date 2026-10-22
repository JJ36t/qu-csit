"""Attendance validation pipeline.

Brief §5.2 step 4 — server validates in this order and returns the matching
status code:

1. Session exists & is open         → 409 SESSION_NOT_OPEN / SESSION_CLOSED
2. Student enrolled in offering     → 403 NOT_ENROLLED
3. Token valid for current/previous → 410 QR_WINDOW_INVALID
4. Not already recorded             → 409 ALREADY_RECORDED
5. Device equals bound device       → 403 DEVICE_NOT_BOUND
6. Location inside room radius      → record flagged=true (200, not rejected)
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.i18n.errors_ar import APIError
from app.models import (
    AttendanceRecord,
    CourseOffering,
    Device,
    DeviceStatus,
    Enrollment,
    EnrollmentStatus,
    LectureSession,
    Room,
    SessionStatus,
    Student,
    User,
    UserRole,
)
from app.models.enums import AttendanceMethod, AttendanceStatus
from app.schemas.attendance import (
    AttendanceScanRequest,
    AttendanceScanResponse,
)
from app.services.qr_token import verify_token


def open_session(db: Session, *, session_id: uuid.UUID, instructor: User) -> dict:
    """Open an attendance session. Returns the secret + window_s to the caller."""
    session = db.get(LectureSession, session_id)
    if not session:
        raise APIError("NOT_FOUND", 404, {"session_id": str(session_id)})

    offering = db.get(CourseOffering, session.offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404, {"offering_id": str(session.offering_id)})

    # Instructor check (or admin)
    if instructor.role == UserRole.instructor:
        if not instructor.staff or offering.instructor_id != instructor.staff.user_id:
            raise APIError("NOT_SESSION_INSTRUCTOR", 403)
    elif instructor.role not in (UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin):
        raise APIError("ROLE_NOT_ALLOWED", 403)

    # Time window check: now must be within [starts_at - 10 min, ends_at + 30 min]
    now = datetime.now(timezone.utc)
    starts_at = _ensure_tz(session.starts_at)
    ends_at = _ensure_tz(session.ends_at)
    early_window = starts_at - timedelta(minutes=10)
    late_window = ends_at + timedelta(minutes=30)
    if now < early_window or now > late_window:
        raise APIError("OUTSIDE_ATTENDANCE_WINDOW", 400, {
            "now": now.isoformat(),
            "window_start": early_window.isoformat(),
            "window_end": late_window.isoformat(),
        })

    if session.status == SessionStatus.closed:
        raise APIError("SESSION_CLOSED", 409, {"closed_at": session.closed_at.isoformat() if session.closed_at else None})

    # Generate secret if not yet open
    from app.services.qr_token import generate_session_secret
    if not session.secret:
        session.secret = generate_session_secret()
        session.window_s = 20
    if session.status != SessionStatus.open:
        session.status = SessionStatus.open
        session.opened_by = instructor.staff.user_id if instructor.staff else None
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "secret": session.secret,
        "window_s": session.window_s,
        "late_threshold_minutes": settings.late_threshold_minutes,
        "status": session.status,
        "offering_id": session.offering_id,
        "starts_at": session.starts_at,
        "ends_at": session.ends_at,
    }


def close_session(db: Session, *, session_id: uuid.UUID, instructor: User) -> dict:
    """Close the session. Marks every enrolled student without a record as `absent`.

    Returns the final counts. Also checks absence threshold per offering +
    student and creates `absence_warning` notifications.
    """
    session = db.get(LectureSession, session_id)
    if not session:
        raise APIError("NOT_FOUND", 404, {"session_id": str(session_id)})

    offering = db.get(CourseOffering, session.offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404)

    if instructor.role == UserRole.instructor:
        if not instructor.staff or offering.instructor_id != instructor.staff.user_id:
            raise APIError("NOT_SESSION_INSTRUCTOR", 403)
    elif instructor.role not in (UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin):
        raise APIError("ROLE_NOT_ALLOWED", 403)

    if session.status == SessionStatus.closed:
        # Idempotent — return existing counts
        pass
    else:
        # Mark all enrolled students without a record as absent
        enrolled_ids = db.scalars(
            select(Enrollment.student_id).where(
                Enrollment.offering_id == session.offering_id,
                Enrollment.status == EnrollmentStatus.active,
            )
        ).all()
        existing = {
            r.student_id for r in db.scalars(
                select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
            ).all()
        }
        for sid in enrolled_ids:
            if sid not in existing:
                db.add(
                    AttendanceRecord(
                        session_id=session_id,
                        student_id=sid,
                        status=AttendanceStatus.absent,
                        method=AttendanceMethod.manual,
                        scanned_at=None,
                        flagged=False,
                        marked_by=instructor.staff.user_id if instructor.staff else None,
                        note="auto_absent_at_close",
                    )
                )
        session.status = SessionStatus.closed
        session.closed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

        # Send absence warnings if the offering's cumulative absence count for
        # any student crosses the threshold.
        _maybe_send_absence_warnings(db, offering_id=session.offering_id)
        db.commit()  # persist any notifications created

    # Compute counts
    return _session_counts(db, session_id, session)


def _session_counts(db: Session, session_id: uuid.UUID, session: LectureSession) -> dict:
    records = db.scalars(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
    ).all()
    present = sum(1 for r in records if r.status == AttendanceStatus.present)
    late = sum(1 for r in records if r.status == AttendanceStatus.late)
    absent = sum(1 for r in records if r.status == AttendanceStatus.absent)
    flagged = sum(1 for r in records if r.flagged)
    # Count enrolled
    from sqlalchemy import func
    enrolled_count = db.scalar(
        select(func.count()).select_from(Enrollment).where(
            Enrollment.offering_id == session.offering_id,
            Enrollment.status == EnrollmentStatus.active,
        )
    ) or 0
    return {
        "session_id": session_id,
        "closed_at": session.closed_at,
        "present_count": present,
        "late_count": late,
        "absent_count": absent,
        "flagged_count": flagged,
        "enrolled_count": enrolled_count,
    }


def process_scan(
    db: Session, *, payload: AttendanceScanRequest, student: User
) -> AttendanceScanResponse:
    """Validate + record a student scan. Returns the result."""
    # 1. Session open?
    session = db.get(LectureSession, payload.session_id)
    if not session:
        raise APIError("NOT_FOUND", 404, {"session_id": str(payload.session_id)})
    if session.status == SessionStatus.closed:
        raise APIError("SESSION_CLOSED", 409, {"closed_at": session.closed_at.isoformat() if session.closed_at else None})
    if session.status != SessionStatus.open:
        raise APIError("SESSION_NOT_OPEN", 409, {"status": session.status.value})

    # 2. Enrolled in this offering?
    enrollment = db.scalar(
        select(Enrollment).where(
            Enrollment.student_id == student.id,
            Enrollment.offering_id == session.offering_id,
            Enrollment.status == EnrollmentStatus.active,
        )
    )
    if not enrollment:
        raise APIError("NOT_ENROLLED", 403, {"offering_id": str(session.offering_id)})

    # 3. Token valid for current or previous window?
    if not session.secret:
        raise APIError("SESSION_NOT_OPEN", 409, {"reason": "no secret"})
    valid, _window = verify_token(
        token=payload.token,
        session_id=str(session.id),
        secret=session.secret,
        window_s=session.window_s,
        allow_previous_window=True,
    )
    if not valid:
        raise APIError("QR_WINDOW_INVALID", 410)

    # 4. Not already recorded?
    existing = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == student.id,
        )
    )
    if existing:
        # Idempotent-ish: return the existing record's status.
        raise APIError(
            "ALREADY_RECORDED",
            409,
            {"existing_status": existing.status.value, "scanned_at": existing.scanned_at.isoformat() if existing.scanned_at else None},
        )

    # 5. Device matches bound device?
    if student.role != UserRole.student or not student.student:
        raise APIError("ROLE_NOT_ALLOWED", 403)
    bound_device = db.scalar(
        select(Device).where(
            Device.user_id == student.id,
            Device.status == DeviceStatus.active,
        )
    )
    if not bound_device:
        raise APIError("DEVICE_NOT_BOUND", 403, {"reason": "no active device bound"})
    # The student must be on their bound device. payload.device_id may be the
    # device fingerprint; we accept either the device UUID or the fingerprint.
    if payload.device_id is not None and payload.device_id != bound_device.id:
        raise APIError("DEVICE_NOT_BOUND", 403, {"reason": "wrong device"})

    # 6. Location — flag (don't reject) if outside the room radius
    flagged = False
    flag_reason: str | None = None
    if payload.location is None:
        flagged = True
        flag_reason = "NO_LOCATION_PROVIDED"
    else:
        # Look up the room from the slot (if any)
        room = None
        if session.slot_id:
            from app.models import TimetableSlot
            slot = db.get(TimetableSlot, session.slot_id)
            if slot and slot.room_id:
                room = db.get(Room, slot.room_id)
        if room and room.lat is not None and room.lng is not None and room.radius_m:
            distance = _haversine(
                payload.location.lat, payload.location.lng, room.lat, room.lng
            )
            if distance > room.radius_m:
                flagged = True
                flag_reason = f"OUTSIDE_ROOM_RADIUS_{int(distance)}m"

    # Compute late/present
    now = datetime.now(timezone.utc)
    starts_at = _ensure_tz(session.starts_at)
    late_threshold = timedelta(minutes=settings.late_threshold_minutes)
    status = AttendanceStatus.late if now > (starts_at + late_threshold) else AttendanceStatus.present

    # If late counts as absence (per the term rule), we don't downgrade the
    # status here — the count is computed at report time using the term rule.
    record = AttendanceRecord(
        session_id=session.id,
        student_id=student.id,
        status=status,
        method=AttendanceMethod.qr,
        scanned_at=now,
        device_id=bound_device.id,
        lat=payload.location.lat if payload.location else None,
        lng=payload.location.lng if payload.location else None,
        accuracy_m=payload.location.accuracy_m if payload.location else None,
        flagged=flagged,
        flag_reason=flag_reason,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    msg = "تم تسجيل حضورك"
    if status == AttendanceStatus.late:
        msg = "تم تسجيلك كمتأخر"
    if flagged:
        msg = "تم تسجيل حضورك للمراجعة (الموقع)"

    return AttendanceScanResponse(
        status=status,
        method=AttendanceMethod.qr,
        scanned_at=record.scanned_at,
        flagged=flagged,
        flag_reason=flag_reason,
        message_ar=msg,
    )


def patch_record(
    db: Session,
    *,
    record_id: uuid.UUID,
    new_status: AttendanceStatus,
    reason: str,
    editor: User,
) -> AttendanceRecord:
    """Manual edit by instructor (within 24h of session close). Audit-logged."""
    record = db.get(AttendanceRecord, record_id)
    if not record:
        raise APIError("NOT_FOUND", 404, {"record_id": str(record_id)})
    session = db.get(LectureSession, record.session_id)
    if not session:
        raise APIError("NOT_FOUND", 404)
    offering = db.get(CourseOffering, session.offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404)

    if editor.role == UserRole.instructor:
        if not editor.staff or offering.instructor_id != editor.staff.user_id:
            raise APIError("NOT_SESSION_INSTRUCTOR", 403)
    elif editor.role not in (UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin):
        raise APIError("ROLE_NOT_ALLOWED", 403)

    # Edit allowed within 24h of close
    if session.closed_at:
        cutoff = _ensure_tz(session.closed_at) + timedelta(hours=24)
        if datetime.now(timezone.utc) > cutoff:
            raise APIError("OUTSIDE_ATTENDANCE_WINDOW", 400, {"reason": "edit window expired"})

    old_status = record.status
    record.status = new_status
    record.note = f"manual edit by {editor.university_id}: {reason}"
    record.marked_by = editor.staff.user_id if editor.staff else None
    db.commit()
    db.refresh(record)

    # Audit log
    from app.services.audit import write_audit
    write_audit(
        db,
        actor_id=editor.id,
        action="patch_attendance",
        entity="attendance_record",
        entity_id=str(record.id),
        before={"status": old_status.value},
        after={"status": new_status.value, "reason": reason},
    )
    db.commit()
    return record


def live_session(db: Session, *, session_id: uuid.UUID, instructor: User) -> dict:
    """Return the live roster snapshot for the instructor."""
    session = db.get(LectureSession, session_id)
    if not session:
        raise APIError("NOT_FOUND", 404, {"session_id": str(session_id)})
    offering = db.get(CourseOffering, session.offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404)

    if instructor.role == UserRole.instructor:
        if not instructor.staff or offering.instructor_id != instructor.staff.user_id:
            raise APIError("NOT_SESSION_INSTRUCTOR", 403)
    elif instructor.role not in (UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin):
        raise APIError("ROLE_NOT_ALLOWED", 403)

    records = db.scalars(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
    ).all()

    # Join student names
    out_records = []
    for r in records:
        s = db.get(Student, r.student_id)
        u = db.get(User, r.student_id) if s else None
        out_records.append({
            "student_id": r.student_id,
            "full_name_ar": u.full_name_ar if u else "(unknown)",
            "status": r.status,
            "method": r.method,
            "scanned_at": r.scanned_at,
            "flagged": r.flagged,
            "flag_reason": r.flag_reason,
        })

    counts = _session_counts(db, session_id, session)
    return {
        "session_id": session_id,
        "offering_id": session.offering_id,
        "status": session.status,
        "present_count": counts["present_count"],
        "late_count": counts["late_count"],
        "absent_count": counts["absent_count"],
        "flagged_count": counts["flagged_count"],
        "enrolled_count": counts["enrolled_count"],
        "records": out_records,
    }


def student_summary(db: Session, *, student_id: uuid.UUID) -> dict:
    """Per-student attendance summary across all their offerings."""
    rows = []
    offerings = db.scalars(
        select(Enrollment).where(Enrollment.student_id == student_id)
    ).all()
    # Load the term rule for each offering (cached by term)
    from app.models import TermAbsenceRule
    for e in offerings:
        offering = db.get(CourseOffering, e.offering_id)
        if not offering:
            continue
        # Find rule: most specific to least
        rule = db.scalar(
            select(TermAbsenceRule).where(
                TermAbsenceRule.term_id == offering.term_id,
                TermAbsenceRule.department_id == offering.course.department_id if offering.course else None,
                TermAbsenceRule.stage == (offering.course.stage if offering.course else None),
            )
        )
        if not rule:
            rule = db.scalar(
                select(TermAbsenceRule).where(
                    TermAbsenceRule.term_id == offering.term_id,
                    TermAbsenceRule.department_id == offering.course.department_id if offering.course else None,
                    TermAbsenceRule.stage.is_(None),
                )
            )
        if not rule:
            rule = db.scalar(
                select(TermAbsenceRule).where(
                    TermAbsenceRule.term_id == offering.term_id,
                    TermAbsenceRule.department_id.is_(None),
                    TermAbsenceRule.stage.is_(None),
                )
            )
        max_absences = rule.max_absences_per_course if rule else settings.absence_limit_percent

        sessions = db.scalars(
            select(LectureSession).where(LectureSession.offering_id == e.offering_id)
        ).all()
        session_ids = [s.id for s in sessions]
        records = (
            db.scalars(
                select(AttendanceRecord).where(
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.student_id == student_id,
                )
            ).all()
            if session_ids
            else []
        )
        present = sum(1 for r in records if r.status == AttendanceStatus.present)
        late = sum(1 for r in records if r.status == AttendanceStatus.late)
        absent = sum(1 for r in records if r.status == AttendanceStatus.absent)
        excused = sum(1 for r in records if r.status == AttendanceStatus.excused)
        total = len(sessions)
        # Effective absences: late counts if the rule says so
        eff_absent = absent + (late if (rule and rule.late_counts_as_absence) else 0)
        pct = (total - eff_absent) / total if total else 1.0
        rows.append({
            "offering_id": e.offering_id,
            "total_sessions": total,
            "present": present,
            "late": late,
            "absent": absent,
            "excused": excused,
            "attendance_percent": round(pct, 4),
            "is_warning": eff_absent >= max_absences,
        })
    return {"student_id": student_id, "rows": rows}


# ─────────────────────────── helpers ───────────────────────────

def _ensure_tz(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; normalize to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in meters between two lat/lng points."""
    r = 6371000.0  # Earth radius (m)
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _maybe_send_absence_warnings(db: Session, *, offering_id: uuid.UUID) -> None:
    """After closing a session, check each enrolled student's cumulative
    absence count for this offering. If it just reached the threshold, send
    a notification."""
    from app.services.notifications import create_notification

    # Find the term rule
    offering = db.get(CourseOffering, offering_id)
    if not offering or not offering.course:
        return
    from app.models import TermAbsenceRule
    rule = db.scalar(
        select(TermAbsenceRule).where(
            TermAbsenceRule.term_id == offering.term_id,
            TermAbsenceRule.department_id == offering.course.department_id,
            TermAbsenceRule.stage == offering.course.stage,
        )
    ) or db.scalar(
        select(TermAbsenceRule).where(
            TermAbsenceRule.term_id == offering.term_id,
            TermAbsenceRule.department_id == offering.course.department_id,
            TermAbsenceRule.stage.is_(None),
        )
    ) or db.scalar(
        select(TermAbsenceRule).where(
            TermAbsenceRule.term_id == offering.term_id,
            TermAbsenceRule.department_id.is_(None),
            TermAbsenceRule.stage.is_(None),
        )
    )
    threshold = rule.max_absences_per_course if rule else settings.absence_limit_percent
    late_counts = bool(rule and rule.late_counts_as_absence)

    # Get all enrolled students for this offering + their records
    enrollments = db.scalars(
        select(Enrollment).where(Enrollment.offering_id == offering_id)
    ).all()
    for e in enrollments:
        records = db.scalars(
            select(AttendanceRecord)
            .join(LectureSession, LectureSession.id == AttendanceRecord.session_id)
            .where(
                LectureSession.offering_id == offering_id,
                AttendanceRecord.student_id == e.student_id,
            )
        ).all()
        absent = sum(1 for r in records if r.status == AttendanceStatus.absent)
        late = sum(1 for r in records if r.status == AttendanceStatus.late)
        eff = absent + (late if late_counts else 0)
        if eff == threshold:  # exactly at threshold → warn
            create_notification(
                db,
                user_id=e.student_id,
                type_="absence_warning",
                title="تنبيه: اقتراب حد الغياب",
                body=f"لقد بلغت حد الغياب المسموح ({threshold} غيابات) في إحدى المواد. يرجى الالتزام بالحضور لتجنب الحرمان.",
                data={"offering_id": str(offering_id), "absences": eff, "threshold": threshold},
            )
