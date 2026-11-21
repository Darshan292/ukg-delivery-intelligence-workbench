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


@pytest.mark.parametrize("text", ["LGPL-2.1 and GPL-3.0", "GPL-3.0 / LGPL-2.1", "LGPLv3, AGPLv3"])
def test_gpl_beside_lgpl_denied_even_dev(text: str) -> None:
    assert lg.check([pkg(text)], dev=True)


@pytest.mark.parametrize(
    "text",
    ["Apache-2.0 WITH Commons-Clause", "Apache License 2.0 with Commons Clause", "MPL-1.1"],
)
def test_restricted_variants_denied(text: str) -> None:
    assert lg.classify(text) == "deny"


def test_cli_empty_input_fails_closed(tmp_path: Path) -> None:
    f = tmp_path / "empty.json"
    f.write_text("[]")
    assert run_cli("--pip-json", str(f)).returncode == 1
    f.write_text("{}")
    assert run_cli("--npm-json", str(f)).returncode == 1


# --- licence exceptions (owner-approved, exact name + version range + licence) ---

EXC = """
[[exception]]
name = "@img/sharp-libvips-linux-x64"
versions = ">=1.3.4,<1.4.0"
licence = "LGPL-3.0-or-later"
reason = "optional native library"
approved_by = "owner"
date = 2026-11-21
"""


def exc(tmp_path: Path, text: str = EXC) -> list[lg.LicenceException]:
    f = tmp_path / "exc.toml"
    f.write_text(text)
    return lg.load_exceptions(f)


def lib(name: str = "@img/sharp-libvips-linux-x64", version: str = "1.3.4", lic: str = "LGPL-3.0-or-later") -> dict[str, str]:
    return {"name": name, "version": version, "license": lic}


def test_exception_allows_exact_match_at_runtime(tmp_path: Path) -> None:
    e = exc(tmp_path)
    assert lg.check([lib()], dev=False)  # still a violation without the exception
    assert lg.check([lib(), lib(version="1.3.9")], dev=False, exceptions=e) == []


@pytest.mark.parametrize(
    "p",
    [
        lib(name="@img/sharp-libvips-linux-x64-evil"),
        lib(name="@img/sharp-libvips-linux"),
        lib(version="1.4.0"),
        lib(version="1.3.3"),
        lib(version="1.3.4-beta"),
        lib(lic="GPL-3.0-only"),
        lib(lic="LGPL-3.0-or-later AND GPL-2.0"),
    ],
)
def test_exception_does_not_widen(tmp_path: Path, p: dict[str, str]) -> None:
    assert lg.check([p], dev=False, exceptions=exc(tmp_path))


@pytest.mark.parametrize(
    "bad",
    [
        EXC.replace('approved_by = "owner"', 'approved_by = "agent"'),
        EXC.replace('name = "@img/sharp-libvips-linux-x64"', 'name = "@img/sharp-libvips-*"'),
        EXC.replace('versions = ">=1.3.4,<1.4.0"', 'versions = "~1.3"'),
        EXC.replace('versions = ">=1.3.4,<1.4.0"', 'versions = ""'),
        EXC.replace('reason = "optional native library"\n', ""),
        EXC.replace("date = 2026-11-21", 'date = "yesterday"'),
        EXC + 'extra = "x"\n',
        "[[exception]]\n",
        "not toml [",
    ],
)
def test_malformed_exceptions_fail_closed(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        exc(tmp_path, bad)


def test_repo_exceptions_file_is_valid_and_exact() -> None:
    entries = lg.load_exceptions(lg.DEFAULT_EXCEPTIONS)
    names = {e.name for e in entries}
    assert "caniuse-lite" in names
    assert all("*" not in n for n in names)
    assert {n for n in names if n.startswith("@img/")} == {
        f"@img/sharp-libvips-{p}"
        for p in ["darwin-arm64", "darwin-x64", "linux-arm", "linux-arm64", "linux-ppc64", "linux-riscv64",
                  "linux-s390x", "linux-x64", "linuxmusl-arm64", "linuxmusl-x64"]
    }


def test_cli_uses_exceptions_file(tmp_path: Path) -> None:
    f = tmp_path / "npm.json"
    f.write_text(json.dumps({"@img/sharp-libvips-linux-x64@1.3.4": {"licenses": "LGPL-3.0-or-later"}}))
    (tmp_path / "exc.toml").write_text(EXC)
    assert run_cli("--npm-json", str(f), "--exceptions", str(tmp_path / "exc.toml")).returncode == 0
    (tmp_path / "none.toml").write_text("")
    assert run_cli("--npm-json", str(f), "--exceptions", str(tmp_path / "none.toml")).returncode == 1
    (tmp_path / "bad.toml").write_text("[[exception]]\n")
    assert run_cli("--npm-json", str(f), "--exceptions", str(tmp_path / "bad.toml")).returncode == 1
