"""Public endpoints: privacy policy, maintenance status, app version check.

Brief §9 + §11:
- Privacy policy page served by the API (required for Google Play Data safety)
- Maintenance mode (forced — client shows a maintenance screen)
- App version check (force-update flow)
"""
from __future__ import annotations


from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db

router = APIRouter()


PRIVACY_POLICY_AR = """# سياسة الخصوصية — تطبيق كلية علوم الحاسوب وتكنولوجيا المعلومات

**جامعة القادسية — كلية علوم الحاسوب وتكنولوجيا المعلومات**

آخر تحديث: 2026-10-23

## 1. البيانات التي نجمعها

نجمع الحد الأدنى من البيانات اللازمة لتقديم الخدمة:

- **بيانات الحساب**: الاسم، الرقم الجامعي، القسم، المرحلة، الشعبة، البريد الإلكتروني، رقم الهاتف.
- **بيانات الحضور**: حالة الحضور لكل محاضرة (حاضر/متأخر/غائب/بعذر)، الوقت، معرّف الجهاز، الموقع الجغرافي لحظة المسح فقط.
- **بيانات الجهاز**: بصمة الجهاز (fingerprint)، طرازه، رمز الإشعارات (FCM token).
- **سجلات الاستخدام**: إجراءات المسؤولين والتدريسيين (سجل التدقيق).

## 2. كيف نستخدم البيانات

- تسجيل الحضور للمحاضرات والعملية التعليمية.
- إرسال الإشعارات المتعلقة بالجدول والإعلانات والمواد.
- تقارير الحضور للطلاب والتدريسيين ومسؤولي الأقسام.
- ضمان أمان الحسابات (ربط جهاز واحد بكل طالب).

## 3. الموقع الجغرافي

- **نرسله فقط لحظة مسح الحضور** ولا نتتبع الطالب في الخلفية أبداً.
- يُستخدم للتحقق من وجود الطالب ضمن نطاق القاعة/الحرم الجامعي.
- إذا تعذّر الحصول على الموقع، يُسجّل الحضور كـ«مشبوه» للمراجعة ولا يُرفض.

## 4. من يصل إلى البيانات

- الطالب يرى بياناته فقط.
- التدريسي يرى بيانات طلاب مواده فقط.
- مسؤول القسم يرى بيانات قسمه.
- عميد الكلية ومدير النظام يصلان لجميع البيانات.
- لا نشارك البيانات مع أي طرف ثالث خارج الجامعة.

## 5. حفظ البيانات

- تُخزّن على سيرفر الجامعة (أو VPS خارجي مؤقتاً ثم تُنقل للجامعة).
- نسخ احتياطي يومي مشفّر.
- لا تُحذف بيانات الحضور نهائياً بل تُؤرشف.

## 6. حقوق الطالب

- **حق الاطلاع**: الطالب يطلب نسخة من بياناته عبر مسؤول القسم.
- **حق التصحيح**: تصحيح البيانات غير الصحيحة.
- **حق الحذف**: عند التخرج، يحق للطالب طلب حذف بياناته وفق سياسة الكلية.

## 7. أمان البيانات

- كلمات المرور مُجزّأة بـ Argon2id (لا تُخزّن نصاً صريحاً).
- الاتصال عبر HTTPS فقط مع HSTS.
- صلاحيات قاعدة البيانات بأقل امتياز.
- سجل تدقيق على كل تعديل في الحضور أو الدرجات أو بيانات المستخدمين.

## 8. التواصل

للاستفسارات المتعلقة بالخصوصية: عمادة كلية علوم الحاسوب وتكنولوجيا المعلومات — جامعة القادسية.
"""

