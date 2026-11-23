# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import time
from datetime import UTC, datetime
from io import BytesIO

import pdfplumber
import pytest

from app.domain.model import Actor, Snapshot
from app.domain.records import Records
from app.ingest.errors import IntakeRejected, Limits, Reason
from app.ingest.fragments import PageFragment
from app.ingest.intake import ingest
from app.ingest.pdf import parse_pdf
from tests.ingest.hostile import MARKER
from tests.ingest.pdfs import build_pdf, make_pdf

_L = Limits()
NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
TWO = [[(72, 700, "OT-1 hello"), (72, 650, "second line")], [(100, 500, "page two")]]


def _rejects(data: bytes, reason: Reason, limits: Limits = _L) -> None:
    with pytest.raises(IntakeRejected) as ei:
        parse_pdf(data, version_id=7, first_locator_id=10, now=NOW, limits=limits)
    exc = ei.value
    assert exc.reason == reason and MARKER not in str(exc) + repr(exc)


def test_two_pages_words_and_dims() -> None:
    locs, pages = parse_pdf(
        make_pdf(TWO), version_id=7, first_locator_id=10, now=NOW, limits=Limits()
    )
    assert [(p.page, p.width, p.height) for p in pages] == [(1, 612, 792), (2, 612, 792)]
    assert [x.snippet for x in locs] == ["OT-1", "hello", "second", "line", "page", "two"]
    assert [x.page for x in locs] == [1, 1, 1, 1, 2, 2]
    assert [x.id for x in locs] == list(range(10, 16))
    assert [p.word_locator_ids for p in pages] == [(10, 11, 12, 13), (14, 15)]
    assert all(x.extractor == "pdf_words@1" and x.document_version_id == 7 for x in locs)
    assert all(x.x0 <= x.x1 and x.top <= x.bottom for x in locs)


def test_empty_page_recorded() -> None:
    _, pages = parse_pdf(
        make_pdf([[(72, 700, "a")], []]), version_id=7, first_locator_id=1, now=NOW, limits=Limits()
    )
    assert pages[1] == PageFragment(page=2, width=612, height=792, word_locator_ids=())


def test_locator_resolves() -> None:
    data = make_pdf(TWO)
    locs, _ = parse_pdf(data, version_id=7, first_locator_id=1, now=NOW, limits=Limits())
    with pdfplumber.open(BytesIO(data)) as pdf:
        for loc in locs:
            page = pdf.pages[loc.page - 1]
            assert page.crop((loc.x0, loc.top, loc.x1, loc.bottom)).extract_text() == loc.snippet


def test_page_cap() -> None:
    _rejects(make_pdf([[], [], []]), "pdf_too_many_pages", Limits(pdf_max_pages=2))


def test_object_cap() -> None:
    _rejects(make_pdf([[]], extra_objects=50), "pdf_too_many_objects", Limits(pdf_max_objects=20))


def test_word_cap() -> None:
    _rejects(make_pdf(TWO), "pdf_too_many_words", Limits(pdf_max_words=3))


def test_per_page_time() -> None:
    _rejects(make_pdf([[(72, 700, "a")]]), "pdf_timeout", Limits(pdf_page_seconds=0))


