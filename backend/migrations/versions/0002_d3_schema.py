# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""D3 schema (relationship-model rev 2.1), roles and database-enforced rules.

Revision ID: 0002
Revises: 0001

Not downgradable (owner question S5-Q9, decided by the team): the tracer tables it drops held
disposable fixtures only, and a downgrade would destroy append-only evidence.
"""
# ruff: noqa: E501

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = (
    "actor",
    "catalogue_entity_type",
    "catalogue_relationship_type",
    "snapshot",
    "document",
    "document_version",
    "evidence_locator",
    "entity",
    "entity_version",
    "relationship",
    "claim",
    "review_event",
    "unresolved_reference",
)


# Raw string: the DDL contains backslashes (regex classes).
TABLES_DDL = r"""
CREATE TABLE actor (
  id bigint PRIMARY KEY,
  kind text NOT NULL CONSTRAINT ck_actor_kind CHECK (kind IN ('human','service')),
  display_name text NOT NULL CONSTRAINT ck_actor_name CHECK (display_name ~ '\S'),
  roles text[] NOT NULL
);
CREATE TABLE catalogue_entity_type (
  product_profile text NOT NULL CONSTRAINT ck_cet_profile CHECK (product_profile IN ('synthetic','ukg_pro_wfm','workforce_central')),
  name text COLLATE "C" NOT NULL,
  snapshot_scoped boolean NOT NULL,
  display_only_attributes text[] NOT NULL,
  PRIMARY KEY (product_profile, name)
);
CREATE TABLE catalogue_relationship_type (
  product_profile text NOT NULL CONSTRAINT ck_crt_profile CHECK (product_profile IN ('synthetic','ukg_pro_wfm','workforce_central')),
  name text COLLATE "C" NOT NULL,
  qualifier_required boolean NOT NULL,
  single_valued_for jsonb NOT NULL,            -- [[source type, target type], ...] in catalogue order
  PRIMARY KEY (product_profile, name)
);
CREATE TABLE snapshot (
  id bigint PRIMARY KEY,
  product_profile text NOT NULL CONSTRAINT ck_snapshot_profile CHECK (product_profile IN ('synthetic','ukg_pro_wfm','workforce_central','unknown')),
  environment text NOT NULL, label text NOT NULL, captured_at timestamptz NOT NULL
);
CREATE TABLE document (
  id bigint PRIMARY KEY,
  product_profile text NOT NULL CONSTRAINT ck_document_profile CHECK (product_profile IN ('synthetic','ukg_pro_wfm','workforce_central','unknown')),
  title text NOT NULL
);
CREATE TABLE document_version (
  id bigint PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES document,
  sha256 text NOT NULL UNIQUE CONSTRAINT ck_dv_sha256 CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  snapshot_id bigint REFERENCES snapshot,
  supersedes_version_id bigint UNIQUE REFERENCES document_version
    CONSTRAINT ck_dv_not_self CHECK (supersedes_version_id <> id),
  declared_by bigint NOT NULL REFERENCES actor,
  uploaded_at timestamptz NOT NULL
);
CREATE TABLE evidence_locator (
  id bigint PRIMARY KEY,
  document_version_id bigint NOT NULL REFERENCES document_version,
  kind text NOT NULL CONSTRAINT ck_locator_kind CHECK (kind IN ('xlsx_cell','pdf_word_bbox')),
  locator jsonb NOT NULL,                       -- kind-specific fields only (sheet, cell | page, x0..)
  snippet text NOT NULL,
  extractor text NOT NULL CONSTRAINT ck_locator_extractor CHECK (extractor ~ '^[^@\s]+@[^@\s]+$'),
  extracted_at timestamptz NOT NULL,
  CONSTRAINT uq_locator_content UNIQUE (document_version_id, kind, extractor, locator)  -- = domain content_key
);
CREATE TABLE entity (
  id bigint PRIMARY KEY,
  product_profile text NOT NULL CONSTRAINT ck_entity_product_profile CHECK (product_profile IN ('synthetic','ukg_pro_wfm','workforce_central','unknown')),
  entity_type text COLLATE "C" NOT NULL,
  natural_key text COLLATE "C" NOT NULL,
  -- unknown-profile entities have no catalogue (decision 0003 Q7): NULL skips the FK
  catalogue_profile text GENERATED ALWAYS AS (NULLIF(product_profile, 'unknown')) STORED,
  CONSTRAINT uq_entity_key UNIQUE (product_profile, entity_type, natural_key),
  FOREIGN KEY (catalogue_profile, entity_type) REFERENCES catalogue_entity_type (product_profile, name)
);
CREATE TABLE entity_version (
  id bigint PRIMARY KEY,
  entity_id bigint NOT NULL REFERENCES entity,
  document_version_id bigint NOT NULL REFERENCES document_version,
  snapshot_id bigint REFERENCES snapshot,
  attributes jsonb NOT NULL,                    -- [{"name","value","locator_id"}]; numbers as {"n": "<decimal text>"}
  locator_ids bigint[] NOT NULL,
  CONSTRAINT uq_entity_version UNIQUE (entity_id, document_version_id)
);
CREATE TABLE relationship (
  id bigint PRIMARY KEY,
  type text COLLATE "C" NOT NULL,
  source_entity_id bigint NOT NULL REFERENCES entity,
  target_entity_id bigint NOT NULL REFERENCES entity,
  qualifier text,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_relationship_key UNIQUE NULLS NOT DISTINCT (type, source_entity_id, target_entity_id, qualifier),
  CONSTRAINT ck_relationship_no_self CHECK (source_entity_id <> target_entity_id)
);
CREATE TABLE claim (
  id bigint PRIMARY KEY,
  relationship_id bigint NOT NULL REFERENCES relationship,
  basis text NOT NULL CONSTRAINT ck_claim_basis
    CHECK (basis IN ('explicit_source','deterministic_rule','llm_suggestion')),
  polarity text NOT NULL CONSTRAINT ck_claim_polarity CHECK (polarity IN ('present','absent')),
  method text NOT NULL CONSTRAINT ck_claim_method CHECK (method ~ '^[^@\s]+@[^@\s]+$'),
  confidence numeric CONSTRAINT ck_claim_confidence_range CHECK (confidence BETWEEN 0 AND 1),
  model_id text, prompt_version text,
  scope_snapshot_id bigint REFERENCES snapshot,
  locator_ids bigint[] NOT NULL,                -- owner question S5-Q3 (pending): array instead of a ClaimEvidence table; sorted by trigger
  locator_set_hash text NOT NULL,               -- set by trigger (Task 9); client values ignored
  created_at timestamptz NOT NULL,
  CONSTRAINT ck_claim_confidence CHECK ((basis = 'explicit_source') = (confidence IS NULL)),
  CONSTRAINT ck_claim_llm CHECK (CASE WHEN basis = 'llm_suggestion'
    THEN model_id IS NOT NULL AND prompt_version IS NOT NULL
    ELSE model_id IS NULL AND prompt_version IS NULL END),
  CONSTRAINT uq_claim_dedup UNIQUE (relationship_id, basis, method, polarity, locator_set_hash)
);
CREATE TABLE review_event (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  target_kind text NOT NULL,
  claim_id bigint REFERENCES claim,
  relationship_id bigint REFERENCES relationship,
  scope_snapshot_id bigint REFERENCES snapshot,
  verdict text NOT NULL,
  reason text CONSTRAINT ck_review_reason CHECK (reason ~ '\S'),
  successor_relationship_id bigint REFERENCES relationship,
  actor_id bigint NOT NULL REFERENCES actor,
  at timestamptz NOT NULL DEFAULT now(),        -- ordering key (at, id); never client-set (Task 4)
  CONSTRAINT ck_review_event_shape CHECK (
    (target_kind = 'claim' AND claim_id IS NOT NULL AND relationship_id IS NULL
      AND scope_snapshot_id IS NULL AND successor_relationship_id IS NULL
      AND verdict IN ('rejected','reinstated') AND reason IS NOT NULL)
    OR
    (target_kind = 'relationship' AND relationship_id IS NOT NULL AND claim_id IS NULL
      AND verdict IN ('accepted','rejected','superseded')
      AND (verdict = 'accepted' OR reason IS NOT NULL)
      AND (verdict = 'superseded') = (successor_relationship_id IS NOT NULL)
      AND successor_relationship_id IS DISTINCT FROM relationship_id))
);
CREATE TABLE unresolved_reference (
  id bigint PRIMARY KEY,
  holder_entity_id bigint NOT NULL REFERENCES entity,
  raw_reference text NOT NULL CONSTRAINT ck_unresolved_raw CHECK (raw_reference ~ '\S'),
  locator_id bigint NOT NULL REFERENCES evidence_locator,
  reason text NOT NULL CONSTRAINT ck_unresolved_reason
    CHECK (reason IN ('missing_target','uncatalogued_type','unknown_profile'))
);
"""

# Owner question S5-Q8 (decided): the migration creates the NOLOGIN group roles; login members
# are created by scripts/dev.sh (dev) and by the test fixtures. No INSERT on `actor` or the
# catalogue for any app role, so an app role cannot mint a human reviewer.
ROLES_DDL = """
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wb_ingest') THEN CREATE ROLE wb_ingest NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'wb_review') THEN CREATE ROLE wb_review NOLOGIN; END IF;
END $$;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO wb_ingest, wb_review;
GRANT INSERT ON snapshot, document, document_version, evidence_locator, entity, entity_version,
  relationship, claim, unresolved_reference TO wb_ingest;
