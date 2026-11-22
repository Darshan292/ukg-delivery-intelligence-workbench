# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""The only XML parser the intake uses: defusedxml, DTDs and entities forbidden."""

from io import BytesIO
from xml.etree.ElementTree import Element  # noqa: S405  (type only; parsing is defusedxml)

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring, iterparse

from app.ingest.errors import IntakeRejected


def parse_xml(data: bytes) -> Element:
    try:
        return fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except DefusedXmlException:
        raise IntakeRejected("xml_forbidden") from None
    except ParseError:
        raise IntakeRejected("xml_malformed") from None


def scan_xml(
    data: bytes, *, max_elements: int, max_depth: int, collect: tuple[str, str] | None = None
) -> list[str]:
    """Stream-parse without keeping a tree; enforce element and depth caps.

    Returns the `attr` values of elements whose local tag is `tag` when `collect=(tag, attr)`.
    """
    out: list[str] = []
    count = depth = 0
    try:
        for event, el in iterparse(
            BytesIO(data),
            events=("start", "end"),
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        ):
            if event == "start":
                count += 1
                depth += 1
                if count > max_elements or depth > max_depth:
                    raise IntakeRejected("xml_forbidden")
                continue
            depth -= 1
            if collect and el.tag.rsplit("}", 1)[-1] == collect[0]:
                out.append(el.get(collect[1], ""))
            el.clear()
    except DefusedXmlException:
        raise IntakeRejected("xml_forbidden") from None
    except ParseError:
        raise IntakeRejected("xml_malformed") from None
    return out
