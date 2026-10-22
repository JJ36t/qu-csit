"""Timetable conflict detection.

Per brief §5.3: creating/editing a slot must reject conflicts for the same
instructor, same room, or same group at overlapping times.
"""
from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.i18n.errors_ar import APIError
from app.models import CourseOffering, TimetableSlot


def _overlap(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """True if [a_start, a_end) overlaps [b_start, b_end)."""
    return a_start < b_end and b_start < a_end


def check_slot_conflicts(
    db: Session,
    *,
    offering_id: uuid.UUID,
    weekday: int,
    start_time: time,
    end_time: time,
    room_id: uuid.UUID | None,
    exclude_slot_id: uuid.UUID | None = None,
) -> None:
    """Raise APIError with SLOT_CONFLICT_* code if any conflict exists.

    Conflicts checked:
    - same instructor in another offering at overlapping time on same weekday
    - same room at overlapping time
    - same group at overlapping time
    """
    offering = db.get(CourseOffering, offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404, {"offering_id": str(offering_id)})

    # All slots on the same weekday for the same term
    q = (
        select(TimetableSlot, CourseOffering)
        .join(CourseOffering, CourseOffering.id == TimetableSlot.offering_id)
        .where(
            TimetableSlot.weekday == weekday,
            CourseOffering.term_id == offering.term_id,
        )
    )
    if exclude_slot_id is not None:
        q = q.where(TimetableSlot.id != exclude_slot_id)
    rows = db.execute(q).all()

    for slot, other_offering in rows:
        if not _overlap(start_time, end_time, slot.start_time, slot.end_time):
            continue

        # Same instructor?
        if (
            offering.instructor_id
            and other_offering.instructor_id == offering.instructor_id
        ):
            raise APIError(
                "SLOT_CONFLICT_INSTRUCTOR",
                409,
                {
                    "conflict_with_slot_id": str(slot.id),
                    "offering_id": str(other_offering.id),
                    "weekday": weekday,
                    "start_time": slot.start_time.isoformat(),
                    "end_time": slot.end_time.isoformat(),
                },
            )

        # Same room?
        if room_id and slot.room_id == room_id:
            raise APIError(
                "SLOT_CONFLICT_ROOM",
                409,
                {
                    "conflict_with_slot_id": str(slot.id),
                    "offering_id": str(other_offering.id),
                    "room_id": str(room_id),
                },
            )

        # Same group?
        if other_offering.group_id == offering.group_id:
            raise APIError(
                "SLOT_CONFLICT_GROUP",
                409,
                {
                    "conflict_with_slot_id": str(slot.id),
                    "offering_id": str(other_offering.id),
                    "group_id": str(other_offering.group_id),
                },
            )
