# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour. Module-level functions the sandbox worker can import."""

import os
import resource
import time

from app.ingest.errors import IntakeRejected, Limits
from tests.ingest.hostile import MARKER


def echo(data: bytes, limits: Limits) -> object:
    return {"n": len(data)}


def sleeper(data: bytes, limits: Limits) -> object:
    time.sleep(60)
    return {}


def crasher(data: bytes, limits: Limits) -> object:
    os._exit(1)


def rejecter(data: bytes, limits: Limits) -> object:
    raise IntakeRejected("macro")


def leaker(data: bytes, limits: Limits) -> object:
    raise RuntimeError(MARKER)


def big_reply(data: bytes, limits: Limits) -> object:
    return {"x": "a" * (2 * 2**20)}


def probe(data: bytes, limits: Limits) -> object:
    with open("/proc/self/environ", "rb") as f:
        raw = f.read().decode("utf-8", "replace")
    names = ("CORE", "FSIZE", "NOFILE", "AS", "CPU")
    return {
        "env": dict(os.environ),
        "environ_file": raw,
        "cwd": os.getcwd(),
        "limits": {n: list(resource.getrlimit(getattr(resource, f"RLIMIT_{n}"))) for n in names},
    }
