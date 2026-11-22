# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Package-level checks on an untrusted xlsx before openpyxl sees it.

Every refusal is a fixed reason code; no part name or content is ever put in an error.
"""

import zipfile
from io import BytesIO
from xml.etree.ElementTree import Element  # noqa: S405  (type only; parsing is defusedxml)

from openpyxl.utils.cell import range_boundaries

from app.ingest.errors import IntakeRejected, Limits
from app.ingest.safe_xml import parse_xml

_CT = "[Content_Types].xml"
_XLSX_MAIN = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
_SS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _check_name(raw: str) -> None:
    if not raw or raw.startswith("/") or any(c in raw for c in "\\:\x00") or ".." in raw.split("/"):
        raise IntakeRejected("archive_bad_entry_name")


def _refuse_named(name: str) -> None:
    low = "/" + name.lower()
    if low.endswith("/vbaproject.bin"):
        raise IntakeRejected("macro")
    if low.startswith("/xl/externallinks/") or low == "/xl/connections.xml":
        raise IntakeRejected("external_link")
    if "/embeddings/" in low or "/activex/" in low:
        raise IntakeRejected("embedded_object")
    # owner question S3-Q3 (decided): .xml and .rels parts only
    if not low.endswith((".xml", ".rels")):
        raise IntakeRejected("unsupported_part")


def _read_all(
    zf: zipfile.ZipFile, infos: list[zipfile.ZipInfo], limits: Limits
) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    budget = limits.zip_max_total_bytes
    for info in infos:
        try:
            # bounded read: the size in the header is attacker-controlled, the bytes are not
            body = zf.open(info).read(budget + 1)
        except Exception:  # BadZipFile (CRC), zlib.error, RuntimeError, ...: all one reason
            raise IntakeRejected("archive_malformed") from None
        budget -= len(body)
        if budget < 0:
            raise IntakeRejected("archive_too_large")
        out[info.filename] = body
    return out


def _check_content_types(root: Element) -> None:
    types = [e.get("ContentType", "") for e in root if e.tag.endswith(("Override", "Default"))]
    if any("macroenabled" in t.lower() or "vbaproject" in t.lower() for t in types):
        raise IntakeRejected("macro")
    if _XLSX_MAIN not in types:
        raise IntakeRejected("unsupported_type")


def _check_merges(parts: dict[str, Element], limits: Limits) -> None:
    total = 0
    for name, root in parts.items():
        if not (name.startswith("xl/worksheets/") and name.count("/") == 2):
            continue
        for m in root.iter(f"{_SS}mergeCell"):
            try:
                c0, r0, c1, r1 = range_boundaries(m.get("ref", ""))
            except (ValueError, TypeError):
                raise IntakeRejected("workbook_malformed") from None
            if c0 is None or r0 is None or c1 is None or r1 is None:
                raise IntakeRejected("workbook_malformed")  # whole-column refs are not merges
            area = (c1 - c0 + 1) * (r1 - r0 + 1)
            if area < 1:
                raise IntakeRejected("workbook_malformed")
            total += area
            if total > limits.max_merged_cells:
                raise IntakeRejected("sheet_too_large")


def inspect_xlsx_package(data: bytes, limits: Limits) -> dict[str, Element]:
    try:
        zf = zipfile.ZipFile(BytesIO(data))
    except Exception:  # BadZipFile, ValueError, OSError, ...
        raise IntakeRejected("archive_malformed") from None
    with zf:
        infos = zf.infolist()
        if len(infos) > limits.zip_max_entries:
            raise IntakeRejected("archive_too_many_entries")
        names = [i.orig_filename for i in infos]  # orig keeps NUL and backslashes
        for n in names:
            _check_name(n)
        if len(set(names)) != len(names):
            raise IntakeRejected("archive_bad_entry_name")
        if any(i.flag_bits & 0x1 for i in infos):
            raise IntakeRejected("archive_encrypted")
        files = [i for i in infos if not i.is_dir()]
        for i in files:
            _refuse_named(i.orig_filename)
        declared = sum(i.file_size for i in files)
        if declared > limits.zip_max_total_bytes:
            raise IntakeRejected("archive_too_large")
        if declared / max(1, sum(i.compress_size for i in files)) > limits.zip_max_ratio:
            raise IntakeRejected("archive_ratio")
        raw = _read_all(zf, files, limits)
    parts = {name: parse_xml(body) for name, body in raw.items()}
    if _CT not in parts:
        raise IntakeRejected("archive_malformed")
    _check_content_types(parts[_CT])
    _check_merges(parts, limits)
    return parts
