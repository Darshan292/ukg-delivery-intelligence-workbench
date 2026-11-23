# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from app.domain.model import Catalogue, EntityTypeSpec, RelationshipTypeSpec
from app.extract.catalogue import AttributeColumn, ReferenceColumn, SheetCatalogue, SheetSpec

DOMAIN = Catalogue(
    product_profile="synthetic",
    entity_types=(
        EntityTypeSpec(name="limit", snapshot_scoped=True, display_only_attributes=("label",)),
        EntityTypeSpec(name="bundle", snapshot_scoped=True),
        EntityTypeSpec(name="check", snapshot_scoped=False),
    ),
    relationship_types=(
        RelationshipTypeSpec(name="contains"),
        RelationshipTypeSpec(name="verifies"),
        RelationshipTypeSpec(name="asserts_value", qualifier_required=True),
    ),
)
SHEETS = SheetCatalogue(
    product_profile="synthetic",
    method="test_xlsx@1",
    notes_sheets=("About",),
    sheets=(
        SheetSpec(
            entity_type="limit",
            key_header="limit_id",
            required_headers=("hours",),
            attributes=(
                AttributeColumn(header="hours", name="hours"),
                AttributeColumn(header="label", name="label"),
            ),
        ),
        SheetSpec(
            entity_type="bundle",
            key_header="bundle_id",
            references=(
                ReferenceColumn(header="limit", relationship_type="contains", target_type="limit"),
            ),
        ),
        SheetSpec(
            entity_type="check",
            key_header="check_id",
            attributes=(AttributeColumn(header="expected", name="expected"),),
            references=(
                ReferenceColumn(
                    header="verifies", relationship_type="verifies", target_type="bundle"
                ),
                ReferenceColumn(
                    header="asserts",
                    relationship_type="asserts_value",
                    target_type="limit",
                    qualifier_header="asserts_attribute",
                ),
            ),
        ),
    ),
)