def test_oversized_reply_is_resource_limit() -> None:
    words = [(10 + i % 40 * 14, 700 - i // 40 * 14, "w") for i in range(200)]
    _rejects(make_pdf([words]), "resource_limit", Limits(worker_max_reply_bytes=1000))


def test_javascript_action_not_handled() -> None:
    js = "/OpenAction << /S /JavaScript /JS (app.alert(1)) >>"
    plain = parse_pdf(make_pdf(TWO), version_id=7, first_locator_id=1, now=NOW, limits=Limits())
    with_js = parse_pdf(
        make_pdf(TWO, catalog_extra=js), version_id=7, first_locator_id=1, now=NOW, limits=Limits()
    )
    assert with_js == plain


def test_overprinted_word_merges_not_duplicates() -> None:
    # pdfplumber groups same-position characters into one (garbled) word, so no duplicate
    # locator arises; Records' content_key uniqueness stays the backstop (S3-Q11)
    out = _ingest(_base(), make_pdf([[(72, 700, "dup"), (72, 700, "dup")]]))
    assert [x.snippet for x in out.records.locators] == ["dduupp"]


def _base() -> Records:
    return Records(
        actors=(Actor(id=1, kind="human", display_name="R", roles=frozenset({"reviewer"})),),
        snapshots=(
            Snapshot(
                id=1, product_profile="synthetic", environment="t", label="s", captured_at=NOW
            ),
        ),
    )


def _ingest(records: Records, data: bytes):  # noqa: ANN202
    return ingest(
        records,
        data,
        declared_kind="pdf",
        product_profile="synthetic",
        title="Synthetic",
        uploaded_by=1,
        snapshot_id=1,
        now=NOW,
    )


def test_ingest_pdf_happy_path_and_invariant() -> None:
    base = _base()
    out = _ingest(base, make_pdf(TWO))  # Ingested validates the invariant on construction
    assert out.parsed.kind == "pdf" and len(out.parsed.pages) == 2
    assert len(out.records.locators) == 6 and set(out.parsed.locator_ids) == {
        x.id for x in out.records.locators
    }


# hostile PDFs: always a fixed reason, never a hang


def test_garbage_and_truncated() -> None:
    _rejects(b"%PDF-1.4\n" + MARKER.encode() * 20, "pdf_malformed")
    data = make_pdf(TWO)
    _rejects(data[: len(data) // 2], "pdf_malformed")


def test_encrypted_pdf() -> None:
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Count 0 /Kids [] >>",
        3: b"<< /Filter /Standard /V 1 /R 2 /P -4 /O ("
        + b"a" * 32
        + b") /U ("
        + b"b" * 32
        + b") >>",
    }
    _rejects(build_pdf(objs, trailer_extra=b"/Encrypt 3 0 R /ID [(a)(b)]"), "pdf_malformed")


def test_huge_page_count() -> None:
    n = 600  # distinct page objects: more than the default cap of 500
    kids = " ".join(f"{i} 0 R" for i in range(10, 10 + n))
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Count {n} /Kids [{kids}] >>".encode(),
        **{i: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] >>" for i in range(10, 10 + n)},
    }
    _rejects(build_pdf(objs), "pdf_too_many_pages")


def test_page_tree_cycle() -> None:
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Count 1 /Kids [2 0 R] >>",
    }
    with pytest.raises(IntakeRejected) as ei:
        parse_pdf(build_pdf(objs), version_id=1, first_locator_id=1, now=NOW, limits=Limits())
    assert ei.value.reason == "pdf_malformed"


def test_deep_indirect_chain_and_nesting() -> None:
    chain = {n: b"%d 0 R" % (n + 1) for n in range(10, 6010)}
    chain[6010] = b"[0 0 100 100]"
    pdf = make_pdf([[(72, 700, "x")]])
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
        4: b"<< /Type /Page /Parent 2 0 R /MediaBox 10 0 R /Foo " + b"[" * 50_000 + b" >>",
        **chain,
    }
    del pdf
    start = time.monotonic()
    with pytest.raises(IntakeRejected) as ei:
        parse_pdf(build_pdf(objs), version_id=1, first_locator_id=1, now=NOW, limits=Limits())
    assert ei.value.reason == "pdf_malformed"
    assert time.monotonic() - start < 60


def test_word_options_pinned() -> None:
    # a 2 pt gap between two show operations: x_tolerance=3 joins them, as pinned
    locs, _ = parse_pdf(
        make_pdf([[(72, 700, "ab"), (87.34, 700, "cd")]]),
        version_id=1,
        first_locator_id=1,
        now=NOW,
        limits=Limits(),
    )
    assert [x.snippet for x in locs] == ["abcd"]


@pytest.mark.parametrize(
    "reply",
    [
        [[0, 612, 792, []]],  # page 0
        [[1, 612, 792, [[MARKER, 5, 1, 4, 2]]]],  # x0 > x1
        [[1, 612, 792, [[MARKER, float("nan"), 1, 4, 2]]]],
        [[1, 612, 792, [[MARKER]]]],  # wrong shape
    ],
)
def test_hostile_worker_reply_is_pdf_malformed(
    monkeypatch: pytest.MonkeyPatch, reply: list[object]
) -> None:
    monkeypatch.setattr("app.ingest.pdf.run_pdf_worker", lambda data, limits: reply)
    _rejects(b"%PDF-", "pdf_malformed")
