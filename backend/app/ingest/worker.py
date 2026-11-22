# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Entry point of the sandbox child: python -I -c ... <mem> <cpu_s>. Not imported by the parent.

Sets the resource limits first, then reads one framed request from stdin, runs the named
function and writes one JSON reply to stdout. The environment is empty (parent passes none).
"""

import contextlib
import importlib
import json
import resource
import struct
import sys
from typing import Any

from app.ingest.errors import IntakeRejected, Limits

NOFILE = 32  # stdin, stdout, stderr, the zip and a few imports


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


def _read_exact(n: int) -> bytes:
    buf = sys.stdin.buffer.read(n)
    if len(buf) != n:
        raise EOFError
    return buf


def main(mem: int, cpu: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))  # no core dump of hostile input
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))  # no regular file can be written
    resource.setrlimit(resource.RLIMIT_NOFILE, (NOFILE, NOFILE))
    on_error = "workbook_malformed"
    limits_mem = mem
    try:
        hlen, dlen = struct.unpack(">II", _read_exact(8))
        header: dict[str, Any] = json.loads(_read_exact(hlen))
        data = _read_exact(dlen)
        on_error = header["on_error"]
        limits = Limits(**header["limits"])
        limits_mem = limits.worker_memory_bytes
        module, _, name = header["func"].partition(":")
        func = getattr(importlib.import_module(module), name)
        msg: dict[str, Any] = {"ok": func(data, limits)}
    except IntakeRejected as e:
        msg = {"error": e.reason}
    except MemoryError:
        msg = {"error": "resource_limit"}
    except BaseException:  # noqa: BLE001  (text of any other error may hold file content)
        msg = {"error": "resource_limit" if _at_memory_limit(limits_mem) else on_error}
    with contextlib.suppress(BaseException):  # on failure the parent sees EOF: resource_limit
        sys.stdout.buffer.write(json.dumps(msg, ensure_ascii=False).encode("utf-8"))
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
