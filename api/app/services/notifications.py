"""Notification + announcement audience resolution.

Brief §5.4:
- Announcement targets: college / department / stage / group / offering.
  Audience is resolved server-side.
- Every remote notification is BOTH stored in the `notifications` inbox
  AND sent via FCM (background job). If FCM credentials are unset the
  notification is still stored; the FCM send is a no-op.
"""
from __future__ import annotations

import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Announcement,
    Enrollment,
    Notification,
    Student,
    User,
)
from app.models.enums import AnnouncementScope


def resolve_announcement_audience(
    db: Session, announcement: Announcement
) -> list[uuid.UUID]:
    """Return user_ids who should see this announcement."""
    scope = announcement.scope
    sid = announcement.scope_id

    if scope == AnnouncementScope.college:
        # All active students + staff
        rows = db.scalars(
            select(User.id).where(User.status == "active")
        ).all()
        return list(rows)

    if scope == AnnouncementScope.department:
        if not sid:
            return []
        dept_id = uuid.UUID(sid)
        # Students in this department
        s_rows = db.scalars(
            select(Student.user_id).where(Student.department_id == dept_id)
        ).all()
        # Staff in this department
        from app.models import Staff
        st_rows = db.scalars(
            select(Staff.user_id).where(Staff.department_id == dept_id)
        ).all()
        return list(s_rows) + list(st_rows)

    if scope == AnnouncementScope.stage:
        if not sid:
            return []
        # sid format: "<department_id>:<stage>"
        try:
            dept_id_str, stage_str = sid.split(":")
            dept_id = uuid.UUID(dept_id_str)
            stage = int(stage_str)
        except (ValueError, AttributeError):
            return []
        rows = db.scalars(
            select(Student.user_id).where(
                Student.department_id == dept_id, Student.stage == stage
            )
        ).all()
        return list(rows)

    if scope == AnnouncementScope.group:
        if not sid:
            return []
        group_id = uuid.UUID(sid)
        rows = db.scalars(
            select(Student.user_id).where(Student.group_id == group_id)
        ).all()
        return list(rows)

    if scope == AnnouncementScope.offering:
        if not sid:
            return []
        offering_id = uuid.UUID(sid)
        rows = db.scalars(
            select(Enrollment.student_id).where(Enrollment.offering_id == offering_id)
        ).all()
        # Include the instructor of the offering
        from app.models import CourseOffering
        off = db.get(CourseOffering, offering_id)
        ids: list[uuid.UUID] = list(rows)
        if off and off.instructor_id:
            ids.append(off.instructor_id)
        return ids

    return []


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    type_: str,
    title: str,
    body: str | None = None,
    data: dict | None = None,
) -> Notification:
    """Insert a notification row. Caller is responsible for committing.
    FCM send is deferred to a background job (Phase 5); for now we no-op."""
    n = Notification(
        user_id=user_id,
        type=type_,  # type: ignore[arg-type]
        title=title,
        body=body,
        data=data,
    )
    db.add(n)
    db.flush()
    return n


def broadcast_notification(
    db: Session,
    *,
    user_ids: Iterable[uuid.UUID],
    type_: str,
    title: str,
    body: str | None = None,
    data: dict | None = None,
) -> int:
    count = 0
    for uid in user_ids:
        create_notification(
            db,
            user_id=uid,
            type_=type_,
            title=title,
            body=body,
            data=data,
        )
        count += 1
    return count
