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
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
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


def _check_content_types(root: Element) -> str:
    """Refuse bad content types; return the workbook part named by the main-type Override."""
    types = [e.get("ContentType", "") for e in root if e.tag.endswith(("Override", "Default"))]
    for t in types:
        for needle, reason in _CT_REFUSED:
            if needle in t.lower():
                raise IntakeRejected(reason)
    mains = [
        e.get("PartName", "")
        for e in root
        if e.tag.endswith("Override") and e.get("ContentType") == _XLSX_MAIN
    ]
    if not mains:
        raise IntakeRejected("unsupported_type")
    if len(mains) > 1:
        raise IntakeRejected("package_inconsistent")
    return posixpath.normpath(mains[0].lstrip("/"))


def _targets(rels_name: str, root: Element, names: set[str]) -> list[tuple[str, str, str]]:
    """Check one .rels part; return (id, type, resolved part) of its internal relationships."""
    base = posixpath.dirname(posixpath.dirname(rels_name))  # the source part's folder
    out: list[tuple[str, str, str]] = []
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
        out.append((rel.get("Id", ""), rtype, path))
    return out


class _Totals:
    """Workbook-wide running totals shared by every part's caps."""

    grid = 0
    merged = 0
    cells = 0


class _SheetCaps:
    """Per-part and workbook-wide caps, counted from the XML before openpyxl allocates.

    Counted: cells (`c`), `dimension`, merges and hyperlink ranges. openpyxl materialises a
    cell for every address in a hyperlink range and a MergedCell for every merged address.
    Not counted (stored as range text, no cells created): dataValidation sqref and
    conditionalFormatting sqref.
    """

    def __init__(self, limits: Limits, totals: _Totals) -> None:
        self.limits, self.totals = limits, totals
        self.linked = 0
        self.max_row = self.max_col = 0

    def on_start(self, tag: str, attrib: Mapping[str, str]) -> None:
        if tag == "mergeCell":
            c0, r0, c1, r1 = self._bounds(attrib.get("ref", ""))
            self.totals.merged += (c1 - c0 + 1) * (r1 - r0 + 1)
            if self.totals.merged > self.limits.max_merged_cells:
                raise IntakeRejected("sheet_too_large")
            self._extend(r1, c1)
        elif tag == "hyperlink":
            c0, r0, c1, r1 = self._bounds(attrib.get("ref", ""))
            area = (c1 - c0 + 1) * (r1 - r0 + 1)
            self.linked += area
            self.totals.cells += area
            if (
                self.linked > self.limits.sheet_max_cells
                or self.totals.cells > self.limits.workbook_max_cells
            ):
                raise IntakeRejected("sheet_too_large")
            self._extend(r1, c1)
        elif tag in ("dimension", "c"):
            _, _, c1, r1 = self._bounds(attrib.get("ref" if tag == "dimension" else "r", ""))
            self._extend(r1, c1)

    def _bounds(self, ref: str) -> tuple[int, int, int, int]:
        try:
            c0, r0, c1, r1 = range_boundaries(ref)
        except (ValueError, TypeError):
            raise IntakeRejected("workbook_malformed") from None
        if c0 is None or r0 is None or c1 is None or r1 is None or c1 < c0 or r1 < r0:
            raise IntakeRejected("workbook_malformed")  # whole-column refs are not ranges
        return c0, r0, c1, r1

    def _extend(self, row: int, col: int) -> None:
        self.max_row, self.max_col = max(self.max_row, row), max(self.max_col, col)
        if self.max_row * self.max_col > self.limits.sheet_max_cells:
            raise IntakeRejected("sheet_too_large")

    def finish(self) -> None:
        self.totals.grid += self.max_row * self.max_col
        if self.totals.grid > self.limits.workbook_max_cells:
            raise IntakeRejected("sheet_too_large")


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
        wb_main = _check_content_types(trees[_CT])
        known = set(files)
        links: dict[str, list[tuple[str, str, str]]] = {}
        for n in files:
            if n.endswith(".rels"):
                trees[n] = tree(n)
                links[n] = _targets(n, trees[n], known)
        wb = next((p for _, t, p in links.get("_rels/.rels", []) if t == "officedocument"), None)
        if wb is None:
            raise IntakeRejected("workbook_malformed")
        if wb != wb_main:  # openpyxl follows the Override; a second opinion must agree
            raise IntakeRejected("package_inconsistent")
        trees[wb] = tree(wb)
        wb_rels = posixpath.join(posixpath.dirname(wb), "_rels", posixpath.basename(wb) + ".rels")
        by_id = {i: (t, p) for i, t, p in links.get(wb_rels, [])}
        # sheets are what <sheet r:id> resolves to by Id (as openpyxl does), whatever the Type
        sheets: dict[str, str] = {}
        for el in trees[wb].iter():
            if el.tag.rsplit("}", 1)[-1] == "sheet":
                rid = el.get(f"{{{_R_NS}}}id", "")
                if rid not in by_id:
                    raise IntakeRejected("workbook_malformed")
                sheets[by_id[rid][1]] = by_id[rid][0]
        for path, rtype in sheets.items():
            # chartsheets are refused later (S3-Q13); everything else must sit in the sheet folder
            if path in trees or (rtype != "chartsheet" and not path.startswith("xl/worksheets/")):
                raise IntakeRejected("unsupported_part")  # before openpyxl can load it
        totals = _Totals()
        for n, info in files.items():
            if n in trees:
                continue
            caps = _SheetCaps(limits, totals)  # every part, whatever its name or rel type
            scan_xml(
                rd.read(info),
                max_elements=limits.xml_max_elements,
                max_depth=limits.xml_max_depth,
                on_start=caps.on_start,
            )
            caps.finish()
    return trees
