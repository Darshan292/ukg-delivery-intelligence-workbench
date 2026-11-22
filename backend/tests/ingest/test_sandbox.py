# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import random
import subprocess
import time
from datetime import UTC, datetime
from typing import Any

import pytest
from openpyxl import Workbook

from app.ingest import sandbox as sb
from app.ingest.errors import IntakeRejected, Limits
from app.ingest.sandbox import run_sandboxed
from app.ingest.xlsx import extract_plain, parse_xlsx
from tests.ingest.hostile import MARKER, workbook_bytes
from tests.ingest.sandbox_funcs import big_reply, crasher, echo, leaker, probe, rejecter, sleeper

L = Limits(worker_seconds=0.5)
Procs = list[subprocess.Popen[bytes]]


@pytest.fixture
def procs(monkeypatch: pytest.MonkeyPatch) -> Procs:
    """Every worker process started, so a test can prove none is left running."""
    made: Procs = []
    real = subprocess.Popen

    def recording(*a: Any, **k: Any) -> Any:
        p: Any = real(*a, **k)
        made.append(p)
        return p

    monkeypatch.setattr(sb.subprocess, "Popen", recording)
    return made


def _all_reaped(procs: Procs) -> None:
    assert procs and all(p.poll() is not None for p in procs)


def test_result_round_trips(procs: Procs) -> None:
    assert run_sandboxed(echo, b"abc", Limits()) == {"n": 3}
    _all_reaped(procs)


def test_wall_clock_timeout_kills_the_child(procs: Procs) -> None:
    start = time.monotonic()
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(sleeper, b"", L)
    assert ei.value.reason == "resource_limit"
    assert time.monotonic() - start < 10
    _all_reaped(procs)


def test_child_crash_is_resource_limit(procs: Procs) -> None:
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(crasher, b"", Limits())
    assert ei.value.reason == "resource_limit"
    _all_reaped(procs)


def test_child_intake_rejection_keeps_its_reason() -> None:
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(rejecter, b"", Limits())
    assert ei.value.reason == "macro"


def test_other_child_exceptions_carry_no_text(procs: Procs) -> None:
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(leaker, b"", Limits())
    exc = ei.value
    assert exc.reason == "workbook_malformed"
    assert MARKER not in str(exc) and MARKER not in repr(exc)
    _all_reaped(procs)


def test_workbook_over_the_memory_budget_is_resource_limit(procs: Procs) -> None:
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
    _all_reaped(procs)


def test_oversized_reply_is_never_parsed(monkeypatch: pytest.MonkeyPatch, procs: Procs) -> None:
    parsed: list[int] = []
    real = sb.json.loads

    def spy(raw: bytes | str, *a: Any, **k: Any) -> Any:
        parsed.append(len(raw))
        return real(raw, *a, **k)

    monkeypatch.setattr(sb.json, "loads", spy)
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(big_reply, b"", Limits(worker_max_reply_bytes=2**20))
    assert ei.value.reason == "resource_limit" and parsed == []
    _all_reaped(procs)


def test_non_ascii_heavy_workbook_hits_the_child_output_budget() -> None:
    rng = random.Random(1)  # noqa: S311  (test data)

    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        for r in range(1, 101):  # well under the cell cap
            text = "".join(chr(0x4E00 + rng.randrange(5000)) for _ in range(5000))
            ws.cell(row=r, column=1, value=text)

    with pytest.raises(IntakeRejected) as ei:
        parse_xlsx(
            workbook_bytes(build),
            version_id=1,
            first_locator_id=1,
            now=datetime.now(UTC),
            limits=Limits(worker_max_reply_bytes=2**20),
        )
    assert ei.value.reason == "resource_limit"


def test_reply_carries_no_duplicate_snippet() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"] = "hello"

    plain = extract_plain(workbook_bytes(build), Limits())
    assert "snippet" not in plain["cells"][0]


def test_child_environment_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WB_TEST_SECRET", "s3cret-value")
    out = run_sandboxed(probe, b"", Limits())
    assert "WB_TEST_SECRET" not in out["env"] and "s3cret-value" not in out["environ_file"]
    assert out["env"] == {} or set(out["env"]) <= {"LC_CTYPE"}  # CPython may add LC_CTYPE
    assert out["cwd"] == "/"


def test_child_resource_limits_are_set() -> None:
    lim = run_sandboxed(probe, b"", Limits(worker_memory_bytes=2**30))["limits"]
    assert lim["CORE"] == [0, 0] and lim["FSIZE"] == [0, 0]
    assert lim["NOFILE"][0] <= 64 and lim["AS"] == [2**30, 2**30]
    assert lim["CPU"][0] >= 1


def test_start_failure_is_resource_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any, **k: Any) -> Any:
        raise OSError(MARKER)

    monkeypatch.setattr(sb.subprocess, "Popen", boom)
    with pytest.raises(IntakeRejected) as ei:
        run_sandboxed(echo, b"", Limits())
    exc = ei.value
    assert exc.reason == "resource_limit" and MARKER not in str(exc) + repr(exc)
    assert exc.__cause__ is None and exc.__suppress_context__
