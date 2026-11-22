# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Run untrusted-input parsing in a resource-limited child process with an empty environment.

The child is a fresh interpreter (`python -I`, no inherited environment, cwd "/"), so it holds
none of the parent's state or secrets. It sets RLIMIT_AS, CPU, CORE, FSIZE and NOFILE itself,
runs one module-level function and returns only JSON. Timeout, out-of-memory, crash, a start
failure or a reply over the cap all become IntakeRejected("resource_limit"). Linux only
(`resource`); reusable for the PDF worker (Task 11). It does NOT isolate network or filesystem
reads: see docs/decisions/0005-ingest-worker-sandbox.md.
"""

import contextlib
import dataclasses
import json
import os
import selectors
import struct
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, get_args

from app.ingest.errors import IntakeRejected, Limits, Reason

_REASONS = frozenset(get_args(Reason))
_ROOT = str(Path(__file__).resolve().parents[2])  # the folder that holds the `app` package
_BOOT = (
    "import sys; sys.path.insert(0, sys.argv[3]); "
    "from app.ingest.worker import main; main(int(sys.argv[1]), int(sys.argv[2]))"
)
_CHUNK = 65536


def _exchange(proc: subprocess.Popen[bytes], payload: bytes, limits: Limits) -> bytes:
    """Feed stdin and collect stdout without blocking past the deadline or the reply cap."""
    assert proc.stdin and proc.stdout  # noqa: S101  (PIPE was requested)
    stdin, stdout = proc.stdin, proc.stdout
    os.set_blocking(stdin.fileno(), False)
    os.set_blocking(stdout.fileno(), False)
    sel = selectors.DefaultSelector()
    sel.register(stdin, selectors.EVENT_WRITE)
    sel.register(stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + limits.worker_seconds
    pos, out = 0, bytearray()
    while True:
        left = deadline - time.monotonic()
        events = sel.select(left) if left > 0 else []
        if not events:
            raise IntakeRejected("resource_limit")  # wall clock
        for key, _ in events:
            if key.fileobj is stdin:
                try:
                    pos += os.write(stdin.fileno(), payload[pos : pos + _CHUNK])
                except BlockingIOError:
                    continue
                except BrokenPipeError:
                    pos = len(payload)  # the child is gone; its end shows on stdout
                if pos >= len(payload):
                    sel.unregister(stdin)
                    with contextlib.suppress(OSError):
                        stdin.close()
            else:
                try:
                    chunk = os.read(stdout.fileno(), _CHUNK)
                except BlockingIOError:
                    continue
                if not chunk:
                    return bytes(out)
                out += chunk
                if len(out) > limits.worker_max_reply_bytes:
                    raise IntakeRejected("resource_limit")  # never parsed


def run_sandboxed(
    func: Callable[[bytes, Limits], object],
    data: bytes,
    limits: Limits,
    on_error: Reason = "workbook_malformed",
) -> Any:
    """`func` must be a module-level function returning JSON-able data."""
    header = json.dumps(
        {
            "func": f"{func.__module__}:{func.__qualname__}",
            "limits": dataclasses.asdict(limits),
            "on_error": on_error,
        }
    ).encode()
    payload = struct.pack(">II", len(header), len(data)) + header + data
    cmd = [
        sys.executable,
        "-I",
        "-B",
        "-c",
        _BOOT,
        str(limits.worker_memory_bytes),
        str(int(limits.worker_seconds) + 1),
        _ROOT,
    ]
    try:
        proc = subprocess.Popen(  # noqa: S603  (fixed argv; no shell; no input in argv)
            cmd,
            env={},  # nothing inherited: the child must not see the parent's secrets
            cwd="/",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception:  # OSError, ValueError, ...: never a raw error with details
        raise IntakeRejected("resource_limit") from None
    try:
        raw = _exchange(proc, payload, limits)
    finally:
        proc.kill()  # no-op if it already exited
        proc.wait()
        for pipe in (proc.stdin, proc.stdout):
            if pipe:
                with contextlib.suppress(OSError):
                    pipe.close()
    if not raw:
        raise IntakeRejected("resource_limit")  # crashed or killed before replying
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
