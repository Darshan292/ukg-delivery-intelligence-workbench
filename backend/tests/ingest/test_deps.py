# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors


def test_openpyxl_routes_xml_through_defusedxml() -> None:
    import openpyxl.xml

    assert openpyxl.xml.DEFUSEDXML is True


def _loaded_after_importing(module: str, names: tuple[str, ...]) -> list[str]:
    import json
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    code = (
        f"import sys; sys.path.insert(0, {str(root)!r}); import {module}; "
        f"print(__import__('json').dumps([m for m in sys.modules if m.split('.')[0] in {names!r}]))"
    )
    done = subprocess.run(  # noqa: S603  (fixed argv)
        [sys.executable, "-I", "-c", code], cwd="/", env={}, capture_output=True, check=True
    )
    return json.loads(done.stdout)


PDF_STACK = ("pdfplumber", "pdfminer", "pypdfium2", "pypdfium2_raw")


def test_pdf_stack_not_loaded_by_the_parent() -> None:
    heavy = (*PDF_STACK, "PIL", "openpyxl")
    for module in ("app.ingest.pdf", "app.ingest.xlsx", "app.ingest.intake"):
        assert _loaded_after_importing(module, heavy) == [], module


def test_child_does_not_load_imaging_or_rendering_for_an_image_pdf() -> None:
    from app.ingest.errors import Limits
    from app.ingest.sandbox import run_sandboxed
    from tests.ingest.pdf_probe import pdf_modules
    from tests.ingest.pdfs import build_pdf

    img = b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceGray "
    img += b"/BitsPerComponent 8 /Length 4 >>\nstream\n\x00\x40\x80\xff\nendstream"
    content = b"q 50 0 0 50 100 100 cm /Im1 Do Q BT /F1 12 Tf 72 700 Td (hi) Tj ET"
    data = build_pdf(
        {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: b"<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font "
            b"<< /F1 3 0 R >> /XObject << /Im1 6 0 R >> >> /Contents 5 0 R >>",
            5: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
            6: img,
        }
    )
    assert run_sandboxed(pdf_modules, data, Limits()) == {
        "PIL": False,
        "pypdfium2": False,
        "pypdfium2_raw": False,
    }


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


def test_pypdfium2_wheel_is_not_musl() -> None:
    import importlib.metadata as md
    import sys

    import pytest

    try:
        wheel = md.distribution("pypdfium2").read_text("WHEEL") or ""
    except md.PackageNotFoundError:
        pytest.skip("pypdfium2 not installed")
    want = {"linux": "manylinux", "darwin": "macosx", "win32": "win"}[sys.platform]
    tags = [ln for ln in wheel.splitlines() if ln.startswith("Tag:")]
    assert tags and all(want in t and "musllinux" not in t for t in tags), tags
