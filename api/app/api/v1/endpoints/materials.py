"""Materials + files endpoints.

Brief §6:
- POST /offerings/{id}/materials  (instructor uploads PDF or adds video link)
- PATCH /materials/{id}            (instructor edits: title/week/publish)
- GET /offerings/{id}/materials   (student/instructor lists)
- GET /files/{id}/download        (short-lived signed URL)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import (
    assert_in_same_department,
    get_current_user,
    require_instructor_or_higher,
)
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import CourseOffering, Material, User, UserRole
from app.models import File as FileModel
from app.models.enums import MaterialKind
from app.schemas.materials import (
    FileDownloadResponse,
    MaterialOut,
    MaterialUpdate,
    MaterialWithDownload,
)
from app.services.audit import write_audit
from app.services.notifications import broadcast_notification
from app.services.storage import compute_checksum, get_storage, make_storage_key

router = APIRouter()


# ── POST /offerings/{id}/materials — upload PDF OR add video/link ──
@router.post(
    "/offerings/{offering_id}/materials",
    response_model=MaterialOut,
    status_code=201,
)
async def create_material(
    offering_id: uuid.UUID,
    title: str = Form(..., min_length=1, max_length=255),
    kind: str = Form("pdf"),
    url: str | None = Form(None, max_length=1024),
    week_no: int | None = Form(None, ge=1, le=20),
    is_published: bool = Form(False),
    description: str | None = Form(None),
    file: UploadFile | None = File(None),
    creator: User = Depends(require_instructor_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    offering = db.get(CourseOffering, offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404, {"offering_id": str(offering_id)})

    # Scope: instructor must be the offering's instructor (or admin)
    if creator.role == UserRole.instructor:
        if not creator.staff or offering.instructor_id != creator.staff.user_id:
            raise APIError("NOT_SESSION_INSTRUCTOR", 403)
    elif creator.role == UserRole.dept_admin:
        if offering.course:
            assert_in_same_department(creator, offering.course.department_id)
    # college_admin / system_admin bypass

    try:
        kind_enum = MaterialKind(kind)
    except ValueError:
        raise APIError("VALIDATION_ERROR", 400, {"kind": kind})

    file_id: uuid.UUID | None = None
    material_url: str | None = None

    if kind_enum == MaterialKind.pdf:
        if file is None:
            raise APIError("VALIDATION_ERROR", 400, {"file": "required for kind=pdf"})
        # Validate mime + size
        if file.content_type not in settings.allowed_mime_list:
            raise APIError(
                "UPLOAD_TYPE_NOT_ALLOWED",
                415,
                {"mime": file.content_type, "allowed": settings.allowed_mime_list},
            )
        raw = await file.read()
        if len(raw) > settings.upload_max_bytes:
            raise APIError("UPLOAD_TOO_LARGE", 413, {"size": len(raw), "max": settings.upload_max_bytes})

        # Save to storage backend
        import io
        storage = get_storage()
        key = make_storage_key(mime=file.content_type, original_name=file.filename)
        storage.save(key=key, stream=io.BytesIO(raw), content_type=file.content_type)
        checksum = compute_checksum(io.BytesIO(raw))

        f = FileModel(
            storage_key=key,
            mime=file.content_type,
            size=len(raw),
            checksum=checksum,
            original_name=file.filename,
            uploader_id=creator.id,
        )
        db.add(f)
        db.flush()
        file_id = f.id
    elif kind_enum in (MaterialKind.video_link, MaterialKind.link):
        if not url:
            raise APIError("VALIDATION_ERROR", 400, {"url": "required for kind=video_link/link"})
        material_url = url
    else:
        raise APIError("VALIDATION_ERROR", 400, {"kind": kind})

    m = Material(
        offering_id=offering_id,
        title=title,
        kind=kind_enum,
        file_id=file_id,
        url=material_url,
        week_no=week_no,
        is_published=is_published,
        description=description,
    )
    db.add(m)
    db.flush()
    write_audit(
        db,
        actor_id=creator.id,
        action="create_material",
        entity="material",
        entity_id=str(m.id),
        after={"offering_id": str(offering_id), "title": title, "kind": kind_enum.value},
        request=request,
    )

    # If published, notify enrolled students + instructor
    if is_published:
        from app.services.notifications import resolve_announcement_audience
        from app.models import Announcement, AnnouncementScope
        fake = Announcement(
            scope=AnnouncementScope.offering,
            scope_id=str(offering_id),
            title="", body="",
        )
        audience = resolve_announcement_audience(db, fake)
        broadcast_notification(
            db,
            user_ids=audience,
            type_="new_material",
            title="محاضرة جديدة",
            body=f"تم نشر محاضرة جديدة: {title}",
            data={"offering_id": str(offering_id), "material_id": str(m.id)},
        )

    db.commit()
    db.refresh(m)
    return MaterialOut.model_validate(m)


# ── PATCH /materials/{id} ──
@router.patch("/materials/{material_id}", response_model=MaterialOut)
async def update_material(
    material_id: uuid.UUID,
    payload: MaterialUpdate,
    editor: User = Depends(require_instructor_or_higher),
    db: Session = Depends(get_db),
    request: Request = None,
):
    m = db.get(Material, material_id)
    if not m:
        raise APIError("NOT_FOUND", 404, {"material_id": str(material_id)})
    offering = db.get(CourseOffering, m.offering_id)
    if offering:
        if editor.role == UserRole.instructor:
            if not editor.staff or offering.instructor_id != editor.staff.user_id:
                raise APIError("NOT_SESSION_INSTRUCTOR", 403)
        elif editor.role == UserRole.dept_admin:
            if offering.course:
                assert_in_same_department(editor, offering.course.department_id)

    was_published = m.is_published
    if payload.title is not None:
        m.title = payload.title
    if payload.url is not None:
        m.url = payload.url
    if payload.week_no is not None:
        m.week_no = payload.week_no
    if payload.is_published is not None:
        m.is_published = payload.is_published
    if payload.description is not None:
        m.description = payload.description

    write_audit(db, actor_id=editor.id, action="update_material", entity="material",
                entity_id=str(m.id), request=request)

    # If newly published, notify
    if not was_published and m.is_published:
        from app.services.notifications import resolve_announcement_audience
        from app.models import Announcement, AnnouncementScope
        fake = Announcement(scope=AnnouncementScope.offering, scope_id=str(m.offering_id), title="", body="")
        audience = resolve_announcement_audience(db, fake)
        broadcast_notification(
            db, user_ids=audience, type_="new_material",
            title="محاضرة جديدة", body=f"تم نشر محاضرة جديدة: {m.title}",
            data={"offering_id": str(m.offering_id), "material_id": str(m.id)},
        )

    db.commit()
    db.refresh(m)
    return MaterialOut.model_validate(m)


# ── GET /offerings/{id}/materials ──
@router.get("/offerings/{offering_id}/materials", response_model=list[MaterialWithDownload])
async def list_materials(
    offering_id: uuid.UUID,
    week_no: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offering = db.get(CourseOffering, offering_id)
    if not offering:
        raise APIError("NOT_FOUND", 404, {"offering_id": str(offering_id)})

    # Students: must be enrolled OR materials must be published
    # Instructors: must be the offering's instructor (or admin)
    if user.role == UserRole.student:
        from app.models import Enrollment
        enrolled = db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == user.id,
                Enrollment.offering_id == offering_id,
            )
        )
        if not enrolled:
            raise APIError("NOT_ENROLLED", 403)
        # Students see only published materials
        q = select(Material).where(
            Material.offering_id == offering_id,
            Material.is_published.is_(True),
        )
    elif user.role == UserRole.instructor:
        if not user.staff or offering.instructor_id != user.staff.user_id:
            raise APIError("NOT_SESSION_INSTRUCTOR", 403)
        q = select(Material).where(Material.offering_id == offering_id)
    else:
        # admin — see all
        q = select(Material).where(Material.offering_id == offering_id)

    if week_no is not None:
        q = q.where(Material.week_no == week_no)
    q = q.order_by(Material.week_no.asc().nullslast(), Material.created_at.desc())
    items = db.scalars(q).all()

    storage = get_storage()
    out: list[MaterialWithDownload] = []
    for m in items:
        item = MaterialWithDownload.model_validate(m)
        if m.file_id and m.kind == MaterialKind.pdf:
            f = db.get(FileModel, m.file_id)
            if f:
                item.download_url = storage.download_url(key=f.storage_key, expires_in=300)
        out.append(item)
    return out


# ── GET /files/{id}/download ──
@router.get("/files/{file_id}/download", response_model=FileDownloadResponse)
async def get_download_url(
    file_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a short-lived signed URL for downloading the file.

    The URL is signed with the JWT secret; the client has 5 minutes to fetch it.
    """
    f = db.get(FileModel, file_id)
    if not f:
        raise APIError("NOT_FOUND", 404, {"file_id": str(file_id)})
    storage = get_storage()
    url = storage.download_url(key=f.storage_key, expires_in=300)
    return FileDownloadResponse(url=url, expires_in=300)


# ── GET /storage/{key} — local dev file serving (signed URL verified) ──
# This route is registered WITHOUT the /api/v1 prefix — see main.py.
@router.get("/storage/{shard}/{key}")
async def serve_local_file(shard: str, key: str, expires: int, sig: str):
    """Local dev file serving. Verifies the signed URL."""
    from app.services.storage import LocalDiskStorage, get_storage
    storage = get_storage()
    if not isinstance(storage, LocalDiskStorage):
        raise APIError("NOT_FOUND", 404)
    full_key = f"{shard}/{key}"
    if not storage.verify_signed_url(key=full_key, expires=expires, sig=sig):
        raise APIError("TOKEN_INVALID", 401, {"reason": "expired or invalid signature"})
    path = storage.read(key=full_key)
    if not path.exists():
        raise APIError("NOT_FOUND", 404)
    import mimetypes
    mime, _ = mimetypes.guess_type(str(path))
    from fastapi.responses import FileResponse
    return FileResponse(path=str(path), media_type=mime or "application/octet-stream")


# silence unused
_ = (datetime, timezone)
