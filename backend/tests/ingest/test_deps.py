# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors


def test_openpyxl_routes_xml_through_defusedxml() -> None:
    import openpyxl.xml

    assert openpyxl.xml.DEFUSEDXML is True
