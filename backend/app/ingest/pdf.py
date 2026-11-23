# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""PDF to word locators and page fragments.

pdfplumber and pdfminer run ONLY in the sandbox child (app.ingest.sandbox, started with the PDF
limits); the parent never imports them. The child returns plain JSON: pages of
[page, width, height, [[text, x0, top, x1, bottom], ...]]. Annotations, attachments and
JavaScript are never read.
"""

import dataclasses
import time
from datetime import datetime
from io import BytesIO
from itertools import islice
from typing import Any

from app.domain.locators import PdfWordBbox
from app.ingest.errors import IntakeRejected, Limits
from app.ingest.fragments import PageFragment
from app.ingest.sandbox import run_sandboxed


def extract_pdf(data: bytes, limits: Limits) -> object:
    """Runs in the sandbox child. Any exception other than IntakeRejected becomes pdf_malformed."""
    import pdfplumber  # noqa: PLC0415  (lazy: after the child's rlimits, never in the parent)
    from pdfminer.pdfpage import PDFPage  # noqa: PLC0415

    start = time.monotonic()
    pages: list[list[Any]] = []
    n_words = 0
    # no `with`: PDF.close() walks pdf.pages, which builds every Page; the child exits anyway
    pdf = pdfplumber.open(BytesIO(data))
    if sum(len(list(x.get_objids())) for x in pdf.doc.xrefs) > limits.pdf_max_objects:
        raise IntakeRejected("pdf_too_many_objects")
    # count lazily, stopping at cap + 1: pdf.pages would build every Page object first
    if sum(1 for _ in islice(PDFPage.create_pages(pdf.doc), limits.pdf_max_pages + 1)) > (
        limits.pdf_max_pages
    ):
        raise IntakeRejected("pdf_too_many_pages")
    for done, page in enumerate(pdf.pages, 1):
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            x_tolerance_ratio=None,
            y_tolerance_ratio=None,
            keep_blank_chars=False,
            use_text_flow=False,
            split_at_punctuation=False,
            expand_ligatures=False,
        )
        n_words += len(words)
        if n_words > limits.pdf_max_words:
            raise IntakeRejected("pdf_too_many_words")
        pages.append(
            [
                page.page_number,
                float(page.width),
                float(page.height),
                [[w["text"], w["x0"], w["top"], w["x1"], w["bottom"]] for w in words],
            ]
        )
        if time.monotonic() - start > limits.pdf_page_seconds * done:
            raise IntakeRejected("pdf_timeout")
    if not pages:
        raise IntakeRejected("pdf_malformed")
    return pages


def run_pdf_worker(data: bytes, limits: Limits) -> list[Any]:
    """The PDF limits drive the shared sandbox (resource_limit on wall clock, memory, reply cap)."""
    sandbox_limits = dataclasses.replace(
        limits,
        worker_seconds=limits.pdf_total_seconds,
        worker_memory_bytes=limits.pdf_memory_bytes,
    )
    out: list[Any] = run_sandboxed(extract_pdf, data, sandbox_limits, on_error="pdf_malformed")
    return out


EXTRACTOR = "pdf_words@1"


def parse_pdf(
    data: bytes, *, version_id: int, first_locator_id: int, now: datetime, limits: Limits
) -> tuple[tuple[PdfWordBbox, ...], tuple[PageFragment, ...]]:
    raw = run_pdf_worker(data, limits)
    locs: list[PdfWordBbox] = []
    pages: list[PageFragment] = []
    try:
        for page, width, height, words in raw:
            ids: list[int] = []
            for text, x0, top, x1, bottom in words:
                i = first_locator_id + len(locs)
                locs.append(
                    PdfWordBbox(
                        id=i,
                        document_version_id=version_id,
                        snippet=text,
                        extractor=EXTRACTOR,
                        extracted_at=now,
                        kind="pdf_word_bbox",
                        page=page,  # pdfplumber page_number: 1-based
                        x0=x0,
                        top=top,
                        x1=x1,
                        bottom=bottom,
                    )
                )
                ids.append(i)
            pages.append(
                PageFragment(page=page, width=width, height=height, word_locator_ids=tuple(ids))
            )
    except Exception:  # a hostile reply must never leak a pydantic error carrying content
        raise IntakeRejected("pdf_malformed") from None
    return tuple(locs), tuple(pages)
