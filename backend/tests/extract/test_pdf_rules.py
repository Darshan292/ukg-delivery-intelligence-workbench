# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""D2 co-mention and D3 value-match rule claims. Test-only. FICTIONAL: not UKG behaviour."""

from decimal import Decimal

from tests.extract.pdf_helpers import line, pdf_edges, pdf_run


def test_comention_claim() -> None:
    _, x = pdf_run([line("B-1", "contains", "L-1")])
    assert pdf_edges(x) == {("contains", "B-1", "L-1", None, ("B-1", "L-1"))}


def test_rule_claim_has_method_and_confidence() -> None:
    _, x = pdf_run([line("B-1", "contains", "L-1")])
    c = x.records.claims[-1]
    assert (c.basis, c.polarity, c.method, c.confidence) == (
        "deterministic_rule",
        "present",
        "pdf_comention@1",
        Decimal("0.6"),
    )
    assert c.scope_snapshot_id is None  # the design note has no snapshot
    assert {x.records.locator_by_id[i].kind for i in c.locator_ids} == {"pdf_word_bbox"}


def test_no_rule_no_claim() -> None:
    # two limits on a line: no limit-to-limit rule, and text is not a claim
    _, x = pdf_run([line("L-1", "and", "L-2")])
    assert pdf_edges(x) == set()


def test_other_line_no_claim() -> None:
    _, x = pdf_run([[(72, 700, "B-1"), (72, 600, "L-1")]])
    assert pdf_edges(x) == set()


def test_value_match_decimal() -> None:
    _, x = pdf_run([line("C-1", "expects", "L-2", "=", "37.50")])  # 37.50 equals 37.5 exactly
    assert pdf_edges(x) == {("asserts_value", "C-1", "L-2", "hours", ("C-1", "L-2", "37.50"))}
    assert x.records.claims[-1].method == "pdf_value_match@1"
    assert x.records.claims[-1].confidence == Decimal("0.5")


def test_value_match_decimal_not_float() -> None:
    _, x = pdf_run([line("C-1", "L-5", "0.30")])  # a float sum 0.1+0.2 would not equal 0.3
    assert len(pdf_edges(x)) == 1


def test_value_match_ambiguous() -> None:
    _, x = pdf_run([line("C-1", "L-3", "5")])  # hours and label both hold 5
    assert pdf_edges(x) == set()
    assert [b.reason for b in x.records.extraction_boundaries] == ["ambiguous_target"]


def test_bool_never_number() -> None:
    _, x = pdf_run([line("C-1", "L-4", "1")])  # label is True; Decimal(1) == True in Python
    assert pdf_edges(x) == set()
    assert not x.records.extraction_boundaries
