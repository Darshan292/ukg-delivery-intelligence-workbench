#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
#
# Start the whole stack (production frontend build), run Playwright, tear everything down.
# MODE=docker|local (auto: docker if "docker info" works). Exit code is Playwright's.
# Extra arguments go to Playwright, e.g. E2E_DEMO=1 E2E_VIDEO=1 bash scripts/e2e.sh e2e/demo.spec.ts
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${MODE:-}" ]; then
  if docker info >/dev/null 2>&1; then MODE=docker; else MODE=local; fi
fi
export MODE FRONTEND=prod
mkdir -p .local

started_db=1
if [ "$MODE" = local ] && bash scripts/pg-local.sh status >/dev/null 2>&1; then started_db=0; fi

setsid bash scripts/dev.sh >.local/e2e-stack.log 2>&1 &
stack=$!
cleanup() {
  trap - INT TERM EXIT
  kill -TERM -- "-$stack" 2>/dev/null || true
  wait "$stack" 2>/dev/null || true
  if [ "$MODE" = docker ]; then docker compose down >/dev/null 2>&1 || true
  elif [ "$started_db" = 1 ]; then bash scripts/pg-local.sh stop >/dev/null || true; fi
}
trap cleanup INT TERM EXIT

for _ in $(seq 1 180); do
  grep -q '^Ready:' .local/e2e-stack.log 2>/dev/null && break
  kill -0 "$stack" 2>/dev/null || { echo "stack exited early:" >&2; tail -n 40 .local/e2e-stack.log >&2; exit 1; }
  sleep 2
done
grep -q '^Ready:' .local/e2e-stack.log || { echo "stack not ready:" >&2; tail -n 40 .local/e2e-stack.log >&2; exit 1; }

rc=0
(cd frontend && npx playwright test "$@") || rc=$?
exit "$rc"
