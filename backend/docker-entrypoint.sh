#!/bin/sh
set -eu

python - <<'PY'
import time
from sqlalchemy import text
from app.database.session import engine

last_error = None
for attempt in range(1, 31):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database is ready.", flush=True)
        break
    except Exception as exc:
        last_error = exc
        print(f"Waiting for database ({attempt}/30): {exc}", flush=True)
        time.sleep(2)
else:
    raise SystemExit(f"Database did not become ready: {last_error}")
PY

python -m alembic upgrade head

exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips="*"
