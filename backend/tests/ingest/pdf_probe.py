# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only sandbox function. Imports nothing heavy itself (openpyxl would load PIL)."""

from app.ingest.errors import Limits


def pdf_modules(data: bytes, limits: Limits) -> object:
    """Parse a PDF in the child, then report which heavy rendering modules got loaded."""
    import sys

    from app.ingest.pdf import extract_pdf

    extract_pdf(data, limits)
    names = ("PIL", "pypdfium2", "pypdfium2_raw")
    return {n: any(m == n or m.startswith(n + ".") for m in sys.modules) for n in names}
