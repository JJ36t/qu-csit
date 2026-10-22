"""Timetable endpoints — student/instructor view + admin CRUD.

Brief §6:
- GET /timetable?from=&to=  — student/instructor
- GET /timetable/changes    — student/instructor
- POST/PATCH/DELETE /admin/timetable (slot CRUD with conflict detection)
- POST /admin/timetable/changes (cancel/move/extra, with notification hook)
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import (
    assert_in_same_department,
    get_current_user,
    require_dept_admin_or_higher,
)
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import (
    CourseOffering,
    Enrollment,
    TimetableChange,
    TimetableSlot,
    User,
    UserRole,
)
from app.models.enums import TimetableChangeType
from app.schemas.features import (
    TimetableChangeCreate,
    TimetableChangeOut,
    TimetableEntry,
    TimetableResponse,
    TimetableSlotCreate,
    TimetableSlotOut,
    TimetableSlotUpdate,
)
from app.services.audit import write_audit
from app.services.notifications import broadcast_notification
from app.services.timetable import check_slot_conflicts

router = APIRouter()


# ── Student/instructor: GET /timetable ──
@router.get("", response_model=list[TimetableResponse])
async def get_my_timetable(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the caller's weekly timetable between [from, to] (default: today + 7 days)."""
    if not from_date:
        from_date = date.today()
    if not to_date:
        to_date = from_date + timedelta(days=7)
    if to_date < from_date:
        raise APIError("VALIDATION_ERROR", 400, {"from": "must be <= to"})

    # Resolve offerings the user can see
    offering_ids: list[uuid.UUID] = []
    if user.role == UserRole.student and user.student:
        offering_ids = [
            o.id
            for o in db.scalars(
                select(CourseOffering).join(Enrollment, Enrollment.offering_id == CourseOffering.id).where(
                    Enrollment.student_id == user.id, Enrollment.status == "active"
                )
            ).all()
        ]
    elif user.role == UserRole.instructor and user.staff:
        offering_ids = [
            o.id
            for o in db.scalars(
                select(CourseOffering).where(CourseOffering.instructor_id == user.id)
            ).all()
        ]
    elif user.role in (UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin):
        # Admins see all offerings in their scope; for simplicity return all in current term
        offering_ids = [
            o.id for o in db.scalars(select(CourseOffering)).all()
        ]

    if not offering_ids:
        return []

    # Slots for those offerings
    slots = db.scalars(
        select(TimetableSlot).where(TimetableSlot.offering_id.in_(offering_ids))
    ).all()
    if not slots:
        return []

    # Changes for those slots in [from, to]
    slot_ids = [s.id for s in slots]
    changes = db.scalars(
        select(TimetableChange)
        .where(TimetableChange.slot_id.in_(slot_ids), TimetableChange.date >= from_date, TimetableChange.date <= to_date)
    ).all()
    changes_by_date_slot: dict[tuple[date, uuid.UUID], list[TimetableChange]] = {}
    for c in changes:
        changes_by_date_slot.setdefault((c.date, c.slot_id), []).append(c)

    # Build response: one entry per date in [from, to] that has a matching slot weekday
    out: list[TimetableResponse] = []
    cur = from_date
    while cur <= to_date:
        python_weekday = cur.weekday()
        slot_weekday_sun0 = (python_weekday + 1) % 7  # Mon=0 → Sun=0
        day_slots = [s for s in slots if s.weekday == slot_weekday_sun0]
        if not day_slots:
            cur += timedelta(days=1)
            continue
        entries: list[TimetableEntry] = []
        for s in day_slots:
            day_changes = changes_by_date_slot.get((cur, s.id), [])
            cancelled = any(c.type == TimetableChangeType.cancel for c in day_changes)
            move = next((c for c in day_changes if c.type == TimetableChangeType.move), None)
            entries.append(
                TimetableEntry(
                    slot=TimetableSlotOut.model_validate(s),
                    changes=[TimetableChangeOut.model_validate(c) for c in day_changes],
                    effective_start=move.new_start if move and move.new_start else s.start_time,
                    effective_end=move.new_end if move and move.new_end else s.end_time,
                    effective_room_id=move.new_room_id if move and move.new_room_id else s.room_id,
                    is_cancelled=cancelled,
                )
            )
        out.append(TimetableResponse(date=cur, entries=entries))
        cur += timedelta(days=1)
    return out


