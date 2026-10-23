#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import os
import time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is required")

deadline = time.time() + 60
last_error = None
while time.time() < deadline:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database is reachable")
        break
    except Exception as exc:  # noqa: BLE001 — retry until ready
        last_error = exc
        time.sleep(2)
else:
    raise SystemExit(f"Database not ready: {last_error}")
PY

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
