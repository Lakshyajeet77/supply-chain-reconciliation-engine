FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY docker-entrypoint.sh .
RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh

EXPOSE 8000

# Standalone (Milestone 1 style): run uvicorn directly.
# Compose overrides CMD with the entrypoint that waits for Postgres and migrates.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
