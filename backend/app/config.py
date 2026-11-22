# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Application settings (environment variables, no prefix)."""

from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # hide_input_in_errors: a rejected token must never appear in an error message
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    database_url: SecretStr
    log_level: str = "INFO"
    # owner question S5-Q2 (pending): Milestone 1 reviewer identity is a static bearer token
    # mapped to one configured human-reviewer actor, OFF by default. RM layer 2 says "authenticated
    # human session; no service tokens", so this needs the owner's approval (decision record 0005).
    reviewer_token: SecretStr | None = None
    reviewer_actor_id: int | None = None

    @field_validator("reviewer_token")
    @classmethod
    def _long_enough(cls, v: SecretStr | None) -> SecretStr | None:
        if v is not None and len(v.get_secret_value()) < 32:
            raise ValueError("reviewer_token must be at least 32 characters")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
