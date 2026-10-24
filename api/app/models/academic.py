"""Academic structure: departments, academic_years, terms, term_absence_rules,
groups, courses, course_offerings, enrollments."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin
from app.models.enums import (
    CourseKind,
    EnrollmentSource,
    EnrollmentStatus,
    SessionKind,
    StudyType,
)


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name_ar: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    stages_count: Mapped[int] = mapped_column(Integer, default=4)


class AcademicYear(Base, TimestampMixin):
    __tablename__ = "academic_years"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(String(32), unique=True)  # e.g. "2025/2026"
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Term(Base, TimestampMixin):
    __tablename__ = "terms"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("academic_years.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))  # e.g. "الرابع - الصباحي"
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    academic_year = relationship("AcademicYear")
    absence_rules: Mapped[list["TermAbsenceRule"]] = relationship(
        back_populates="term", cascade="all, delete-orphan"
    )


class TermAbsenceRule(Base, TimestampMixin):
    """Configurable per-term absence policy (Gate Q2 answer).

    Rules can be set per term, optionally overridden per department and stage.
    When department_id and stage are NULL the row is the term-level default.
    """

    __tablename__ = "term_absence_rules"
    __table_args__ = (
        UniqueConstraint(
            "term_id", "department_id", "stage", name="uq_term_absence_rule_scope"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    term_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("terms.id", ondelete="CASCADE"), index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("departments.id"), nullable=True, index=True
    )
    stage: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    max_absences_per_course: Mapped[int] = mapped_column(Integer, default=10)
    late_threshold_minutes: Mapped[int] = mapped_column(Integer, default=15)
    late_counts_as_absence: Mapped[bool] = mapped_column(Boolean, default=False)
    attendance_warning_threshold: Mapped[int] = mapped_column(Integer, default=8)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    term: Mapped["Term"] = relationship(back_populates="absence_rules")
    department = relationship("Department")


class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("departments.id"), index=True
    )
    stage: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(64))  # e.g. "A"
    study_type: Mapped[StudyType] = mapped_column(default=StudyType.morning)
    term_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("terms.id"), index=True
    )

    department = relationship("Department")
    term = relationship("Term")
    offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="group")


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name_ar: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("departments.id"), index=True
    )
    stage: Mapped[int] = mapped_column(Integer, index=True)
    units: Mapped[int] = mapped_column(Integer, default=3)
    kind: Mapped[CourseKind] = mapped_column(default=CourseKind.theory)

    department = relationship("Department")


class CourseOffering(Base, TimestampMixin):
    """The central entity: ties a Course to a Term + Group + Instructor."""

    __tablename__ = "course_offerings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("courses.id"), index=True
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("terms.id"), index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("groups.id"), index=True
    )
    instructor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("staff.user_id"), nullable=True, index=True
    )
    session_kind: Mapped[SessionKind] = mapped_column(default=SessionKind.theory)

    course = relationship("Course")
    term = relationship("Term")
    group: Mapped["Group"] = relationship(back_populates="offerings")
    instructor = relationship("Staff", foreign_keys=[instructor_id])
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="offering", cascade="all, delete-orphan"
    )
    slots = relationship("TimetableSlot", back_populates="offering")
    sessions = relationship("LectureSession", back_populates="offering")
    materials = relationship("Material", back_populates="offering")


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "offering_id", name="uq_enrollment_student_offering"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("students.user_id", ondelete="CASCADE"), index=True
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("course_offerings.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[EnrollmentSource] = mapped_column(default=EnrollmentSource.auto)
    status: Mapped[EnrollmentStatus] = mapped_column(
        default=EnrollmentStatus.active, index=True
    )

    student = relationship("Student")
    offering: Mapped["CourseOffering"] = relationship(back_populates="enrollments")


# Re-exported to satisfy flake8 forward refs used by CourseKind.
_ = CourseKind
