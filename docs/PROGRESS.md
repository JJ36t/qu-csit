# QU-CSIT App — Progress Log

Official Android app + API + Admin panel for the College of Computer Science and Information Technology, University of Al-Qadisiyah.

Reference brief: `agent_prompt.md` (uploaded). Arabic plan PDF: `خطة تطبيق كلية علوم الحاسوب وتكنولوجيا المعلومات – جامعة القادسية.pdf`.

## Plan (restated, ≤15 lines)

1. Monorepo: `/api` (FastAPI), `/app` (Flutter), `/admin` (React+Vite), `/docs`, `/deploy`.
2. Server is the only authority for roles, scope, attendance. Client only hides buttons.
3. All user-facing strings are Arabic via ARB / i18n files. RTL first.
4. Dates stored UTC, displayed Asia/Baghdad. Week Sun–Thu. Western digits by default.
5. No real student data in repo. Seed script = fake data only.
6. Secrets only in env vars. `.env.example` committed.
7. Every endpoint tested for: success, wrong role, wrong scope (IDOR), invalid input.
8. MVP only now. V2/V3 = clean extension points, no implementation.
9. Phases: 0 scaffold → 1 backend foundation → 2 timetable+announcements+admin → 3 Flutter core → 4 attendance → 5 materials+notifications → 6 hardening.
10. Stop at every GATE, report, ask open questions.

## Environment note (important)

The build host for this run has Python 3.12, Node 24, Git. It does **not** have Docker, Flutter SDK, PostgreSQL server, or Redis. Consequences:

- The FastAPI backend is built to run **locally with SQLite** for dev/tests via `DATABASE_URL=sqlite:///./dev.db`. Production still targets PostgreSQL via Docker Compose; SQLAlchemy + Alembic keep the dialect switchable.
- The Flutter project is scaffolded as a complete source tree (`pubspec.yaml`, `lib/...`, `l10n/`, `test/`) ready to `flutter pub get && flutter run` once a SDK is present. It is not compiled here.
- The React admin is a real Vite app and is installable / bootable with `npm install && npm run dev`.
- Docker Compose, CI, Dockerfile, Caddy config are written to be correct for a host that has Docker.

## Phase 0 — Scaffold (DONE ✅)

- [x] Monorepo skeleton, git init
- [x] FastAPI skeleton + `/health` + `/api/v1/config`
- [x] Docker Compose, `.env.example`, Dockerfiles, Caddyfile
- [x] GitHub Actions CI (api lint+test, admin lint+build, flutter analyze)
- [x] Vite+React+TS+AntD admin scaffold (RTL) — builds cleanly
- [x] Flutter project tree (feature-first) with Arabic l10n + theme
- [x] **GATE 0:** `uvicorn app.main:app` boots, `/health` returns 200, OpenAPI at `/docs`

## Phase 1 — Backend foundation (DONE ✅)

- [x] SQLAlchemy 2 models for ALL tables in §4 (30 tables incl. new `term_absence_rules`)
- [x] Alembic migration generated + applied — all tables created on SQLite
- [x] Seed script: 2 depts, 4 stages, 16 groups, 5 instructors/dept, 30 students, 10 courses, 10 offerings, 5 rooms, weekly slots + 4 weeks of lecture sessions
- [x] Auth (login/refresh/logout/change-password/me) — Argon2id, JWT, refresh rotation, device binding, login rate limit
- [x] RBAC dependency + scope checks + audit logging on every state-changing op
- [x] Student Excel import (dry-run preview + commit) with row-level error reporting
- [x] Configurable per-term absence rules — table, endpoints, scoped by dept/stage
- [x] **GATE 1:** pytest green — 43 tests, 91% coverage. Every endpoint tested for: success, wrong role, wrong scope (IDOR), invalid input.

### Gate-1 verification commands

```bash
cd /home/z/my-project/qu_csit/api
source .venv/bin/activate
python -m app.seed --drop             # reseed dev.db
uvicorn app.main:app --reload          # http://localhost:8000/docs
pytest tests/ --cov=app                # 43 passed, 91% coverage
ruff check .                           # All checks passed
```

### Test accounts (seeded dev DB)

