"""Shared pytest fixtures.

Per brief rule §5: every endpoint is tested for success, wrong role,
wrong scope (IDOR), and invalid input. This conftest provides:
- A fresh in-memory SQLite DB per test
- A TestClient with auth helpers per role
- Helper factories for Excel files, attendance payloads, etc.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

# Set test env BEFORE importing app.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "")

# Make sure api/ is on sys.path when pytest runs from anywhere.
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_all  # noqa: E402


@pytest.fixture(scope="function")
def seeded_db():
    """Seed before each test so tests are isolated. Slower (~1s/test) but
    makes the suite robust against password/device changes."""
    Base.metadata.drop_all(bind=engine)
    seed_all(drop_first=True)
    yield


@pytest.fixture()
def client(seeded_db, monkeypatch):
    # Reset the in-memory rate-limit buckets between tests
    import app.api.v1.endpoints.auth as _auth
    _auth._LOGIN_BUCKETS.clear()
    # Don't enable rate-limiting unless the test opts in
    monkeypatch.delenv("ENABLE_LOGIN_RATELIMIT", raising=False)
    return TestClient(app)


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# ── Auth helpers ──
def login(client: TestClient, university_id: str, password: str = "Pass1234", device_fp: str | None = None) -> dict:
    payload = {"university_id": university_id, "password": password}
    if device_fp:
        payload["device_fingerprint"] = device_fp
    r = client.post("/api/v1/auth/login", json=payload)
    assert r.status_code == 200, f"login failed for {university_id}: {r.status_code} {r.text}"
    return r.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student_token(client):
    return login(client, "S1001", device_fp="student-fp-1")


@pytest.fixture()
def instructor_token(client):
    return login(client, "T1000")


@pytest.fixture()
def dept_admin_cs_token(client):
    return login(client, "DA_CS")


@pytest.fixture()
def dept_admin_is_token(client):
    return login(client, "DA_IS")


@pytest.fixture()
def college_admin_token(client):
    return login(client, "CA")


@pytest.fixture()
def system_admin_token(client):
    return login(client, "ROOT")


# ── Excel file builder for student import tests ──
def make_students_xlsx(rows: list[dict]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(
        ["university_id", "full_name_ar", "email", "phone", "department_code", "stage", "study_type", "group_name"]
    )
    for r in rows:
        ws.append(
            [
                r.get("university_id", ""),
                r.get("full_name_ar", ""),
                r.get("email", ""),
                r.get("phone", ""),
                r.get("department_code", "CS"),
                r.get("stage", 1),
                r.get("study_type", "morning"),
                r.get("group_name", "A"),
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
