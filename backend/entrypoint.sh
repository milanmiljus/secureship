#!/bin/bash
set -e
alembic upgrade head
if [ "$RUN_SEED" = "true" ]; then
    python scripts/seed_data.py
fi
exec uvicorn main:app --host 0.0.0.0 --port 8000 ${RELOAD_FLAG:-}
