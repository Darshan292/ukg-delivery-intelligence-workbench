# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from app.domain.locators import XlsxCell
from app.domain.model import Actor, Document, DocumentVersion, ProductProfile, Snapshot
from app.domain.records import Records
from app.ingest.errors import IntakeRejected, Limits
from app.ingest.fragments import ParsedDocument
from app.ingest.intake import Ingested, ingest
from tests.ingest.hostile import MARKER, rewrite_zip, workbook_bytes

NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def _base() -> Records:
    return Records(
        actors=(Actor(id=1, kind="human", display_name="Reviewer", roles=frozenset({"reviewer"})),),
        snapshots=(
            Snapshot(
                id=1,
                product_profile="synthetic",
                environment="test",
                label="s1",
                captured_at=NOW,
            ),
        ),
    )


def _wb(extra: str = "") -> bytes:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"], ws["B1"], ws["A2"] = "ukg_pro_wfm", 40, "unknown" + extra

    return workbook_bytes(build)


def _go(records: Records, data: bytes, **kw: Any) -> Ingested:
    args: dict[str, Any] = {
        "declared_kind": "xlsx",
        "product_profile": "synthetic",
        "title": "Synthetic file",
        "uploaded_by": 1,
        "snapshot_id": 1,
        "now": NOW,
    }
    return ingest(records, data, **{**args, **kw})


def test_ingest_xlsx_happy_path() -> None:
    data = _wb()
    base = _base()
    out = _go(base, data)
    r = out.records
    assert len(r.documents) == 1 and len(r.document_versions) == 1 and len(r.locators) == 3
    v = r.document_versions[0]
    assert v.sha256 == hashlib.sha256(data).hexdigest()
    assert (v.snapshot_id, v.declared_by, v.supersedes_version_id) == (1, 1, None)
    assert out.parsed.kind == "xlsx"


def test_every_fragment_resolves() -> None:
    out = _go(_base(), _wb())
    ids = out.parsed.locator_ids
    for i in ids:
        assert out.records.locator_by_id[i].document_version_id == out.parsed.document_version_id
    mine = {
        x.id
        for x in out.records.locators
        if x.document_version_id == out.parsed.document_version_id
    }
    assert mine == set(ids)


def test_ingested_rejects_orphan_or_dangling() -> None:
    out = _go(_base(), _wb())
    p = out.parsed
    dangling = ParsedDocument(
        document_version_id=p.document_version_id,
        product_profile="synthetic",
        kind="xlsx",
        sheets=p.sheets,
        cells=(*p.cells, p.cells[0].model_copy(update={"locator_id": 99})),
    )
    with pytest.raises(ValidationError):
        Ingested(records=out.records, parsed=dangling)
    orphan = ParsedDocument(
        document_version_id=p.document_version_id,
        product_profile="synthetic",
        kind="xlsx",
        sheets=p.sheets,
        cells=p.cells[:-1],
    )
    with pytest.raises(ValidationError):
        Ingested(records=out.records, parsed=orphan)


def test_declared_profile_carried_through() -> None:
    out = _go(_base(), _wb())
    doc = out.records.document_by_id[
        out.records.version_by_id[out.parsed.document_version_id].document_id
    ]
    assert out.parsed.product_profile == doc.product_profile == "synthetic"
    assert {c.value for c in out.parsed.cells} >= {"unknown", "ukg_pro_wfm"}


@pytest.mark.parametrize("profile", ["ukg_pro_wfm", "workforce_central", "unknown"])
def test_profile_gate(profile: ProductProfile) -> None:
    # owner question S3-Q1 (decided): synthetic only until G-REAL
    with pytest.raises(IntakeRejected) as ei:
        _go(_base(), _wb(), product_profile=profile)
    assert ei.value.reason == "profile_not_permitted"


def test_oversize() -> None:
    with pytest.raises(IntakeRejected) as ei:
        _go(_base(), b"x" * 2048, limits=Limits(max_file_bytes=1024))
    assert ei.value.reason == "too_large"


def test_same_bytes_twice() -> None:
    data = _wb()  # saved workbooks embed a timestamp: build the bytes once
    first = _go(_base(), data)
    with pytest.raises(IntakeRejected) as ei:
        _go(first.records, data)
    assert ei.value.reason == "already_ingested"


def test_extension_spoof_pdf_declared_xlsx() -> None:
    with pytest.raises(IntakeRejected) as ei:
        _go(_base(), b"%PDF-1.4\n%%EOF", declared_kind="xlsx")
    assert ei.value.reason == "type_mismatch"


def test_unknown_snapshot() -> None:
    with pytest.raises(IntakeRejected) as ei:
        _go(_base(), _wb(), snapshot_id=999)
    assert ei.value.reason == "records_invalid"


def test_ids_continue() -> None:
    base = _base()
    base = base.extended(
        documents=(Document(id=1, product_profile="synthetic", title="old"),),
        document_versions=(
            DocumentVersion(
                id=1,
                document_id=1,
                sha256="0" * 64,
                snapshot_id=None,
                supersedes_version_id=None,
                declared_by=1,
                uploaded_at=NOW,
            ),
        ),
        locators=tuple(
            XlsxCell(
                id=i,
                document_version_id=1,
                kind="xlsx_cell",
                extractor="t@1",
                extracted_at=NOW,
                snippet="",
                sheet="Old",
                cell=f"A{i}",
            )
            for i in (1, 2, 3)
        ),
    )
    out = _go(base, _wb())
    assert out.parsed.document_version_id == 2
    assert sorted(out.parsed.locator_ids) == [4, 5, 6]


def _spoof() -> bytes:
    return b"%PDF-1.4 " + MARKER.encode()


def _traversal() -> bytes:
    return rewrite_zip(_wb(), add={f"../{MARKER}.xml": b"<a/>"})


def _xxe() -> bytes:
    xxe = f'<!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/hostname">]><r>{MARKER}&e;</r>'
    return rewrite_zip(_wb(), add={"xl/sharedStrings.xml": xxe.encode()})


@pytest.mark.parametrize("make", [_spoof, _traversal, _xxe])
def test_rejection_is_clean_and_silent_about_content(
    make: Any, caplog: pytest.LogCaptureFixture
) -> None:
    base = _base()
    before = base.model_dump()
    with caplog.at_level(logging.DEBUG), pytest.raises(IntakeRejected) as ei:
        _go(base, make(), title=MARKER)
    exc = ei.value
    assert MARKER not in str(exc) and MARKER not in repr(exc)
    assert all(MARKER not in r.getMessage() and r.exc_info is None for r in caplog.records)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert [w.getMessage() for w in warnings] == [f"intake rejected: {exc.reason}"]
    assert base.model_dump() == before


def test_deterministic() -> None:
    data = _wb()
    assert _go(_base(), data) == _go(_base(), data)
