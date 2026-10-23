# Supply-Chain Reconciliation Engine

Production-style Applied AI portfolio project: extract structured data from purchase orders, delivery documents, and supplier invoices, then reconcile them with **deterministic** business rules.

**MATCHED is not payment authorization.** This system supports review; it never executes payments.

## Security limitation (MVP)

There is **no authentication** in the local MVP. Do **not** expose an unauthenticated instance to the public internet.

## Milestone / task status

| Stage | Status |
|-------|--------|
| Milestone 0 — FastAPI core, validation, duplicates, fixture extraction, reconciliation | **Done** |
| Milestone 1 — Backend Dockerfile + container health | **Done** |
| Task A — PostgreSQL, SQLAlchemy, Alembic, Compose, persistent documents, logging | **Done** |
| Task B — Live AI extraction, full workflow, human review, audit | Planned |
| Task C — React dashboard, evaluation, final Compose verification | Planned |

## Local setup (Windows PowerShell)

```powershell
cd "C:\Users\ASUS\OneDrive\Desktop\Supply-Chain Reconciliation Engine"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
Copy-Item .env.example backend\.env
```

### Run API against Compose Postgres

```powershell
# Terminal 1 — database (+ optional full stack)
docker compose up -d db

# Terminal 2 — apply migrations, then run API
cd backend
$env:DATABASE_URL = "postgresql+psycopg://reconcile:reconcile@localhost:5432/reconcile"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Docs: http://127.0.0.1:8000/docs
Health: `GET /health`
Readiness (DB): `GET /ready`

### Run tests

Tests use an **isolated SQLite file per test** (via fixtures). They do not modify your development Postgres data.

```powershell
cd backend
pytest -q
```

## Docker Compose (backend + PostgreSQL)

```powershell
cd "C:\Users\ASUS\OneDrive\Desktop\Supply-Chain Reconciliation Engine"
Copy-Item .env.example .env   # optional; compose has defaults
docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

Verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Stop:

```powershell
docker compose down
# Keep DB/upload volumes: omit -v
# Wipe volumes: docker compose down -v
```

### Standalone backend image (Milestone 1)

Still builds from `backend/Dockerfile`. Without Postgres and migrations it cannot persist documents:

```powershell
cd backend
docker build -t supply-chain-reconciliation:local .
```

Prefer `docker compose` for Task A+.

## Alembic migrations

From `backend/` with `DATABASE_URL` set:

```powershell
alembic upgrade head
alembic current
alembic downgrade -1
```

Initial migration: `alembic/versions/20260321_0001_create_documents.py`

## Configuration

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://...`) |
| `UPLOAD_DIR` | File storage path (Compose: `/data/uploads` volume) |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `POSTGRES_*` | Compose database credentials (placeholders only in `.env.example`) |

Never commit real secrets. `.env` is gitignored.

## Persistence and logging notes

- Document metadata (including SHA-256) is stored in PostgreSQL with a unique constraint on `sha256`.
- Uploaded **files** are stored on the filesystem (`UPLOAD_DIR`); Compose mounts volume `upload_data`.
- Application logging uses the stdlib `logging` module (startup, DB errors, uploads, duplicates, reconciliation outcomes). Logs must not include API keys or full document bytes.

## What exists vs what does not

**Exists:** upload validation, SHA-256 duplicates, Postgres-backed document records, Alembic, Docker Compose, centralized logging, fixture extraction, deterministic reconciliation, pytest.

**Not yet:** live vision LLM, React dashboard, human-review persistence, Redis/Celery, authentication.
