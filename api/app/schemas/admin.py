"""Schemas for admin endpoints."""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StudyType


class DepartmentCreate(BaseModel):
    name_ar: str = Field(min_length=1, max_length=255)
    name_en: str | None = None
    code: str = Field(min_length=1, max_length=16)
    stages_count: int = Field(default=4, ge=1, le=8)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name_ar: str
    name_en: str | None
    code: str
    stages_count: int


class AcademicYearCreate(BaseModel):
    label: str = Field(min_length=3, max_length=32)
    is_current: bool = False


class AcademicYearOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    label: str
    is_current: bool


class TermCreate(BaseModel):
    academic_year_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool = False


class TermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool


class TermAbsenceRuleCreate(BaseModel):
    """Create/update a per-term absence rule (Gate Q2 answer)."""

    term_id: uuid.UUID
    department_id: uuid.UUID | None = None
    stage: int | None = Field(default=None, ge=1, le=8)
    max_absences_per_course: int = Field(default=10, ge=1, le=50)
    late_threshold_minutes: int = Field(default=15, ge=1, le=120)
    late_counts_as_absence: bool = False
    attendance_warning_threshold: int = Field(default=8, ge=1, le=50)
    notes: str | None = None


class TermAbsenceRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    term_id: uuid.UUID
    department_id: uuid.UUID | None
    stage: int | None
    max_absences_per_course: int
    late_threshold_minutes: int
    late_counts_as_absence: bool
    attendance_warning_threshold: int
    notes: str | None


class GroupCreate(BaseModel):
    department_id: uuid.UUID
    stage: int = Field(ge=1, le=8)
    name: str = Field(min_length=1, max_length=64)
    study_type: StudyType = StudyType.morning
    term_id: uuid.UUID


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    department_id: uuid.UUID
    stage: int
    name: str
    study_type: StudyType
    term_id: uuid.UUID


class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name_ar: str = Field(min_length=1, max_length=255)
    name_en: str | None = None
    department_id: uuid.UUID
    stage: int = Field(ge=1, le=8)
    units: int = Field(default=3, ge=1, le=10)
    kind: str = "theory"


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name_ar: str
    name_en: str | None
    department_id: uuid.UUID
    stage: int
    units: int
    kind: str


class OfferingCreate(BaseModel):
    course_id: uuid.UUID
    term_id: uuid.UUID
    group_id: uuid.UUID
    instructor_id: uuid.UUID | None = None
    session_kind: str = "theory"


class OfferingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    course_id: uuid.UUID
    term_id: uuid.UUID
    group_id: uuid.UUID
    instructor_id: uuid.UUID | None
    session_kind: str


class StudentImportRow(BaseModel):
    """One row in the Excel file. Header names accepted (case-insensitive):
    university_id, full_name_ar, email, phone, department_code, stage,
    study_type, group_name."""

    university_id: str
    full_name_ar: str
    email: str | None = None
    phone: str | None = None
    department_code: str
    stage: int = Field(ge=1, le=8)
    study_type: StudyType = StudyType.morning
    group_name: str | None = None


class StudentImportPreviewRow(BaseModel):
    row: int
    ok: bool
    error: str | None = None
    university_id: str
    full_name_ar: str


class StudentImportPreview(BaseModel):
    batch_id: str
    total_rows: int
    valid_rows: int
    error_rows: int
    initial_password: str  # one shared initial password for this batch
    rows: list[StudentImportPreviewRow]


class StudentImportCommit(BaseModel):
    batch_id: str


class UserResetPasswordRequest(BaseModel):
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class UnbindDeviceRequest(BaseModel):
    user_id: uuid.UUID
