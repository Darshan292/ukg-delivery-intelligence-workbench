# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: tiny hand-written PDFs (Helvetica text, a classic xref table)."""

from collections.abc import Sequence

Word = tuple[float, float, str]  # x, y (from the bottom), text


def _esc(t: str) -> str:
    return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(objs: dict[int, bytes], root: int = 1, trailer_extra: bytes = b"") -> bytes:
    """Serialise numbered object bodies with a correct xref table."""
    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for n in sorted(objs):
        offsets[n] = len(out)
        out += b"%d 0 obj\n" % n + objs[n] + b"\nendobj\n"
    size = max(objs) + 1
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for n in range(1, size):
        out += (b"%010d 00000 n \n" % offsets[n]) if n in offsets else b"0000000000 65535 f \n"
    out += b"trailer\n<< /Size %d /Root %d 0 R %s >>\nstartxref\n%d\n%%%%EOF\n" % (
        size,
        root,
        trailer_extra,
        xref,
    )
    return bytes(out)


def make_pdf(
    pages: Sequence[Sequence[Word]],
    *,
    size: tuple[int, int] = (612, 792),
    extra_objects: int = 0,
    catalog_extra: str = "",
) -> bytes:
    """Object ids: 1 catalog, 2 page tree, 3 font, then (page, content) pairs, then padding."""
    objs: dict[int, bytes] = {3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"}
    kids: list[int] = []
    n = 4
    for words in pages:
        body = "".join(f"BT /F1 12 Tf {x} {y} Td ({_esc(t)}) Tj ET\n" for x, y, t in words)
        objs[n + 1] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(body), body.encode())
        objs[n] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {size[0]} {size[1]}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {n + 1} 0 R >>"
        ).encode()
        kids.append(n)
        n += 2
    objs[2] = (
        f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(f'{k} 0 R' for k in kids)}] >>"
    ).encode()
    objs[1] = f"<< /Type /Catalog /Pages 2 0 R {catalog_extra} >>".encode()
    for _ in range(extra_objects):
        objs[n] = b"<< /Padding true >>"
        n += 1
    return build_pdf(objs)
