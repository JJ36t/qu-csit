"""HMAC-based time-windowed QR token for attendance.

Brief §5.2:
1. Instructor opens a session → server generates a random `secret` (per session).
2. The instructor's phone displays a QR that changes every `window_s` (default 20s):
   payload = `session_id | window_index | HMAC_SHA256(secret, session_id|window_index)`
   where `window_index = floor(unix_time / window_s)`.
3. The HMAC is computed LOCALLY on the instructor's phone (works with weak internet).
4. The student scans → sends `{session_id, token, device_id, location}` to /attendance/scan.
5. Server validates the token against the current OR previous window (allows for
   scan-in-flight delay). A token older than 1 window is rejected (410).
"""
from __future__ import annotations

import hashlib
import hmac
import time
import uuid


def generate_session_secret() -> str:
    """A 32-byte random hex secret — one per session."""
    return hashlib.sha256(uuid.uuid4().bytes + uuid.uuid4().bytes).hexdigest()


def compute_window_index(now_unix: int | None = None, window_s: int = 20) -> int:
    """`window_index = floor(unix_time / window_s)`."""
    return (now_unix if now_unix is not None else int(time.time())) // window_s


def compute_hmac_token(
    *,
    session_id: str | uuid.UUID,
    window_index: int,
    secret: str,
) -> str:
    """Returns the canonical QR token string `session_id|window_index|sig`."""
    msg = f"{session_id}|{window_index}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"{session_id}|{window_index}|{sig}"


def compute_fallback_code(
    *,
    session_id: str | uuid.UUID,
    window_index: int,
    secret: str,
) -> str:
    """6-digit numeric code (alternative when the camera can't see the QR).
    Derived from the same HMAC, truncated to 6 digits.
    """
    msg = f"{session_id}|{window_index}".encode()
    full = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    # Take the last 8 hex chars → 32-bit int → mod 1e6 → pad to 6 digits
    return str(int(full[-8:], 16) % 1_000_000).zfill(6)


def verify_token(
    *,
    token: str,
    session_id: str | uuid.UUID,
    secret: str,
    window_s: int = 20,
    now_unix: int | None = None,
    allow_previous_window: bool = True,
) -> tuple[bool, int | None]:
    """Verify a token. Returns (valid, window_index_used).

    Tries the current window first; if allow_previous_window, also tries
    the immediately preceding window (covers a scan that was in-flight when
    the QR rotated).
    """
    current = compute_window_index(now_unix, window_s)
    candidates = [current]
    if allow_previous_window:
        candidates.append(current - 1)

    for w in candidates:
        expected = compute_hmac_token(
            session_id=session_id,
            window_index=w,
            secret=secret,
        )
        # Constant-time compare to prevent timing attacks.
        if hmac.compare_digest(expected, token):
            return (True, w)
    return (False, None)


def parse_token(token: str) -> tuple[str, int] | None:
    """Parse `session_id|window_index|sig` → (session_id, window_index).

    Used by the instructor phone to know which window the QR is for
    (purely informational; the server re-derives it from time).
    """
    parts = token.split("|")
    if len(parts) != 3:
        return None
    try:
        return (parts[0], int(parts[1]))
    except ValueError:
        return None
