# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import re
import zipfile
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.ingest.errors import IntakeRejected, Limits, Reason
from app.ingest.ooxml import inspect_xlsx_package
from tests.ingest.hostile import (
    CT_NS,
    MARKER,
    SS_NS,
    rewrite_zip,
    workbook_bytes,
    zip_bytes,
)

L = Limits()


def _wb() -> bytes:
    def build(wb: Workbook) -> None:
        wb.active["A1"] = "hello"  # type: ignore[index]  # pyright: ignore[reportOptionalSubscript]

    return workbook_bytes(build)


def _rejects(data: bytes, reason: Reason, limits: Limits = L) -> IntakeRejected:
    with pytest.raises(IntakeRejected) as ei:
        inspect_xlsx_package(data, limits)
    assert ei.value.reason == reason
    return ei.value


def test_minimal_openpyxl_workbook_passes() -> None:
    assert "xl/workbook.xml" in inspect_xlsx_package(_wb(), L)


def test_not_a_zip() -> None:
    _rejects(b"hello", "archive_malformed")
    data = _wb()
    _rejects(data[: len(data) // 2], "archive_malformed")


def test_entry_count_cap() -> None:
    _rejects(_wb(), "archive_too_many_entries", Limits(zip_max_entries=5))


def test_total_uncompressed_cap() -> None:
    data = rewrite_zip(_wb(), add={"xl/pad.xml": b"<a>" + b"x" * (2 * 2**20) + b"</a>"})
    _rejects(data, "archive_too_large", Limits(zip_max_total_bytes=2**20))


def test_zip_bomb_ratio() -> None:
    data = rewrite_zip(_wb(), add={"xl/pad.xml": b"<a/>" * (2**20)})
    _rejects(data, "archive_ratio")


def test_lying_size_header() -> None:
    data = rewrite_zip(_wb(), fake_sizes={"xl/workbook.xml": 10})
    _rejects(data, "archive_malformed")


@pytest.mark.parametrize(
    "name",
    ["../x.xml", "/abs.xml", "a\\b.xml", "C:x.xml", "a/../../b.xml", "a\x00b.xml"],
)
def test_bad_entry_names(name: str) -> None:
    _rejects(rewrite_zip(_wb(), add={name: b"<a/>"}), "archive_bad_entry_name")


def test_duplicate_entry_name() -> None:
    data = rewrite_zip(_wb(), extra_pairs=[("xl/workbook.xml", b"<a/>")])
    _rejects(data, "archive_bad_entry_name")


def test_encrypted_entry() -> None:
    _rejects(rewrite_zip(_wb(), flag_bits=0x1), "archive_encrypted")


def _content_types(data: bytes) -> bytes:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        return zf.read("[Content_Types].xml")


@pytest.mark.parametrize(
    ("part", "reason"),
    [
        ("xl/vbaProject.bin", "macro"),
        ("xl/externalLinks/externalLink1.xml", "external_link"),
        ("xl/connections.xml", "external_link"),
        ("xl/embeddings/oleObject1.bin", "embedded_object"),
        ("xl/activeX/activeX1.xml", "embedded_object"),
        ("xl/inner.zip", "unsupported_part"),
        ("xl/media/image1.png", "unsupported_part"),
    ],
)
def test_refused_parts(part: str, reason: Reason) -> None:
    _rejects(rewrite_zip(_wb(), add={part: b"<a/>"}), reason)


def test_macro_content_type_without_vba_part() -> None:
    ct = _content_types(_wb()).replace(
        b"spreadsheetml.sheet.main+xml", b"ms-excel.sheet.macroEnabled.main+xml"
    )
    _rejects(rewrite_zip(_wb(), replace={"[Content_Types].xml": ct}), "macro")


def test_docx_main_part() -> None:
    ct = (
        f'<Types xmlns="{CT_NS}"><Override PartName="/word/document.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    ).encode()
    data = zip_bytes({"[Content_Types].xml": ct, "word/document.xml": b"<d/>"})
    _rejects(data, "unsupported_type")


def test_missing_content_types() -> None:
    _rejects(rewrite_zip(_wb(), drop=["[Content_Types].xml"]), "archive_malformed")


def test_xxe_in_shared_strings() -> None:
    xxe = f'<!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/hostname">]><r>{MARKER}&e;</r>'.encode()
    exc = _rejects(rewrite_zip(_wb(), add={"xl/sharedStrings.xml": xxe}), "xml_forbidden")
    assert MARKER not in str(exc)


def test_billion_laughs_in_sheet() -> None:
    laughs = (
        b'<!DOCTYPE r [<!ENTITY a "xxxxxxxxxx"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
        b'<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]><r>&c;</r>'
    )
    _rejects(rewrite_zip(_wb(), replace={"xl/worksheets/sheet1.xml": laughs}), "xml_forbidden")


def _sheet_with_merge(ref: str) -> bytes:
    return (
        f'<worksheet xmlns="{SS_NS}"><sheetData/><mergeCells count="1">'
        f'<mergeCell ref="{ref}"/></mergeCells></worksheet>'
    ).encode()


def test_merge_area_cap() -> None:
    data = rewrite_zip(_wb(), replace={"xl/worksheets/sheet1.xml": _sheet_with_merge("A1:Z4000")})
    _rejects(data, "sheet_too_large", Limits(max_merged_cells=1000))


def test_bad_merge_ref() -> None:
    data = rewrite_zip(_wb(), replace={"xl/worksheets/sheet1.xml": _sheet_with_merge("zz")})
    _rejects(data, "workbook_malformed")


def test_reason_message_free_of_names() -> None:
    exc = _rejects(rewrite_zip(_wb(), add={f"../{MARKER}.xml": b"<a/>"}), "archive_bad_entry_name")
    assert MARKER not in str(exc) and MARKER not in repr(exc)
    assert re.fullmatch(r"intake rejected: \w+", str(exc))
