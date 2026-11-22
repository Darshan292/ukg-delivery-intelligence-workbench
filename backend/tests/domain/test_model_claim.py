# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.model import Claim

T = datetime(2026, 1, 1, tzinfo=UTC)


def claim(**kw: Any) -> Claim:
    d: dict[str, Any] = {
        "id": 1,
        "relationship_id": 1,
        "basis": "explicit_source",
        "polarity": "present",
        "method": "xlsx-ref@1",
        "scope_snapshot_id": None,
        "locator_ids": (1,),
        "created_at": T,
    }
    return Claim(**{**d, **kw})


RULE: dict[str, Any] = {"basis": "deterministic_rule", "confidence": Decimal("0.5")}
LLM: dict[str, Any] = {
    "basis": "llm_suggestion",
    "confidence": Decimal("0.5"),
    "model_id": "m",
    "prompt_version": "p1",
}


def test_rule_claim_requires_confidence() -> None:
    assert claim(**RULE)
    with pytest.raises(ValidationError):
        claim(basis="deterministic_rule")


def test_llm_claim_requires_confidence_model_and_prompt() -> None:
    assert claim(**LLM)
    for drop in ("confidence", "model_id", "prompt_version"):
        with pytest.raises(ValidationError):
            claim(**{k: v for k, v in LLM.items() if k != drop})


def test_explicit_claim_rejects_confidence() -> None:
    with pytest.raises(ValidationError):
        claim(confidence=Decimal("1"))


def test_non_llm_claim_rejects_model_fields() -> None:
    for extra in ({"model_id": "m"}, {"prompt_version": "p"}):
        with pytest.raises(ValidationError):
            claim(**RULE, **extra)
        with pytest.raises(ValidationError):
            claim(**extra)


@pytest.mark.parametrize("c", [Decimal("0"), Decimal("1"), Decimal("0.85")])
def test_confidence_accepts(c: Decimal) -> None:
    assert claim(**{**RULE, "confidence": c}).confidence == c


@pytest.mark.parametrize("c", [Decimal("-0.01"), Decimal("1.01"), Decimal("NaN"), 0.5])
def test_confidence_rejects(c: object) -> None:
    with pytest.raises(ValidationError):
        claim(**{**RULE, "confidence": c})


def test_confidence_serialises_as_decimal_string() -> None:
    c = claim(**{**RULE, "confidence": Decimal("0.85")})
    assert c.model_dump(mode="json")["confidence"] == "0.85"


def test_claim_needs_a_locator() -> None:
    with pytest.raises(ValidationError):
        claim(locator_ids=())


@pytest.mark.parametrize("extra", [{}, RULE, LLM])
def test_absent_polarity_allowed_for_every_basis(extra: dict[str, Any]) -> None:
    assert claim(polarity="absent", **extra).polarity == "absent"


def test_method_must_be_versioned() -> None:
    with pytest.raises(ValidationError):
        claim(method="xlsx-ref")


def test_dedup_key_ignores_locator_order() -> None:
    assert claim(locator_ids=(2, 1)).dedup_key == claim(locator_ids=(1, 2)).dedup_key
    assert claim(polarity="absent").dedup_key != claim().dedup_key
