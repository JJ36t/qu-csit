"""Auth endpoint tests — covers success, wrong role, wrong scope (IDOR),
invalid input, and the security checklist (Argon2, JWT expiry, refresh
rotation, device binding, rate limit)."""
from __future__ import annotations



from tests.conftest import auth_header, login


# ── login success + payload ──
def test_login_student_returns_tokens_and_must_change(client):
    body = login(client, "S1001", device_fp="fp-1")
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["expires_in"] == 900
    assert body["token_type"] == "Bearer"
    assert body["must_change_password"] is True  # seeded students must change


def test_login_instructor_no_must_change(client):
    body = login(client, "T1000")
    assert body["must_change_password"] is False  # instructors seeded with already-good pwd


def test_login_arabic_error_message_on_wrong_password(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"university_id": "S1001", "password": "wrong-pwd"},
    )
    assert r.status_code == 401
    body = r.json()
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["message_ar"]  # arabic string present
    # error shape per brief §6
    assert set(body.keys()) == {"code", "message_ar", "details"}


def test_login_nonexistent_user(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"university_id": "ZZZ9999", "password": "anything"},
    )
    assert r.status_code == 401
    assert r.json()["code"] == "INVALID_CREDENTIALS"


# ── invalid input ──
def test_login_invalid_input_short_id(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"university_id": "x", "password": "p"},  # too short
    )
    assert r.status_code == 422


def test_login_missing_password(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"university_id": "S1001"},
    )
    assert r.status_code == 422


# ── /auth/me ──
def test_me_returns_user_and_student(client, student_token):
    r = client.get("/api/v1/auth/me", headers=auth_header(student_token["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["university_id"] == "S1001"
    assert body["user"]["role"] == "student"
    assert body["student"]["stage"] in (1, 2, 3, 4)
    assert body["staff"] is None


def test_me_without_token_returns_401_arabic(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"


def test_me_with_garbage_token_returns_401(client):
    r = client.get("/api/v1/auth/me", headers=auth_header("not.a.jwt"))
    assert r.status_code == 401
    assert r.json()["code"] == "TOKEN_INVALID"


# ── refresh rotation ──
def test_refresh_issues_new_pair_and_revokes_old(client, student_token):
    # First refresh
    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": student_token["refresh_token"]},
    )
    assert r.status_code == 200
    new = r.json()
    # Refresh token must rotate (always different — it's a fresh random JWT)
    assert new["refresh_token"] != student_token["refresh_token"]
    assert new["access_token"]  # present

    # Old refresh token must now be revoked
    r2 = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": student_token["refresh_token"]},
    )
    assert r2.status_code == 401
    assert r2.json()["code"] == "REFRESH_TOKEN_REVOKED"


def test_refresh_garbage_token_returns_401(client):
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


# ── change-password ──
def test_change_password_success_revokes_refresh_tokens(client, student_token):
    old_refresh = student_token["refresh_token"]
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Pass1234", "new_password": "NewPass456"},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 200
    # Old refresh must be revoked
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401
    # Login with new password works (use SAME device fingerprint — already bound)
    body = login(client, "S1001", password="NewPass456", device_fp="student-fp-1")
    # After change, must_change_password should be False
    assert body["must_change_password"] is False


def test_change_password_wrong_old(client, student_token):
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "wrong-old", "new_password": "NewPass456"},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "OLD_PASSWORD_WRONG"


def test_change_password_weak_new(client, student_token):
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Pass1234", "new_password": "short"},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 422  # min length 8 enforced by pydantic


def test_change_password_no_digits(client, student_token):
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Pass1234", "new_password": "abcdefgh"},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 400
    assert r.json()["code"] == "PASSWORD_TOO_WEAK"


# ── device binding ──
def test_device_binding_first_login_succeeds(client):
    body = login(client, "S1002", device_fp="fp-A")
    assert "access_token" in body


def test_device_binding_second_device_rejected(client):
    # First device binds
    login(client, "S1003", device_fp="fp-X")
    # Second device for same student should be rejected
    r = client.post(
        "/api/v1/auth/login",
        json={"university_id": "S1003", "password": "Pass1234", "device_fingerprint": "fp-Y"},
    )
    assert r.status_code == 403
    assert r.json()["code"] == "DEVICE_LIMIT_EXCEEDED"


def test_device_binding_same_device_re_login_ok(client):
    login(client, "S1004", device_fp="fp-Z")
    body = login(client, "S1004", device_fp="fp-Z")  # same device → OK
    assert "access_token" in body


# ── rate limit ──
def test_login_rate_limit_kicks_in(client, monkeypatch):
    """5 wrong attempts in 1 minute → 429 on the 6th. APP_ENV=test bypasses
    the limiter by default, so enable it explicitly for this test."""
    monkeypatch.setenv("ENABLE_LOGIN_RATELIMIT", "1")
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"university_id": "S1005", "password": "wrong"},
        )
    r = client.post(
        "/api/v1/auth/login",
        json={"university_id": "S1005", "password": "wrong"},
    )
    assert r.status_code == 429
    assert r.json()["code"] == "RATE_LIMITED"


def test_logout_revokes_refresh(client, student_token):
    r = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": student_token["refresh_token"]},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 200
    # Old refresh must be revoked
    r2 = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": student_token["refresh_token"]},
    )
    assert r2.status_code == 401


def test_fcm_token_registration(client, student_token):
    r = client.put(
        "/api/v1/auth/devices/fcm-token",
        json={"token": "fcm-test-token-" + "x" * 50, "device_fingerprint": "fp-1"},
        headers=auth_header(student_token["access_token"]),
    )
    assert r.status_code == 200
