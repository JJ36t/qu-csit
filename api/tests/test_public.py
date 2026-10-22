"""Public endpoints tests — privacy, maintenance, app version, stats."""
from __future__ import annotations


def test_privacy_policy_arabic(client):
    r = client.get("/api/v1/public/privacy")
    assert r.status_code == 200
    data = r.json()
    assert data["lang"] == "ar"
    assert "الخصوصية" in data["title"]
    assert "جامعة القادسية" in data["policy"]
    assert "Argon2id" in data["policy"]
    assert "الموقع" in data["policy"]


def test_privacy_policy_english(client):
    r = client.get("/api/v1/public/privacy?lang=en")
    assert r.status_code == 200
    data = r.json()
    assert data["lang"] == "en"
    assert "Privacy" in data["title"]
    assert "University of Al-Qadisiyah" in data["policy"]
    assert "Argon2id" in data["policy"]


def test_privacy_policy_no_auth_required(client):
    """Privacy policy must be accessible without authentication."""
    r = client.get("/api/v1/public/privacy")
    assert r.status_code == 200


def test_maintenance_status(client):
    r = client.get("/api/v1/public/maintenance")
    assert r.status_code == 200
    data = r.json()
    assert "maintenance" in data
    assert "message_ar" in data
    assert "message_en" in data
    assert data["maintenance"] is False  # not in maintenance mode


def test_app_version_check_no_update_needed(client):
    r = client.get("/api/v1/public/app-version?platform=android&version=0.1.0")
    assert r.status_code == 200
    data = r.json()
    assert data["update_required"] is False
    assert data["min_version"] == "0.1.0"
    assert "play.google.com" in data["download_url"]


def test_app_version_check_update_required(client):
    """Client with version 0.0.1 should be told to update."""
    r = client.get("/api/v1/public/app-version?platform=android&version=0.0.1")
    assert r.status_code == 200
    data = r.json()
    assert data["update_required"] is True


def test_app_version_invalid_version_format(client):
    """Malformed version should not crash — returns update_required=True."""
    r = client.get("/api/v1/public/app-version?platform=android&version=garbage")
    assert r.status_code == 200
    data = r.json()
    # _version_lt("garbage", "0.1.0") returns True (can't parse → treat as older)
    assert data["update_required"] is True


def test_public_stats(client):
    r = client.get("/api/v1/public/stats")
    assert r.status_code == 200
    data = r.json()
    assert "students" in data
    assert "instructors" in data
    assert "courses" in data
    assert "departments" in data
    assert data["students"] >= 30  # seeded
    assert data["departments"] >= 2  # CS + IS


def test_public_stats_no_auth_required(client):
    """Stats must be accessible without authentication (for store landing page)."""
    r = client.get("/api/v1/public/stats")
    assert r.status_code == 200
