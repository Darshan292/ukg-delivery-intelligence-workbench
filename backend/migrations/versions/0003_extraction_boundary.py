# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""extraction_boundary: what extraction could not model, stated rather than dropped (Slice 4).

Revision ID: 0003
Revises: 0002

Not downgradable, as 0002: a downgrade would destroy append-only evidence.
"""
# ruff: noqa: E501

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = ("extraction_boundary",)

REASONS = (
    "unknown_sheet", "ambiguous_sheet", "unrecognised_column", "missing_key", "duplicate_key",
    "duplicate_value", "ambiguous_target", "self_reference", "missing_qualifier",
    "no_cached_value", "error_value", "unsupported_value", "invalid_profile",
    "unknown_profile_entity", "hidden_cell",
)  # fmt: skip

DDL = """
CREATE TABLE extraction_boundary (
  id bigint PRIMARY KEY CONSTRAINT ck_extraction_boundary_id CHECK (id > 0),
  document_version_id bigint NOT NULL REFERENCES document_version,
  reason text NOT NULL CONSTRAINT ck_boundary_reason CHECK (reason IN (__REASONS__)),
  locator_ids bigint[] NOT NULL CONSTRAINT ck_boundary_locators CHECK (cardinality(locator_ids) > 0),
  CONSTRAINT uq_extraction_boundary UNIQUE (document_version_id, reason, locator_ids)
);

-- every cited locator exists, once, in the boundary's own version (the domain's _boundaries
-- check); the array is stored sorted so the unique constraint equals the domain's SortedIds
CREATE FUNCTION public.wb_extraction_boundary_rules() RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE n bigint;
BEGIN
  SELECT count(*) INTO n FROM public.evidence_locator l
   WHERE l.id = ANY (NEW.locator_ids) AND l.document_version_id = NEW.document_version_id;
  IF cardinality(NEW.locator_ids) = 0 OR n <> cardinality(NEW.locator_ids) THEN
    RAISE EXCEPTION 'boundary: locator missing, repeated or in another version' USING ERRCODE = 'WB003';
  END IF;
  NEW.locator_ids := ARRAY(SELECT x FROM unnest(NEW.locator_ids) AS x ORDER BY x);
  RETURN NEW;
END $$;
CREATE TRIGGER wb_extraction_boundary_rules BEFORE INSERT ON public.extraction_boundary
  FOR EACH ROW EXECUTE FUNCTION public.wb_extraction_boundary_rules();

CREATE TRIGGER wb_append_only BEFORE UPDATE OR DELETE ON public.extraction_boundary
  FOR EACH STATEMENT EXECUTE FUNCTION public.wb_forbid_change();

GRANT SELECT ON extraction_boundary TO wb_ingest, wb_review;
GRANT INSERT ON extraction_boundary TO wb_ingest;
"""


def upgrade() -> None:
    op.execute(DDL.replace("__REASONS__", ", ".join(f"'{r}'" for r in REASONS)))


def downgrade() -> None:
    raise RuntimeError("0003 is irreversible: it would destroy append-only evidence")
