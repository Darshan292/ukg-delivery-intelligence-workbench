# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Numbers are Decimal parsed from source text, never float."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.derive import conflicts
from app.domain.model import Attribute, number_from_cell_text, number_from_cell_value
from tests.domain.builders import World


@pytest.mark.parametrize("t", ["40", " 40 ", "-1.5", "+2", "0.30", ".5", "1e3", "1.5E-2"])
def test_number_from_cell_text_accepts(t: str) -> None:
    assert number_from_cell_text(t) == Decimal(t.strip())


@pytest.mark.parametrize(
    "t", ["", "  ", "NaN", "Infinity", "-inf", "1,5", "0x10", "1 2", "--1", "e5", "1e"]
)
def test_number_from_cell_text_rejects(t: str) -> None:
    with pytest.raises(ValueError, match="number") as e:
        number_from_cell_text(t)
    assert t.strip() == "" or t not in str(e.value)


def test_text_and_float_cell_values_agree() -> None:
    assert number_from_cell_text("37.5") == number_from_cell_value(37.5) == Decimal("37.5")
    assert number_from_cell_value(40) == Decimal(40)


@pytest.mark.parametrize("v", [float("nan"), float("inf"), True])
def test_number_from_cell_value_rejects(v: float) -> None:
    with pytest.raises(ValueError, match="number"):
        number_from_cell_value(v)


def test_decimal_arithmetic_is_exact() -> None:
    assert Decimal("0.1") + Decimal("0.2") == number_from_cell_text("0.3")


def test_attribute_rejects_float_without_echoing_it() -> None:
    with pytest.raises(ValidationError) as e:
        Attribute(name="a", value=12345.678, locator_id=1)  # pyright: ignore[reportArgumentType]
    assert "12345.678" not in str(e.value)
    assert Attribute(name="a", value=Decimal("1.5"), locator_id=1)


def test_attribute_rejects_non_finite_decimal() -> None:
    with pytest.raises(ValidationError):
        Attribute(name="a", value=Decimal("NaN"), locator_id=1)


def kinds(w: World, v1: Decimal, v2: Decimal) -> list[str]:
    s1 = w.snapshot("s1")
    e1, e1b = w.export(s1), w.export(s1)
    x = w.entity("cfg", "X")
    w.version(x, e1, q=v1)
    w.version(x, e1b, q=v2)
    return [c.kind for c in conflicts(w.build(), s1.id)]


def test_no_attribute_conflict_between_text_and_float_cell_forms(world: World) -> None:
    assert kinds(world, number_from_cell_text("37.5"), number_from_cell_value(37.5)) == []


def test_40_and_40_point_0_are_equal(world: World) -> None:
    assert kinds(world, number_from_cell_text("40"), number_from_cell_text("40.0")) == []


def test_trailing_zero_decimals_are_equal(world: World) -> None:
    assert kinds(world, number_from_cell_text("0.30"), number_from_cell_text("0.3")) == []


def test_different_numbers_conflict(world: World) -> None:
    assert kinds(world, Decimal("40"), Decimal("37.5")) == ["attribute"]


@pytest.mark.parametrize(
    ("value", "text"),
    [(0.1, "0.1"), (37.3, "37.3"), (1.1, "1.1")],  # none is exact in binary floating point
)
def test_number_from_cell_value_keeps_shortest_text(value: float, text: str) -> None:
    # Decimal(0.1) would be 0.1000000000000000055511151231257827...; the cell shows 0.1.
    assert number_from_cell_value(value) == Decimal(text)
    assert str(number_from_cell_value(value)) == text
