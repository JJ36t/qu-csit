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
