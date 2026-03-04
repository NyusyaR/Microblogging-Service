#!/usr/bin/env bash
set -e

python -m alembic upgrade head
uvicorn service_app.main:app --host 0.0.0.0 --port 8000