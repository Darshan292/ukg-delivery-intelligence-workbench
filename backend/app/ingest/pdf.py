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
from io import BytesIO
from typing import Any

from app.ingest.errors import IntakeRejected, Limits
from app.ingest.sandbox import run_sandboxed


def extract_pdf(data: bytes, limits: Limits) -> object:
    """Runs in the sandbox child. Any exception other than IntakeRejected becomes pdf_malformed."""
    import pdfplumber  # noqa: PLC0415  (lazy: after the child's rlimits, never in the parent)

    start = time.monotonic()
    pages: list[list[Any]] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(
                x_tolerance=3, y_tolerance=3, keep_blank_chars=False, use_text_flow=False
            )
            pages.append(
                [
                    page.page_number,
                    float(page.width),
                    float(page.height),
                    [[w["text"], w["x0"], w["top"], w["x1"], w["bottom"]] for w in words],
                ]
            )
    if not pages:
        raise IntakeRejected("pdf_malformed")
    _ = start
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
