"""Admin endpoints: student Excel import, user management, device unbind,
term absence rules management.

Implements brief §6 admin endpoints + Gate Q2 (configurable per-term absence rules).
"""
from __future__ import annotations

import io
import secrets
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Request, UploadFile
from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import (
    require_dept_admin_or_higher,
    assert_in_same_department,
)
from app.core.security import hash_password
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import (
    Department,
    Device,
    DeviceStatus,
    Group,
    RefreshToken,
    Student,
    TermAbsenceRule,
    User,
    UserRole,
    UserStatus,
)
from app.models.enums import StudentStatus, StudyType
from app.schemas.admin import (
    StudentImportPreview,
    StudentImportPreviewRow,
    TermAbsenceRuleCreate,
    TermAbsenceRuleOut,
    UserResetPasswordRequest,
    UnbindDeviceRequest,
)
from app.services.audit import write_audit

router = APIRouter()


# ── Student Excel import ──
# Two-phase: POST with file → preview + batch_id; POST batch_id/commit → persist.
# Phase 1 implementation: batches stored in-memory (dev). Prod would use Redis.

_BATCHES: dict[str, dict[str, Any]] = {}  # batch_id → {rows: [...], initial_password, expires_at}


@router.post("/students/import", response_model=StudentImportPreview)
async def import_students(
    file: UploadFile = File(...),
    dry_run: bool = True,
    initial_password: str | None = None,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    """Upload an .xlsx file of students. Returns a preview + batch_id.

    Excel header (case-insensitive): university_id | full_name_ar | email |
    phone | department_code | stage | study_type | group_name
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise APIError("VALIDATION_ERROR", 400, {"file": "must be .xlsx"})

    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:  # 10 MB
        raise APIError("UPLOAD_TOO_LARGE", 413)
    try:
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception:
        raise APIError("VALIDATION_ERROR", 400, {"file": "invalid xlsx"})
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = [str(c).strip().lower() if c is not None else "" for c in next(rows_iter)]
    except StopIteration:
        raise APIError("VALIDATION_ERROR", 400, {"file": "empty"})

    required = ["university_id", "full_name_ar", "department_code", "stage"]
    for col in required:
        if col not in header:
            raise APIError(
                "VALIDATION_ERROR",
                400,
                {"missing_column": col, "found_columns": header},
            )

    idx = {col: i for i, col in enumerate(header)}
    pwd = initial_password or _gen_initial_password()
    preview_rows: list[StudentImportPreviewRow] = []
    valid_records: list[dict[str, Any]] = []
    dept_cache: dict[str, Department] = {}

    for line_no, row in enumerate(rows_iter, start=2):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue
        try:
            university_id = str(row[idx["university_id"]]).strip()
            full_name_ar = str(row[idx["full_name_ar"]]).strip()
            department_code = str(row[idx["department_code"]]).strip()
            stage = int(row[idx["stage"]])
            if stage < 1 or stage > 8:
                raise ValueError("stage out of range")
            email = str(row[idx["email"]]).strip() if "email" in idx and row[idx["email"]] else None
            phone = str(row[idx["phone"]]).strip() if "phone" in idx and row[idx["phone"]] else None
            study_type_raw = (
                str(row[idx["study_type"]]).strip().lower()
                if "study_type" in idx and row[idx["study_type"]]
                else "morning"
            )
            study_type = StudyType(study_type_raw) if study_type_raw in ("morning", "evening") else StudyType.morning
            group_name = str(row[idx["group_name"]]).strip() if "group_name" in idx and row[idx["group_name"]] else None
        except Exception as exc:
            preview_rows.append(
                StudentImportPreviewRow(
                    row=line_no, ok=False, error=f"بيانات غير صحيحة: {exc}",
                    university_id="", full_name_ar="",
                )
            )
            continue

        # Scope check: dept_admin may only import into their own department.
        dept = dept_cache.get(department_code)
        if dept is None:
            dept = db.scalar(select(Department).where(Department.code == department_code))
            if dept:
                dept_cache[department_code] = dept
        if not dept:
            preview_rows.append(
                StudentImportPreviewRow(
                    row=line_no, ok=False, error=f"قسم غير موجود: {department_code}",
                    university_id=university_id, full_name_ar=full_name_ar,
                )
            )
            continue
        try:
            assert_in_same_department(admin, dept.id)
        except APIError:
            preview_rows.append(
                StudentImportPreviewRow(
                    row=line_no, ok=False, error="خارج نطاق صلاحيتك",
                    university_id=university_id, full_name_ar=full_name_ar,
                )
            )
            continue

        # Duplicate check (existing university_id)
        exists = db.scalar(select(User).where(User.university_id == university_id))
        if exists:
            preview_rows.append(
                StudentImportPreviewRow(
                    row=line_no, ok=False, error="الرقم الجامعي مستخدم مسبقاً",
                    university_id=university_id, full_name_ar=full_name_ar,
                )
            )
            continue

        valid_records.append(
            {
                "university_id": university_id,
                "full_name_ar": full_name_ar,
                "email": email,
                "phone": phone,
                "department_id": dept.id,
                "stage": stage,
                "study_type": study_type,
                "group_name": group_name,
            }
        )
        preview_rows.append(
            StudentImportPreviewRow(
                row=line_no, ok=True, university_id=university_id, full_name_ar=full_name_ar
            )
        )

    # Resolve group_ids for valid records (best-effort: name match within dept+stage+study_type)
    for rec in valid_records:
        if rec["group_name"]:
            grp = db.scalar(
                select(Group).where(
                    Group.department_id == rec["department_id"],
                    Group.stage == rec["stage"],
                    Group.study_type == rec["study_type"],
                    Group.name == rec["group_name"],
                )
            )
            rec["group_id"] = grp.id if grp else None
        else:
            rec["group_id"] = None

    batch_id = secrets.token_urlsafe(16)
    _BATCHES[batch_id] = {"records": valid_records, "initial_password": pwd}

    return StudentImportPreview(
        batch_id=batch_id,
        total_rows=len(preview_rows),
        valid_rows=sum(1 for r in preview_rows if r.ok),
        error_rows=sum(1 for r in preview_rows if not r.ok),
        initial_password=pwd,
        rows=preview_rows,
    )


@router.post("/students/import/{batch_id}/commit")
async def commit_student_import(
    batch_id: str,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Persist a previously-previewed batch."""
    batch = _BATCHES.get(batch_id)
    if not batch:
        raise APIError("NOT_FOUND", 404, {"batch_id": batch_id})

    pwd = batch["initial_password"]
    hashed = hash_password(pwd)
    created: list[uuid.UUID] = []
    for rec in batch["records"]:
        try:
            assert_in_same_department(admin, rec["department_id"])
        except APIError:
            continue  # silently skip — already flagged in preview
        u = User(
            role=UserRole.student,
            university_id=rec["university_id"],
            full_name_ar=rec["full_name_ar"],
            email=rec.get("email"),
            phone=rec.get("phone"),
            password_hash=hashed,
            status=UserStatus.active,
            must_change_password=True,
        )
        db.add(u)
        db.flush()
        s = Student(
            user_id=u.id,
            department_id=rec["department_id"],
            stage=rec["stage"],
            study_type=rec["study_type"],
            group_id=rec.get("group_id"),
            enrollment_year=2025,
            status=StudentStatus.active,
        )
        db.add(s)
        created.append(u.id)

    if created:
        write_audit(
            db,
            actor_id=admin.id,
            action="student_import_commit",
            entity="user",
            entity_id=str(admin.id),
            after={"count": len(created), "initial_password": pwd, "user_ids": [str(u) for u in created]},
            request=request,
        )
    db.commit()
    _BATCHES.pop(batch_id, None)
    return {"ok": True, "created": len(created), "initial_password": pwd}


# ── Term absence rules (Gate Q2) ──
@router.post("/term-absence-rules", response_model=TermAbsenceRuleOut)
async def create_term_absence_rule(
    payload: TermAbsenceRuleCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Create or update a per-term absence rule. dept_admin can scope to
    their own department; college_admin/system_admin can scope to the whole term.
    """
    if payload.department_id is not None:
        assert_in_same_department(admin, payload.department_id)
    # Upsert by (term_id, department_id, stage)
    q = select(TermAbsenceRule).where(TermAbsenceRule.term_id == payload.term_id)
    if payload.department_id is None:
        q = q.where(TermAbsenceRule.department_id.is_(None))
    else:
        q = q.where(TermAbsenceRule.department_id == payload.department_id)
    if payload.stage is None:
        q = q.where(TermAbsenceRule.stage.is_(None))
    else:
        q = q.where(TermAbsenceRule.stage == payload.stage)
    existing = db.scalar(q)
    if existing:
        existing.max_absences_per_course = payload.max_absences_per_course
        existing.late_threshold_minutes = payload.late_threshold_minutes
        existing.late_counts_as_absence = payload.late_counts_as_absence
        existing.attendance_warning_threshold = payload.attendance_warning_threshold
        existing.notes = payload.notes
        obj = existing
    else:
        obj = TermAbsenceRule(
            term_id=payload.term_id,
            department_id=payload.department_id,
            stage=payload.stage,
            max_absences_per_course=payload.max_absences_per_course,
            late_threshold_minutes=payload.late_threshold_minutes,
            late_counts_as_absence=payload.late_counts_as_absence,
            attendance_warning_threshold=payload.attendance_warning_threshold,
            notes=payload.notes,
        )
        db.add(obj)
    db.flush()
    write_audit(
        db,
        actor_id=admin.id,
        action="term_absence_rule_upsert",
        entity="term_absence_rule",
        entity_id=str(obj.id),
        after={
            "term_id": str(obj.term_id),
            "department_id": str(obj.department_id) if obj.department_id else None,
            "stage": obj.stage,
            "max_absences_per_course": obj.max_absences_per_course,
            "late_counts_as_absence": obj.late_counts_as_absence,
        },
        request=request,
    )
    db.commit()
    return TermAbsenceRuleOut.model_validate(obj)


@router.get("/term-absence-rules", response_model=list[TermAbsenceRuleOut])
async def list_term_absence_rules(
    term_id: uuid.UUID | None = None,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    q = select(TermAbsenceRule)
    if term_id is not None:
        q = q.where(TermAbsenceRule.term_id == term_id)
    rules = db.scalars(q).all()
    out = []
    for r in rules:
        # dept_admin sees only their own dept's rules + the term default
        if admin.role == UserRole.dept_admin:
            my_dept = admin.staff.department_id if admin.staff else None
            if r.department_id is not None and r.department_id != my_dept:
                continue
        out.append(TermAbsenceRuleOut.model_validate(r))
    return out


# ── User management: reset password, disable, unbind device ──
@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: uuid.UUID,
    payload: UserResetPasswordRequest,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    target = db.get(User, user_id)
    if not target:
        raise APIError("NOT_FOUND", 404)
    # Scope: dept_admin can only reset users in their dept.
    if target.role == UserRole.student and target.student:
        assert_in_same_department(admin, target.student.department_id)
    elif target.staff and target.staff.department_id:
        assert_in_same_department(admin, target.staff.department_id)
    elif target.role in (UserRole.college_admin, UserRole.system_admin):
        # Only college/system admin can manage admins (handled by require_dept_admin_or_higher check above)
        if admin.role != UserRole.system_admin:
            raise APIError("OUT_OF_SCOPE", 403)

    new_pwd = payload.new_password or _gen_initial_password()
    if not (len(new_pwd) >= 8 and any(c.isdigit() for c in new_pwd) and any(c.isalpha() for c in new_pwd)):
        raise APIError("PASSWORD_TOO_WEAK", 400)
    target.password_hash = hash_password(new_pwd)
    target.must_change_password = bool(payload.new_password is None)
    # Revoke all refresh tokens for this user
    db.query(RefreshToken).filter(RefreshToken.user_id == target.id).update(
        {"revoked_at": datetime.utcnow()}
    )
    write_audit(db, actor_id=admin.id, action="reset_password", entity="user", entity_id=str(target.id), request=request)
    db.commit()
    return {"ok": True, "initial_password": new_pwd if payload.new_password is None else None}


@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: uuid.UUID,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    target = db.get(User, user_id)
    if not target:
        raise APIError("NOT_FOUND", 404)
    if target.role == UserRole.student and target.student:
        assert_in_same_department(admin, target.student.department_id)
    new_status = UserStatus.disabled if target.status == UserStatus.active else UserStatus.active
    target.status = new_status
    write_audit(db, actor_id=admin.id, action="toggle_user_status", entity="user", entity_id=str(target.id), after={"status": new_status.value}, request=request)
    db.commit()
    return {"ok": True, "status": new_status.value}


@router.post("/users/unbind-device")
async def unbind_device(
    payload: UnbindDeviceRequest,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    target = db.get(User, payload.user_id)
    if not target:
        raise APIError("NOT_FOUND", 404)
    if target.role == UserRole.student and target.student:
        assert_in_same_department(admin, target.student.department_id)
    devices = db.scalars(select(Device).where(Device.user_id == target.id, Device.status == DeviceStatus.active)).all()
    for d in devices:
        d.status = DeviceStatus.unbound
    write_audit(db, actor_id=admin.id, action="unbind_device", entity="user", entity_id=str(target.id), after={"devices_unbound": len(devices)}, request=request)
    db.commit()
    return {"ok": True, "devices_unbound": len(devices)}


# ── helpers ──
def _gen_initial_password() -> str:
    """A strong but memorable initial password."""
    import string
    alphabet = string.ascii_letters + string.digits
    return "Q" + "".join(secrets.choice(alphabet) for _ in range(8)) + "1"


_ = (io,)
