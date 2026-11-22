# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Fixed reason codes: the only text an intake rejection carries (never content or names)."""

from dataclasses import dataclass
from typing import Literal

Reason = Literal[
    "too_large",
    "profile_not_permitted",
    "already_ingested",
    "unsupported_type",
    "type_mismatch",
    "archive_malformed",
    "archive_too_many_entries",
    "archive_too_large",
    "archive_ratio",
    "archive_bad_entry_name",
    "archive_encrypted",
    "unsupported_part",
    "macro",
    "external_link",
    "embedded_object",
    "xml_forbidden",
    "xml_malformed",
    "workbook_malformed",
    "sheet_too_large",
    "unsupported_cell",
    "pdf_too_many_pages",
    "pdf_too_many_objects",
    "pdf_timeout",
    "pdf_resource_limit",
    "pdf_malformed",
    "pdf_worker_failed",
    "package_inconsistent",
    "resource_limit",
    "records_invalid",
]


class IntakeRejected(ValueError):
    def __init__(self, reason: Reason) -> None:
        super().__init__(f"intake rejected: {reason}")
        self.reason: Reason = reason


_MIB = 1024 * 1024


# owner question S3-Q7 (decided): placeholder limits set by the team, not measured
@dataclass(frozen=True, slots=True)
class Limits:
    max_file_bytes: int = 10 * _MIB
    zip_max_entries: int = 1000
    zip_max_total_bytes: int = 50 * _MIB
    zip_max_ratio: int = 100
    sheet_max_cells: int = 100_000  # max_row x max_column grid
    workbook_max_cells: int = 100_000  # sum of sheet grids across the workbook
    max_merged_cells: int = 100_000  # sum of merge areas
    xml_tree_max_bytes: int = 2 * _MIB  # parts parsed into a tree (content types, rels, workbook)
    xml_max_elements: int = 5_000_000  # streamed scan of every other XML part
    xml_max_depth: int = 100
    worker_seconds: float = 30  # wall clock for the sandboxed child (also its CPU limit)
    worker_memory_bytes: int = 1024 * _MIB  # RLIMIT_AS for the sandboxed child
    worker_max_reply_bytes: int = 64 * _MIB  # JSON the child may send; placeholder, not measured
    pdf_max_pages: int = 500
    pdf_max_objects: int = 100_000
    pdf_page_seconds: float = 5
    pdf_total_seconds: float = 30
    pdf_memory_bytes: int = 1024 * _MIB


DEFAULT_LIMITS = Limits()
