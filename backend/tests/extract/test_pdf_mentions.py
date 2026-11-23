# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""D1 mention index. Test-only. FICTIONAL: not UKG behaviour."""

from tests.extract.pdf_helpers import line, pdf_edges, pdf_run, with_x_limit


def test_mention_trim() -> None:
    _, x = pdf_run([line("B-1", "holds", "L-1,")])  # the comma is trimmed before matching
    assert pdf_edges(x) == {("contains", "B-1", "L-1", None, ("B-1", "L-1,"))}


def test_mention_case_sensitive() -> None:
    _, x = pdf_run([line("B-1", "holds", "l-1")])
    assert pdf_edges(x) == set()


def test_mention_ambiguous() -> None:
    # X-1 is both a limit and a bundle: the word is stated, never guessed
    _, x = pdf_run([line("X-1", "holds", "L-1")], build=with_x_limit)
    ids = [i for i, loc in enumerate(x.records.locators) if loc.kind == "pdf_word_bbox"]
    assert ids
    assert [b.reason for b in x.records.extraction_boundaries] == ["ambiguous_target"]
    assert pdf_edges(x) == set()
