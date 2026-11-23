# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import hashlib
import struct
import time
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

import pdfplumber
import pytest

import app.ingest.pdf as pdf_mod
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


def _rc4(key: bytes, data: bytes) -> bytes:
    sbox, j = list(range(256)), 0
    for i in range(256):
        j = (j + sbox[i] + key[i % len(key)]) % 256
        sbox[i], sbox[j] = sbox[j], sbox[i]
    out, i, j = bytearray(), 0, 0
    for byte in data:
        i = (i + 1) % 256
        j = (j + sbox[i]) % 256
        sbox[i], sbox[j] = sbox[j], sbox[i]
        out.append(byte ^ sbox[(sbox[i] + sbox[j]) % 256])
    return bytes(out)


def _empty_password_rc4_pdf() -> bytes:
    """40-bit RC4 (V1 R2) with an EMPTY user password: it opens without any password."""
    pad = bytes.fromhex("28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A")
    owner, ident, perms = b"o" * 32, b"0123456789abcdef", -4
    key = hashlib.md5(pad + owner + struct.pack("<i", perms) + ident).digest()[:5]  # noqa: S324
    user = _rc4(key, pad)
    enc = b"<< /Filter /Standard /V 1 /R 2 /P %d /O <%s> /U <%s> >>" % (
        perms,
        owner.hex().encode(),
        user.hex().encode(),
    )
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
        3: enc,
        4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] >>",
    }
    h = ident.hex().encode()
    return build_pdf(objs, trailer_extra=b"/Encrypt 3 0 R /ID [<%s> <%s>]" % (h, h))


def test_encrypted_pdf_with_empty_password_is_refused() -> None:
    _rejects(_empty_password_rc4_pdf(), "pdf_encrypted")


def test_encrypted_pdf_with_unknown_password_is_refused() -> None:
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Count 0 /Kids [] >>",
        3: b"<< /Filter /Standard /V 1 /R 2 /P -4 /O (%s) /U (%s) >>" % (b"a" * 32, b"b" * 32),
    }
    _rejects(build_pdf(objs, trailer_extra=b"/Encrypt 3 0 R /ID [(a)(b)]"), "pdf_encrypted")


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


REPLIES: list[list[list[Any]]] = [
    [[0, 612, 792, []]],  # page 0
    [[1, 612, 792, [[MARKER, 5, 1, 4, 2]]]],  # x0 > x1
    [[1, 612, 792, [[MARKER, float("nan"), 1, 4, 2]]]],
    [[1, 612, 792, [[MARKER]]]],  # wrong shape
    [[2, 612, 792, []], [1, 612, 792, []]],  # out of order
    [[1, 612, 792, []], [3, 612, 792, []]],  # gap
]


@pytest.mark.parametrize("reply", REPLIES)
def test_hostile_worker_reply_is_pdf_malformed(
    monkeypatch: pytest.MonkeyPatch, reply: list[list[Any]]
) -> None:
    def fake(data: bytes, limits: Limits) -> list[list[Any]]:  # noqa: ARG001
        return reply

    monkeypatch.setattr(pdf_mod, "run_pdf_worker", fake)
    _rejects(b"%PDF-", "pdf_malformed")


def _page_tree(n: int) -> bytes:
    kids = " ".join(f"{i} 0 R" for i in range(10, 10 + n))
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Count {n} /Kids [{kids}] >>".encode(),
        **{i: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] >>" for i in range(10, 10 + n)},
    }
    return build_pdf(objs)


def test_page_cap_fires_before_any_page_is_extracted() -> None:
    # page_seconds=0 would give pdf_timeout if the cap ran after the first extraction
    _rejects(
        make_pdf([[(72, 700, "a")], [], []]),
        "pdf_too_many_pages",
        Limits(pdf_max_pages=2, pdf_page_seconds=0),
    )


def test_many_pages_rejected_without_materialising_them() -> None:
    data = _page_tree(60_000)
    start = time.monotonic()
    _rejects(data, "pdf_too_many_pages", Limits(pdf_max_objects=10**6))
    assert time.monotonic() - start < 3  # building 60k Page objects first takes about 4 s


def _cmap_pdf() -> bytes:
    cmap = b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
    cmap += b"1 begincodespacerange <00> <FF> endcodespacerange\n"
    cmap += b"1 beginbfchar <41> <0000> endbfchar\nendcmap end end"
    content = b"BT /F1 12 Tf 72 700 Td (AB) Tj ET"
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /ToUnicode 6 0 R >>",
        4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
        5: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        6: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(cmap), cmap),
    }
    return build_pdf(objs)


def test_nul_in_extracted_text_is_rejected() -> None:
    _rejects(_cmap_pdf(), "pdf_malformed")


def _simple_pdf(font: bytes, content: bytes, extra: dict[int, bytes] | None = None) -> bytes:
    return build_pdf(
        {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: b"<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
            3: font,
            4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
            5: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
            **(extra or {}),
        }
    )


def test_ligature_is_not_expanded() -> None:
    font = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding << /Type /Encoding /Differences [1 /fi] >> >>"
    )
    pdf = _simple_pdf(font, b"BT /F1 12 Tf 72 700 Td (\\001) Tj ET")
    locs, _ = parse_pdf(pdf, version_id=1, first_locator_id=1, now=NOW, limits=Limits())
    assert [x.snippet for x in locs] == ["ﬁ"]  # one ligature character, not "fi"


def test_punctuation_is_not_split() -> None:
    locs, _ = parse_pdf(
        make_pdf([[(72, 700, "OT-1.2/x")]]),
        version_id=1,
        first_locator_id=1,
        now=NOW,
        limits=Limits(),
    )
    assert [x.snippet for x in locs] == ["OT-1.2/x"]
