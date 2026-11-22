# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import dataclasses

import pytest

from app.ingest.errors import DEFAULT_LIMITS, IntakeRejected


def test_message_is_reason_only() -> None:
    assert str(IntakeRejected("macro")) == "intake rejected: macro"
    assert IntakeRejected("macro").reason == "macro"


def test_limits_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_LIMITS.max_file_bytes = 1  # type: ignore[misc]  # pyright: ignore[reportAttributeAccessIssue]


def test_default_ratio_is_milestone_value() -> None:
    assert DEFAULT_LIMITS.zip_max_ratio == 100
