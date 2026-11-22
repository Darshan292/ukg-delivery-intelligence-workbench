# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Differential check: every part openpyxl opens was read and checked by the scanner first."""

import zipfile
from collections.abc import Callable
from typing import Any

import pytest
from openpyxl import Workbook

import app.ingest.ooxml as ooxml
from app.ingest.errors import Limits
from app.ingest.xlsx import extract_plain
from tests.ingest.hostile import rewrite_zip, workbook_bytes

L = Limits()


def _plain(wb: Workbook) -> None:
    ws = wb.active
    assert ws is not None
    ws["A1"] = "x"


def _rich(wb: Workbook) -> None:
    ws = wb.active
    assert ws is not None
    ws["A1"], ws["B2"] = "x", 2
    ws.merge_cells("C1:E1")
    ws["A3"].hyperlink = "http://example.invalid/"
    ws.row_dimensions[2].hidden = True
    wb.create_sheet("Two")["A1"] = "y"
    wb.create_sheet("Hidden").sheet_state = "hidden"


def _with_comment() -> bytes:
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    com = (
        f'<comments xmlns="{ns}"><authors><author>a</author></authors><commentList>'
        '<comment ref="A1" authorId="0"><text><t>n</t></text></comment></commentList></comments>'
    ).encode()
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
    rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdc" Type="{rel}" Target="../comments1.xml"/></Relationships>'
    ).encode()
    add = {"xl/comments1.xml": com, "xl/worksheets/_rels/sheet1.xml.rels": rels}
    return rewrite_zip(workbook_bytes(_plain), add=add)


CORPUS: list[Callable[[], bytes]] = [
    lambda: workbook_bytes(_plain),
    lambda: workbook_bytes(_rich),
    _with_comment,
]


def _name(target: Any) -> str:
    return target.orig_filename if isinstance(target, zipfile.ZipInfo) else str(target)


@pytest.mark.parametrize("make", CORPUS, ids=["plain", "rich", "comment"])
def test_openpyxl_opens_only_parts_the_scanner_read(
    make: Callable[[], bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = make()
    scanned: set[str] = set()
    orig_read = ooxml._Reader.read  # pyright: ignore[reportPrivateUsage]

    def spy_scan(self: Any, info: zipfile.ZipInfo, cap: int | None = None) -> bytes:
        scanned.add(info.orig_filename)
        return orig_read(self, info, cap)

    monkeypatch.setattr(ooxml._Reader, "read", spy_scan)  # pyright: ignore[reportPrivateUsage]
    ooxml.inspect_xlsx_package(data, L)
    monkeypatch.undo()

    opened: set[str] = set()
    orig_open, orig_zread = zipfile.ZipFile.open, zipfile.ZipFile.read

    def spy_open(self: zipfile.ZipFile, name: Any, *a: Any, **k: Any) -> Any:
        opened.add(_name(name))
        return orig_open(self, name, *a, **k)

    def spy_zread(self: zipfile.ZipFile, name: Any, *a: Any, **k: Any) -> bytes:
        opened.add(_name(name))
        return orig_zread(self, name, *a, **k)

    monkeypatch.setattr(zipfile.ZipFile, "open", spy_open)
    monkeypatch.setattr(zipfile.ZipFile, "read", spy_zread)
    extract_plain(data, L)
    assert opened and opened <= scanned
    assert all(n.startswith("xl/worksheets/") for n in opened if "/worksheets/sheet" in n)
