"""Materials + FCM endpoint tests — success, wrong role, IDOR, invalid input."""
from __future__ import annotations

import io
import uuid

from sqlalchemy import select, func

from app.models import (
    CourseOffering,
    File as FileModel,
    Notification,
    User,
    UserRole,
)

from tests.conftest import auth_header, login


# ── Helpers ──

def _find_instructor_with_offering(db) -> tuple[User, CourseOffering]:
    sub = (
        select(CourseOffering.instructor_id, func.count().label("c"))
        .group_by(CourseOffering.instructor_id)
        .having(func.count() >= 1)
    ).subquery()
    instr_id = db.scalar(select(sub.c.instructor_id).order_by(sub.c.c.desc()))
    user = db.get(User, instr_id)
    offering = db.scalar(select(CourseOffering).where(CourseOffering.instructor_id == instr_id))
    return user, offering


def _find_student_enrolled_in_offering(db, offering_id) -> User | None:
    from app.models import Enrollment
    sid = db.scalar(select(Enrollment.student_id).where(Enrollment.offering_id == offering_id))
    return db.get(User, sid) if sid else None


def _make_pdf_bytes(content: str = "dummy pdf content") -> bytes:
    return content.encode()


# ─────────────────────────── create material (PDF upload) ───────────────────────────

