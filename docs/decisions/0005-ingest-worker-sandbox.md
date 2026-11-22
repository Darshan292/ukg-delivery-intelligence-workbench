# 0005: Ingest worker sandbox (what it isolates, what it does not)

Status: proposed with PR A (xlsx intake). Needs owner and architect review.

## Context

Untrusted workbooks are parsed by openpyxl. The package scanner (`app/ingest/ooxml.py`) caps
what it can see before loading, but openpyxl and the scanner can disagree, so the load itself
runs in a backstop: `app/ingest/sandbox.py` starting `app/ingest/worker.py`. Task 11 (PDF)
reuses it.

## What the worker isolates

- **Memory:** `RLIMIT_AS` (`worker_memory_bytes`, placeholder 1 GiB).
- **CPU:** `RLIMIT_CPU` (`worker_seconds` + 1).
- **Wall clock:** the parent stops waiting after `worker_seconds`, kills and waits (no zombies).
- **Reply size:** capped at `worker_max_reply_bytes` (placeholder 64 MiB); a larger reply is
  never parsed. The child also keeps its own output budget.
- **Environment:** the child is `python -I -B` with `env={}` and cwd `/`: no inherited
  variables, so no `DATABASE_URL`, tokens or proxy settings, also not via `/proc/self/environ`.
- **Core dumps:** `RLIMIT_CORE` 0.
- **File writes:** `RLIMIT_FSIZE` 0 (no regular file can be written; pipes are unaffected).
- **File descriptors:** `RLIMIT_NOFILE` 32.
- **Start failure, crash, timeout, out-of-memory:** all become `IntakeRejected("resource_limit")`
  with no detail.

## What it does NOT isolate

- **Network:** the child can open sockets.
- **Filesystem reads:** the child can read anything the service user can read.
- **Other processes and syscalls:** no seccomp filter, no user namespace, no PID namespace.

These need OS or container isolation at deployment, for example a container or user namespace
with no network, a read-only root, a seccomp profile and a non-privileged user.
**This is required before gate G-REAL** (real customer data). Until then the worker is a
resource backstop, not a security boundary, and only synthetic data may be ingested (Q1).

## Known imprecision

When a library swallows or re-wraps `MemoryError`, the worker infers a memory-limit hit from
`VmPeak` being within 5 percent of the limit and reports `resource_limit`; otherwise the
generic reason (`workbook_malformed`). The file is rejected either way, but the reason code
can differ run to run near the limit.

## Consequences for callers

- `run_sandboxed` blocks (a process start, up to `worker_seconds`). The future FastAPI upload
  route must call it from a thread pool (for example `run_in_threadpool`), never on the event
  loop.
- Linux only (`resource`); CI is Ubuntu.
- The limits are placeholders set by the team, not measured (Q7).
