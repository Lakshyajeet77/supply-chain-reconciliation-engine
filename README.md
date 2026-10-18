# Supply-Chain Reconciliation Engine

Production-style Applied AI portfolio project: extract structured data from purchase orders, delivery documents, and supplier invoices, then reconcile them with **deterministic** business rules.

**MATCHED is not payment authorization.** This system supports review; it never executes payments.

## Security limitation (MVP)

There is **no authentication** in the local MVP. Do **not** expose an unauthenticated instance to the public internet.

## Milestone status

| Milestone | Status |
|-----------|--------|
| 0 — FastAPI core, upload validation, SHA-256 duplicates, fixture extraction, reconciliation tests | **Implemented** |
| 1 — Backend Dockerfile + container verification | Next |
| 2 — PostgreSQL, SQLAlchemy, Alembic, Docker Compose | Planned |
| Later — Live LLM extraction, full workflow, React, evaluation | Planned |

## Milestone 0 setup (Windows PowerShell)

```powershell
cd "c:\Users\ASUS\OneDrive\Desktop\Supply-Chain Reconciliation Engine"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
Copy-Item .env.example backend\.env
```

### Run the API

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

Open interactive docs: http://127.0.0.1:8000/docs

### Run tests

```powershell
cd backend
pytest -q
```

## Configuration

Copy `.env.example` to `backend/.env`. Uploaded files go under `backend/uploads/` (gitignored). No LLM API keys are required for Milestone 0.

## What exists vs what does not

**Exists:** upload validation (PDF/PNG/JPEG signatures), SHA-256 exact-file duplicates, in-memory registry, Pydantic extraction schemas (INR fixtures), fixture extraction stub, deterministic reconciliation engine, pytest suite.

**Does not exist yet:** Docker, PostgreSQL, live vision LLM, fuzzy item matching, human-review UI, React dashboard.
