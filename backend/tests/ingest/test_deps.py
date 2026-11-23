# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors


def test_openpyxl_routes_xml_through_defusedxml() -> None:
    import openpyxl.xml

    assert openpyxl.xml.DEFUSEDXML is True


def test_pdfplumber_importable_lazily() -> None:
    import subprocess
    import sys

    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    code = (
        f"import sys; sys.path.insert(0, {str(root)!r}); import app.ingest.pdf; "
        "assert 'pdfplumber' not in sys.modules"
    )
    done = subprocess.run(  # noqa: S603  (fixed argv)
        [sys.executable, "-I", "-c", code],
        cwd="/",
        env={},
        capture_output=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr.decode()[-300:]
