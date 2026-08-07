#!/bin/sh
set -eu
if [ "$#" -gt 0 ]; then exec "$@"; fi
alembic upgrade head
if [ "${SEED_DEMO:-true}" = "true" ]; then python -m app.db.seed; fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