-- no id, no at: the database alone assigns identity and time (ordering cannot be forged)
GRANT INSERT (target_kind, claim_id, relationship_id, scope_snapshot_id, verdict, reason,
  successor_relationship_id, actor_id) ON review_event TO wb_review;
"""

# owner question S5-Q4 (pending): every table is append-only, including the whole actor row and
# the catalogue. Stricter than RM BC 30a (which freezes only actor kind and roles).
APPEND_ONLY_FN = """
CREATE FUNCTION public.wb_forbid_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'append-only: % cannot be updated or deleted', TG_TABLE_NAME USING ERRCODE = 'WB001';
END $$;
"""
# Statement-level: it fires even when no row matches. TRUNCATE is deliberately not covered:
# only the owner holds it, and the app roles never do.
APPEND_ONLY_TRIGGER = """
CREATE TRIGGER wb_append_only BEFORE UPDATE OR DELETE ON public.{t}
  FOR EACH STATEMENT EXECUTE FUNCTION public.wb_forbid_change();
"""

# Constraint triggers (the approved slice wording: "constraint trigger plus role privileges").
# NOT DEFERRABLE: a session cannot postpone the check with SET CONSTRAINTS. Actor rows are
# immutable (append-only), so the check cannot be raced by changing the actor afterwards.
# Trigger functions run with the caller's privileges: both app roles have SELECT on everything
# they read, so no SECURITY DEFINER is needed. Every name is schema-qualified. Messages are fixed
# strings and never contain values.
RULES_DDL = """
CREATE FUNCTION public.wb_is_human_reviewer(actor bigint) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT EXISTS (SELECT 1 FROM public.actor a
                 WHERE a.id = actor AND a.kind = 'human' AND 'reviewer' = ANY (a.roles)) $$;

