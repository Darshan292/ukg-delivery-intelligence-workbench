# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour. Hand-written PDFs through the real intake."""

from decimal import Decimal
from typing import Any

from openpyxl import Workbook

from app.extract.pdf import MentionRule, PdfRuleCatalogue, extract_pdf_rules
from app.extract.xlsx import Extracted
from app.ingest.intake import Ingested, ingest
from tests.extract.helpers import NOW, edges, put, run
from tests.ingest.pdfs import Word, make_pdf

RULES = PdfRuleCatalogue(
    product_profile="synthetic",
    comention_method="pdf_comention@1",
    value_method="pdf_value_match@1",
    comention=(
        MentionRule(
            source_type="bundle",
            target_type="limit",
            relationship_type="contains",
            confidence=Decimal("0.6"),
        ),
    ),
    value_holders=(
        MentionRule(
            source_type="check",
            target_type="limit",
            relationship_type="asserts_value",
            confidence=Decimal("0.5"),
        ),
    ),
)

LIMITS: list[list[Any]] = [
    ["limit_id", "hours", "label"],
    ["L-1", 40, "a"],
    ["L-2", 37.5, "b"],
    ["L-3", 5, 5],  # two attributes hold 5
    ["L-4", 7, True],  # a boolean attribute: never matches a number
    ["L-5", 0.3, "c"],
]


def config(wb: Workbook) -> None:
    put(wb, "Limits", LIMITS)
    put(wb, "Bundles", [["bundle_id"], ["B-1"], ["X-1"]])
    put(wb, "Checks", [["check_id"], ["C-1"]])


def with_x_limit(wb: Workbook) -> None:
    config(wb)
    wb.worksheets[0].append(["X-1", 1, "x"])


def pdf_run(
    pages: list[list[Word]], *, build: Any = config, rules: PdfRuleCatalogue = RULES
) -> tuple[Ingested, Extracted]:
    _, x = run(build)
    ing = ingest(
        x.records,
        make_pdf(pages),
        declared_kind="pdf",
        product_profile="synthetic",
        title="design note",
        uploaded_by=1,
        snapshot_id=None,
        now=NOW,
    )
    return ing, extract_pdf_rules(ing.records, ing.parsed, rules, now=NOW)


def line(*words: str, y: float = 700) -> list[Word]:
    return [(72 + 60 * i, y, w) for i, w in enumerate(words)]


def pdf_edges(x: Extracted) -> set[tuple[Any, ...]]:
    """Edges whose claims cite pdf words: (type, src, dst, qualifier, words)."""
    r = x.records
    ids = {loc.id for loc in r.locators if loc.kind == "pdf_word_bbox"}
    out: set[tuple[Any, ...]] = set()
    for c in r.claims:
        if not ids & set(c.locator_ids):
            continue
        rel = r.relationship_by_id[c.relationship_id]
        out.add(
            (
                rel.type,
                r.entity_by_id[rel.source_entity_id].natural_key,
                r.entity_by_id[rel.target_entity_id].natural_key,
                rel.qualifier,
                tuple(getattr(r.locator_by_id[i], "snippet") for i in c.locator_ids),  # noqa: B009
            )
        )
    return out


__all__ = ["RULES", "edges", "line", "pdf_edges", "pdf_run", "with_x_limit"]
