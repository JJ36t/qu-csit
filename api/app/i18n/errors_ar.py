"""Standardized Arabic error codes → messages. Single source of truth."""
from __future__ import annotations

ERROR_MESSAGES_AR: dict[str, str] = {
    # Auth
    "INVALID_CREDENTIALS": "رقم الجامعي أو كلمة المرور غير صحيح",
    "ACCOUNT_LOCKED": "تم قفل الحساب مؤقتاً بسبب محاولات كثيرة، حاول لاحقاً",
    "MUST_CHANGE_PASSWORD": "يجب تغيير كلمة المرور الأولية قبل المتابعة",
    "TOKEN_EXPIRED": "انتهت صلاحية الجلسة، يرجى تسجيل الدخول مجدداً",
    "TOKEN_INVALID": "جلسة غير صالحة",
    "REFRESH_TOKEN_REVOKED": "تم إلغاء هذه الجلسة",
    "DEVICE_NOT_BOUND": "هذا الجهاز غير مرتبط بحسابك، يرجى مراجعة القسم",
    "DEVICE_LIMIT_EXCEEDED": "تم ربط الجهاز بحساب آخر، يرجى مراجعة القسم",
    "PASSWORD_TOO_WEAK": "كلمة المرور ضعيفة: يجب 8 محارف على الأقل وأرقام وحروف",
    "OLD_PASSWORD_WRONG": "كلمة المرور الحالية غير صحيحة",
    "UNAUTHENTICATED": "يجب تسجيل الدخول",
    "FORBIDDEN": "ليست لديك صلاحية للقيام بهذا الإجراء",
    "ROLE_NOT_ALLOWED": "دورك لا يسمح بهذا الإجراء",
    "OUT_OF_SCOPE": "هذا الإجراء خارج نطاق صلاحيتك",
    # Attendance
    "SESSION_NOT_OPEN": "جلسة الحضور غير مفتوحة",
    "SESSION_EXPIRED": "انتهت صلاحية رمز الحضور",
    "SESSION_CLOSED": "أُغلقت جلسة الحضور",
    "NOT_ENROLLED": "أنت غير مسجّل في هذه المادة",
    "ALREADY_RECORDED": "تم تسجيل حضورك مسبقاً",
    "QR_WINDOW_INVALID": "رمز الحضور غير صالح أو منتهي",
    "ATTENDANCE_FLAGGED": "تم تسجيل حضورك للمراجعة (الموقع غير متحقق منه)",
    "NOT_SESSION_INSTRUCTOR": "أنت لست مدرّس هذه المادة",
    "OUTSIDE_ATTENDANCE_WINDOW": "الوقت خارج نافذة الحضور المسموحة",
    # Timetable
    "SLOT_CONFLICT_INSTRUCTOR": "تعارض: التدريسي مشغول في هذا الوقت",
    "SLOT_CONFLICT_ROOM": "تعارض: القاعة محجوزة في هذا الوقت",
    "SLOT_CONFLICT_GROUP": "تعارض: الشعبة لها حصة في هذا الوقت",
    # Generic
    "NOT_FOUND": "غير موجود",
    "ALREADY_EXISTS": "العنصر موجود مسبقاً",
    "VALIDATION_ERROR": "بيانات غير صحيحة",
    "RATE_LIMITED": "محاولات كثيرة جداً، انتظر قليلاً",
    "UPLOAD_TOO_LARGE": "حجم الملف يتجاوز الحد المسموح",
    "UPLOAD_TYPE_NOT_ALLOWED": "نوع الملف غير مسموح",
    "INTERNAL_ERROR": "حدث خطأ داخلي، يرجى المحاولة لاحقاً",
    "MAINTENANCE": "النظام تحت الصيانة",
    "OPEN_QUESTION_UNRESOLVED": "هذه الميزة غير مفعّلة بعد (بانتظار قرار الكلية)",
}


def ar(code: str, default: str | None = None) -> str:
    return ERROR_MESSAGES_AR.get(code, default or code)


class APIError(Exception):
    """Raised inside handlers/services; converted to a uniform response."""

    def __init__(self, code: str, status: int = 400, details: dict | None = None):
        self.code = code
        self.status = status
        self.details = details or {}
        super().__init__(ar(code))
