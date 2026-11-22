# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""The only XML parser the intake uses: defusedxml, DTDs and entities forbidden."""

from xml.etree.ElementTree import Element  # noqa: S405  (type only; parsing is defusedxml)

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from app.ingest.errors import IntakeRejected


def parse_xml(data: bytes) -> Element:
    try:
        return fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except DefusedXmlException:
        raise IntakeRejected("xml_forbidden") from None
    except ParseError:
        raise IntakeRejected("xml_malformed") from None
