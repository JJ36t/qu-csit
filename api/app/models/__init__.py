"""All ORM models. Import from here: `from app.models import User, Student, ...`"""
from __future__ import annotations

# Enums re-exported for convenience (one import line per call site).
from app.models.enums import (
    AnnouncementScope,
    AssessmentKind,
    AttendanceMethod,
    AttendanceStatus,
    CourseKind,
    DeviceStatus,
    EnrollmentSource,
    EnrollmentStatus,
    MaterialKind,
    NotificationType,
    RequestCategory,
    RequestStatus,
    SessionKind,
    SessionStatus,
    SlotKind,
    StudyType,
    StudentStatus,
    TimetableChangeType,
    UserRole,
    UserStatus,
)

from app.models.identity import (
    Device,
    FcmToken,
    RefreshToken,
    Staff,
    Student,
    User,
)
from app.models.academic import (
    AcademicYear,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    Group,
    Term,
    TermAbsenceRule,
)
from app.models.schedule import (
    LectureSession,
    Room,
    TimetableChange,
    TimetableSlot,
)
from app.models.attendance import (
    AbsenceExcuse,
    AttendanceRecord,
)
from app.models.content import (
    Assessment,
    File,
    Grade,
    Material,
)
from app.models.comms import (
    Announcement,
    AnnouncementRead,
    AuditLog,
    Notification,
    Request,
    RequestMessage,
)

__all__ = [
    # identity
    "User", "Student", "Staff", "Device", "RefreshToken", "FcmToken",
    # academic
    "Department", "AcademicYear", "Term", "TermAbsenceRule", "Group",
    "Course", "CourseOffering", "Enrollment",
    # schedule
    "Room", "TimetableSlot", "TimetableChange", "LectureSession",
    # attendance
    "AttendanceRecord", "AbsenceExcuse",
    # content
    "File", "Material", "Assessment", "Grade",
    # comms/audit
    "Announcement", "AnnouncementRead", "Notification", "Request",
    "RequestMessage", "AuditLog",
    # enums
    "AnnouncementScope", "AssessmentKind", "AttendanceMethod", "AttendanceStatus",
    "CourseKind", "DeviceStatus", "EnrollmentSource", "EnrollmentStatus",
    "MaterialKind", "NotificationType", "RequestCategory", "RequestStatus",
    "SessionKind", "SessionStatus", "SlotKind", "StudyType", "StudentStatus",
    "TimetableChangeType", "UserRole", "UserStatus",
]
