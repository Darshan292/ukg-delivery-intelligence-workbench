# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import subprocess
from typing import Any

import pytest

from app.ingest import sandbox as sb
from app.ingest.errors import IntakeRejected, Limits
from app.ingest.pdf import run_pdf_worker
from tests.ingest.hostile import MARKER
from tests.ingest.pdfs import make_pdf

MIB = 2**20
Procs = list[subprocess.Popen[bytes]]


@pytest.fixture
def procs(monkeypatch: pytest.MonkeyPatch) -> Procs:
    made: Procs = []
    real = subprocess.Popen

    def recording(*a: Any, **k: Any) -> Any:
        p: Any = real(*a, **k)
        made.append(p)
        return p

    monkeypatch.setattr(sb.subprocess, "Popen", recording)
    return made


def _reason(data: bytes, limits: Limits | None = None) -> IntakeRejected:
    with pytest.raises(IntakeRejected) as ei:
        run_pdf_worker(data, limits or Limits())
    return ei.value


def test_worker_returns_words() -> None:
    pages = run_pdf_worker(make_pdf([[(72, 700, "OT-1 hello")]]), Limits())
    assert [p[0] for p in pages] == [1]
    words = pages[0][3]
    assert [w[0] for w in words] == ["OT-1", "hello"]
    assert words[0][1] == pytest.approx(72, abs=0.5)  # the Td operand, independent of our code


def test_total_timeout_kills_worker(procs: Procs) -> None:
    exc = _reason(make_pdf([[(72, 700, "x")]]), Limits(pdf_total_seconds=0.05))
    assert exc.reason == "resource_limit"
    assert procs and all(p.poll() is not None for p in procs)


def test_memory_limit_applied() -> None:
    exc = _reason(make_pdf([[(72, 700, "x")]]), Limits(pdf_memory_bytes=32 * MIB))
    assert exc.reason in {"resource_limit", "pdf_malformed"}  # how the child dies varies


def test_truncated_pdf() -> None:
    data = make_pdf([[(72, 700, "OT-1 hello")]])
    assert _reason(data[: len(data) // 2]).reason == "pdf_malformed"


def test_garbage_after_header_carries_no_content() -> None:
    exc = _reason(b"%PDF-1.4\n" + MARKER.encode() * 50)
    assert exc.reason == "pdf_malformed" and MARKER not in str(exc) + repr(exc)
