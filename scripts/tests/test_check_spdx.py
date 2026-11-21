# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Tests for scripts/check_spdx.py."""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import check_spdx  # noqa: E402

HEADER = (
    "# SPDX-License-Identifier: Apache-2.0\n"
    "# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors\n"
)


def put(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_missing_header_reported(tmp_path: Path) -> None:
    put(tmp_path, "a.py", "print(1)\n")
    assert check_spdx.missing_headers(tmp_path) == [tmp_path / "a.py"]


def test_header_present_passes(tmp_path: Path) -> None:
    put(tmp_path, "a.py", HEADER + "print(1)\n")
    put(tmp_path, "b.ts", "// SPDX-License-Identifier: Apache-2.0\n// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors\n")
    assert check_spdx.missing_headers(tmp_path) == []


def test_only_one_line_is_missing(tmp_path: Path) -> None:
    put(tmp_path, "a.py", "# SPDX-License-Identifier: Apache-2.0\nprint(1)\n")
    assert check_spdx.missing_headers(tmp_path) == [tmp_path / "a.py"]


def test_exempt_paths_ignored(tmp_path: Path) -> None:
    for rel in [
        "node_modules/x/i.js",
        "frontend/node_modules/x/i.js",
        ".venv/lib/x.py",
        "frontend/.next/a.js",
        ".git/hooks/h.sh",
        "frontend/src/components/ui/button.tsx",
        "frontend/next-env.d.ts",
        "frontend/gen/types.d.ts",
    ]:
        put(tmp_path, rel, "x\n")
    assert check_spdx.missing_headers(tmp_path) == []


def test_other_extensions_ignored(tmp_path: Path) -> None:
    put(tmp_path, "README.md", "x\n")
    put(tmp_path, "data.json", "{}\n")
    assert check_spdx.missing_headers(tmp_path) == []


def test_shebang_header_on_lines_2_3(tmp_path: Path) -> None:
    put(tmp_path, "run.sh", "#!/usr/bin/env bash\n" + HEADER + "echo hi\n")
    assert check_spdx.missing_headers(tmp_path) == []


def test_header_after_line_5_fails(tmp_path: Path) -> None:
    put(tmp_path, "a.py", "\n\n\n\n\n" + HEADER)
    assert check_spdx.missing_headers(tmp_path) == [tmp_path / "a.py"]


def test_cli_exit_code(tmp_path: Path) -> None:
    put(tmp_path, "a.py", "print(1)\n")
    cmd = [sys.executable, str(SCRIPTS / "check_spdx.py"), str(tmp_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 1
    assert "a.py" in r.stdout
    put(tmp_path, "a.py", HEADER)
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 0


def test_css_and_other_script_extensions_are_checked(tmp_path: Path) -> None:
    names = {"a.css", "b.cjs", "c.jsx", "d.mts", "e.cts"}
    for name in names:
        (tmp_path / name).write_text("body {}\n")
    assert {p.name for p in check_spdx.missing_headers(tmp_path)} == names
