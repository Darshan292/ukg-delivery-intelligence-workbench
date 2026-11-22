# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Run untrusted-input parsing in a resource-limited child process (spawn, not fork).

The child sets RLIMIT_AS and RLIMIT_CPU, runs one module-level function, and returns only JSON.
Timeout, out-of-memory or crash all become IntakeRejected("resource_limit"). Linux only
(`resource`); reusable for the PDF worker (Task 11).
"""

import contextlib
import json
import multiprocessing
import resource
from collections.abc import Callable
from multiprocessing.connection import Connection
from typing import Any, get_args

from app.ingest.errors import IntakeRejected, Limits, Reason

_MAX_REPLY = 256 * 1024 * 1024  # a reply larger than this is a runaway child, not a result
_REASONS = frozenset(get_args(Reason))


def _at_memory_limit(limit: int) -> bool:
    """Libraries often swallow or re-wrap MemoryError; the peak address space still shows it."""
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith("VmPeak:"):
                    return int(line.split()[1]) * 1024 >= limit * 0.95
    except (OSError, ValueError):
        pass
    return False


def _child(
    conn: Connection,
    func: Callable[[bytes, Limits], object],
    data: bytes,
    limits: Limits,
    on_error: Reason,
) -> None:
    try:
        mem = limits.worker_memory_bytes
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
        cpu = int(limits.worker_seconds) + 1
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
        msg: dict[str, Any] = {"ok": func(data, limits)}
    except IntakeRejected as e:
        msg = {"error": e.reason}
    except MemoryError:
        msg = {"error": "resource_limit"}
    except BaseException:  # noqa: BLE001  (text of any other error may hold file content)
        msg = {
            "error": "resource_limit" if _at_memory_limit(limits.worker_memory_bytes) else on_error
        }
    with contextlib.suppress(BaseException):  # on failure the parent sees EOF: resource_limit
        conn.send_bytes(json.dumps(msg).encode())
    conn.close()


def run_sandboxed(
    func: Callable[[bytes, Limits], object],
    data: bytes,
    limits: Limits,
    on_error: Reason = "workbook_malformed",
) -> Any:
    """`func` must be a module-level function returning JSON-able data."""
    ctx = multiprocessing.get_context("spawn")  # spawn: the child holds no parent state
    recv, send = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(send, func, data, limits, on_error), daemon=True)
    proc.start()
    send.close()
    try:
        if not recv.poll(limits.worker_seconds):
            raise IntakeRejected("resource_limit")
        try:
            raw = recv.recv_bytes(_MAX_REPLY)
        except (EOFError, OSError):
            raise IntakeRejected("resource_limit") from None
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join()
        proc.close()
        recv.close()
    try:
        msg = json.loads(raw)
        if "error" in msg:
            reason = msg["error"]
            raise IntakeRejected(reason if reason in _REASONS else on_error)
        return msg["ok"]
    except IntakeRejected:
        raise
    except Exception:
        raise IntakeRejected(on_error) from None
