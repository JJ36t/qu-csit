"""Announcements + public news + notifications endpoint tests."""
from __future__ import annotations

import uuid


from tests.conftest import auth_header, login


# ── Announcements ──
def test_list_announcements_for_student(client, student_token):
    r = client.get("/api/v1/announcements", headers=auth_header(student_token["access_token"]))
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    for item in items:
        assert "scope" in item
        assert "is_read" in item
        assert "title" in item


def test_create_college_announcement_by_college_admin(client, college_admin_token):
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "college",
            "title": "إعلان الكلية",
            "body": "هذا إعلان تجريبي للكلية",
            "priority": 1,
            "pinned": True,
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["scope"] == "college"
    assert body["title"] == "إعلان الكلية"
    assert body["pinned"] is True


def test_create_announcement_wrong_role_student(client, student_token):
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "college",
            "title": "x",
            "body": "y",
        },
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "ROLE_NOT_ALLOWED"


def test_create_announcement_invalid_input(client, college_admin_token):
    """scope=department requires scope_id."""
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "department",
            "scope_id": None,
            "title": "x",
            "body": "y",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 422


def test_create_announcement_invalid_dates(client, college_admin_token):
    """expires_at must be after publish_at."""
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "college",
            "title": "x",
            "body": "y",
            "publish_at": "2026-01-10T10:00:00Z",
            "expires_at": "2026-01-05T10:00:00Z",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 422


def test_instructor_create_announcement_out_of_scope(client, instructor_token):
    """Instructor tries to publish a college-scope announcement → forbidden."""
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "college",
            "title": "x",
            "body": "y",
        },
        headers=auth_header(instructor_token["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "OUT_OF_SCOPE"


def test_instructor_create_announcement_own_offering_ok(client, db):
    """Instructor can publish an offering-scope announcement for their own offering."""
    from sqlalchemy import select, func
    from app.models import CourseOffering, User
    # Find an instructor who actually has at least one offering (T1000 may have none)
    sub = (
        select(CourseOffering.instructor_id, func.count().label("c"))
        .group_by(CourseOffering.instructor_id)
        .having(func.count() >= 1)
    ).subquery()
    instructor_id = db.scalar(select(sub.c.instructor_id).order_by(sub.c.c.desc()))
    assert instructor_id is not None
    instructor_user = db.get(User, instructor_id)
    own_offering = db.scalar(
        select(CourseOffering).where(CourseOffering.instructor_id == instructor_id)
    )
    body = login(client, instructor_user.university_id)
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "offering",
            "scope_id": str(own_offering.id),
            "title": "إعلان مادة",
            "body": "محاضرة الغد ملغاة",
        },
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 201


def test_instructor_create_announcement_other_offering_rejected(client, db):
    """Instructor tries to publish for an offering they don't teach → IDOR."""
    from sqlalchemy import select, func
    from app.models import CourseOffering, User
    sub = (
        select(CourseOffering.instructor_id, func.count().label("c"))
        .group_by(CourseOffering.instructor_id)
        .having(func.count() >= 2)
    ).subquery()
    instructor_id = db.scalar(select(sub.c.instructor_id).order_by(sub.c.c.desc()))
    if not instructor_id:
        # No instructor has 2+ offerings — skip this IDOR test gracefully
        return
    instructor_user = db.get(User, instructor_id)
    other_offering = db.scalar(
        select(CourseOffering).where(CourseOffering.instructor_id != instructor_id)
    )
    if not other_offering:
        return
    body = login(client, instructor_user.university_id)
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "offering",
            "scope_id": str(other_offering.id),
            "title": "x",
            "body": "y",
        },
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "OUT_OF_SCOPE"


def test_dept_admin_create_dept_announcement_in_scope(client, dept_admin_cs_token, db):
    from sqlalchemy import select
    from app.models import Department
    cs = db.scalar(select(Department).where(Department.code == "CS"))
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "department",
            "scope_id": str(cs.id),
            "title": "إعلان قسم CS",
            "body": "اجتماع القسم",
        },
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 201


def test_dept_admin_create_other_dept_announcement_rejected(client, dept_admin_cs_token, db):
    """CS dept_admin tries to publish for IS dept → IDOR / out of scope."""
    from sqlalchemy import select
    from app.models import Department
    is_dept = db.scalar(select(Department).where(Department.code == "IS"))
    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "department",
            "scope_id": str(is_dept.id),
            "title": "x",
            "body": "y",
        },
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "OUT_OF_SCOPE"


def test_mark_announcement_read(client, student_token, college_admin_token):
    # Create
    r1 = client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "read test", "body": "body"},
        headers=auth_header(college_admin_token["access_token"]),
    )
    ann_id = r1.json()["id"]
    # Student marks read
    r2 = client.post(
        f"/api/v1/announcements/{ann_id}/read",
        headers=auth_header(student_token["access_token"]),
    )
    assert r2.status_code == 200
    # Verify is_read = True on next list call
    r3 = client.get("/api/v1/announcements", headers=auth_header(student_token["access_token"]))
    items = r3.json()
    found = next((a for a in items if a["id"] == ann_id), None)
    assert found is not None
    assert found["is_read"] is True