CREATE FUNCTION public.wb_is_scoped(source_id bigint, target_id bigint) RETURNS boolean
LANGUAGE sql STABLE AS $$
  -- no catalogue row (unknown profile) counts as scoped (decision 0003 Q7)
  SELECT bool_and(coalesce(t.snapshot_scoped, true))
  FROM public.entity e
  LEFT JOIN public.catalogue_entity_type t ON t.product_profile = e.product_profile AND t.name = e.entity_type
  WHERE e.id IN (source_id, target_id) $$;

CREATE FUNCTION public.wb_review_event_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rel public.relationship%ROWTYPE; profile text;
BEGIN
  IF NOT public.wb_is_human_reviewer(NEW.actor_id) THEN
    RAISE EXCEPTION 'review: actor is not a human reviewer' USING ERRCODE = 'WB002';
  END IF;
  IF NEW.target_kind = 'claim' THEN RETURN NULL; END IF;
  SELECT * INTO rel FROM public.relationship WHERE id = NEW.relationship_id;
  SELECT coalesce(max(NULLIF(e.product_profile, 'unknown')), 'unknown') INTO profile
    FROM public.entity e WHERE e.id IN (rel.source_entity_id, rel.target_entity_id);
  IF public.wb_is_scoped(rel.source_entity_id, rel.target_entity_id) THEN
    IF NOT EXISTS (SELECT 1 FROM public.snapshot s
                   WHERE s.id = NEW.scope_snapshot_id AND s.product_profile = profile) THEN
      RAISE EXCEPTION 'review: scope must name a snapshot of the profile' USING ERRCODE = 'WB003';
    END IF;
  ELSIF NEW.scope_snapshot_id IS NOT NULL THEN
    RAISE EXCEPTION 'review: scope must be null for unscoped relationship' USING ERRCODE = 'WB003';
  END IF;
  IF NEW.successor_relationship_id IS NOT NULL THEN
    IF (SELECT source_entity_id FROM public.relationship WHERE id = NEW.successor_relationship_id)
       <> rel.source_entity_id THEN
      RAISE EXCEPTION 'review: successor must share the source entity' USING ERRCODE = 'WB003';
    END IF;
    -- owner question S5-Q5 (decided): checked per scope, over every superseded event.
    -- shortcut (S5-Q6, decided): no lock, so two concurrent supersessions could still close a
    -- cycle; add pg_advisory_xact_lock when M1's single reviewer becomes several.
    IF EXISTS (WITH RECURSIVE chain(id) AS (
                 SELECT NEW.successor_relationship_id
                 UNION
                 SELECT e.successor_relationship_id FROM public.review_event e
                 JOIN chain ON e.relationship_id = chain.id
                 WHERE e.verdict = 'superseded'
                   AND e.scope_snapshot_id IS NOT DISTINCT FROM NEW.scope_snapshot_id)
               SELECT 1 FROM chain WHERE chain.id = NEW.relationship_id) THEN
      RAISE EXCEPTION 'review: supersession cycle' USING ERRCODE = 'WB003';
    END IF;
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER wb_review_event_rules AFTER INSERT ON public.review_event
  NOT DEFERRABLE FOR EACH ROW EXECUTE FUNCTION public.wb_review_event_rules();

