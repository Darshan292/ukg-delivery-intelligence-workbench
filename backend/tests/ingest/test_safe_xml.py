# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import pytest

from app.ingest.errors import IntakeRejected
from app.ingest.safe_xml import parse_xml
from tests.ingest.hostile import MARKER

XXE = b'<!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/hostname">]><r>&e;</r>'


def _laughs() -> bytes:
    lol = b'<!ENTITY a "' + b"x" * 10 + b'">'
    b = b'<!ENTITY b "' + b"&a;" * 10 + b'">'
    c = b'<!ENTITY c "' + b"&b;" * 10 + b'">'
    return b"<!DOCTYPE r [" + lol + b + c + b"]><r>&c;</r>"


@pytest.mark.parametrize(
    "payload",
    [
        XXE,
        _laughs(),
        b"<!DOCTYPE r><r/>",
        b'<!DOCTYPE r SYSTEM "http://example.invalid/x.dtd"><r/>',
    ],
    ids=["xxe", "laughs", "plain_doctype", "external_dtd"],
)
def test_forbidden_rejected(payload: bytes) -> None:
    with pytest.raises(IntakeRejected) as ei:
        parse_xml(payload)
    assert ei.value.reason == "xml_forbidden"


def test_malformed_rejected() -> None:
    with pytest.raises(IntakeRejected) as ei:
        parse_xml(b"<r><x></r>")
    assert ei.value.reason == "xml_malformed"


def test_wellformed_parses() -> None:
    assert parse_xml(b'<r a="1"/>').get("a") == "1"


@pytest.mark.parametrize("tail", [b"<r><x></r>", XXE.replace(b"&e;", MARKER.encode())])
def test_reason_has_no_content(tail: bytes) -> None:
    payload = tail.replace(b"<x>", b"<" + MARKER.encode() + b">")
    with pytest.raises(IntakeRejected) as ei:
        parse_xml(payload)
    exc = ei.value
    assert MARKER not in str(exc) and MARKER not in repr(exc)
    assert exc.__cause__ is None and exc.__suppress_context__
