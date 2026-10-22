# Decisions Log

Ambiguities resolved with the simplest option. Open questions from brief §12 are NOT decided here — they wait for the user at Gate 0.

## D001 — Local dev database
- **Decision**: SQLite (`dev.db`) for local dev + tests; PostgreSQL in Docker Compose for prod. `DATABASE_URL` env var selects dialect.
- **Reason**: build host has no Docker/Postgres. SQLite via SQLAlchemy keeps the ORM portable; Alembic migrations are written PostgreSQL-friendly (avoid SQLite-only features, use generic types).
- **Risk**: PostgreSQL-specific types (UUID, JSONB, INTERVAL) need careful Alembic rendering. Mitigation: use `sqlalchemy.UUID` (server_default for postgres only) and `JSON` (maps to JSONB on PG, JSON on SQLite). Test migrations on SQLite; note that prod migration is run on PG.

## D002 — Arabic strings in code
- **Decision**: API error messages stored in a single `app/i18n/errors_ar.py` dict keyed by code; returned as `message_ar`. No hardcoded Arabic scattered in handlers.
- **Reason**: brief §6 requires `{code, message_ar, details}` and brief §1 rule 3 forbids hardcoded Arabic in Dart (mirrored on the backend).

## D003 — Password hashing
- **Decision**: `argon2-cffi` with `argon2id`, params: `memory_cost=19456, time_cost=2, parallelism=1` (OWASP recommendation tier).
- **Reason**: brief §9 security checklist requires Argon2.

## D004 — JWT
- **Decision**: `PyJWT`, Access 15 min, Refresh 30 days rotating, stored hashed (SHA-256) in `refresh_tokens`.
- **Reason**: brief §5.1.

## D005 — Rate limiting
- **Decision**: `slowapi` with in-memory backend for dev, Redis backend ready for prod. Login: 5/min per (university_id + IP).
- **Reason**: brief §5.1.

## D006 — Timezone
- **Decision**: store all timestamps UTC (DateTime with timezone). Convert to `Asia/Baghdad` for display. Weekday numbering: Mon=0..Sun=6 (Python default); timetable `weekday` field uses 0=Sunday..4=Thursday for clarity (documented).
- **Reason**: brief §1 rule 4.

## D007 — Excel import
- **Decision**: `openpyxl` for parsing. Two-phase: `POST /admin/students/import?dry_run=true` returns preview + row errors + a `batch_id`; `POST /admin/students/import/{batch_id}/commit` persists (batch cached in Redis 10 min).
- **Reason**: brief §6 admin import spec.

## D008 — File storage abstraction
- **Decision**: `app/services/storage.py` with `StorageBackend` protocol; `LocalDiskStorage` for dev, `S3Storage` stub for prod (not implemented, raises NotImplementedError).
- **Reason**: brief §7 storage note.

## D009 — FCM
- **Decision**: `firebase-admin` SDK for HTTP v1. Background worker (`arq`) batches sends. FCM not exercised in dev (no credentials); the pipeline is wired but no-ops if `FIREBASE_CREDENTIALS_JSON` unset.
- **Reason**: brief §5.4 + §7.

## D010 — Background jobs
- **Decision**: `arq` (asyncio + Redis). Dev fallback: if Redis unavailable, jobs run inline via `asyncio.create_task` (with a warning log) so the API still works for local dev/tests.
- **Reason**: build host has no Redis; tests must pass.

## D011 — Flutter not compiled here
- **Decision**: Flutter source tree is authored completely and linted structurally; not compiled because no SDK. `analysis_options.yaml` included.
- **Reason**: environment.

## D012 — App name / package id (RESOLVED ✅)
- **Decision**: Arabic display name `علوم الحاسوب`, English `QU CSIT`, package id `iq.edu.qu.csit`.
- **Source**: User Gate 0 answer, 2026-10-23.

## D013 — Absence rule (RESOLVED, with placeholder ✅)
- **Decision**: configurable per-term in the DB via the new `term_absence_rules` table; editable from admin panel. Placeholder defaults until the department confirms: `max_absences_per_course=10`, `late_threshold_minutes=15`, `late_counts_as_absence=False`, `attendance_warning_threshold=8`.
- **Resolution path**: dept confirms official rule → admin updates the row from the panel. No code change needed.
- **Source**: User Gate 0 answer, 2026-10-23.

## D014 — Grades in first release (RESOLVED ✅)
- **Decision**: tables `assessments` and `grades` are CREATED (migration stable) but NO endpoints/screens in MVP.
- **Source**: User Gate 0 answer, 2026-10-23.

## D015 — Study days + scope model (RESOLVED ✅)
- **Decision**: study week Sun–Thu, configurable via `APP_WEEK_START` env. Departments/stages/groups are NOT hardcoded — seeded with fake data (2 depts × 4 stages × 2 groups per stage) and entered for real via the admin panel. Slot start/end times are free-form per slot (no fixed hourly grid).
- **Source**: User Gate 0 answer, 2026-10-23.

## D016 — Hosting (RESOLVED ✅)
- **Decision**: external VPS for dev+pilot, everything in Docker Compose so it can be lifted to a university server later without code changes. `docker-compose.yml` has all 5 services (api, worker, postgres, redis, caddy, admin).
- **Source**: User Gate 0 answer, 2026-10-23.

## D017 — SQLite datetime handling
- **Decision**: SQLite returns naive datetimes even when columns are declared `DateTime(timezone=True)`. Code that compares DB-stored timestamps against `datetime.now(timezone.utc)` must normalize via `.replace(tzinfo=timezone.utc)` when `tzinfo is None`. Centralized in `auth.py` refresh handler; apply the same pattern in attendance endpoints (Phase 4).
- **Reason**: discovered via test failure; affects any time-aware comparison.

## D018 — Login rate limit in tests
- **Decision**: rate limiter is bypassed when `APP_ENV=test` UNLESS the test sets `ENABLE_LOGIN_RATELIMIT=1` env var. The single dedicated rate-limit test does this. Without the bypass, the shared TestClient IP causes cascading 429s across the suite.
- **Reason**: test isolation; in production the limiter is always on (uses slowapi+Redis).
