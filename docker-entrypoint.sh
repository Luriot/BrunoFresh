#!/usr/bin/env bash
set -euo pipefail

cd /app/backend
alembic upgrade head
python seed.py

exec "$@"
