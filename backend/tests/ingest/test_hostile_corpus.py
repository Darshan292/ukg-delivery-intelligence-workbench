# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""The milestone's hostile-input list, executable: every case is refused by ingest() with a fixed
reason, no content in the message, and exactly one WARNING line. PDF cases arrive with PR B."""

import logging
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook

from app.domain.model import Actor, Snapshot
from app.domain.records import Records
from app.ingest.errors import IntakeRejected, Limits
from app.ingest.intake import ingest
from tests.ingest.hostile import MARKER, rewrite_zip, workbook_bytes

NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
M = MARKER.encode()


def _wb() -> bytes:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"] = "x"

    return workbook_bytes(build)


def _ct() -> bytes:
    with zipfile.ZipFile(BytesIO(_wb())) as zf:
        return zf.read("[Content_Types].xml")


LAUGHS = (
    b'<!DOCTYPE r [<!ENTITY a "xxxxxxxxxx"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
    b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]><r>&c;</r>'
)
XXE = b'<!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/hostname">]><r>&e;</r>'

# (id, bytes, declared kind, expected reason)
CASES: list[tuple[str, Callable[[], bytes], str, str]] = [
    (
        "zip_bomb",
        lambda: rewrite_zip(_wb(), add={"xl/pad.xml": b"<a/>" * 2**20}),
        "xlsx",
        "archive_ratio",
    ),
    (
        "path_traversal",
        lambda: rewrite_zip(_wb(), add={f"../{MARKER}.xml": b"<a/>"}),
        "xlsx",
        "archive_bad_entry_name",
    ),
    (
        "xxe",
        lambda: rewrite_zip(_wb(), add={"xl/sharedStrings.xml": XXE + M}),
        "xlsx",
        "xml_forbidden",
    ),
    (
        "billion_laughs",
        lambda: rewrite_zip(_wb(), replace={"xl/worksheets/sheet1.xml": LAUGHS}),
        "xlsx",
        "xml_forbidden",
    ),
    ("macro_part", lambda: rewrite_zip(_wb(), add={"xl/vbaProject.bin": M}), "xlsx", "macro"),
    (
        "xlsm_content_type",
        lambda: rewrite_zip(
            _wb(),
            replace={
                "[Content_Types].xml": _ct().replace(
                    b"spreadsheetml.sheet.main", b"ms-excel.sheet.macroEnabled.main"
                )
            },
        ),
        "xlsx",
        "macro",
    ),
    (
        "external_link",
        lambda: rewrite_zip(_wb(), add={"xl/externalLinks/externalLink1.xml": b"<a/>"}),
        "xlsx",
        "external_link",
    ),
    (
        "ole_embedding",
        lambda: rewrite_zip(_wb(), add={"xl/embeddings/oleObject1.bin": M}),
        "xlsx",
        "embedded_object",
    ),
    (
        "nested_archive",
        lambda: rewrite_zip(_wb(), add={"xl/inner.zip": M}),
        "xlsx",
        "unsupported_part",
    ),
    ("extension_spoof", lambda: b"%PDF-1.4 " + M, "xlsx", "type_mismatch"),
    ("xlsx_declared_pdf", _wb, "pdf", "type_mismatch"),
    ("oversized", lambda: b"PK\x03\x04" + b"0" * 4096, "xlsx", "too_large"),
    ("truncated_xlsx", lambda: _wb()[: len(_wb()) // 2], "xlsx", "archive_malformed"),
    # owner question S3-Q2 (pending): other formats are refused before parsing, nesting included
    ("deeply_nested_json", lambda: b"[" * 100_000, "xlsx", "unsupported_type"),
    ("csv", lambda: b"a,b\n1,2\n", "xlsx", "unsupported_type"),
]


@pytest.mark.parametrize(("name", "make", "kind", "reason"), CASES, ids=[c[0] for c in CASES])
def test_hostile_file_rejected(
    name: str,
    make: Callable[[], bytes],
    kind: str,
    reason: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    records = Records(
        actors=(Actor(id=1, kind="human", display_name="R", roles=frozenset({"reviewer"})),),
        snapshots=(
            Snapshot(
                id=1, product_profile="synthetic", environment="t", label="s", captured_at=NOW
            ),
        ),
    )
    kw: dict[str, Any] = {"limits": Limits(max_file_bytes=2048)} if name == "oversized" else {}
    with caplog.at_level(logging.DEBUG), pytest.raises(IntakeRejected) as ei:
        ingest(
            records,
            make(),
            declared_kind=kind,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
            product_profile="synthetic",
            title=MARKER,
            uploaded_by=1,
            snapshot_id=1,
            now=NOW,
            **kw,
        )
    exc = ei.value
    assert exc.reason == reason
    assert MARKER not in str(exc) and MARKER not in repr(exc)
    assert all(MARKER not in r.getMessage() and r.exc_info is None for r in caplog.records)
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        f"intake rejected: {reason}"
    ]
