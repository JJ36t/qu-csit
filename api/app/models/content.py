"""Content: files, materials, assessments + grades (V2 tables only)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampMixin
from app.models.enums import AssessmentKind, MaterialKind


class File(Base, TimestampMixin):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    storage_key: Mapped[str] = mapped_column(String(512), index=True)
    mime: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploader_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )

    materials: Mapped[list["Material"]] = relationship(back_populates="file")


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    offering_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("course_offerings.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[MaterialKind] = mapped_column(default=MaterialKind.pdf)
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    week_no: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    offering = relationship("CourseOffering", back_populates="materials")
    file: Mapped["File | None"] = relationship(back_populates="materials")


class Assessment(Base, TimestampMixin):
    """V2 — table created for migration stability, no endpoints."""

    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    offering_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("course_offerings.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[AssessmentKind] = mapped_column(default=AssessmentKind.quiz)
    max_score: Mapped[float] = mapped_column(default=100.0)
    weight: Mapped[float] = mapped_column(default=0.0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    offering = relationship("CourseOffering")
    grades: Mapped[list["Grade"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Grade(Base, TimestampMixin):
    """V2 — table created for migration stability, no endpoints."""

    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id", name="uq_grade_assessment_student"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("students.user_id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(default=0.0)
    entered_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("staff.user_id"), nullable=True
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="grades")
    student = relationship("Student")
