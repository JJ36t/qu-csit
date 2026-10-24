"""Timetable endpoint tests — success, wrong role, conflict detection, scope."""
from __future__ import annotations

import uuid
from datetime import date, timedelta


from tests.conftest import auth_header, login


# ── GET /timetable (student view) ──
def test_student_gets_own_timetable(client, student_token):
    r = client.get(
        "/api/v1/timetable",
        params={"from": date.today().isoformat(), "to": (date.today() + timedelta(days=7)).isoformat()},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # Each item is {date, entries: [{slot, changes, effective_start, effective_end, ...}]}
    for item in items:
        assert "date" in item
        assert "entries" in item
        for entry in item["entries"]:
            assert "slot" in entry
            assert "is_cancelled" in entry


def test_timetable_invalid_date_range(client, student_token):
    r = client.get(
        "/api/v1/timetable",
        params={"from": "2026-01-10", "to": "2026-01-05"},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_timetable_without_token(client):
    r = client.get("/api/v1/timetable")
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


def test_instructor_gets_own_timetable(client, instructor_token):
    r = client.get(
        "/api/v1/timetable",
        params={"from": date.today().isoformat(), "to": (date.today() + timedelta(days=14)).isoformat()},
        headers=auth_header(instructor_token["access_token"]),
    )
    assert r.status_code == 200


# ── GET /timetable/changes ──
def test_timetable_changes_returns_list(client, student_token):
    r = client.get("/api/v1/timetable/changes", headers=auth_header(student_token["access_token"]))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── POST /admin/timetable — create slot ──
def _get_first_offering_id(client, admin_token) -> str:
    r = client.get("/api/v1/admin/offerings", headers=auth_header(admin_token["access_token"]))
    return r.json()[0]["id"]


def _get_first_room_id(client, admin_token) -> str:
    # No GET /rooms endpoint yet — fetch via a slot's room_id from existing timetable
    r = client.get("/api/v1/timetable", headers=auth_header(admin_token["access_token"]))
    items = r.json()
    for item in items:
        for entry in item.get("entries", []):
            if entry["slot"].get("room_id"):
                return entry["slot"]["room_id"]
    return ""


def test_admin_create_slot_success(client, college_admin_token):
    offering_id = _get_first_offering_id(client, college_admin_token)
    # Pick an unused weekday/time to avoid conflicts
    r = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": offering_id,
            "weekday": 4,  # Thursday
            "start_time": "16:00:00",
            "end_time": "17:30:00",
            "room_id": None,
            "kind": "theory",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["offering_id"] == offering_id
    assert body["weekday"] == 4
    assert body["start_time"] == "16:00:00"


def test_admin_create_slot_invalid_times(client, college_admin_token):
    offering_id = _get_first_offering_id(client, college_admin_token)
    r = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": offering_id,
            "weekday": 0,
            "start_time": "10:00:00",
            "end_time": "09:00:00",  # end before start
            "kind": "theory",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 422


def test_admin_create_slot_nonexistent_offering(client, college_admin_token):
    r = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": str(uuid.uuid4()),
            "weekday": 0,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "kind": "theory",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 404


def test_admin_create_slot_wrong_role_student(client, student_token):
    offering_id = _get_first_offering_id(client, login(client, "CA"))
    r = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": offering_id,
            "weekday": 0,
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "kind": "theory",
        },
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "ROLE_NOT_ALLOWED"


def test_admin_create_slot_conflict_instructor(client, college_admin_token, db):
    """Two offerings with the same instructor at overlapping times → conflict."""
    from sqlalchemy import select
    from app.models import CourseOffering, TimetableSlot
    offerings = db.scalars(select(CourseOffering).where(CourseOffering.instructor_id.is_not(None))).all()
    # Find two offerings with the same instructor
    by_instr: dict = {}
    for o in offerings:
        by_instr.setdefault(o.instructor_id, []).append(o)
    same_instr = next((lst for lst in by_instr.values() if len(lst) >= 2), None)
    if not same_instr:
        # Force it: assign both offerings to the same instructor
        same_instr = offerings[:2]
        same_instr[1].instructor_id = same_instr[0].instructor_id
        db.commit()

    # Find a weekday not used by either offering
    existing_slots = db.scalars(
        select(TimetableSlot).where(TimetableSlot.offering_id.in_([same_instr[0].id, same_instr[1].id]))
    ).all()
    used_weekdays = {s.weekday for s in existing_slots}
    weekday = next((d for d in range(7) if d not in used_weekdays), 5)
    slot_hour = 20  # late evening — definitely free

    # Slot 1
    r1 = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": str(same_instr[0].id),
            "weekday": weekday,
            "start_time": f"{slot_hour:02d}:00:00",
            "end_time": f"{slot_hour + 1}:30:00",
            "kind": "theory",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r1.status_code == 201, r1.text

    # Slot 2 — same instructor, overlapping time → conflict
    r2 = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": str(same_instr[1].id),
            "weekday": weekday,
            "start_time": f"{slot_hour + 1}:00:00",  # overlaps slot 1
            "end_time": f"{slot_hour + 2}:30:00",
            "kind": "theory",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r2.status_code == 409
    body = r2.json()
    assert body["code"] == "SLOT_CONFLICT_INSTRUCTOR"


def test_admin_update_slot_success(client, college_admin_token):
    offering_id = _get_first_offering_id(client, college_admin_token)
    # Create
    r1 = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": offering_id,
            "weekday": 1,
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "kind": "theory",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r1.status_code == 201
    slot_id = r1.json()["id"]

    # Update — move to non-overlapping time
    r2 = client.patch(
        f"/api/v1/admin/timetable/{slot_id}",
        json={"start_time": "16:00:00", "end_time": "17:30:00"},
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r2.status_code == 200
    assert r2.json()["start_time"] == "16:00:00"


def test_admin_delete_slot_success(client, college_admin_token):
    offering_id = _get_first_offering_id(client, college_admin_token)
    r1 = client.post(
        "/api/v1/admin/timetable",
        json={
            "offering_id": offering_id,
            "weekday": 2,
            "start_time": "18:00:00",
            "end_time": "19:30:00",
            "kind": "theory",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    slot_id = r1.json()["id"]
    r2 = client.delete(
        f"/api/v1/admin/timetable/{slot_id}",
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r2.status_code == 200


# ── Timetable changes (cancel/move/extra) ──
def test_admin_create_change_cancel(client, college_admin_token, db):
    from sqlalchemy import select
    from app.models import TimetableSlot
    slot = db.scalar(select(TimetableSlot))
    assert slot is not None
    target_date = date.today() + timedelta(days=1)
    r = client.post(
        "/api/v1/admin/timetable/changes",
        json={
            "slot_id": str(slot.id),
            "date": target_date.isoformat(),
            "type": "cancel",
            "reason": "اختبار إلغاء",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "cancel"
    assert body["reason"] == "اختبار إلغاء"


def test_admin_create_change_move_requires_new_times(client, college_admin_token, db):
    from sqlalchemy import select
    from app.models import TimetableSlot
    slot = db.scalar(select(TimetableSlot))
    r = client.post(
        "/api/v1/admin/timetable/changes",
        json={
            "slot_id": str(slot.id),
            "date": date.today().isoformat(),
            "type": "move",
            # missing new_start / new_end
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 422


def test_admin_create_change_triggers_notification(client, college_admin_token, db):
    """Creating a change broadcasts a notification to enrolled students."""
    from sqlalchemy import select
    from app.models import Notification, TimetableSlot
    slot = db.scalar(select(TimetableSlot))
    target_date = date.today() + timedelta(days=2)
    r = client.post(
        "/api/v1/admin/timetable/changes",
        json={
            "slot_id": str(slot.id),
            "date": target_date.isoformat(),
            "type": "extra",
            "new_start": "16:00:00",
            "new_end": "17:30:00",
            "reason": "حصة استثنائية",
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 201
    db.expire_all()
    # At least one notification should exist with type=timetable_change
    notes = db.scalars(
        select(Notification).where(Notification.type == "timetable_change")
    ).all()
    assert len(notes) >= 1
    assert any("استثنائية" in (n.body or "") for n in notes)
