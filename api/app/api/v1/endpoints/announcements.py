"""Announcements + notifications + public news endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.rbac import (
    assert_in_same_department,
    get_current_user,
    require_instructor_or_higher,
)
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import (
    Announcement,
    AnnouncementRead,
    AnnouncementScope,
    Enrollment,
    Notification,
    User,
    UserRole,
)
from app.schemas.features import (
    AnnouncementCreate,
    AnnouncementOut,
    NotificationListResponse,
    NotificationOut,
    PublicNewsOut,
)
from app.services.audit import write_audit
from app.services.notifications import (
    broadcast_notification,
    resolve_announcement_audience,
)

router = APIRouter()


# ── GET /announcements — list visible to caller ──
@router.get("", response_model=list[AnnouncementOut])
async def list_announcements(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Announcements visible to the caller based on their role and group/stage/dept."""
    now = datetime.now(timezone.utc)

    # Build visibility clause
    clauses = [Announcement.scope == AnnouncementScope.college]
    if user.student:
        dept_id = user.student.department_id
        stage = user.student.stage
        group_id = user.student.group_id
        clauses.append(
            (Announcement.scope == AnnouncementScope.department)
            & (Announcement.scope_id == str(dept_id))
        )
        clauses.append(
            (Announcement.scope == AnnouncementScope.stage)
            & (Announcement.scope_id == f"{dept_id}:{stage}")
        )
        if group_id:
            clauses.append(
                (Announcement.scope == AnnouncementScope.group)
                & (Announcement.scope_id == str(group_id))
            )
        # offerings the student is enrolled in
        enrolled_offerings = db.scalars(
            select(Enrollment.offering_id).where(Enrollment.student_id == user.id)
        ).all()
        if enrolled_offerings:
            clauses.append(
                (Announcement.scope == AnnouncementScope.offering)
                & (Announcement.scope_id.in_([str(o) for o in enrolled_offerings]))
            )
    elif user.staff:
        if user.staff.department_id:
            dept_id = user.staff.department_id
            clauses.append(
                (Announcement.scope == AnnouncementScope.department)
                & (Announcement.scope_id == str(dept_id))
            )
        # Instructor sees announcements for their offerings
        from app.models import CourseOffering
        my_offerings = db.scalars(
            select(CourseOffering.id).where(CourseOffering.instructor_id == user.id)
        ).all()
        if my_offerings:
            clauses.append(
                (Announcement.scope == AnnouncementScope.offering)
                & (Announcement.scope_id.in_([str(o) for o in my_offerings]))
            )

    q = (
        select(Announcement)
        .where(or_(*clauses))
        .where(
            or_(Announcement.publish_at.is_(None), Announcement.publish_at <= now)
        )
        .where(or_(Announcement.expires_at.is_(None), Announcement.expires_at > now))
        .order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = db.scalars(q).all()

    # Mark read status for caller
    out: list[AnnouncementOut] = []
    if items:
        read_ids = set(
            db.scalars(
                select(AnnouncementRead.announcement_id).where(AnnouncementRead.user_id == user.id)
            ).all()
        )
        for a in items:
            ao = AnnouncementOut.model_validate(a)
            ao.is_read = a.id in read_ids
            out.append(ao)
    return out


# ── POST /announcements — create ──
@router.post("", response_model=AnnouncementOut, status_code=201)
async def create_announcement(
    payload: AnnouncementCreate,
    creator: User = Depends(require_instructor_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Create an announcement. Scope rules:
    - instructor: only offering-scope, for their own offerings
    - dept_admin: department / stage / group / offering within their dept
    - college_admin / system_admin: any scope
    """
    # Validate scope ownership
    if creator.role == UserRole.instructor:
        if payload.scope != AnnouncementScope.offering:
            raise APIError("OUT_OF_SCOPE", 403, {"reason": "instructors can only publish to their own offerings"})
        offering_id = uuid.UUID(payload.scope_id) if payload.scope_id else None
        if offering_id:
            from app.models import CourseOffering
            off = db.get(CourseOffering, offering_id)
            if not off or off.instructor_id != creator.id:
                raise APIError("OUT_OF_SCOPE", 403, {"reason": "not the instructor of this offering"})
    elif creator.role == UserRole.dept_admin:
        if payload.scope == AnnouncementScope.department:
            assert_in_same_department(creator, uuid.UUID(payload.scope_id))
        elif payload.scope == AnnouncementScope.stage:
            dept_str, _ = (payload.scope_id or "").split(":")
            assert_in_same_department(creator, uuid.UUID(dept_str))
        elif payload.scope == AnnouncementScope.group:
            from app.models import Group
            g = db.get(Group, uuid.UUID(payload.scope_id))
            if g:
                assert_in_same_department(creator, g.department_id)
        elif payload.scope == AnnouncementScope.offering:
            from app.models import CourseOffering
            off = db.get(CourseOffering, uuid.UUID(payload.scope_id))
            if off and off.course:
                assert_in_same_department(creator, off.course.department_id)

    ann = Announcement(
        scope=payload.scope,
        scope_id=payload.scope_id,
        title=payload.title,
        body=payload.body,
        priority=payload.priority,
        pinned=payload.pinned,
        publish_at=payload.publish_at,
        expires_at=payload.expires_at,
        created_by=creator.id,
    )
    db.add(ann)
    db.flush()
    write_audit(db, actor_id=creator.id, action="create_announcement",
                entity="announcement", entity_id=str(ann.id),
                after={"scope": ann.scope.value, "title": ann.title}, request=request)

    # Resolve audience + broadcast notification
    audience = resolve_announcement_audience(db, ann)
    broadcast_notification(
        db,
        user_ids=audience,
        type_="announcement",
        title=ann.title,
        body=ann.body[:200] if ann.body else None,
        data={"announcement_id": str(ann.id), "scope": ann.scope.value},
    )
    db.commit()
    db.refresh(ann)
    return AnnouncementOut.model_validate(ann)


# ── POST /announcements/{id}/read ──
@router.post("/{announcement_id}/read")
async def mark_announcement_read(
    announcement_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ann = db.get(Announcement, announcement_id)
    if not ann:
        raise APIError("NOT_FOUND", 404, {"announcement_id": str(announcement_id)})
    existing = db.scalar(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == user.id,
        )
    )
    if not existing:
        db.add(AnnouncementRead(announcement_id=announcement_id, user_id=user.id))
        db.commit()
    return {"ok": True}


# ─────────────────────────── public news (no auth) ───────────────────────────
public_router = APIRouter()


@public_router.get("/news", response_model=list[PublicNewsOut])
async def public_news(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Public news: college-scope announcements only, no auth required."""
    now = datetime.now(timezone.utc)
    q = (
        select(Announcement)
        .where(Announcement.scope == AnnouncementScope.college)
        .where(
            or_(Announcement.publish_at.is_(None), Announcement.publish_at <= now)
        )
        .where(or_(Announcement.expires_at.is_(None), Announcement.expires_at > now))
        .order_by(Announcement.pinned.desc(), Announcement.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = db.scalars(q).all()
    return [PublicNewsOut.model_validate(a) for a in items]


# ─────────────────────────── notifications ───────────────────────────
notifications_router = APIRouter()


@notifications_router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        q = q.where(Notification.read_at.is_(None))
    q = q.order_by(Notification.created_at.desc())
    total_q = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        total_q = total_q.where(Notification.read_at.is_(None))
    total = len(db.scalars(total_q).all())
    unread = len(db.scalars(
        select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ).all())
    items = db.scalars(q.offset((page - 1) * limit).limit(limit)).all()
    return NotificationListResponse(
        items=[NotificationOut.model_validate(n) for n in items],
        total=total,
        unread=unread,
    )


@notifications_router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.read_at.is_(None)
    ).update({"read_at": datetime.now(timezone.utc)})
    db.commit()
    return {"ok": True}


@notifications_router.post("/{notification_id}/read")
async def mark_one_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise APIError("NOT_FOUND", 404, {"notification_id": str(notification_id)})
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.commit()
    return {"ok": True}
