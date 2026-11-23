# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""ingest(): untrusted bytes plus declared metadata in, new Records plus IR out, or a reason code.

Pure and in-memory: nothing is returned on rejection, so there are no partial records.
"""

import hashlib
import logging
from datetime import datetime
from typing import Literal, Self

from pydantic import SkipValidation, ValidationError, model_validator

from app.domain.model import Document, DocumentVersion, ProductProfile, Record
from app.domain.records import Records
from app.ingest.errors import DEFAULT_LIMITS, IntakeRejected, Limits
from app.ingest.fragments import CellFragment, PageFragment, ParsedDocument, SheetFragment
from app.ingest.pdf import parse_pdf
from app.ingest.xlsx import parse_xlsx

log = logging.getLogger(__name__)


class Ingested(Record):
    # SkipValidation: Records is validated when built; revalidating an instance whose cached
    # lookups are populated fails (extra_forbidden on the cached_property keys)
    records: SkipValidation[Records]
    parsed: ParsedDocument

    @model_validator(mode="after")
    def _acceptance_invariant(self) -> Self:
        """Every fragment resolves; every locator of the version is referenced exactly once."""
        p, r = self.parsed, self.records
        ver = r.version_by_id.get(p.document_version_id)
        if ver is None:
            raise ValueError("ingested: unknown document version")
        if r.document_by_id[ver.document_id].product_profile != p.product_profile:
            raise ValueError("ingested: profile differs from the document's")
        want = "xlsx_cell" if p.kind == "xlsx" else "pdf_word_bbox"
        for i in p.locator_ids:
            loc = r.locator_by_id.get(i)
            if loc is None or loc.kind != want or loc.document_version_id != ver.id:
                raise ValueError(f"ingested: dangling or mismatched locator id {i}")
        if {x.id for x in r.locators if x.document_version_id == ver.id} != set(p.locator_ids):
            raise ValueError("ingested: orphan locator")
        return self


def sniff_kind(data: bytes) -> Literal["xlsx", "pdf"]:
    """The kind comes from the bytes, never from a filename or an extension."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        # a zip container: ooxml.inspect decides whether it is a real xlsx, with a specific reason
        # (macro, malformed, not a spreadsheet), so the sniff stays shallow
        return "xlsx"
    raise IntakeRejected("unsupported_type")


def _next_id(xs: tuple[object, ...]) -> int:
    return max((getattr(x, "id") for x in xs), default=0) + 1  # noqa: B009


def _ingest(
    records: Records,
    data: bytes,
    declared_kind: Literal["xlsx", "pdf"],
    product_profile: ProductProfile,
    title: str,
    uploaded_by: int,
    snapshot_id: int | None,
    now: datetime,
    limits: Limits,
) -> Ingested:
    if (
        product_profile != "synthetic"
    ):  # owner question S3-Q1 (decided): synthetic only until G-REAL
        raise IntakeRejected("profile_not_permitted")
    if len(data) > limits.max_file_bytes:
        raise IntakeRejected("too_large")
    sha = hashlib.sha256(data).hexdigest()
    if any(v.sha256 == sha for v in records.document_versions):  # S3-Q4 (decided): reject
        raise IntakeRejected("already_ingested")
    # owner question S3-Q2 (pending): allow-list is xlsx and pdf only; csv/docx/xml/json refused
    kind = sniff_kind(data)
    if kind != declared_kind:
        raise IntakeRejected("type_mismatch")
    doc_id, ver_id = _next_id(records.documents), _next_id(records.document_versions)
    parse_args = {
        "version_id": ver_id,
        "first_locator_id": _next_id(records.locators),
        "now": now,
        "limits": limits,
    }
    sheets: tuple[SheetFragment, ...] = ()
    cells: tuple[CellFragment, ...] = ()
    pages: tuple[PageFragment, ...] = ()
    if kind == "pdf":
        locs, pages = parse_pdf(data, **parse_args)  # type: ignore[arg-type]
    else:
        locs, sheets, cells = parse_xlsx(data, **parse_args)  # type: ignore[arg-type]
    try:
        new = records.extended(
            documents=(Document(id=doc_id, product_profile=product_profile, title=title),),
            document_versions=(
                DocumentVersion(
                    id=ver_id,
                    document_id=doc_id,
                    sha256=sha,
                    snapshot_id=snapshot_id,
                    supersedes_version_id=None,  # S3-Q5 (decided): lineage deferred to Slice 5
                    declared_by=uploaded_by,
                    uploaded_at=now,
                ),
            ),
            locators=locs,
        )
        parsed = ParsedDocument(
            document_version_id=ver_id,
            product_profile=product_profile,
            kind=kind,
            sheets=sheets,
            cells=cells,
            pages=pages,
        )
        return Ingested(records=new, parsed=parsed)
    except (ValidationError, ValueError):
        raise IntakeRejected("records_invalid") from None


def ingest(
    records: Records,
    data: bytes,
    *,
    declared_kind: Literal["xlsx", "pdf"],
    product_profile: ProductProfile,
    title: str,
    uploaded_by: int,
    snapshot_id: int | None,
    now: datetime,
    limits: Limits = DEFAULT_LIMITS,
) -> Ingested:
    try:
        out = _ingest(
            records,
            data,
            declared_kind,
            product_profile,
            title,
            uploaded_by,
            snapshot_id,
            now,
            limits,
        )
    except IntakeRejected as e:
        log.warning("intake rejected: %s", e.reason)  # reason code only, no exc_info
        raise
    log.info("ingested %s %s", declared_kind, out.records.document_versions[-1].sha256)
    return out
