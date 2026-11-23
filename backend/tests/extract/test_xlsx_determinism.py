# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Determinism, re-extraction, and no untrusted content in logs or errors. FICTIONAL."""

import hashlib
import logging

import pytest
from openpyxl import Workbook

from app.extract.xlsx import AlreadyExtracted, extract_xlsx
from app.ingest.fragments import ParsedDocument
from app.ingest.intake import ingest
from tests.extract.helpers import NOW, SHEETS, base_records, put, run
from tests.extract.test_xlsx_messy import messy
from tests.ingest.hostile import MARKER, workbook_bytes


def dump(x: object) -> str:
    return x.records.model_dump_json()  # type: ignore[attr-defined]


def test_byte_identical_twice() -> None:
    ing, x1 = run(messy)
    x2 = extract_xlsx(ing.records, ing.parsed, SHEETS, now=NOW)
    assert dump(x1) == dump(x2)


def test_order_independent() -> None:
    ing, x1 = run(messy)
    p = ing.parsed
    flipped = ParsedDocument(
        document_version_id=p.document_version_id,
        product_profile=p.product_profile,
        kind=p.kind,
        sheets=tuple(reversed(p.sheets)),
        cells=tuple(reversed(p.cells)),
    )
    x2 = extract_xlsx(ing.records, flipped, SHEETS, now=NOW)
    assert dump(x1) == dump(x2)


def test_fresh_runs_identical() -> None:
    data = workbook_bytes(lambda wb: messy(wb))  # one file: openpyxl stamps its own save time
    digests: set[str] = set()
    for _ in range(2):
        ing = ingest(
            base_records(), data, declared_kind="xlsx", product_profile="synthetic",
            title="t", uploaded_by=1, snapshot_id=1, now=NOW,
        )  # fmt: skip
        x = extract_xlsx(ing.records, ing.parsed, SHEETS, now=NOW)
        digests.add(hashlib.sha256(dump(x).encode()).hexdigest())
    assert len(digests) == 1


def test_reextract_refused() -> None:
    ing, x = run(messy)
    with pytest.raises(AlreadyExtracted):
        extract_xlsx(x.records, ing.parsed, SHEETS, now=NOW)


def test_no_content_in_logs_or_errors(caplog: pytest.LogCaptureFixture) -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["limit_id", "hours", MARKER], [f"L-{MARKER}", 1, 2]])
        put(wb, f"Scratch {MARKER}"[:31], [[MARKER]])

    caplog.set_level(logging.DEBUG)
    ing, x = run(build)
    assert MARKER in {getattr(loc, "snippet", "") for loc in x.records.locators}  # it was read
    errors: list[str] = []
    for bad in (
        lambda: extract_xlsx(x.records, ing.parsed, SHEETS, now=NOW),  # already extracted
        lambda: extract_xlsx(
            ing.records, ing.parsed, SHEETS.model_copy(update={"product_profile": "ukg_pro_wfm"}),
            now=NOW,
        ),
    ):  # fmt: skip
        with pytest.raises(ValueError) as e:
            bad()
        errors.append(str(e.value) + repr(e.value))
    assert errors and not any(MARKER in m for m in errors)
    assert MARKER not in caplog.text
