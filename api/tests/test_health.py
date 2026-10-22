"""Health + meta endpoints."""
from __future__ import annotations


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_meta(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["docs"] == "/docs"


def test_public_config(client):
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["package_id"] == "iq.edu.qu.csit"
    assert body["timezone"] == "Asia/Baghdad"
    assert body["week_start"] == "sunday"
    assert body["maintenance"] is False


def test_openapi_lists_all_phase1_routes(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = set(r.json()["paths"].keys())
    required = {
        "/health",
        "/api/v1/config",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/change-password",
        "/api/v1/auth/me",
        "/api/v1/auth/devices/fcm-token",
        "/api/v1/admin/students/import",
        "/api/v1/admin/students/import/{batch_id}/commit",
        "/api/v1/admin/term-absence-rules",
        "/api/v1/admin/users/{user_id}/reset-password",
        "/api/v1/admin/users/{user_id}/toggle-status",
        "/api/v1/admin/users/unbind-device",
    }
    missing = required - paths
    assert not missing, f"missing routes: {missing}"
