# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Find a PostgreSQL ``pg_ctl`` for the pytest-postgresql test path.

pytest-postgresql defaults to /usr/lib/postgresql/14/bin/pg_ctl, which does not exist on
most machines, and CI runner images differ in version and PATH.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Literal

_VERSION_DIR = re.compile(r"^\d+(\.\d+)*$")


def find_pg_ctl(
    search_root: str = "/usr/lib/postgresql",
    on_path: str | None | Literal["auto"] = "auto",
) -> str | None:
    """Return a pg_ctl path: PATH first, then the highest numeric version under search_root."""
    found = shutil.which("pg_ctl") if on_path == "auto" else on_path
    if found:
        return found
    candidates: list[tuple[tuple[int, ...], str]] = []
    for exe in Path(search_root).glob("*/bin/pg_ctl"):
        version = exe.parent.parent.name
        if _VERSION_DIR.match(version) and os.access(exe, os.X_OK):
            candidates.append((tuple(int(part) for part in version.split(".")), str(exe)))
    return max(candidates)[1] if candidates else None
