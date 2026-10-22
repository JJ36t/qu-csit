"""Admin endpoints: term absence rules (per Gate Q2), student Excel import,
user management (reset password, toggle status, unbind device), and RBAC
scope checks (wrong role, wrong scope/IDOR)."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from tests.conftest import auth_header, login, make_students_xlsx


# ─────────────────────────── Term absence rules ───────────────────────────

def test_term_absence_rule_seeded_by_default(client):
    """The seed creates one term-level rule (max_absences=10, late ≠ absence)."""
    body = login(client, "CA")  # college admin sees all
    r = client.get("/api/v1/admin/term-absence-rules", headers=auth_header(body["access_token"]))
    assert r.status_code == 200
    rules = r.json()
    assert any(rule["max_absences_per_course"] == 10 for rule in rules)
    assert any(rule["late_counts_as_absence"] is False for rule in rules)


def test_term_absence_rule_student_forbidden(client, student_token):
    """Wrong role: student cannot manage absence rules."""
    r = client.get(
        "/api/v1/admin/term-absence-rules",
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "ROLE_NOT_ALLOWED"


def test_term_absence_rule_create_and_update(client, college_admin_token, db):
    from sqlalchemy import select
    from app.models import Term

    term = db.scalar(select(Term).where(Term.is_current.is_(True)))
    assert term is not None
    payload = {
        "term_id": str(term.id),
        "department_id": None,
        "stage": None,
        "max_absences_per_course": 12,
        "late_threshold_minutes": 10,
        "late_counts_as_absence": False,
        "attendance_warning_threshold": 9,
        "notes": "phase-1 test",
    }
    r = client.post(
        "/api/v1/admin/term-absence-rules",
        json=payload,
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["max_absences_per_course"] == 12
    rule_id = body["id"]

    # Update same rule (upsert)
    payload["max_absences_per_course"] = 14
    r2 = client.post(
        "/api/v1/admin/term-absence-rules",
        json=payload,
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == rule_id
    assert r2.json()["max_absences_per_course"] == 14


def test_term_absence_rule_dept_admin_scope(client, dept_admin_cs_token, dept_admin_is_token, db):
    """Wrong scope: CS dept_admin cannot create a rule scoped to IS dept."""
    from sqlalchemy import select
    from app.models import Department, Term

    cs = db.scalar(select(Department).where(Department.code == "CS"))
    is_ = db.scalar(select(Department).where(Department.code == "IS"))
    term = db.scalar(select(Term).where(Term.is_current.is_(True)))

    # In-scope: CS admin creating a CS rule
    r = client.post(
        "/api/v1/admin/term-absence-rules",
        json={
            "term_id": str(term.id),
            "department_id": str(cs.id),
            "stage": 1,
            "max_absences_per_course": 8,
        },
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 200

    # Out-of-scope (IDOR): CS admin creating an IS rule
    r2 = client.post(
        "/api/v1/admin/term-absence-rules",
        json={
            "term_id": str(term.id),
            "department_id": str(is_.id),
            "stage": 1,
            "max_absences_per_course": 8,
        },
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r2.status_code == 403
    assert r2.json()["code"] == "OUT_OF_SCOPE"


def test_term_absence_rule_invalid_input(client, college_admin_token):
    """max_absences_per_course must be in [1,50]; stage in [1,8]."""
    from sqlalchemy import select
    from app.models import Term
    from app.db.base import SessionLocal

    db = SessionLocal()
    term = db.scalar(select(Term).where(Term.is_current.is_(True)))
    db.close()

    r = client.post(
        "/api/v1/admin/term-absence-rules",
        json={
            "term_id": str(term.id),
            "department_id": None,
            "stage": 99,  # out of range
            "max_absences_per_course": 99,  # out of range
        },
        headers=auth_header(college_admin_token["access_token"]),
    )
    assert r.status_code == 422


# ─────────────────────────── Student Excel import ───────────────────────────

def test_student_import_dry_run_preview(client, dept_admin_cs_token):
    """Preview returns a batch_id, total count, and per-row ok flags."""
    rows = [
        {"university_id": "IMP001", "full_name_ar": "طالب مستورد 1", "department_code": "CS", "stage": 1},
        {"university_id": "IMP002", "full_name_ar": "طالب مستورد 2", "department_code": "CS", "stage": 2},
    ]
    xlsx = make_students_xlsx(rows)
    r = client.post(
        "/api/v1/admin/students/import?dry_run=true",
        files={"file": ("students.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 2
    assert body["error_rows"] == 0
    assert body["batch_id"]
    assert body["initial_password"]
    assert len(body["rows"]) == 2


def test_student_import_commit_creates_accounts(client, dept_admin_cs_token):
    rows = [
        {"university_id": "IMP100", "full_name_ar": "طالب جديد 1", "department_code": "CS", "stage": 1, "study_type": "morning", "group_name": "A"},
    ]
    xlsx = make_students_xlsx(rows)
    r1 = client.post(
        "/api/v1/admin/students/import?dry_run=true",
        files={"file": ("students.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    batch_id = r1.json()["batch_id"]
    pwd = r1.json()["initial_password"]
    r2 = client.post(
        f"/api/v1/admin/students/import/{batch_id}/commit",
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r2.status_code == 200
    assert r2.json()["created"] == 1
    # Student can now log in with the initial password
    body = login(client, "IMP100", password=pwd, device_fp="fp-imp")
    assert body["must_change_password"] is True


def test_student_import_wrong_role_student(client, student_token):
    rows = [{"university_id": "X1", "full_name_ar": "x", "department_code": "CS", "stage": 1}]
    xlsx = make_students_xlsx(rows)
    r = client.post(
        "/api/v1/admin/students/import",
        files={"file": ("students.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 403


def test_student_import_wrong_scope_dept_admin(client, dept_admin_cs_token):
    """CS dept_admin cannot import students into IS department."""
    rows = [
        {"university_id": "IS-001", "full_name_ar": "طالب IS", "department_code": "IS", "stage": 1},
    ]
    xlsx = make_students_xlsx(rows)
    r = client.post(
        "/api/v1/admin/students/import?dry_run=true",
        files={"file": ("students.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 200
    body = r.json()
    # Row should be flagged as out-of-scope, not ok
    assert body["valid_rows"] == 0
    assert body["error_rows"] == 1
    assert "صلاحية" in body["rows"][0]["error"] or "نطاق" in body["rows"][0]["error"]


def test_student_import_duplicate_university_id_flagged(client, dept_admin_cs_token):
    """Existing university_id (S1001) should be flagged in preview."""
    rows = [
        {"university_id": "S1001", "full_name_ar": "مكرر", "department_code": "CS", "stage": 1},
    ]
    xlsx = make_students_xlsx(rows)
    r = client.post(
        "/api/v1/admin/students/import?dry_run=true",
        files={"file": ("students.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    body = r.json()
    assert body["error_rows"] == 1
    assert "مستخدم" in body["rows"][0]["error"]


def test_student_import_invalid_file_type(client, dept_admin_cs_token):
    r = client.post(
        "/api/v1/admin/students/import",
        files={"file": ("not-an-excel.txt", b"hello", "text/plain")},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_ERROR"


# ─────────────────────────── User management ───────────────────────────

def test_reset_password_dept_admin_in_scope(client, dept_admin_cs_token, db):
    """CS dept_admin can reset a CS student's password."""
    from sqlalchemy import select
    from app.models import User, UserRole

    student = db.scalar(select(User).where(User.university_id == "S1001"))
    r = client.post(
        f"/api/v1/admin/users/{student.id}/reset-password",
        json={"new_password": "ResetPass99"},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 200, r.text
    # New password works
    body = login(client, "S1001", password="ResetPass99", device_fp="fp-reset")
    assert "access_token" in body


def test_reset_password_dept_admin_out_of_scope(client, dept_admin_cs_token, db):
    """CS dept_admin cannot reset an IS student's password (IDOR)."""
    from sqlalchemy import select
    from app.models import User, Student, Department

    is_dept = db.scalar(select(Department).where(Department.code == "IS"))
    is_student = db.scalar(
        select(User)
        .join(Student, Student.user_id == User.id)
        .where(Student.department_id == is_dept.id)
    )
    r = client.post(
        f"/api/v1/admin/users/{is_student.id}/reset-password",
        json={"new_password": "HackedPass99"},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "OUT_OF_SCOPE"


def test_reset_password_weak_password_rejected(client, dept_admin_cs_token, db):
    from sqlalchemy import select
    from app.models import User

    student = db.scalar(select(User).where(User.university_id == "S1002"))
    r = client.post(
        f"/api/v1/admin/users/{student.id}/reset-password",
        json={"new_password": "short"},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 422


def test_toggle_user_status(client, dept_admin_cs_token, db):
    from sqlalchemy import select
    from app.models import User

    student = db.scalar(select(User).where(User.university_id == "S1005"))
    r = client.post(
        f"/api/v1/admin/users/{student.id}/toggle-status",
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "disabled"
    # Disabled student cannot log in
    r2 = client.post(
        "/api/v1/auth/login",
        json={"university_id": "S1005", "password": "Pass1234", "device_fingerprint": "x"},
    )
    assert r2.status_code == 403


def test_unbind_device_allows_rebinding_to_new_device(client, dept_admin_cs_token, db):
    """First device binding blocks 2nd; admin unbind → student can re-bind to a new device."""
    # Bind student S1006 to device fp-A
    login(client, "S1006", device_fp="fp-A")
    # Trying fp-B fails
    r1 = client.post(
        "/api/v1/auth/login",
        json={"university_id": "S1006", "password": "Pass1234", "device_fingerprint": "fp-B"},
    )
    assert r1.status_code == 403

    # Admin unbinds
    from sqlalchemy import select
    from app.models import User
    student = db.scalar(select(User).where(User.university_id == "S1006"))
    r2 = client.post(
        "/api/v1/admin/users/unbind-device",
        json={"user_id": str(student.id)},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r2.status_code == 200
    assert r2.json()["devices_unbound"] >= 1

    # Now fp-B works
    body = login(client, "S1006", device_fp="fp-B")
    assert "access_token" in body


def test_admin_audit_log_written(client, dept_admin_cs_token, db):
    """Reset password should write an audit_logs row."""
    from sqlalchemy import select
    from app.models import AuditLog, User

    student = db.scalar(select(User).where(User.university_id == "S1007"))
    r = client.post(
        f"/api/v1/admin/users/{student.id}/reset-password",
        json={"new_password": "AuditPass99"},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 200
    db.expire_all()
    logs = db.scalars(select(AuditLog).where(AuditLog.entity == "user", AuditLog.entity_id == str(student.id))).all()
    actions = [log.action for log in logs]
    assert "reset_password" in actions


def test_nonexistent_user_returns_404(client, dept_admin_cs_token):
    fake_id = str(uuid.uuid4())
    r = client.post(
        f"/api/v1/admin/users/{fake_id}/reset-password",
        json={"new_password": "Xyz12345"},
        headers=auth_header(dept_admin_cs_token["access_token"]),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"
