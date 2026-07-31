#!/usr/bin/env bash
set -euo pipefail

cd /app/backend

PUID=${PUID:-1000}
PGID=${PGID:-1000}
chown -R "$PUID:$PGID" /app/backend/data

gosu "$PUID:$PGID" bash -c '
  cd /app/backend
  alembic upgrade head
  python seed.py
'

exec gosu "$PUID:$PGID" "$@"