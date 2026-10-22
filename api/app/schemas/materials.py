"""Schemas for materials + files."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MaterialKind


class MaterialCreate(BaseModel):
    """Create a material. Either `file` upload OR `url` is required depending on `kind`."""

    title: str = Field(min_length=1, max_length=255)
    kind: MaterialKind = MaterialKind.pdf
    url: str | None = Field(default=None, max_length=1024)
    week_no: int | None = Field(default=None, ge=1, le=20)
    is_published: bool = False
    description: str | None = None


class MaterialUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, max_length=1024)
    week_no: int | None = Field(default=None, ge=1, le=20)
    is_published: bool | None = None
    description: str | None = None


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    storage_key: str
    mime: str
    size: int
    checksum: str | None
    original_name: str | None


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    offering_id: uuid.UUID
    title: str
    kind: MaterialKind
    file_id: uuid.UUID | None
    url: str | None
    week_no: int | None
    is_published: bool
    description: str | None
    created_at: datetime


class MaterialWithDownload(MaterialOut):
    """MaterialOut + a short-lived download URL (for PDF materials)."""
    download_url: str | None = None


class FileDownloadResponse(BaseModel):
    """Response for /files/{id}/download — a short-lived signed URL."""
    url: str
    expires_in: int
