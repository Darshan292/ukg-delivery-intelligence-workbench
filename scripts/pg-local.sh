#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
#
# Local throwaway Postgres for cloud agents / machines without Docker.
# Usage: scripts/pg-local.sh start|stop|status|url
# Dev-only credentials. Trust auth only on the owner-only (0700) unix socket; TCP needs scram.
set -euo pipefail

PORT=55432
BIN=/usr/lib/postgresql/16/bin
if [ ! -x "$BIN/initdb" ]; then
  found="$(command -v initdb || true)"
  [ -n "$found" ] || { echo "initdb not found" >&2; exit 1; }
  BIN="$(dirname "$found")"
fi

if [ "$(id -u)" = 0 ]; then
  # initdb refuses to run as root, so everything runs as the postgres user.
  OWNER=postgres
  DIR=/tmp/tracer-pg
  as() { runuser -u postgres -- "$@"; }
else
  OWNER="$(id -un)"
  DIR="${TMPDIR:-/tmp}/tracer-pg-$(id -u)"
  as() { "$@"; }
fi
PGDATA="$DIR/data"
LOG="$DIR/server.log"

# Never chown: create the directory as its future owner and refuse anything pre-existing
# that is a symlink or owned by someone else.
if [ -L "$DIR" ]; then echo "refusing symlinked $DIR" >&2; exit 1; fi
if [ -e "$DIR" ]; then
  [ "$(stat -c %U "$DIR")" = "$OWNER" ] || { echo "refusing $DIR: not owned by $OWNER" >&2; exit 1; }
else
  as mkdir -m 700 "$DIR"
fi
as chmod 700 "$DIR"

running() { as "$BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; }

start() {
  if [ ! -f "$PGDATA/PG_VERSION" ]; then
    as "$BIN/initdb" -D "$PGDATA" -U postgres --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 >/dev/null
  fi
  if ! running; then
    as "$BIN/pg_ctl" -D "$PGDATA" -l "$LOG" -w \
      -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=$DIR -c unix_socket_permissions=0700" start >/dev/null
  fi
  psql_() { as "$BIN/psql" -h "$DIR" -p "$PORT" -U postgres -v ON_ERROR_STOP=1 -qtA "$@"; }
  if [ "$(psql_ -d postgres -c "SELECT 1 FROM pg_roles WHERE rolname='tracer'")" != 1 ]; then
    psql_ -d postgres -c "CREATE ROLE tracer LOGIN CREATEDB CREATEROLE PASSWORD 'tracer'"
  fi
  # CREATEROLE lets the migration create the wb_* group roles (in PostgreSQL 16 the creator gets
  # ADMIN on them, which IN ROLE needs); the ALTER also upgrades clusters made by older versions.
  psql_ -d postgres -c "ALTER ROLE tracer CREATEROLE"
  if [ "$(psql_ -d postgres -c "SELECT 1 FROM pg_database WHERE datname='tracer'")" != 1 ]; then
    psql_ -d postgres -c "CREATE DATABASE tracer OWNER tracer"
  fi
  echo "postgres running on 127.0.0.1:$PORT"
}

case "${1:-}" in
  start) start ;;
  stop) if running; then as "$BIN/pg_ctl" -D "$PGDATA" -m fast -w stop >/dev/null; fi; echo stopped ;;
  status) if running; then echo running; else echo stopped; exit 3; fi ;;
  url) echo "postgresql+pg8000://tracer:tracer@127.0.0.1:$PORT/tracer" ;;
  *) echo "usage: $0 start|stop|status|url" >&2; exit 2 ;;
esac
