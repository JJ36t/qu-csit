# QU-CSIT

Official Android app + REST API + web admin panel for the
**College of Computer Science and Information Technology, University of Al-Qadisiyah**.

## Repo layout (monorepo)

```
qu_csit/
├── api/         # FastAPI backend + arq worker
├── app/         # Flutter Android app (Arabic RTL)
├── admin/       # React + Vite + AntD admin panel (RTL)
├── deploy/      # Caddy config + ops scripts
├── docs/        # PROGRESS.md, DECISIONS.md, ARCHITECTURE
└── docker-compose.yml
```

## Quick start (dev — no Docker required)

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # uses SQLite + inline jobs → no Postgres/Redis needed
uvicorn app.main:app --reload  # http://localhost:8000/docs
```

## Quick start (prod-like, all services)

```bash
cp api/.env.example api/.env
# edit POSTGRES_PASSWORD, JWT_SECRET, FIREBASE_CREDENTIALS_JSON, DOMAIN
docker compose up --build
```

## Docs

- `docs/PROGRESS.md` — phase-by-phase progress log
- `docs/DECISIONS.md` — engineering decisions
- API docs: `/docs` once the server is running

## Status

Phase 0 (scaffold) — see `docs/PROGRESS.md`.
