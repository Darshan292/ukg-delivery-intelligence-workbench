# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import pytest

from app.config import Settings


def test_settings_repr_hides_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+pg8000://u:hunter2@h/db")
    s = Settings()  # pyright: ignore[reportCallIssue]
    assert "hunter2" not in repr(s)
    assert "hunter2" not in str(s)
    assert s.database_url.get_secret_value().endswith("@h/db")
    assert s.log_level == "INFO"
