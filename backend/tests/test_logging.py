# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import json
import logging

from hypothesis import given
from hypothesis import strategies as st

from app.logging_config import JsonFormatter


def _record(msg: str) -> logging.LogRecord:
    return logging.LogRecord("t", logging.INFO, __file__, 1, "%s", (msg,), None)


@given(st.text())
def test_json_formatter_valid_json(msg: str) -> None:
    out = json.loads(JsonFormatter().format(_record(msg)))
    assert out["message"] == msg
    assert out["level"] == "INFO"
    assert {"ts", "logger"} <= out.keys()


def test_json_formatter_includes_exc() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        rec = logging.LogRecord("t", logging.ERROR, __file__, 1, "x", (), sys.exc_info())
    assert "ValueError" in json.loads(JsonFormatter().format(rec))["exc"]
