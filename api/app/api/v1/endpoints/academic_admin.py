"""Admin academic endpoints: academic years, terms, departments, groups,
courses, offerings, audit log read.

All scoped: dept_admin sees only their dept; college_admin/system_admin sees all.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.rbac import (
    assert_in_same_department,
    get_user_department_id,
    require_dept_admin_or_higher,
)
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import (
    AcademicYear,
    AuditLog,
    Course,
    CourseOffering,
    Department,
    Group,
    Staff,
    Student,
    Term,
    User,
    UserRole,
)
from app.schemas.admin import (
    AcademicYearCreate,
    AcademicYearOut,
    CourseCreate,
    CourseOut,
    DepartmentCreate,
    DepartmentOut,
    GroupCreate,
    GroupOut,
    OfferingCreate,
    OfferingOut,
    TermCreate,
    TermOut,
)
from app.schemas.features import AuditLogOut
from app.services.audit import write_audit
from app.services.session_generator import generate_sessions_for_term

router = APIRouter()


# ── Departments ──
@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    items = db.scalars(select(Department).order_by(Department.name_ar)).all()
    out: list[DepartmentOut] = []
    for d in items:
        if admin.role == UserRole.dept_admin:
            my_dept = get_user_department_id(admin)
            if my_dept and d.id != my_dept:
                continue
        out.append(DepartmentOut.model_validate(d))
    return out


@router.post("/departments", response_model=DepartmentOut, status_code=201)
async def create_department(
    payload: DepartmentCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if admin.role not in (UserRole.college_admin, UserRole.system_admin):
        raise APIError("OUT_OF_SCOPE", 403, {"reason": "only college/system admin can create departments"})
    existing = db.scalar(select(Department).where(Department.code == payload.code))
    if existing:
        raise APIError("ALREADY_EXISTS", 409, {"code": payload.code})
    d = Department(name_ar=payload.name_ar, name_en=payload.name_en, code=payload.code, stages_count=payload.stages_count)
    db.add(d)
    db.flush()
    write_audit(db, actor_id=admin.id, action="create_department", entity="department", entity_id=str(d.id),
                after={"code": d.code, "name_ar": d.name_ar}, request=request)
    db.commit()
    db.refresh(d)
    return DepartmentOut.model_validate(d)


# ── Academic years + terms ──
@router.get("/academic-years", response_model=list[AcademicYearOut])
async def list_academic_years(
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    items = db.scalars(select(AcademicYear).order_by(AcademicYear.label.desc())).all()
    return [AcademicYearOut.model_validate(a) for a in items]


@router.post("/academic-years", response_model=AcademicYearOut, status_code=201)
async def create_academic_year(
    payload: AcademicYearCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if payload.is_current:
        # Unset is_current on all existing years + terms
        for ay in db.scalars(select(AcademicYear).where(AcademicYear.is_current.is_(True))).all():
            ay.is_current = False
    ay = AcademicYear(label=payload.label, is_current=payload.is_current)
    db.add(ay)
    db.flush()
    write_audit(db, actor_id=admin.id, action="create_academic_year", entity="academic_year",
                entity_id=str(ay.id), after={"label": ay.label, "is_current": ay.is_current}, request=request)
    db.commit()
    db.refresh(ay)
    return AcademicYearOut.model_validate(ay)


@router.get("/terms", response_model=list[TermOut])
async def list_terms(
    academic_year_id: uuid.UUID | None = None,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    q = select(Term)
    if academic_year_id:
        q = q.where(Term.academic_year_id == academic_year_id)
    items = db.scalars(q.order_by(Term.start_date.desc())).all()
    return [TermOut.model_validate(t) for t in items]


@router.post("/terms", response_model=TermOut, status_code=201)
async def create_term(
    payload: TermCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if payload.is_current:
        for t in db.scalars(select(Term).where(Term.is_current.is_(True))).all():
            t.is_current = False
    t = Term(
        academic_year_id=payload.academic_year_id,
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
    )
    db.add(t)
    db.flush()
    write_audit(db, actor_id=admin.id, action="create_term", entity="term", entity_id=str(t.id),
                after={"name": t.name, "is_current": t.is_current}, request=request)
    db.commit()
    db.refresh(t)
    return TermOut.model_validate(t)


@router.post("/terms/{term_id}/generate-sessions")
async def generate_sessions(
    term_id: uuid.UUID,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    """Generate lecture_sessions for every slot, every week of the term.
    Idempotent — only creates sessions that don't exist yet."""
    term = db.get(Term, term_id)
    if not term:
        raise APIError("NOT_FOUND", 404, {"term_id": str(term_id)})
    count = generate_sessions_for_term(db, term)
    return {"ok": True, "created": count, "term": term.name}


