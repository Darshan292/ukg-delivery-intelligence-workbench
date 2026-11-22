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


# --- security review fixes: relationship-driven checks and parse amplification ---

WB_RELS = "xl/_rels/workbook.xml.rels"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _part(data: bytes, name: str) -> bytes:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        return zf.read(name)


def _with_rel(rel_xml: str, part: str | None = None, rels_name: str = WB_RELS) -> bytes:
    data = _wb()
    has = rels_name in _names(data)
    rels = (
        _part(data, rels_name)
        if has
        else (
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            b"</Relationships>"
        )
    )
    rels = rels.replace(b"</Relationships>", rel_xml.encode() + b"</Relationships>")
    extra = {part: b"<a/>"} if part else {}
    if has:
        return rewrite_zip(data, replace={rels_name: rels}, add=extra)
    return rewrite_zip(data, add={rels_name: rels, **extra})


def _names(data: bytes) -> list[str]:
    with zipfile.ZipFile(BytesIO(data)) as zf:
        return zf.namelist()


def _moved_sheet(sheet_xml: bytes, target: str = "sheets2/s.xml") -> bytes:
    data = _wb()
    rels = _part(data, WB_RELS).replace(b"/xl/worksheets/sheet1.xml", target.encode())
    return rewrite_zip(
        data,
        replace={WB_RELS: rels},
        drop=["xl/worksheets/sheet1.xml"],
        add={"xl/sheets2/s.xml": sheet_xml},
    )


def test_merge_cap_applies_to_sheet_at_nonstandard_path() -> None:
    data = _moved_sheet(_sheet_with_merge("A1:Z4000"))
    _rejects(data, "sheet_too_large", Limits(max_merged_cells=1000))


def test_relationship_target_outside_package() -> None:
    data = _moved_sheet(_sheet_with_merge("A1:B2"), target="../../x.xml")
    _rejects(data, "archive_bad_entry_name")


def test_relationship_target_missing_part() -> None:
    data = _moved_sheet(_sheet_with_merge("A1:B2"), target="nope/gone.xml")
    _rejects(data, "workbook_malformed")


@pytest.mark.parametrize(
    ("rel_type", "reason"),
    [
        ("externalLink", "external_link"),
        ("connections", "external_link"),
        ("oleObject", "embedded_object"),
        ("package", "embedded_object"),
        ("activeXControl", "embedded_object"),
        ("vbaProject", "macro"),
    ],
)
def test_renamed_part_refused_by_relationship_type(rel_type: str, reason: Reason) -> None:
    rel = f'<Relationship Id="rId9" Type="{REL_NS}/{rel_type}" Target="misc/a.xml"/>'
    _rejects(_with_rel(rel, "xl/misc/a.xml"), reason)


def test_external_target_mode_refused_except_hyperlink() -> None:
    ext = 'Target="http://example.invalid/i" TargetMode="External"/>'
    bad = f'<Relationship Id="rId9" Type="{REL_NS}/image" {ext}'
    _rejects(_with_rel(bad), "external_link")
    ok = f'<Relationship Id="rId9" Type="{REL_NS}/hyperlink" {ext}'
    assert "xl/workbook.xml" in inspect_xlsx_package(
        _with_rel(ok, rels_name="xl/worksheets/_rels/sheet1.xml.rels"), L
    )


def test_external_link_content_type_on_renamed_part() -> None:
    data = _wb()
    ct = _content_types(data).replace(
        b"</Types>",
        b'<Override PartName="/xl/misc/a.xml" ContentType="application/vnd.openxmlformats-'
        b'officedocument.spreadsheetml.externalLink+xml"/></Types>',
    )
    _rejects(
        rewrite_zip(data, replace={"[Content_Types].xml": ct}, add={"xl/misc/a.xml": b"<a/>"}),
        "external_link",
    )


def test_unneeded_part_is_not_parsed_into_a_tree() -> None:
    pad = b"<r>" + b"".join(b'<a n="%d"/>' % i for i in range(20000)) + b"</r>"
    parts = inspect_xlsx_package(rewrite_zip(_wb(), add={"xl/pad.xml": pad}), L)
    assert "xl/pad.xml" not in parts and "xl/workbook.xml" in parts


def test_unneeded_part_still_scanned_for_dtd_and_caps() -> None:
    _rejects(
        rewrite_zip(_wb(), add={"xl/pad.xml": b"<!DOCTYPE r><r/>"}),
        "xml_forbidden",
    )
    many = b"<r>" + b"".join(b'<a n="%d"/>' % i for i in range(1000)) + b"</r>"
    _rejects(
        rewrite_zip(_wb(), add={"xl/pad.xml": many}), "xml_forbidden", Limits(xml_max_elements=100)
    )
    deep = b"<a>" * 1000 + b"</a>" * 1000
    _rejects(
        rewrite_zip(_wb(), add={"xl/pad.xml": deep}), "xml_forbidden", Limits(xml_max_depth=50)
    )


def test_tree_part_byte_budget() -> None:
    big = b"<r>" + b"<a/>" * 5000 + b"</r>"
    _rejects(
        rewrite_zip(_wb(), replace={"xl/workbook.xml": big}),
        "archive_too_large",
        Limits(xml_tree_max_bytes=1000),
    )
