# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Tests for scripts/license_gate.py."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import license_gate as lg  # noqa: E402


def pkg(lic: str, name: str = "p") -> dict[str, str]:
    return {"name": name, "version": "1", "license": lic}


def test_gpl_runtime_fails() -> None:
    assert lg.check([pkg("GPL-3.0-only")], dev=False)


def test_gpl_dev_fails() -> None:
    assert lg.check([pkg("GNU General Public License v3 (GPLv3)")], dev=True)


def test_agpl_dev_fails() -> None:
    assert lg.check([pkg("GNU Affero General Public License v3")], dev=True)


def test_lgpl_dev_passes() -> None:
    assert lg.check([pkg("GNU Lesser General Public License v3 (LGPLv3)")], dev=True) == []


def test_lgpl_runtime_fails() -> None:
    assert lg.check([pkg("LGPL-3.0-or-later")], dev=False)


@pytest.mark.parametrize("text", ["", "  ", "UNKNOWN", "SEE LICENSE IN LICENSE.txt", "Proprietary"])
def test_blank_or_unknown_fails(text: str) -> None:
    assert lg.classify(text) == "deny"


def test_or_allowed() -> None:
    assert lg.classify("MIT OR Apache-2.0") == "allow"


def test_or_with_gpl_alternative_allowed() -> None:
    assert lg.classify("GPL-3.0-only OR MIT") == "allow"


def test_and_with_gpl_denied() -> None:
    assert lg.classify("GPL-3.0-only AND MIT") == "deny"


def test_parenthesised_expression() -> None:
    assert lg.classify("(MIT OR GPL-2.0) AND BSD-3-Clause") == "allow"


def test_with_exception_judges_base() -> None:
    assert lg.classify("Apache-2.0 WITH LLVM-exception") == "allow"
    assert lg.classify("GPL-2.0-only WITH Classpath-exception-2.0") == "deny"


@pytest.mark.parametrize(
    "text",
    [
        "MIT License",
        "BSD License",
        "Apache Software License",
        "Mozilla Public License 2.0 (MPL 2.0)",
        "Python Software Foundation License",
        "BSD-3-Clause",
        "ISC",
        "0BSD",
        "Unlicense",
        "CC0-1.0",
        "Python-2.0",
        "Zlib",
    ],
)
def test_allowed_strings(text: str) -> None:
    assert lg.classify(text) == "allow"


@pytest.mark.parametrize(
    "text",
    ["SSPL-1.0", "Server Side Public License", "BUSL-1.1", "Business Source License 1.1", "CC-BY-NC-4.0", "Non-Commercial Use Only"],
)
def test_other_denied(text: str) -> None:
    assert lg.classify(text) == "deny"


def test_lgpl_classified_dev_only() -> None:
    assert lg.classify("LGPLv2.1") == "dev_only"


def test_gpl_not_confused_with_lgpl() -> None:
    assert lg.classify("GNU Lesser General Public License v3 (LGPLv3)") == "dev_only"
    assert lg.classify("GNU General Public License v3 (GPLv3)") == "deny"


def test_npm_array_form(tmp_path: Path) -> None:
    f = tmp_path / "npm.json"
    f.write_text(json.dumps({"a@1.0.0": {"licenses": ["MIT", "Apache-2.0"]}, "b@2.0.0": {"licenses": "ISC"}}))
    assert lg.load_npm(f) == [
        {"name": "a", "version": "1.0.0", "license": "MIT AND Apache-2.0"},
        {"name": "b", "version": "2.0.0", "license": "ISC"},
    ]


def test_npm_scoped_name(tmp_path: Path) -> None:
    f = tmp_path / "npm.json"
    f.write_text(json.dumps({"@x/y@3.0.0": {"licenses": "MIT"}}))
    assert lg.load_npm(f)[0]["name"] == "@x/y"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "license_gate.py"), *args], capture_output=True, text=True
    )


def test_cli_exit_codes(tmp_path: Path) -> None:
    f = tmp_path / "pip.json"
    f.write_text(json.dumps([{"Name": "bad", "Version": "1", "License": "GPL-3.0-only"}]))
    r = run_cli("--pip-json", str(f))
    assert r.returncode == 1
    assert "bad" in r.stdout + r.stderr

    f.write_text(json.dumps([{"Name": "ok", "Version": "1", "License": "LGPL-3.0-only"}]))
    assert run_cli("--pip-json", str(f)).returncode == 1
    assert run_cli("--pip-json", str(f), "--dev").returncode == 0


def test_cli_npm(tmp_path: Path) -> None:
    f = tmp_path / "npm.json"
    f.write_text(json.dumps({"x@1.0.0": {"licenses": "UNKNOWN"}}))
    assert run_cli("--npm-json", str(f)).returncode == 1


def test_wrapped_single_licence() -> None:
    assert lg.classify("(MIT)") == "allow"
    assert lg.classify("(GPL-3.0-only)") == "deny"
