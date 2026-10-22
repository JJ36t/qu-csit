"""Seed script — fake data for dev and tests.

Creates:
- 1 college (implicit — represented by 2 departments)
- 2 departments (CS, IS)
- 1 academic year (current) + 1 current term
- 4 stages per department, 2 groups per stage (morning + evening)
- 5 instructors per department (10 total)
- ~30 students total (split across stages)
- courses per stage, course offerings, rooms, weekly timetable slots

Run:  python -m app.seed   (or)  python scripts/seed.py
"""
from __future__ import annotations

import argparse
import logging
import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import SessionLocal, engine, Base
from app.models import (
    AcademicYear,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Group,
    LectureSession,
    Room,
    Staff,
    Student,
    Term,
    TermAbsenceRule,
    TimetableSlot,
    User,
)
from app.models.enums import (
    CourseKind,
    EnrollmentSource,
    EnrollmentStatus,
    SessionKind,
    SessionStatus,
    SlotKind,
    StudyType,
    UserRole,
    UserStatus,
)

import app.models  # noqa: F401  # ensure metadata is registered

# Quiet SQL echo during seeding regardless of APP_DEBUG.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
engine.echo = False


# Deterministic initial passwords so tests can log in.
INITIAL_PASSWORD = "Pass1234"


def seed_all(drop_first: bool = False) -> dict:
    if drop_first:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        return _seed(db)
    finally:
        db.close()


