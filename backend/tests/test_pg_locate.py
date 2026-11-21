# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Locating pg_ctl for the pytest-postgresql path (runners differ in version and PATH)."""

from pathlib import Path

import pytest

from tests.pg_locate import find_pg_ctl


def _make(root: Path, version: str) -> Path:
    exe = root / version / "bin" / "pg_ctl"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\n")
    exe.chmod(0o755)
    return exe


def test_prefers_highest_numeric_version(tmp_path: Path) -> None:
    _make(tmp_path, "9.6")
    _make(tmp_path, "16")
    newest = _make(tmp_path, "18")
    assert find_pg_ctl(search_root=str(tmp_path), on_path=None) == str(newest)


def test_path_entry_wins_over_versioned_install(tmp_path: Path) -> None:
    _make(tmp_path, "16")
    assert (
        find_pg_ctl(search_root=str(tmp_path), on_path="/opt/custom/pg_ctl") == "/opt/custom/pg_ctl"
    )


def test_none_when_nothing_installed(tmp_path: Path) -> None:
    assert find_pg_ctl(search_root=str(tmp_path), on_path=None) is None


@pytest.mark.parametrize("junk", ["latest", "16-beta", "x"])
def test_ignores_non_numeric_directories(tmp_path: Path, junk: str) -> None:
    _make(tmp_path, junk)
    assert find_pg_ctl(search_root=str(tmp_path), on_path=None) is None
