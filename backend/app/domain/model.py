# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Typed records of the canonical relationship model (rev 2.1). Pure, in-memory, no I/O."""

from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


Id = Annotated[int, Field(ge=1)]
ProductProfile = Literal["synthetic", "ukg_pro_wfm", "workforce_central", "unknown"]
Basis = Literal["explicit_source", "deterministic_rule", "llm_suggestion"]
BASIS_RANK: Final[dict[Basis, int]] = {
    "explicit_source": 3,
    "deterministic_rule": 2,
    "llm_suggestion": 1,
}
Polarity = Literal["present", "absent"]
NonBlank = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Versioned = Annotated[str, StringConstraints(pattern=r"^[^@\s]+@[^@\s]+$")]  # name@version
SAME_AS: Final = "same_as"
KEY_NORMALISATION: Final = "v1"


def normalise_key_v1(raw: str) -> str:
    """Trim whitespace only (RM g): no case or punctuation folding.

    Strings compare with Python `<`; code-point order equals UTF-8 byte order, which is the
    byte order the docs require.
    """
    return raw.strip()