PRIVACY_POLICY_EN = """# Privacy Policy — College of Computer Science and IT App

**University of Al-Qadisiyah — College of Computer Science and Information Technology**

Last updated: 2026-10-23

## 1. Data We Collect

We collect the minimum data necessary to provide the service:

- **Account data**: name, university ID, department, stage, group, email, phone.
- **Attendance data**: attendance status per lecture (present/late/absent/excused), timestamp, device ID, GPS location at scan time only.
- **Device data**: device fingerprint, model, FCM token.
- **Audit logs**: admin and instructor actions.

## 2. How We Use Data

- Recording attendance for lectures and academic process.
- Sending notifications about timetable, announcements, materials.
- Attendance reports for students, instructors, department staff.
- Account security (one device per student binding).

## 3. GPS Location

- Sent only at the moment of scanning attendance; we never track in the background.
- Used to verify the student is within the room/campus radius.
- If location is unavailable, the scan is flagged for review and never rejected.

## 4. Who Accesses Data

- Student sees only their own data.
- Instructor sees data for their course offerings only.
- Department admin sees their department's data.
- College admin and system admin access all data.
- We do not share data with any third party outside the university.

## 5. Data Retention

- Stored on the university server (or external VPS temporarily, then migrated).
- Encrypted daily backups.
- Attendance records are archived, not hard-deleted.

## 6. Student Rights

- **Access**: request a copy of your data via the department admin.
- **Correction**: correct inaccurate data.
- **Deletion**: upon graduation, you may request deletion per college policy.

## 7. Data Security

- Passwords hashed with Argon2id (never stored in plaintext).
- HTTPS only with HSTS.
- Least-privilege database accounts.
- Audit log on every attendance/grade/user change.

## 8. Contact

Privacy inquiries: College of Computer Science and IT — University of Al-Qadisiyah.
"""


@router.get("/privacy")
async def privacy_policy(lang: str = "ar"):
    """Privacy policy page. Served by the API so the app and Play Store link to it.

    ?lang=ar (default) → Arabic
    ?lang=en → English
    """
    if lang == "en":
        return {
            "lang": "en",
            "title": "Privacy Policy — College of Computer Science and IT App",
            "policy": PRIVACY_POLICY_EN,
            "last_updated": "2026-10-23",
        }
    return {
        "lang": "ar",
        "title": "سياسة الخصوصية — تطبيق كلية علوم الحاسوب وتكنولوجيا المعلومات",
        "policy": PRIVACY_POLICY_AR,
        "last_updated": "2026-10-23",
    }


@router.get("/maintenance")
async def maintenance_status():
    """Client checks this on startup. If `maintenance: true`, the app shows
    a maintenance screen and blocks login."""
    return {
        "maintenance": False,
        "message_ar": "النظام يعمل بشكل طبيعي",
        "message_en": "System is operating normally",
        "estimated_end": None,
    }


@router.get("/app-version")
async def app_version_check(platform: str = "android", version: str = "0.1.0"):
    """Force-update check. Client sends its current version; server returns
    whether an update is required and the minimum version."""
    min_version = "0.1.0"
    latest_version = "0.1.0"
    update_required = _version_lt(version, min_version)
    return {
        "platform": platform,
        "your_version": version,
        "min_version": min_version,
        "latest_version": latest_version,
        "update_required": update_required,
        "download_url": "https://play.google.com/store/apps/details?id=" + settings.app_package_id,
    }


def _version_lt(a: str, b: str) -> bool:
    """True if version a < version b (semantic versioning).

    Unparseable versions are treated as older (safer to force update).
    """
    try:
        a_parts = [int(x) for x in a.split(".")]
        b_parts = [int(x) for x in b.split(".")]
        # Pad with zeros
        while len(a_parts) < len(b_parts):
            a_parts.append(0)
        while len(b_parts) < len(a_parts):
            b_parts.append(0)
        return a_parts < b_parts
    except (ValueError, AttributeError):
        return True  # unparseable → treat as older → force update


@router.get("/stats")
async def public_stats(db: Session = Depends(get_db)):
    """Public statistics (no auth) — for the landing page / store listing.
    Returns counts that don't reveal personal data."""
    from sqlalchemy import func
    from app.models import User, Course, Department
    students_count = db.scalar(
        select(func.count()).select_from(User).where(User.role == "student")
    ) or 0
    instructors_count = db.scalar(
        select(func.count()).select_from(User).where(User.role == "instructor")
    ) or 0
    courses_count = db.scalar(select(func.count()).select_from(Course)) or 0
    departments_count = db.scalar(select(func.count()).select_from(Department)) or 0
    return {
        "students": students_count,
        "instructors": instructors_count,
        "courses": courses_count,
        "departments": departments_count,
    }
