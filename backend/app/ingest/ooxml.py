# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Package-level checks on an untrusted xlsx before openpyxl sees it.

Every refusal is a fixed reason code; no part name or content is ever put in an error.
"""

import posixpath
import zipfile
from collections.abc import Mapping
from io import BytesIO
from xml.etree.ElementTree import Element  # noqa: S405  (type only; parsing is defusedxml)

from openpyxl.utils.cell import range_boundaries

from app.ingest.errors import IntakeRejected, Limits, Reason
from app.ingest.safe_xml import parse_xml, scan_xml

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


class _Reader:
    """Streams entries, counting the bytes actually inflated (headers can lie)."""

    def __init__(self, zf: zipfile.ZipFile, limits: Limits, data_len: int) -> None:
        self.zf, self.limits, self.total = zf, limits, 0
        self.compressed = max(1, min(data_len, sum(i.compress_size for i in zf.infolist())))

    def read(self, info: zipfile.ZipInfo, cap: int | None = None) -> bytes:
        chunks: list[bytes] = []
        n = 0
        try:
            with self.zf.open(info) as f:
                while chunk := f.read(65536):
                    n += len(chunk)
                    self.total += len(chunk)
                    if self.total > self.limits.zip_max_total_bytes or (
                        cap is not None and n > cap
                    ):
                        raise IntakeRejected("archive_too_large")
                    if self.total > self.limits.zip_max_ratio * self.compressed:
                        raise IntakeRejected("archive_ratio")
                    chunks.append(chunk)
        except IntakeRejected:
            raise
        except Exception:  # BadZipFile (CRC), zlib.error, RuntimeError, ...: all one reason
            raise IntakeRejected("archive_malformed") from None
        return b"".join(chunks)


# relationship Type (last URI segment, lower case) -> reason; matched on the type, never the name
_REL_REFUSED: dict[str, Reason] = {
    "externallink": "external_link",
    "externallinkpath": "external_link",
    "connections": "external_link",
    "oleobject": "embedded_object",
    "package": "embedded_object",
    "activexcontrol": "embedded_object",
    "activexcontrolbinary": "embedded_object",
    "vbaproject": "macro",
}
# content-type substring (lower case) -> reason
_CT_REFUSED: tuple[tuple[str, Reason], ...] = (
    ("macroenabled", "macro"),
    ("vbaproject", "macro"),
    ("externallink", "external_link"),
    ("spreadsheetml.connections", "external_link"),
    ("oleobject", "embedded_object"),
    ("activex", "embedded_object"),
)


def _check_content_types(root: Element) -> None:
    types = [e.get("ContentType", "") for e in root if e.tag.endswith(("Override", "Default"))]
    for t in types:
        for needle, reason in _CT_REFUSED:
            if needle in t.lower():
                raise IntakeRejected(reason)
    if _XLSX_MAIN not in types:
        raise IntakeRejected("unsupported_type")


def _targets(rels_name: str, root: Element, names: set[str]) -> list[tuple[str, str]]:
    """Check one .rels part; return (type, resolved part name) of its internal relationships."""
    base = posixpath.dirname(posixpath.dirname(rels_name))  # the source part's folder
    out: list[tuple[str, str]] = []
    for rel in root:
        if not rel.tag.endswith("Relationship"):
            continue
        rtype = rel.get("Type", "").rsplit("/", 1)[-1].lower()
        if rtype in _REL_REFUSED:
            raise IntakeRejected(_REL_REFUSED[rtype])
        if rel.get("TargetMode") == "External":
            if rtype != "hyperlink":
                raise IntakeRejected("external_link")
            continue
        t = rel.get("Target", "").split("#")[0]
        path = posixpath.normpath(t[1:] if t.startswith("/") else posixpath.join(base, t))
        if not t or path == ".." or path.startswith("../"):
            raise IntakeRejected("archive_bad_entry_name")
        if path not in names:
            raise IntakeRejected("workbook_malformed")
        out.append((rtype, path))
    return out


class _SheetCaps:
    """Per-sheet and workbook-wide caps, counted from the XML before openpyxl allocates."""

    def __init__(self, limits: Limits, workbook_grid: int) -> None:
        self.limits, self.workbook_grid = limits, workbook_grid
        self.merged = 0
        self.max_row = self.max_col = 0

    def on_start(self, tag: str, attrib: Mapping[str, str]) -> None:
        if tag == "mergeCell":
            self._merge(attrib.get("ref", ""))
        elif tag == "dimension":
            self._grid(attrib.get("ref", ""))
        elif tag == "c":
            self._cell(attrib.get("r", ""))

    def _bounds(self, ref: str) -> tuple[int, int, int, int]:
        try:
            c0, r0, c1, r1 = range_boundaries(ref)
        except (ValueError, TypeError):
            raise IntakeRejected("workbook_malformed") from None
        if c0 is None or r0 is None or c1 is None or r1 is None or c1 < c0 or r1 < r0:
            raise IntakeRejected("workbook_malformed")  # whole-column refs are not ranges
        return c0, r0, c1, r1

    def _merge(self, ref: str) -> None:
        c0, r0, c1, r1 = self._bounds(ref)
        self.merged += (c1 - c0 + 1) * (r1 - r0 + 1)
        if self.merged > self.limits.max_merged_cells:
            raise IntakeRejected("sheet_too_large")

    def _grid(self, ref: str) -> None:
        _, _, c1, r1 = self._bounds(ref)
        self._extend(r1, c1)

    def _cell(self, ref: str) -> None:
        _, _, c1, r1 = self._bounds(ref)
        self._extend(r1, c1)

    def _extend(self, row: int, col: int) -> None:
        self.max_row, self.max_col = max(self.max_row, row), max(self.max_col, col)
        if self.max_row * self.max_col > self.limits.sheet_max_cells:
            raise IntakeRejected("sheet_too_large")

    def finish(self) -> int:
        self.workbook_grid += self.max_row * self.max_col
        if self.workbook_grid > self.limits.workbook_max_cells:
            raise IntakeRejected("sheet_too_large")
        return self.workbook_grid


def inspect_xlsx_package(data: bytes, limits: Limits) -> dict[str, Element]:
    """Returns only the small parts that are tree-parsed: content types, .rels, the workbook."""
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
        files = {i.orig_filename: i for i in infos if not i.is_dir()}
        for n in files:
            _refuse_named(n)
        declared = sum(i.file_size for i in files.values())
        if declared > limits.zip_max_total_bytes:
            raise IntakeRejected("archive_too_large")
        if declared / max(1, sum(i.compress_size for i in files.values())) > limits.zip_max_ratio:
            raise IntakeRejected("archive_ratio")
        rd = _Reader(zf, limits, len(data))

        def tree(name: str) -> Element:
            return parse_xml(rd.read(files[name], limits.xml_tree_max_bytes))

        if _CT not in files:
            raise IntakeRejected("archive_malformed")
        trees = {_CT: tree(_CT)}
        _check_content_types(trees[_CT])
        known = set(files)
        links: dict[str, list[tuple[str, str]]] = {}
        for n in files:
            if n.endswith(".rels"):
                trees[n] = tree(n)
                links[n] = _targets(n, trees[n], known)
        wb = next((p for t, p in links.get("_rels/.rels", []) if t == "officedocument"), None)
        if wb is None:
            raise IntakeRejected("workbook_malformed")
        trees[wb] = tree(wb)
        wb_rels = posixpath.join(posixpath.dirname(wb), "_rels", posixpath.basename(wb) + ".rels")
        # worksheets are what the workbook's relationships say, not what a path pattern says
        sheets = {p for t, p in links.get(wb_rels, []) if t == "worksheet"}
        if any(not p.startswith("xl/worksheets/") for p in sheets):
            raise IntakeRejected("unsupported_part")  # before openpyxl can load it
        grid = 0
        for n, info in files.items():
            if n in trees:
                continue
            caps = _SheetCaps(limits, grid) if n in sheets else None
            scan_xml(
                rd.read(info),
                max_elements=limits.xml_max_elements,
                max_depth=limits.xml_max_depth,
                on_start=caps.on_start if caps else None,
            )
            grid = caps.finish() if caps else grid
    return trees
