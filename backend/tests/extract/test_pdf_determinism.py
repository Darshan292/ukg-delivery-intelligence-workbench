# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""D4 determinism and the invariant for PDFs. Test-only. FICTIONAL: not UKG behaviour."""

import pytest

from app.extract.pdf import extract_pdf_rules
from app.extract.xlsx import AlreadyExtracted
from app.ingest.fragments import ParsedDocument
from tests.extract.helpers import NOW
from tests.extract.pdf_helpers import RULES, line, pdf_run

PAGES = [
    line("B-1", "contains", "L-1", "and", "prose", "here") + line("C-1", "L-2", "37.50", y=650),
    line("B-1", "L-2", y=700),
]


def test_byte_identical_twice() -> None:
    ing, x1 = pdf_run(PAGES)
    x2 = extract_pdf_rules(ing.records, ing.parsed, RULES, now=NOW)
    assert x1.records.model_dump_json() == x2.records.model_dump_json()


def test_reversed_pages_identical() -> None:
    ing, x1 = pdf_run(PAGES)
    p = ing.parsed
    flipped = ParsedDocument(
        document_version_id=p.document_version_id,
        product_profile=p.product_profile,
        kind=p.kind,
        pages=tuple(reversed(p.pages)),
    )
    x2 = extract_pdf_rules(ing.records, flipped, RULES, now=NOW)
    assert x1.records.model_dump_json() == x2.records.model_dump_json()


def test_every_word_consumed_or_structural() -> None:
    ing, x = pdf_run(PAGES)  # Extracted validates itself; prose words are structural
    words = {i for p in ing.parsed.pages for i in p.word_locator_ids}
    prose = {x.records.locator_by_id[i].snippet: i for i in words}["prose"]  # type: ignore[attr-defined]
    assert prose in x.structural_locator_ids


def test_reextract_refused() -> None:
    ing, x = pdf_run(PAGES)
    with pytest.raises(AlreadyExtracted):
        extract_pdf_rules(x.records, ing.parsed, RULES, now=NOW)