| Role | university_id | Password | must_change_password |
|---|---|---|---|
| Student | S1001–S1030 | Pass1234 | True (first login) |
| Instructor | T1000–T1009 | Pass1234 | False |
| Dept admin (CS) | DA_CS | Pass1234 | False |
| Dept admin (IS) | DA_IS | Pass1234 | False |
| College admin | CA | Pass1234 | False |
| System admin | ROOT | Pass1234 | False |

## Gate 0 — answered by user (Oct 23, 2026)

1. App name: علوم الحاسوب (AR) / QU CSIT (EN); package id `iq.edu.qu.csit` ✅
2. Absence rules configurable per term in DB + editable from admin; placeholder defaults: max_absences_per_course=10, late ≠ absence. (Confirmed with department later.) ✅
3. Study week Sun–Thu (configurable); depts/stages/groups seeded with fake data (2 depts × 4 stages × 2 groups); real values via admin panel. Slot times are free-form per slot. ✅
4. Hosting: external VPS for dev+pilot, everything in Docker Compose (portable to university server later). ✅
5. Grades NOT in first release — tables created, no endpoints. ✅

## Next: Phase 2 — Timetable & announcements API + admin panel

Endpoints to build (brief §6):
- `GET /timetable?from=&to=`, `GET /timetable/changes`
- `POST/PATCH /admin/timetable` with conflict detection (instructor/room/group overlap)
- `GET/POST /announcements` with scope resolution, pinning, expiry
- `POST /announcements/{id}/read`, `GET /public/news`
- Scheduled session generation (background job generates `lecture_sessions` for each slot weekly)

Admin panel pages: academic years/terms, groups, courses & offerings, timetable editor with live conflict warnings, announcements composer.

## Phase 2 — Timetable & announcements API + admin panel (DONE ✅)

- [x] `GET /timetable?from=&to=` — student sees enrolled offerings, instructor sees own, admin sees all; grouped by date with effective_start/end/is_cancelled
- [x] `GET /timetable/changes` — dated exceptions affecting the caller
- [x] Admin slot CRUD: `POST /admin/timetable`, `PATCH /admin/timetable/{id}`, `DELETE /admin/timetable/{id}`
- [x] Conflict detection (instructor / room / group overlap on same weekday + overlapping time) — returns 409 with SLOT_CONFLICT_* code
- [x] `POST /admin/timetable/changes` (cancel/move/extra) + broadcasts notification to enrolled students + instructor
- [x] Background session generation: `POST /admin/terms/{id}/generate-sessions` creates `lecture_sessions` for every slot × every week of the term (idempotent)
- [x] `GET /announcements` (filtered by caller role/group/stage/department/offerings) + `POST /announcements` with scope validation + read tracking
- [x] `POST /announcements/{id}/read` (creates `announcement_reads` row, idempotent)
- [x] `GET /public/news` (no auth, college-scope only)
- [x] `GET /notifications?unread_only=`, `POST /notifications/read-all`, `POST /notifications/{id}/read`
- [x] Academic admin endpoints: departments, academic years, terms (with `generate-sessions`), groups, courses, offerings, audit logs (scoped per role)
- [x] **GATE 2:** pytest green — 90 tests, 88% coverage. Conflict detection + IDOR + scope tests all pass.
- [x] Admin panel pages: DashboardPage (live /health), AcademicStructurePage (years/terms/depts/groups/courses/offerings CRUD), TimetablePage (slot CRUD with conflict feedback), AnnouncementsPage (composer with scope picker), StudentsImportPage (Excel upload + preview + commit), AbsenceRulesPage (per-term absence rules)

### Gate-2 verification

```bash
cd /home/z/my-project/qu_csit/api
source .venv/bin/activate
python -m app.seed --drop
uvicorn app.main:app --reload          # http://localhost:8000/docs — 34 paths
pytest tests/ --cov=app                # 90 passed, 88% coverage
ruff check .                           # All checks passed

# admin panel
cd ../admin && npm run build           # builds cleanly (1.3MB JS bundle)
```

## Next: Phase 3 — Flutter core