# ── Groups ──
@router.get("/groups", response_model=list[GroupOut])
async def list_groups(
    department_id: uuid.UUID | None = None,
    stage: int | None = Query(default=None, ge=1, le=8),
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    q = select(Group)
    if department_id:
        q = q.where(Group.department_id == department_id)
    if stage:
        q = q.where(Group.stage == stage)
    items = db.scalars(q.order_by(Group.department_id, Group.stage, Group.name)).all()
    out: list[GroupOut] = []
    for g in items:
        if admin.role == UserRole.dept_admin:
            my_dept = get_user_department_id(admin)
            if g.department_id != my_dept:
                continue
        out.append(GroupOut.model_validate(g))
    return out


@router.post("/groups", response_model=GroupOut, status_code=201)
async def create_group(
    payload: GroupCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    assert_in_same_department(admin, payload.department_id)
    g = Group(
        department_id=payload.department_id,
        stage=payload.stage,
        name=payload.name,
        study_type=payload.study_type,
        term_id=payload.term_id,
    )
    db.add(g)
    db.flush()
    write_audit(db, actor_id=admin.id, action="create_group", entity="group", entity_id=str(g.id),
                after={"department_id": str(g.department_id), "stage": g.stage, "name": g.name}, request=request)
    db.commit()
    db.refresh(g)
    return GroupOut.model_validate(g)


# ── Courses ──
@router.get("/courses", response_model=list[CourseOut])
async def list_courses(
    department_id: uuid.UUID | None = None,
    stage: int | None = Query(default=None, ge=1, le=8),
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    q = select(Course)
    if department_id:
        q = q.where(Course.department_id == department_id)
    if stage:
        q = q.where(Course.stage == stage)
    items = db.scalars(q.order_by(Course.code)).all()
    out: list[CourseOut] = []
    for c in items:
        if admin.role == UserRole.dept_admin:
            my_dept = get_user_department_id(admin)
            if c.department_id != my_dept:
                continue
        out.append(CourseOut.model_validate(c))
    return out


@router.post("/courses", response_model=CourseOut, status_code=201)
async def create_course(
    payload: CourseCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    assert_in_same_department(admin, payload.department_id)
    existing = db.scalar(select(Course).where(Course.code == payload.code))
    if existing:
        raise APIError("ALREADY_EXISTS", 409, {"code": payload.code})
    c = Course(
        code=payload.code, name_ar=payload.name_ar, name_en=payload.name_en,
        department_id=payload.department_id, stage=payload.stage,
        units=payload.units, kind=payload.kind,  # type: ignore[arg-type]
    )
    db.add(c)
    db.flush()
    write_audit(db, actor_id=admin.id, action="create_course", entity="course", entity_id=str(c.id),
                after={"code": c.code, "name_ar": c.name_ar}, request=request)
    db.commit()
    db.refresh(c)
    return CourseOut.model_validate(c)


# ── Course offerings ──
@router.get("/offerings", response_model=list[OfferingOut])
async def list_offerings(
    term_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    instructor_id: uuid.UUID | None = None,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    q = select(CourseOffering)
    if term_id:
        q = q.where(CourseOffering.term_id == term_id)
    if group_id:
        q = q.where(CourseOffering.group_id == group_id)
    if instructor_id:
        q = q.where(CourseOffering.instructor_id == instructor_id)
    items = db.scalars(q).all()
    out: list[OfferingOut] = []
    for o in items:
        if o.course:
            if admin.role == UserRole.dept_admin:
                my_dept = get_user_department_id(admin)
                if o.course.department_id != my_dept:
                    continue
        out.append(OfferingOut.model_validate(o))
    return out


@router.post("/offerings", response_model=OfferingOut, status_code=201)
async def create_offering(
    payload: OfferingCreate,
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    course = db.get(Course, payload.course_id)
    if not course:
        raise APIError("NOT_FOUND", 404, {"course_id": str(payload.course_id)})
    assert_in_same_department(admin, course.department_id)
    o = CourseOffering(
        course_id=payload.course_id,
        term_id=payload.term_id,
        group_id=payload.group_id,
        instructor_id=payload.instructor_id,
        session_kind=payload.session_kind,  # type: ignore[arg-type]
    )
    db.add(o)
    db.flush()
    write_audit(db, actor_id=admin.id, action="create_offering", entity="course_offering",
                entity_id=str(o.id),
                after={"course_id": str(o.course_id), "group_id": str(o.group_id)}, request=request)
    db.commit()
    db.refresh(o)
    return OfferingOut.model_validate(o)


# ── Audit log ──
@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    entity: str | None = None,
    actor_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    admin: User = Depends(require_dept_admin_or_higher),
    db: Session = Depends(get_db),
):
    """Audit log viewer. dept_admin sees only entries in their own dept.
    college_admin / system_admin see all entries."""
    if admin.role == UserRole.dept_admin:
        # Filter to actor_ids in the dept
        my_dept = get_user_department_id(admin)
        if not my_dept:
            return []
        actor_ids = set(db.scalars(
            select(User.id)
            .join(Student, Student.user_id == User.id, isouter=True)
            .join(Staff, Staff.user_id == User.id, isouter=True)
            .where(
                or_(Student.department_id == my_dept, Staff.department_id == my_dept)
            )
        ).all())
        # fall back to all entries that match dept context (slower but simpler)
        # For now: just return recent logs by those actors
        q = (
            select(AuditLog)
            .where(AuditLog.actor_id.in_(list(actor_ids)))
            .order_by(AuditLog.created_at.desc())
        )
    else:
        q = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity:
        q = q.where(AuditLog.entity == entity)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    items = db.scalars(q.offset((page - 1) * limit).limit(limit)).all()
    return [AuditLogOut.model_validate(item) for item in items]


# silence unused
_ = or_
