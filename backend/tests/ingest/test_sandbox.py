# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import multiprocessing
import os
import time
from datetime import UTC, datetime

import pytest
from openpyxl import Workbook

from app.ingest.errors import IntakeRejected, Limits
from app.ingest.sandbox import run_sandboxed
from app.ingest.xlsx import parse_xlsx
from tests.ingest.hostile import MARKER, workbook_bytes

L = Limits(worker_seconds=0.5)


def echo(data: bytes, limits: Limits) -> object:
    return {"n": len(data)}


def sleeper(data: bytes, limits: Limits) -> object:
    time.sleep(60)
    return {}


def crasher(data: bytes, limits: Limits) -> object:
    os._exit(1)


def rejecter(data: bytes, limits: Limits) -> object:
    from app.ingest.errors import IntakeRejected

    raise IntakeRejected("macro")


def leaker(data: bytes, limits: Limits) -> object:
    raise RuntimeError(MARKER)


def _no_children() -> None:
    assert multiprocessing.active_children() == []


def test_result_round_trips() -> None:
    assert run_sandboxed(echo, b"abc", Limits()) == {"n": 3}
    _no_children()


def test_wall_clock_timeout_kills_the_child() -> None:
    start = time.monotonic()
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(sleeper, b"", L)
    assert ei.value.reason == "resource_limit"
    assert time.monotonic() - start < 10
    _no_children()


def test_child_crash_is_resource_limit() -> None:
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(crasher, b"", Limits())
    assert ei.value.reason == "resource_limit"
    _no_children()


def test_child_intake_rejection_keeps_its_reason() -> None:
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(rejecter, b"", Limits())
    assert ei.value.reason == "macro"


def test_other_child_exceptions_carry_no_text() -> None:
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(leaker, b"", Limits())
    exc = ei.value
    assert exc.reason == "workbook_malformed"
    assert MARKER not in str(exc) and MARKER not in repr(exc)
    _no_children()


def test_workbook_over_the_memory_budget_is_resource_limit() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        for r in range(1, 4001):
            ws.cell(row=r, column=1, value=f"text {r}")

    data = workbook_bytes(build)  # passes the scanner; ~10 MB to load, against a 1 MiB budget
    with pytest.raises(IntakeRejected) as ei:
        parse_xlsx(
            data,
            version_id=1,
            first_locator_id=1,
            now=datetime.now(UTC),
            limits=Limits(worker_memory_bytes=2**20),
        )
    assert ei.value.reason == "resource_limit"
    _no_children()