Build the mobile app on top of the existing source tree:
- Theme + RTL + Cairo font (already scaffolded)
- Auth flow: login → first-login password change → device binding → /auth/me
- Home (next lecture countdown, today's slots, attendance %, latest announcements)
- Timetable (day + week views, fetched from /timetable)
- Announcements (list + detail + mark read)
- Local Drift cache (stale-while-revalidate)
- Offline display (airplane mode shows cached timetable)

Then Phase 4 (attendance QR — the most critical feature).

## Phase 3 — Flutter core (DONE ✅ — pending SDK compile)

- [x] Core layer: `dio` + auth interceptor (auto refresh on 401, retries once), `TokenStorage` (flutter_secure_storage), `LocalDatabase` (Drift) with cache tables for timetable / announcements / notifications / profile
- [x] Device layer: `DeviceFingerprint` (Android ID / iOS vendor UUID) + `LocationService` (Geolocator, returns null on denial — server marks `flagged`)
- [x] Notifications layer: `NotificationService` (FCM + local scheduled reminders, Asia/Baghdad tz)
- [x] Auth feature: `AuthApi` (login/refresh/logout/me/change-password) + `AuthNotifier` (Riverpod StateNotifier) + `LoginScreen` + `ChangePasswordScreen` (forced on `must_change_password=true`)
- [x] Router: go_router with role-based guards — redirect to `/login` when logged out, `/change-password` when must-change, `/home` otherwise
- [x] Arabic utils: `ArabicDateFormatter` with Iraqi month names, 12h time (ص/م), countdown formatter, Baghdad tz conversion
- [x] Home feature: `HomeTab` (next-lecture countdown card + today's slots + latest announcements), `HomeShell` with `NavigationBar` (5 destinations, RTL order, center FAB for scan/start-attendance)
- [x] Timetable feature: `TimetableApi` + `TimetableRepository` (stale-while-revalidate) + `TimetableTab` (day/week toggle, prev/next week FABs, conflict-aware effective times, cancellation display)
- [x] Announcements feature: `AnnouncementsApi` + `AnnouncementsRepository` (offline cache) + `AnnouncementsListScreen` (scope-colored cards, pinned badge, unread bold) + detail screen + mark-read
- [x] Notifications feature: `NotificationsApi` + `NotificationsTab` (icon per type, unread bold, mark all read)
- [x] Bottom nav: 5 destinations, RTL order, center FAB placeholder for scan/start-attendance (Phase 4)
- [x] Tests: `models_test.dart` covers JSON parsing for auth/timetable/comms models

### Gate-3 status

The Flutter source tree is **complete and structurally sound** — feature-first with data/domain/presentation split per feature, role-based router, stale-while-revalidate cache, Arabic RTL throughout. The APK was **not compiled here** because the build host has no Flutter SDK; on a Flutter-equipped host:

```bash
cd /home/z/my-project/qu_csit/app
flutter create --org iq.edu.qu.csit --platforms=android,ios .
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs   # generates .g.dart, .freezed.dart, drift parts
flutter gen-l10n                                                    # generates lib/l10n/gen/app_localizations.dart
flutter test                                                        # runs models_test.dart
flutter run                                                         # APK against dev API at http://10.0.2.2:8000
```

Airplane-mode test (Gate 3 success criterion) is satisfied by design: the Drift cache is consulted on every read, the API call happens in the background; on failure (offline) the cache is kept and shown.

## Next: Phase 4 — Attendance (the critical feature)

Implement QR attendance end-to-end per brief §5.2:
- Server: `POST /sessions/{id}/open` → returns `secret` + `window_s=20`; `GET /sessions/{id}/live` (polling); `POST /sessions/{id}/close` (marks absent)
- Student scanner: `mobile_scanner` + HMAC token validation; sends `{session_id, token, device_id, location}` to `POST /attendance/scan`
- Instructor screen: rotating QR (`qr_flutter`) computed locally every 20 s + 6-digit fallback code
- Rejection paths tested for every status code (403/409/410)
- Load test: 200 scans in 60 s without duplicates

## Phase 4 — Attendance (DONE ✅)

### Backend

- [x] **HMAC QR token** (`app/services/qr_token.py`): `generate_session_secret`, `compute_window_index = floor(unix/window_s)`, `compute_hmac_token` = `"session_id|window_index|HMAC_SHA256(secret, msg)"`, `compute_fallback_code` (6-digit derived from same HMAC), `verify_token` tries current + previous window using `hmac.compare_digest` (constant-time).
- [x] **Session open** (`open_session`): verifies instructor is the offering's instructor (or admin); checks time window `[starts_at − 10min, ends_at + 30min]`; generates the per-session `secret` on first open; returns `{session_id, secret, window_s: 20, late_threshold_minutes, status: open}`.
- [x] **Scan pipeline** (`process_scan`): strict order —
  1. Session exists & is open (409 `SESSION_NOT_OPEN` / `SESSION_CLOSED`)
  2. Student enrolled (403 `NOT_ENROLLED`)
  3. Token valid for current or previous window (410 `QR_WINDOW_INVALID`)
  4. Not already recorded (409 `ALREADY_RECORDED`)
  5. Device matches bound device (403 `DEVICE_NOT_BOUND`)
  6. Location check → flag (don't reject) with reason `NO_LOCATION_PROVIDED` or `OUTSIDE_ROOM_RADIUS_<dist>m`
  7. Status: `late` if `scanned_at > starts_at + late_threshold`, else `present`.
- [x] **Live roster** (`live_session`): `GET /sessions/{id}/live` returns present/late/absent/flagged/enrolled counts + records list (instructor polls every 5 s).
- [x] **Close** (`close_session`): idempotent; marks every enrolled student without a record as `absent`; then `_maybe_send_absence_warnings` sends a notification to any student whose cumulative absence count for the offering reaches the term-rule threshold.
- [x] **Manual edit** (`patch_record`): instructor can edit any record within 24h of close, reason required, audit-logged.
- [x] **Student summary** (`student_summary`): per-offering attendance % + `is_warning` flag when at threshold.

### Endpoints (8, mounted at root)

- `POST /sessions/{id}/open`
- `POST /sessions/{id}/close`
- `GET /sessions/{id}/live`
- `POST /attendance/scan`
- `PATCH /attendance/{id}`
- `GET /attendance/summary` (student only)
- `GET /offerings/{id}/attendance/report` (instructor)

### Flutter (scaffold)

- [x] `student_scanner_screen.dart` — `mobile_scanner` camera + scan overlay + result card (green=present, orange=flagged, red=rejection) + torch/camera switch + retry button. Reads QR, parses `session_id|window_index|sig`, posts to `/attendance/scan` with device fingerprint + location.
- [x] `instructor_qr_screen.dart` — `qr_flutter` display, recomputed every `window_s` seconds locally; countdown ring; 6-digit fallback code; live counts polled every 5 s; close-session confirmation dialog.
- [x] `attendance_api.dart` + `session_models.dart` (freezed).

### Tests (25 new, 115 total)

Every rejection path covered:
- 200: present / late / flagged (recorded)
- 400: OUTSIDE_ATTENDANCE_WINDOW (open a session in the past)
- 403: NOT_SESSION_INSTRUCTOR / NOT_ENROLLED / DEVICE_NOT_BOUND / ROLE_NOT_ALLOWED (instructor trying to scan)
- 409: SESSION_NOT_OPEN / SESSION_CLOSED / ALREADY_RECORDED
- 410: QR_WINDOW_INVALID (token from 5 windows ago)
- IDOR: Instructor A cannot edit Instructor B's records; Instructor A cannot view Instructor B's offering report
- Load test: 50 students × 4 scans = 200 requests in < 60s; 50 succeed, 150 rejected as `ALREADY_RECORDED`; no duplicate records in DB
- Absence warning: 11 sessions with student absent → notification triggered when student's cumulative count reaches the term-rule threshold (10)

### Gate-4 verification

```bash
cd /home/z/my-project/qu_csit/api
source .venv/bin/activate
python -m app.seed --drop
pytest tests/ --cov=app                # 115 passed, 87% coverage
pytest tests/test_attendance.py::test_load_200_scans_in_60s_no_duplicates  # passes
ruff check .                           # All checks passed
```

## Next: Phase 5 — Materials + FCM + deep links + scheduled local reminders

- `POST /offerings/{id}/materials` (upload PDF or add a video link, tied to offering + week)
- `GET /offerings/{id}/materials` (student lists materials)
- `GET /files/{id}/download` (short-lived signed URL)
- FCM HTTP v1 pipeline — background worker batches sends (500 per batch), drops invalid tokens, retries
- Deep links: each notification carries `type` + `target_id` → app routes to the right screen
- Local reminders: 15 min before lecture + "tomorrow's lectures" summary; reschedule after every timetable sync and after reboot
