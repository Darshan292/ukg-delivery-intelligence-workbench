# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Robustness: whatever the bytes, only IntakeRejected (or a valid result) comes out."""

import contextlib
from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st
from openpyxl import Workbook

from app.domain.model import Actor, Snapshot
from app.domain.records import Records
from app.ingest.errors import IntakeRejected
from app.ingest.intake import ingest
from tests.ingest.hostile import workbook_bytes

NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
RECORDS = Records(
    actors=(Actor(id=1, kind="human", display_name="R", roles=frozenset({"reviewer"})),),
    snapshots=(
        Snapshot(id=1, product_profile="synthetic", environment="t", label="s", captured_at=NOW),
    ),
)


def _build(wb: Workbook) -> None:
    ws = wb.active
    assert ws is not None
    ws["A1"], ws["B1"] = "text", 40
    ws["A2"] = "=B1*2"


VALID = workbook_bytes(_build)


def _try(data: bytes) -> None:
    with contextlib.suppress(IntakeRejected):
        ingest(
            RECORDS,
            data,
            declared_kind="xlsx",
            product_profile="synthetic",
            title="t",
            uploaded_by=1,
            snapshot_id=1,
            now=NOW,
        )


@settings(max_examples=200, deadline=None)
@given(st.binary(max_size=4096))
def test_random_bytes_only_rejected(data: bytes) -> None:
    _try(data)


@settings(max_examples=200, deadline=None)
@given(st.integers(0, len(VALID) - 1), st.integers(1, 255))
def test_bitflipped_workbook_only_rejected_or_ok(pos: int, xor: int) -> None:
    flipped = bytearray(VALID)
    flipped[pos] ^= xor
    _try(bytes(flipped))
