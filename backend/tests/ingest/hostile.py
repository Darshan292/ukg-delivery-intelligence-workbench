# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

import warnings
import zipfile
from collections.abc import Callable, Iterable, Mapping
from io import BytesIO

from openpyxl import Workbook

MARKER = "ZZ-SECRET-MARKER-7731"

CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
SHEET_MAIN = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
SS_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def workbook_bytes(build: Callable[[Workbook], None]) -> bytes:
    wb = Workbook()
    build(wb)
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def zip_pairs(
    pairs: Iterable[tuple[str, bytes]],
    *,
    flag_bits: int = 0,
    fake_sizes: Mapping[str, int] | None = None,
) -> bytes:
    """Deflated zip. flag_bits and fake_sizes are set on the central directory only."""
    out = BytesIO()
    patches: list[tuple[bytes, bytes]] = []
    with warnings.catch_warnings(), zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        warnings.simplefilter("ignore")  # duplicate names are deliberate
        for name, body in pairs:
            safe = name.replace("\x00", "\x01")  # ZipInfo truncates at NUL; patch the bytes back
            if safe != name:
                patches.append((safe.encode(), name.encode()))
            zf.writestr(safe, body)
        for info in zf.filelist:
            info.flag_bits |= flag_bits
            if fake_sizes and info.filename in fake_sizes:
                info.file_size = fake_sizes[info.filename]
    data = out.getvalue()
    for old, new in patches:
        data = data.replace(old, new)
    return data


def zip_bytes(entries: Mapping[str, bytes], *, flag_bits: int = 0) -> bytes:
    return zip_pairs(entries.items(), flag_bits=flag_bits)


def rewrite_zip(
    data: bytes,
    replace: Mapping[str, bytes] | None = None,
    add: Mapping[str, bytes] | None = None,
    drop: Iterable[str] = (),
    *,
    extra_pairs: Iterable[tuple[str, bytes]] = (),
    flag_bits: int = 0,
    fake_sizes: Mapping[str, int] | None = None,
) -> bytes:
    replace, dropped = replace or {}, set(drop)
    with zipfile.ZipFile(BytesIO(data)) as zf:
        pairs = [
            (i.filename, replace.get(i.filename, zf.read(i)))
            for i in zf.infolist()
            if i.filename not in dropped
        ]
    pairs += list((add or {}).items()) + list(extra_pairs)
    return zip_pairs(pairs, flag_bits=flag_bits, fake_sizes=fake_sizes)
