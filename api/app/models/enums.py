"""Shared enum definitions used across models and APIs."""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    student = "student"
    instructor = "instructor"
    dept_admin = "dept_admin"
    college_admin = "college_admin"
    system_admin = "system_admin"


class UserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    pending = "pending"


class StudyType(str, enum.Enum):
    morning = "morning"
    evening = "evening"


class StudentStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    graduated = "graduated"
    withdrawn = "withdrawn"


class DeviceStatus(str, enum.Enum):
    active = "active"
    unbound = "unbound"


class SessionKind(str, enum.Enum):
    theory = "theory"
    lab = "lab"


class CourseKind(str, enum.Enum):
    theory = "theory"
    lab = "lab"


class SlotKind(str, enum.Enum):
    theory = "theory"
    lab = "lab"


class TimetableChangeType(str, enum.Enum):
    cancel = "cancel"
    move = "move"
    extra = "extra"


class SessionStatus(str, enum.Enum):
    scheduled = "scheduled"
    open = "open"
    closed = "closed"
    cancelled = "cancelled"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    late = "late"
    absent = "absent"
    excused = "excused"


class AttendanceMethod(str, enum.Enum):
    qr = "qr"
    code = "code"
    id_scan = "id_scan"
    manual = "manual"


class MaterialKind(str, enum.Enum):
    pdf = "pdf"
    video_link = "video_link"
    link = "link"


class AssessmentKind(str, enum.Enum):
    quiz = "quiz"
    lab = "lab"
    midterm = "midterm"
    final = "final"
    other = "other"


class AnnouncementScope(str, enum.Enum):
    college = "college"
    department = "department"
    stage = "stage"
    group = "group"
    offering = "offering"


class RequestCategory(str, enum.Enum):
    complaint = "complaint"
    inquiry = "inquiry"
    petition = "petition"
    other = "other"


class RequestStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class NotificationType(str, enum.Enum):
    timetable_change = "timetable_change"
    attendance_open = "attendance_open"
    announcement = "announcement"
    new_material = "new_material"
    absence_warning = "absence_warning"
    grade_published = "grade_published"
    excuse_reviewed = "excuse_reviewed"
    request_updated = "request_updated"


class EnrollmentSource(str, enum.Enum):
    auto = "auto"
    manual = "manual"


class EnrollmentStatus(str, enum.Enum):
    active = "active"
    dropped = "dropped"
