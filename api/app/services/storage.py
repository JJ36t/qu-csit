"""File storage abstraction.

- LocalDiskStorage for dev (writes to STORAGE_LOCAL_DIR, serves via STORAGE_BASE_URL)
- S3Storage for prod (boto3, pre-signed URLs for download)

Both produce a `storage_key` that goes in the `files` table and a `download_url`
that the client uses. Downloads use short-lived signed URLs (5 min default).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import IO

from app.core.config import settings


class StorageBackend:
    """Interface — both backends implement these."""

    def save(self, *, key: str, stream: IO[bytes], content_type: str) -> str:
        """Save the stream under `key`. Returns the storage_key actually used."""
        raise NotImplementedError

    def download_url(self, *, key: str, expires_in: int = 300) -> str:
        """Return a short-lived signed URL for downloading."""
        raise NotImplementedError

    def delete(self, *, key: str) -> None:
        raise NotImplementedError


class LocalDiskStorage(StorageBackend):
    def __init__(self, base_dir: str, base_url: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def save(self, *, key: str, stream: IO[bytes], content_type: str) -> str:
        # Use a sharded layout: first 2 chars of key / key
        shard = key[:2]
        shard_dir = self.base_dir / shard
        shard_dir.mkdir(parents=True, exist_ok=True)
        path = shard_dir / key
        with open(path, "wb") as f:
            while True:
                chunk = stream.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        return key

    def download_url(self, *, key: str, expires_in: int = 300) -> str:
        # Signed URL: key + expiry + HMAC (so the client can't tamper with expiry)
        import hmac

        expiry = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp())
        msg = f"{key}|{expiry}".encode()
        sig = hmac.new(settings.jwt_secret.encode(), msg, hashlib.sha256).hexdigest()
        return f"{self.base_url}/{key}?expires={expiry}&sig={sig}"

    def verify_signed_url(self, *, key: str, expires: int, sig: str) -> bool:
        import hmac

        msg = f"{key}|{expires}".encode()
        expected = hmac.new(settings.jwt_secret.encode(), msg, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return False
        return datetime.now(timezone.utc).timestamp() < expires

    def read(self, *, key: str) -> Path:
        shard = key[:2]
        return self.base_dir / shard / key

    def delete(self, *, key: str) -> None:
        shard = key[:2]
        path = self.base_dir / shard / key
        if path.exists():
            path.unlink()


class S3Storage(StorageBackend):
    """Production S3 storage. Uses boto3; pre-signed URLs for download."""

    def __init__(self, bucket: str, region: str):
        self.bucket = bucket
        self.region = region
        # Lazy-import so tests/dev don't need AWS credentials.
        import boto3
        self._client = boto3.client("s3", region_name=region)

    def save(self, *, key: str, stream: IO[bytes], content_type: str) -> str:
        self._client.upload_fileobj(stream, self.bucket, key, ExtraArgs={"ContentType": content_type})
        return key

    def download_url(self, *, key: str, expires_in: int = 300) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete(self, *, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)


def get_storage() -> StorageBackend:
    if settings.storage_backend == "s3":
        return S3Storage(bucket=settings.s3_bucket, region=settings.s3_region)
    return LocalDiskStorage(
        base_dir=settings.storage_local_dir,
        base_url=settings.storage_base_url,
    )


def make_storage_key(*, mime: str, original_name: str | None = None) -> str:
    """Generate a random storage key with a sensible extension."""
    ext = ""
    if original_name and "." in original_name:
        ext = "." + original_name.rsplit(".", 1)[-1].lower()
    elif mime:
        # Map common mimes to extensions
        mime_to_ext = {
            "application/pdf": ".pdf",
            "video/mp4": ".mp4",
            "image/png": ".png",
            "image/jpeg": ".jpg",
        }
        ext = mime_to_ext.get(mime, "")
    return secrets.token_hex(16) + ext


def compute_checksum(stream: IO[bytes]) -> str:
    """SHA-256 checksum of a stream."""
    h = hashlib.sha256()
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        h.update(chunk)
    stream.seek(0)
    return h.hexdigest()