@router.get("/changes", response_model=list[TimetableChangeOut])
async def get_my_timetable_changes(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return dated timetable changes that affect the caller."""
    if not from_date:
        from_date = date.today()
    if not to_date:
        to_date = from_date + timedelta(days=30)

    # Resolve offerings
    offering_ids: list[uuid.UUID] = []
    if user.role == UserRole.student and user.student:
        offering_ids = [
            o.id
            for o in db.scalars(
                select(CourseOffering).join(Enrollment, Enrollment.offering_id == CourseOffering.id).where(
                    Enrollment.student_id == user.id
                )
            ).all()
        ]
    elif user.role == UserRole.instructor and user.staff:
        offering_ids = [
            o.id for o in db.scalars(select(CourseOffering).where(CourseOffering.instructor_id == user.id)).all()
        ]
    else:
        offering_ids = [o.id for o in db.scalars(select(CourseOffering)).all()]

    if not offering_ids:
        return []

    slot_ids = [
        s.id for s in db.scalars(select(TimetableSlot).where(TimetableSlot.offering_id.in_(offering_ids))).all()
    ]
    if not slot_ids:
        return []

    changes = db.scalars(
        select(TimetableChange)
        .where(TimetableChange.slot_id.in_(slot_ids), TimetableChange.date >= from_date, TimetableChange.date <= to_date)
        .order_by(TimetableChange.date)
    ).all()
    return [TimetableChangeOut.model_validate(c) for c in changes]


# ─────────────────────────── admin: slot CRUD ───────────────────────────
admin_router = APIRouter()


@admin_router.post("", response_model=TimetableSlotOut, status_code=201)
async def create_slot(
    payload: TimetableSlotCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    offering = db.get(CourseOffering, payload.offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404, {"offering_id": str(payload.offering_id)})

    # Scope: dept_admin can only edit slots for offerings in their dept
    course = offering.course
    if course:
        assert_in_same_department(admin, course.department_id)

    check_slot_conflicts(
        db,
        offering_id=payload.offering_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        room_id=payload.room_id,
    )
    slot = TimetableSlot(
        offering_id=payload.offering_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        room_id=payload.room_id,
        kind=payload.kind,
    )
    db.add(slot)
    db.flush()
    write_audit(
        db,
        actor_id=admin.id,
        action="create_slot",
        entity="timetable_slot",
        entity_id=str(slot.id),
        after={"offering_id": str(slot.offering_id), "weekday": slot.weekday, "start": slot.start_time.isoformat()},
        request=request,
    )
    db.commit()
    db.refresh(slot)
    return TimetableSlotOut.model_validate(slot)


@admin_router.patch("/{slot_id}", response_model=TimetableSlotOut)
async def update_slot(
    slot_id: uuid.UUID,
    payload: TimetableSlotUpdate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    slot = db.get(TimetableSlot, slot_id)
    if not slot:
        raise APIError("NOT_FOUND", 404, {"slot_id": str(slot_id)})

    offering = db.get(CourseOffering, slot.offering_id)
    course = offering.course if offering else None
    if course:
        assert_in_same_department(admin, course.department_id)

    new_weekday = payload.weekday if payload.weekday is not None else slot.weekday
    new_start = payload.start_time if payload.start_time is not None else slot.start_time
    new_end = payload.end_time if payload.end_time is not None else slot.end_time
    new_room = payload.room_id if payload.room_id is not None else slot.room_id
    if new_start >= new_end:
        raise APIError("VALIDATION_ERROR", 400, {"end_time": "must be after start_time"})

    check_slot_conflicts(
        db,
        offering_id=slot.offering_id,
        weekday=new_weekday,
        start_time=new_start,
        end_time=new_end,
        room_id=new_room,
        exclude_slot_id=slot.id,
    )
    before = {
        "weekday": slot.weekday, "start": slot.start_time.isoformat(),
        "end": slot.end_time.isoformat(), "room_id": str(slot.room_id) if slot.room_id else None,
    }
    slot.weekday = new_weekday
    slot.start_time = new_start
    slot.end_time = new_end
    slot.room_id = new_room
    if payload.kind is not None:
        slot.kind = payload.kind
    write_audit(
        db, actor_id=admin.id, action="update_slot", entity="timetable_slot",
        entity_id=str(slot.id), before=before,
        after={"weekday": new_weekday, "start": new_start.isoformat(), "end": new_end.isoformat()},
        request=request,
    )
    db.commit()
    db.refresh(slot)
    return TimetableSlotOut.model_validate(slot)


@admin_router.delete("/{slot_id}")
async def delete_slot(
    slot_id: uuid.UUID,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    slot = db.get(TimetableSlot, slot_id)
    if not slot:
        raise APIError("NOT_FOUND", 404, {"slot_id": str(slot_id)})
    offering = db.get(CourseOffering, slot.offering_id)
    course = offering.course if offering else None
    if course:
        assert_in_same_department(admin, course.department_id)
    db.delete(slot)
    write_audit(db, actor_id=admin.id, action="delete_slot", entity="timetable_slot",
                entity_id=str(slot_id), request=request)
    db.commit()
    return {"ok": True}


# ─────────────────────────── admin: changes ───────────────────────────
@admin_router.post("/changes", response_model=TimetableChangeOut, status_code=201)
async def create_change(
    payload: TimetableChangeCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    slot = db.get(TimetableSlot, payload.slot_id)
    if not slot:
        raise APIError("NOT_FOUND", 404, {"slot_id": str(payload.slot_id)})
    offering = db.get(CourseOffering, slot.offering_id)
    course = offering.course if offering else None
    if course:
        assert_in_same_department(admin, course.department_id)

    change = TimetableChange(
        slot_id=slot.id,
        date=payload.date,
        type=payload.type,
        new_start=payload.new_start,
        new_end=payload.new_end,
        new_room_id=payload.new_room_id,
        reason=payload.reason,
        created_by=admin.id,
    )
    db.add(change)
    db.flush()
    write_audit(db, actor_id=admin.id, action="create_timetable_change",
                entity="timetable_change", entity_id=str(change.id),
                after={"date": change.date.isoformat(), "type": change.type.value},
                request=request)

    # Notify enrolled students + instructor
    from app.services.notifications import resolve_announcement_audience
    from app.models import Announcement, AnnouncementScope
    fake_announcement = Announcement(
        scope=AnnouncementScope.offering,
        scope_id=str(offering.id),
        title="", body="",
    )  # re-use audience resolver
    audience = resolve_announcement_audience(db, fake_announcement)
    title = "تعديل في الجدول"
    body = f"تم تعديل حصة بتاريخ {payload.date.isoformat()}"
    if payload.type == TimetableChangeType.cancel:
        body = f"تم إلغاء حصة بتاريخ {payload.date.isoformat()}"
    elif payload.type == TimetableChangeType.extra:
        body = f"تمت إضافة حصة استثنائية بتاريخ {payload.date.isoformat()}"
    if payload.reason:
        body += f" — {payload.reason}"
    broadcast_notification(
        db,
        user_ids=audience,
        type_="timetable_change",
        title=title,
        body=body,
        data={"offering_id": str(offering.id), "date": payload.date.isoformat(), "change_type": payload.type.value},
    )
    db.commit()
    db.refresh(change)
    return TimetableChangeOut.model_validate(change)


_ = Any  # silence unused import