def _seed(db) -> dict:
    # ── Academic year + term ──
    ay = AcademicYear(label="2025/2026", is_current=True)
    db.add(ay)
    db.flush()
    term = Term(
        academic_year_id=ay.id,
        name="الخريف 2025/2026",
        start_date=date(2025, 9, 21),
        end_date=date(2026, 1, 22),
        is_current=True,
    )
    db.add(term)
    db.flush()

    # Term-level absence rule (per Gate Q2 answer).
    db.add(
        TermAbsenceRule(
            term_id=term.id,
            department_id=None,
            stage=None,
            max_absences_per_course=10,
            late_threshold_minutes=15,
            late_counts_as_absence=False,
            attendance_warning_threshold=8,
        )
    )

    # ── Departments ──
    cs = Department(name_ar="علوم الحاسوب", name_en="Computer Science", code="CS", stages_count=4)
    is_ = Department(name_ar="نظم المعلومات", name_en="Information Systems", code="IS", stages_count=4)
    db.add_all([cs, is_])
    db.flush()

    # ── Rooms ──
    rooms = []
    room_defs = [
        ("قاعة 101", "مبنى الكلية", 31.9946, 44.9196, 80),
        ("قاعة 102", "مبنى الكلية", 31.9947, 44.9197, 80),
        ("مختبر 1", "مبنى المختبرات", 31.9950, 44.9200, 60),
        ("مختبر 2", "مبنى المختبرات", 31.9951, 44.9201, 60),
        ("قاعة 201", "مبنى الكلية", 31.9948, 44.9198, 80),
    ]
    for name, b, lat, lng, r in room_defs:
        rooms.append(Room(name=name, building=b, lat=lat, lng=lng, radius_m=r))
    db.add_all(rooms)
    db.flush()

    # ── Instructors (5 per dept = 10) ──
    instructor_ar_names = [
        "د. أحمد عبد الله", "د. سارة علي حسن", "م. عمر ياسين", "م. ليلى فاضل",
        "د. مصطفى كاظم", "د. نور الهدى", "م. حسين جاسم", "د. زينب عبد الأمير",
        "م. كرار صباح", "د. مرتضى حميد",
    ]
    instructors = []
    for i, name in enumerate(instructor_ar_names):
        dept = cs if i < 5 else is_
        u = User(
            role=UserRole.instructor,
            university_id=f"T{1000 + i}",
            full_name_ar=name,
            email=f"instructor{i+1}@example.com",
            phone=f"0780{100000 + i}",
            password_hash=hash_password(INITIAL_PASSWORD),
            status=UserStatus.active,
            must_change_password=False,
        )
        db.add(u)
        db.flush()
        s = Staff(
            user_id=u.id,
            department_id=dept.id,
            academic_title="دكتور" if name.startswith("د.") else "مهندس",
            office=f"مكتب {i+1}",
        )
        db.add(s)
        db.flush()
        instructors.append((u, s, dept))

    # ── Admins: 1 dept_admin per dept, 1 college_admin, 1 system_admin ──
    cs_dept_admin = User(
        role=UserRole.dept_admin,
        university_id="DA_CS",
        full_name_ar="مسؤول قسم علوم الحاسوب",
        password_hash=hash_password(INITIAL_PASSWORD),
        status=UserStatus.active,
        must_change_password=False,
    )
    is_dept_admin = User(
        role=UserRole.dept_admin,
        university_id="DA_IS",
        full_name_ar="مسؤول قسم نظم المعلومات",
        password_hash=hash_password(INITIAL_PASSWORD),
        status=UserStatus.active,
        must_change_password=False,
    )
    college_admin = User(
        role=UserRole.college_admin,
        university_id="CA",
        full_name_ar="عميد الكلية",
        password_hash=hash_password(INITIAL_PASSWORD),
        status=UserStatus.active,
        must_change_password=False,
    )
    system_admin = User(
        role=UserRole.system_admin,
        university_id="ROOT",
        full_name_ar="مدير النظام",
        password_hash=hash_password(INITIAL_PASSWORD),
        status=UserStatus.active,
        must_change_password=False,
    )
    db.add_all([cs_dept_admin, is_dept_admin, college_admin, system_admin])
    db.flush()
    db.add(Staff(user_id=cs_dept_admin.id, department_id=cs.id, academic_title="مسؤول قسم"))
    db.add(Staff(user_id=is_dept_admin.id, department_id=is_.id, academic_title="مسؤول قسم"))
    db.add(Staff(user_id=college_admin.id, department_id=None, academic_title="عميد"))
    db.add(Staff(user_id=system_admin.id, department_id=None, academic_title="مدير النظام"))
    db.flush()

    # ── Groups: 4 stages × 2 (morning + evening) per dept = 16 ──
    groups_by_dept_stage = {}  # (dept_id, stage, study_type) → Group
    for dept in (cs, is_):
        for stage in range(1, 5):
            for st in (StudyType.morning, StudyType.evening):
                g = Group(
                    department_id=dept.id,
                    stage=stage,
                    name=f"{'A' if st == StudyType.morning else 'B'}",
                    study_type=st,
                    term_id=term.id,
                )
                db.add(g)
                db.flush()
                groups_by_dept_stage[(dept.id, stage, st)] = g

    # ── Courses + Offerings ──
    cs_course_names = [
        ("CS101", "مقدمة في البرمجة", 1),
        ("CS201", "هياكل البيانات", 2),
        ("CS301", "قواعد البيانات", 3),
        ("CS401", "الذكاء الاصطناعي", 4),
        ("CS102", "مختبر البرمجة", 1),
        ("CS202", "مختبر هياكل البيانات", 2),
    ]
    is_course_names = [
        ("IS101", "مبادئ نظم المعلومات", 1),
        ("IS201", "تحليل النظم", 2),
        ("IS301", "إدارة قواعد البيانات", 3),
        ("IS401", "أمن المعلومات", 4),
    ]
    courses_by_dept = {cs.id: [], is_.id: []}
    for code, name, stage in cs_course_names:
        kind = CourseKind.lab if "مختبر" in name else CourseKind.theory
        c = Course(code=code, name_ar=name, department_id=cs.id, stage=stage, kind=kind)
        db.add(c)
        db.flush()
        courses_by_dept[cs.id].append(c)
    for code, name, stage in is_course_names:
        c = Course(code=code, name_ar=name, department_id=is_.id, stage=stage, kind=CourseKind.theory)
        db.add(c)
        db.flush()
        courses_by_dept[is_.id].append(c)

    # Offerings: assign each course to the morning group of its stage
    # in its department, and assign a round-robin instructor.
    dept_instructors = {cs.id: [i for i in instructors if i[2].id == cs.id],
                        is_.id: [i for i in instructors if i[2].id == is_.id]}
    offerings = []
    for dept in (cs, is_):
        for c in courses_by_dept[dept.id]:
            g = groups_by_dept_stage[(dept.id, c.stage, StudyType.morning)]
            instr_pool = dept_instructors[dept.id]
            iu, _, _ = instr_pool[c.stage % len(instr_pool)]
            off = CourseOffering(
                course_id=c.id,
                term_id=term.id,
                group_id=g.id,
                instructor_id=iu.id,
                session_kind=SessionKind.theory if c.kind == CourseKind.theory else SessionKind.lab,
            )
            db.add(off)
            db.flush()
            offerings.append(off)

    # ── Students: 30 total, distributed ──
    # Distribute: CS gets 18 students (4 morning stage1 + 4 morning stage2 +
    # 3 morning stage3 + 4 morning stage4 + 3 evening), IS gets 12.
    student_count = 0
    distribution = [
        (cs, 1, StudyType.morning, 4),
        (cs, 2, StudyType.morning, 4),
        (cs, 3, StudyType.morning, 3),
        (cs, 4, StudyType.morning, 4),
        (cs, 2, StudyType.evening, 3),
        (is_, 1, StudyType.morning, 3),
        (is_, 2, StudyType.morning, 3),
        (is_, 3, StudyType.morning, 3),
        (is_, 4, StudyType.morning, 3),
    ]
    # Pre-generate timetable slots for each offering (so each student's group has visible slots)
    slots_per_offering: dict[uuid.UUID, list[TimetableSlot]] = {}
    # We'll do this after creating offerings (done above).
    weekday = 0  # 0 = Sunday
    hour = 9
    for off in offerings:
        slot = TimetableSlot(
            offering_id=off.id,
            weekday=weekday,
            start_time=time(hour, 0),
            end_time=time(hour + 1, 30),
            room_id=rooms[hour % len(rooms)].id,
            kind=SlotKind.theory if off.session_kind == SessionKind.theory else SlotKind.lab,
        )
        db.add(slot)
        db.flush()
        slots_per_offering[off.id] = [slot]
        weekday = (weekday + 1) % 5  # rotate through Sun..Thu
        hour = 9 + ((hour - 9 + 1) % 5)

    # Generate lecture_sessions for the next 4 weeks (so tests can run scans)
    today = date.today()
    for off in offerings:
        for slot in slots_per_offering[off.id]:
            for week_offset in range(0, 4):
                # Find the next date that matches the slot's weekday
                target = today + timedelta(days=week_offset * 7)
                while target.weekday() != slot.weekday:
                    target += timedelta(days=1)
                starts_at = datetime.combine(target, slot.start_time)
                ends_at = datetime.combine(target, slot.end_time)
                db.add(
                    LectureSession(
                        offering_id=off.id,
                        slot_id=slot.id,
                        date=target,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        status=SessionStatus.scheduled,
                    )
                )

    # Now create students + enrollments
    for dept, stage, st, n in distribution:
        g = groups_by_dept_stage[(dept.id, stage, st)]
        for _ in range(n):
            student_count += 1
            u = User(
                role=UserRole.student,
                university_id=f"S{1000 + student_count}",
                full_name_ar=f"طالب {student_count}",
                email=f"s{student_count}@example.com",
                phone=f"0770{200000 + student_count}",
                password_hash=hash_password(INITIAL_PASSWORD),
                status=UserStatus.active,
                must_change_password=True,  # first-login forced change
            )
            db.add(u)
            db.flush()
            db.add(
                Student(
                    user_id=u.id,
                    department_id=dept.id,
                    stage=stage,
                    study_type=st,
                    group_id=g.id,
                    enrollment_year=2025,
                )
            )
            db.flush()
            # Enroll this student in every offering for their group.
            group_offerings = db.scalars(
                select(CourseOffering).where(CourseOffering.group_id == g.id)
            ).all()
            for off in group_offerings:
                db.add(
                    Enrollment(
                        student_id=u.id,
                        offering_id=off.id,
                        source=EnrollmentSource.auto,
                        status=EnrollmentStatus.active,
                    )
                )

    db.commit()
    return {
        "departments": 2,
        "stages": 4,
        "groups": 16,
        "instructors": 10,
        "students": student_count,
        "courses": len(courses_by_dept[cs.id]) + len(courses_by_dept[is_.id]),
        "offerings": len(offerings),
        "initial_password": INITIAL_PASSWORD,
        "test_accounts": {
            "student": ("S1001", INITIAL_PASSWORD),
            "instructor": ("T1000", INITIAL_PASSWORD),
            "dept_admin": ("DA_CS", INITIAL_PASSWORD),
            "college_admin": ("CA", INITIAL_PASSWORD),
            "system_admin": ("ROOT", INITIAL_PASSWORD),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop all tables before seeding")
    args = parser.parse_args()
    summary = seed_all(drop_first=args.drop)
    print("Seed complete:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
