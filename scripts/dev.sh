#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
#
# Start database (MODE=docker|local), migrate, seed, then backend (8000) and frontend (3000).
# FRONTEND=dev (default) runs next dev; FRONTEND=prod runs next build + next start.
# Ctrl-C (or SIGTERM) stops the backend and frontend. The database is left running (make db-down).
set -euo pipefail
cd "$(dirname "$0")/.."
MODE=${MODE:-docker}
FRONTEND=${FRONTEND:-dev}

case "$MODE" in
  docker)
    docker compose up -d --wait db
    export DATABASE_URL='postgresql+pg8000://tracer:tracer@127.0.0.1:5432/tracer' ;;
  local)
    bash scripts/pg-local.sh start
    DATABASE_URL=$(bash scripts/pg-local.sh url); export DATABASE_URL ;;
  *) echo "MODE must be docker or local" >&2; exit 2 ;;
esac

(cd backend && uv run alembic upgrade head && uv run python -m app.seed)

pids=()
stop() {
  trap - INT TERM EXIT
  for p in "${pids[@]}"; do kill -TERM -- "-$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop INT TERM EXIT

# setsid gives each server its own process group so the whole tree can be stopped.
(cd backend && exec setsid uv run uvicorn app.main:app --host 127.0.0.1 --port 8000) &
pids+=("$!")
if [ "$FRONTEND" = prod ]; then
  (cd frontend && exec setsid sh -c 'npm run build && exec npm run start -- --hostname 127.0.0.1 --port 3000') &
else
  (cd frontend && exec setsid npm run dev -- --hostname 127.0.0.1 --port 3000) &
fi
pids+=("$!")

for _ in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1 \
     && curl -fsS -o /dev/null http://127.0.0.1:3000/ 2>/dev/null; then
    echo "Ready: open http://127.0.0.1:3000  (Ctrl-C to stop)"
    wait; exit 0
  fi
  for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null || { echo "a server exited early" >&2; exit 1; }; done
  sleep 2
done
echo "timed out waiting for the stack" >&2; exit 1
