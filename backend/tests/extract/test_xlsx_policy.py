# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Pending owner questions stay isolated in single functions (S4-P3, S4-P5). FICTIONAL."""

import importlib.util
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest
from openpyxl import Workbook

from app.domain.model import BoundaryReason
from app.extract import xlsx
from tests.extract.helpers import attrs, bounds, put, run


def hidden_row(wb: Workbook) -> None:
    ws = put(wb, "Limits", [["limit_id", "hours"], ["L-1", 40], ["L-2", 41]])
    ws.row_dimensions[3].hidden = True


def test_hidden_extracted_by_default() -> None:
    _, x = run(hidden_row)
    assert attrs(x, "L-2") == {"hours": Decimal("41")}


def test_hidden_policy_boundary_is_stated_not_blanked(monkeypatch: pytest.MonkeyPatch) -> None:
    def stated(row: bool, col: bool, state: str) -> str:
        return "boundary"

    monkeypatch.setattr(xlsx, "_hidden_policy", stated)
    _, x = run(hidden_row)
    assert bounds(x) == {("hidden_cell", ("Limits!A3", "Limits!B3"))}
    assert {e.natural_key for e in x.records.entities} == {"L-1"}


def test_no_cached_decision_lives_in_one_function() -> None:
    assert xlsx._cell_kind("=1", "empty", None) == "no_cached"  # pyright: ignore[reportPrivateUsage]
    src = Path(xlsx.__file__).read_text()
    load = src[src.index("def _load(") : src.index("# ---- the run")]
    assert "no_cached" not in load


def test_migration_reason_list_equals_the_domain_literal() -> None:
    path = Path(__file__).resolve().parents[2] / "migrations/versions/0003_extraction_boundary.py"
    spec = importlib.util.spec_from_file_location("mig0003", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert set(mod.REASONS) == set(get_args(BoundaryReason))
    assert len(mod.REASONS) == len(set(mod.REASONS))
