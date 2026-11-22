# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""The only XML parser the intake uses: defusedxml, DTDs and entities forbidden."""

from collections.abc import Callable, Mapping
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
    except (ParseError, LookupError, ValueError):  # LookupError: unknown encoding names echo input
        raise IntakeRejected("xml_malformed") from None


def scan_xml(
    data: bytes,
    *,
    max_elements: int,
    max_depth: int,
    on_start: Callable[[str, Mapping[str, str]], None] | None = None,
) -> None:
    """Stream-parse without keeping a tree; enforce element and depth caps.

    `on_start(local_tag, attributes)` sees every start element (used for cell and merge caps).
    """
    count = 0
    stack: list[Element] = []
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
                stack.append(el)
                if count > max_elements or len(stack) > max_depth:
                    raise IntakeRejected("xml_forbidden")
                if on_start:
                    on_start(el.tag.rsplit("}", 1)[-1], el.attrib)
                continue
            stack.pop()
            el.clear()
            if stack:
                stack[-1].remove(el)  # clear() alone leaves the empty element attached: O(n) memory
    except DefusedXmlException:
        raise IntakeRejected("xml_forbidden") from None
    except (ParseError, LookupError, ValueError):  # LookupError: unknown encoding names echo input
        raise IntakeRejected("xml_malformed") from None