CREATE FUNCTION public.wb_document_version_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prev public.document_version%ROWTYPE;
BEGIN
  IF NEW.snapshot_id IS NOT NULL AND
     (SELECT product_profile FROM public.snapshot WHERE id = NEW.snapshot_id)
       <> (SELECT product_profile FROM public.document WHERE id = NEW.document_id) THEN
    RAISE EXCEPTION 'profiles: document version snapshot' USING ERRCODE = 'WB003';
  END IF;
  IF NEW.supersedes_version_id IS NULL THEN RETURN NULL; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.actor WHERE id = NEW.declared_by AND kind = 'human') THEN
    RAISE EXCEPTION 'lineage: declarer must be human' USING ERRCODE = 'WB002';
  END IF;
  SELECT * INTO prev FROM public.document_version WHERE id = NEW.supersedes_version_id;
  IF prev.document_id <> NEW.document_id OR prev.snapshot_id IS DISTINCT FROM NEW.snapshot_id THEN
    RAISE EXCEPTION 'lineage: document or snapshot differs' USING ERRCODE = 'WB003';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER wb_document_version_rules AFTER INSERT ON public.document_version
  NOT DEFERRABLE FOR EACH ROW EXECUTE FUNCTION public.wb_document_version_rules();

CREATE FUNCTION public.wb_relationship_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE s public.entity%ROWTYPE; t public.entity%ROWTYPE; profile text; spec public.catalogue_relationship_type%ROWTYPE;
BEGIN
  SELECT * INTO s FROM public.entity WHERE id = NEW.source_entity_id;
  SELECT * INTO t FROM public.entity WHERE id = NEW.target_entity_id;
  IF s.id IS NULL OR t.id IS NULL THEN RETURN NEW; END IF;  -- the foreign key reports it
  IF s.product_profile = 'unknown' AND t.product_profile = 'unknown' THEN
    RAISE EXCEPTION 'catalogue: relationship between unknown entities' USING ERRCODE = 'WB003';
  END IF;
  IF s.product_profile <> t.product_profile AND 'unknown' NOT IN (s.product_profile, t.product_profile) THEN
    RAISE EXCEPTION 'profiles: relationship endpoints' USING ERRCODE = 'WB003';
  END IF;
  profile := CASE WHEN s.product_profile = 'unknown' THEN t.product_profile ELSE s.product_profile END;
  SELECT * INTO spec FROM public.catalogue_relationship_type c WHERE c.product_profile = profile AND c.name = NEW.type;
  IF spec.name IS NULL THEN
    RAISE EXCEPTION 'catalogue: relationship type' USING ERRCODE = 'WB003';
  END IF;
  IF spec.qualifier_required <> (NEW.qualifier IS NOT NULL) THEN
    RAISE EXCEPTION 'catalogue: qualifier' USING ERRCODE = 'WB003';
  END IF;
  -- explicit COLLATE: plpgsql row variables may not carry the column collation
  IF NEW.type = 'same_as' AND (s.product_profile <> t.product_profile OR s.entity_type <> t.entity_type
     OR NOT (s.natural_key COLLATE "C" < t.natural_key COLLATE "C")) THEN
    RAISE EXCEPTION 'same_as: profile, type and key order' USING ERRCODE = 'WB003';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER wb_relationship_rules BEFORE INSERT ON public.relationship
  FOR EACH ROW EXECUTE FUNCTION public.wb_relationship_rules();
"""


def upgrade() -> None:
    for t in ("evidence_locator", "relationship", "entity"):
        op.drop_table(t)
    op.execute(TABLES_DDL)
    op.execute(ROLES_DDL)
    op.execute(APPEND_ONLY_FN)
    for t in TABLES:
        op.execute(APPEND_ONLY_TRIGGER.format(t=t))
    op.execute(RULES_DDL)


def downgrade() -> None:
    raise RuntimeError("0002 is irreversible: it would destroy append-only evidence")