def test_create_material_pdf_success(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    pdf = _make_pdf_bytes("test pdf content")
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={
            "title": "محاضرة 1",
            "kind": "pdf",
            "week_no": 1,
            "is_published": "true",
            "description": "مقدمة",
        },
        files={"file": ("lecture1.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "محاضرة 1"
    assert data["kind"] == "pdf"
    assert data["file_id"] is not None
    assert data["is_published"] is True


def test_create_material_video_link_success(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={
            "title": "فيديو المحاضرة",
            "kind": "video_link",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "week_no": 2,
            "is_published": "true",
        },
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["kind"] == "video_link"
    assert data["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_create_material_pdf_missing_file(client, db):
    """kind=pdf requires a file."""
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "x", "kind": "pdf"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_create_material_video_link_missing_url(client, db):
    """kind=video_link requires a url."""
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "x", "kind": "video_link"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_create_material_invalid_kind(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "x", "kind": "INVALID_KIND"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_create_material_wrong_instructor(client, db):
    """Instructor A cannot upload to Instructor B's offering."""
    user, offering = _find_instructor_with_offering(db)
    other = db.scalar(select(User).where(User.role == UserRole.instructor, User.id != user.id))
    if not other:
        return
    body = login(client, other.university_id)
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "x", "kind": "video_link", "url": "https://example.com", "is_published": "false"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "NOT_SESSION_INSTRUCTOR"


def test_create_material_student_forbidden(client, db):
    """Student cannot upload materials."""
    user, offering = _find_instructor_with_offering(db)
    student = _find_student_enrolled_in_offering(db, offering.id)
    if not student:
        return
    body = login(client, student.university_id, device_fp="fp-stu-1")
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "x", "kind": "video_link", "url": "https://example.com"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "ROLE_NOT_ALLOWED"


def test_create_material_nonexistent_offering(client, db):
    user, _ = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.post(
        f"/api/v1/offerings/{uuid.uuid4()}/materials",
        data={"title": "x", "kind": "video_link", "url": "https://example.com"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 404


def test_create_material_invalid_mime(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "x", "kind": "pdf"},
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 415
    assert r.json()["code"] == "UPLOAD_TYPE_NOT_ALLOWED"


# ─────────────────────────── list materials ───────────────────────────

def test_list_materials_as_instructor(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    # Create a published material first
    client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "test", "kind": "video_link", "url": "https://example.com", "is_published": "false"},
        headers=auth_header(body["access_token"]),
    )
    r = client.get(
        f"/api/v1/offerings/{offering.id}/materials",
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 1
    # Instructor sees unpublished too
    assert any(not it["is_published"] for it in items)


def test_list_materials_as_student_only_published(client, db):
    user, offering = _find_instructor_with_offering(db)
    instr_body = login(client, user.university_id)
    # Create unpublished + published
    client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "unpublished", "kind": "video_link", "url": "https://x.com", "is_published": "false"},
        headers=auth_header(instr_body["access_token"]),
    )
    client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "published", "kind": "video_link", "url": "https://y.com", "is_published": "true"},
        headers=auth_header(instr_body["access_token"]),
    )

    # Login as student enrolled in this offering
    student = _find_student_enrolled_in_offering(db, offering.id)
    assert student is not None
    student_body = login(client, student.university_id, device_fp="fp-stu-list-1")
    r = client.get(
        f"/api/v1/offerings/{offering.id}/materials",
        headers=auth_header(student_body["access_token"]),
    )
    assert r.status_code == 200
    items = r.json()
    # Students see only published
    for it in items:
        assert it["is_published"] is True
    titles = [it["title"] for it in items]
    assert "published" in titles
    assert "unpublished" not in titles


def test_list_materials_unenrolled_student_forbidden(client, db):
    user, offering = _find_instructor_with_offering(db)
    # Find a student NOT enrolled
    from app.models import Enrollment
    enrolled_ids = set(db.scalars(
        select(Enrollment.student_id).where(Enrollment.offering_id == offering.id)
    ).all())
    all_students = db.scalars(select(User).where(User.role == UserRole.student)).all()
    unenrolled = next((u for u in all_students if u.id not in enrolled_ids), None)
    if not unenrolled:
        return
    body = login(client, unenrolled.university_id, device_fp="fp-unenr-1")
    r = client.get(
        f"/api/v1/offerings/{offering.id}/materials",
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "NOT_ENROLLED"


def test_list_materials_filter_by_week(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    # Create materials in different weeks
    for w in [1, 2, 3]:
        client.post(
            f"/api/v1/offerings/{offering.id}/materials",
            data={"title": f"w{w}", "kind": "video_link", "url": "https://x.com", "week_no": str(w), "is_published": "true"},
            headers=auth_header(body["access_token"]),
        )
    r = client.get(
        f"/api/v1/offerings/{offering.id}/materials?week_no=2",
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 200
    items = r.json()
    for it in items:
        assert it["week_no"] == 2


# ─────────────────────────── patch material ───────────────────────────

def test_patch_material_success(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    create_r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "original", "kind": "video_link", "url": "https://x.com", "is_published": "false"},
        headers=auth_header(body["access_token"]),
    )
    material_id = create_r.json()["id"]
    r = client.patch(
        f"/api/v1/materials/{material_id}",
        json={"title": "updated title", "is_published": True, "week_no": 5},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["title"] == "updated title"
    assert r.json()["is_published"] is True
    assert r.json()["week_no"] == 5


def test_patch_material_other_instructor_rejected(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    create_r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "x", "kind": "video_link", "url": "https://x.com"},
        headers=auth_header(body["access_token"]),
    )
    material_id = create_r.json()["id"]

    other = db.scalar(select(User).where(User.role == UserRole.instructor, User.id != user.id))
    if not other:
        return
    other_body = login(client, other.university_id)
    r = client.patch(
        f"/api/v1/materials/{material_id}",
        json={"title": "hacked"},
        headers=auth_header(other_body["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "NOT_SESSION_INSTRUCTOR"


def test_patch_material_nonexistent(client, db):
    user, _ = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.patch(
        f"/api/v1/materials/{uuid.uuid4()}",
        json={"title": "x"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 404


# ─────────────────────────── file download ───────────────────────────

def test_file_download_returns_signed_url(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    pdf = _make_pdf_bytes("downloadable content")
    create_r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "dl-test", "kind": "pdf", "is_published": "true"},
        files={"file": ("lecture.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=auth_header(body["access_token"]),
    )
    file_id = create_r.json()["file_id"]
    r = client.get(
        f"/api/v1/files/{file_id}/download",
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 200
    data = r.json()
    assert "url" in data
    assert "expires_in" in data
    assert data["expires_in"] == 300
    assert "sig=" in data["url"]
    assert "expires=" in data["url"]


def test_file_download_nonexistent(client, db):
    user, _ = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    r = client.get(
        f"/api/v1/files/{uuid.uuid4()}/download",
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 404


# ─────────────────────────── notification on publish ───────────────────────────

def test_publish_material_triggers_notification(client, db):
    """When a material is published, enrolled students get a new_material notification."""
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    before = db.scalars(select(Notification).where(Notification.type == "new_material")).all()
    before_count = len(before)

    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "published notification test", "kind": "video_link",
              "url": "https://example.com", "is_published": "true"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 201

    db.expire_all()
    after = db.scalars(select(Notification).where(Notification.type == "new_material")).all()
    assert len(after) > before_count


def test_unpublished_material_no_notification(client, db):
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    before = len(db.scalars(select(Notification).where(Notification.type == "new_material")).all())
    r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "unpublished", "kind": "video_link",
              "url": "https://example.com", "is_published": "false"},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 201
    db.expire_all()
    after = len(db.scalars(select(Notification).where(Notification.type == "new_material")).all())
    assert after == before  # no new notification


def test_patch_to_publish_triggers_notification(client, db):
    """Publishing via PATCH also triggers the notification."""
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    # Create unpublished
    create_r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "will-publish-later", "kind": "video_link",
              "url": "https://example.com", "is_published": "false"},
        headers=auth_header(body["access_token"]),
    )
    material_id = create_r.json()["id"]
    before = len(db.scalars(select(Notification).where(Notification.type == "new_material")).all())
    # Publish via PATCH
    r = client.patch(
        f"/api/v1/materials/{material_id}",
        json={"is_published": True},
        headers=auth_header(body["access_token"]),
    )
    assert r.status_code == 200
    db.expire_all()
    after = len(db.scalars(select(Notification).where(Notification.type == "new_material")).all())
    assert after > before


# ─────────────────────────── FCM pipeline (dev no-op) ───────────────────────────

def test_fcm_flush_pending_notifications_dev_no_op(client, db):
    """In dev (no FIREBASE_CREDENTIALS_JSON), flush is a no-op but notifications remain."""
    from app.services.fcm import flush_pending_notifications
    # Create some notifications first (via announcement)
    ca_body = login(client, "CA")
    client.post(
        "/api/v1/announcements",
        json={"scope": "college", "title": "fcm test", "body": "x"},
        headers=auth_header(ca_body["access_token"]),
    )
    # Flush — should return sent=0 (dev no FCM) but not error
    result = flush_pending_notifications(batch_size=100)
    assert "sent" in result
    assert "failed" in result
    assert isinstance(result["total_pending"], int)


# ─────────────────────────── storage integrity ───────────────────────────

def test_pdf_upload_saves_file_to_disk(client, db):
    """After upload, the file should exist on disk and have a checksum."""
    user, offering = _find_instructor_with_offering(db)
    body = login(client, user.university_id)
    pdf_content = b"integrity test pdf content"
    create_r = client.post(
        f"/api/v1/offerings/{offering.id}/materials",
        data={"title": "integrity", "kind": "pdf", "is_published": "true"},
        files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers=auth_header(body["access_token"]),
    )
    assert create_r.status_code == 201
    file_id = create_r.json()["file_id"]

    f = db.get(FileModel, uuid.UUID(file_id))
    assert f is not None
    assert f.size == len(pdf_content)
    assert f.checksum  # SHA-256 hex digest
    assert f.mime == "application/pdf"
    assert f.original_name == "test.pdf"
    # Verify the file exists on disk
    from app.services.storage import get_storage
    storage = get_storage()
    if hasattr(storage, "read"):
        path = storage.read(key=f.storage_key)
        assert path.exists()
        with open(path, "rb") as fp:
            assert fp.read() == pdf_content