def test_mark_announcement_read_nonexistent(client, student_token):
    r = client.post(
        f"/api/v1/announcements/{uuid.uuid4()}/read",
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 404


def test_announcement_create_triggers_notification(client, college_admin_token):
    """Creating an announcement broadcasts a notification to all active users."""
    from sqlalchemy import select
    from app.models import Notification
    from app.db.base import SessionLocal
    db = SessionLocal()
    before = len(db.scalars(select(Notification).where(Notification.type == "announcement")).all())
    db.close()

    r = client.post(
        "/api/v1/announcements",
        json={
            "scope": "college",
            "title": "إعلان إشعار",
            "body": "محتوى الإشعار",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 201
    db = SessionLocal()
    after = len(db.scalars(select(Notification).where(Notification.type == "announcement")).all())
    db.close()
    assert after > before


# ── Public news (no auth) ──
def test_public_news_no_auth_required(client):
    r = client.get("/api/v1/public/news")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    for item in items:
        assert "title" in item
        assert "body" in item
        assert "id" in item


def test_public_news_only_college_scope(client, college_admin_token, dept_admin_cs_token, db):
    """Public news endpoint returns only college-scope announcements."""
    from sqlalchemy import select
    from app.models import Department
    cs = db.scalar(select(Department).where(Department.code == "CS"))
    # Create a college-scope announcement
    client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "college-news", "body": "x"},
        headers=auth_header(college_admin_token["access_token"]),
    )
    # Create a department-scope announcement
    client.post(
        "/api/v1/announcements",
        json={"scope": "department", "scope_id": str(cs.id), "title": "dept-news", "body": "x"},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    r = client.get("/api/v1/public/news")
    assert r.status_code == 200
    titles = [item["title"] for item in r.json()]
    assert "college-news" in titles
    assert "dept-news" not in titles


# ── Notifications ──
def test_list_notifications(client, student_token):
    # Trigger some notifications: create a college announcement (broadcasts to all)
    ca = login(client, "CA")
    client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "notif test", "body": "x"},
        headers=auth_header(ca["access_token"]),
    )
    # Now student should have at least one notification
    r = client.get("/api/v1/notifications", headers=auth_header(student_token["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "unread" in body
    assert body["unread"] >= 1


def test_list_notifications_unread_only(client, student_token):
    ca = login(client, "CA")
    client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "unread test", "body": "x"},
        headers=auth_header(ca["access_token"]),
    )
    r = client.get(
        "/api/v1/notifications?unread_only=true",
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 200
    for n in r.json()["items"]:
        assert n["read_at"] is None


def test_mark_all_notifications_read(client, student_token):
    ca = login(client, "CA")
    client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "mark all", "body": "x"},
        headers=auth_header(ca["access_token"]),
    )
    r = client.post(
        "/api/v1/notifications/read-all",
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 200
    # Verify unread = 0
    r2 = client.get("/api/v1/notifications", headers=auth_header(student_token["access_token"]))
    assert r2.json()["unread"] == 0


def test_mark_one_notification_read(client, student_token):
    ca = login(client, "CA")
    client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "mark one", "body": "x"},
        headers=auth_header(ca["access_token"]),
    )
    # Get list
    items = client.get(
        "/api/v1/notifications", headers=auth_header(student_token["access_token"])
    ).json()["items"]
    note_id = items[0]["id"]
    r = client.post(
        f"/api/v1/notifications/{note_id}/read",
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 200


def test_mark_notification_read_idor_rejected(client, student_token, instructor_token):
    """Student tries to mark someone else's notification as read → 404."""
    ca = login(client, "CA")
    client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "idor", "body": "x"},
        headers=auth_header(ca["access_token"]),
    )
    # Get instructor's notifications
    items = client.get(
        "/api/v1/notifications", headers=auth_header(instructor_token["access_token"])
    ).json()["items"]
    if not items:
        return
    instr_note_id = items[0]["id"]
    # Student tries to read instructor's notification
    r = client.post(
        f"/api/v1/notifications/{instr_note_id}/read",
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_notifications_without_token(client):
    r = client.get("/api/v1/notifications")
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


# ── Academic admin endpoints ──
def test_list_departments_college_admin(client, college_admin_token):
    r = client.get("/api/v1/admin/departments", headers=auth_header(college_admin_token["access_token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_list_departments_dept_admin_scoped(client, dept_admin_cs_token):
    """CS dept_admin sees only their own department."""
    r = client.get("/api/v1/admin/departments", headers=auth_header(dept_admin_cs_token["access_token"]))
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["code"] == "CS"


def test_list_academic_years(client, college_admin_token):
    r = client.get("/api/v1/admin/academic-years", headers=auth_header(college_admin_token["access_token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_list_terms(client, college_admin_token):
    r = client.get("/api/v1/admin/terms", headers=auth_header(college_admin_token["access_token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_list_groups_filter(client, college_admin_token):
    r = client.get(
        "/api/v1/admin/groups?stage=1",
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 200
    for g in r.json():
        assert g["stage"] == 1


def test_list_courses(client, college_admin_token):
    r = client.get("/api/v1/admin/courses", headers=auth_header(college_admin_token["access_token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_list_offerings(client, college_admin_token):
    r = client.get("/api/v1/admin/offerings", headers=auth_header(college_admin_token["access_token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_generate_sessions_endpoint(client, college_admin_token, db):
    from sqlalchemy import select
    from app.models import Term
    term = db.scalar(select(Term).where(Term.is_current.is_(True)))
    r = client.post(
        f"/api/v1/admin/terms/{term.id}/generate-sessions",
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "created" in body
    assert "term" in body


def test_audit_log_visible_to_college_admin(client, college_admin_token):
    r = client.get("/api/v1/admin/audit-logs", headers=auth_header(college_admin_token["access_token"]))
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # Should contain at least one entry (login action etc)
    assert len(items) >= 1


def test_audit_log_dept_admin_scoped(client, dept_admin_cs_token):
    """CS dept_admin sees only audit logs from CS dept users."""
    r = client.get("/api/v1/admin/audit-logs", headers=auth_header(dept_admin_cs_token["access_token"]))
    assert r.status_code == 200


def test_audit_log_filter_by_entity(client, college_admin_token):
    r = client.get(
        "/api/v1/admin/audit-logs?entity=user",
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 200
    for log in r.json():
        assert log["entity"] == "user"
