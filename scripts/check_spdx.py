# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Report source files missing the two-line SPDX header (stdlib only).

Usage: check_spdx.py [ROOT]   (exit 1 and list files when any are missing)
"""

import sys
from pathlib import Path

EXTS = {".py", ".ts", ".tsx", ".js", ".mjs", ".sh", ".sql"}
SKIP_DIRS = {"node_modules", ".venv", ".next", ".git"}
LINES = (
    "SPDX-License-Identifier: Apache-2.0",
    "SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors",
)


def _exempt(rel: Path) -> bool:
    if SKIP_DIRS & set(rel.parts):
        return True
    posix = rel.as_posix()
    # shortcut: *.d.ts all exempt (generated types), tighten if hand-written ones appear
    return "frontend/src/components/ui/" in posix or rel.name.endswith(".d.ts")


def missing_headers(root: Path) -> list[Path]:
    bad: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.suffix not in EXTS or not p.is_file() or _exempt(p.relative_to(root)):
            continue
        head = p.read_text(errors="replace").splitlines()[:5]
        if not all(any(s in line for line in head) for s in LINES):
            bad.append(p)
    return bad


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    bad = missing_headers(root)
    for p in bad:
        print(f"missing SPDX header: {p.relative_to(root)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
