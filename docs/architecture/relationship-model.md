# Proposed canonical relationship model

Status: **proposal rev 2, awaiting approval (D3); not implemented.** Items marked *Recommendation* are proposals for you to choose, not decisions.

## Changes from rev 1

- Review has **two targets**: claims (is this source still valid evidence?) and relationships (is the link true in this scope?). Rev 1 had relationship review only.
- `superseded_by_claim_id` is removed. A claim is superseded when its **document version** is replaced. That status is derived, not reviewed. `superseded` on a relationship now means only "a human corrected this edge", and it requires a successor.
- New: snapshot and environment scope. Relationships carry no scope; claims and verdicts do. Acceptance never carries over to another snapshot automatically.
- New: claim polarity (`present` / `absent`), a claim dedup key, deterministic conflict detection, and the derived state `unsupported`.
- New (added in coordinator review): **attribute-value conflicts** and which entity version a snapshot diff uses (section h).
- Entity identity uses stable keys, plus `same_as` as a reviewed relationship. Entities are never physically merged.
- The edge-tier rule is moved here. `impact-propagation.md` consumes it.

## Core model in one paragraph

An **Entity** is a stable identity (profile, type, key). An **EntityVersion** holds its attributes in one document version or snapshot, which is what snapshot diffs compare. A **Relationship** is a typed edge between two entities. A **Claim** is one way we came to know the edge: its basis, method, polarity, scope and immutable **EvidenceLocators**. A **ReviewEvent** is an append-only human verdict on either a claim or a relationship. Everything else (effective state, display labels, conflicts, edge tier) is **derived** by deterministic code and never stored.

---

## a. Claim-level review versus relationship-level adjudication

| Option | Who reviews what | Trade-off |
|---|---|---|
| A1. Relationship only (rev 1) | One verdict per edge | Simple. Cannot drop one stale source without judging the edge (see b) |
| A2. Claims only | The edge state is derived from claim verdicts | "This document says it correctly" is not the same as "this is true in prod". It cannot express "true although every document is stale" |
| A3. Both, with distinct meanings | Claim verdict = **evidence assessment** (`rejected` / `reinstated`). Relationship verdict = **adjudication in a scope** (`accepted` / `rejected` / `superseded`) | Two concepts for reviewers to learn, but each answers one question |

*Recommendation:* **A3, with no claim-level "accept".** Nothing would consume an accepted claim: the relationship verdict already records what the human vouches for. A claim-accept can be added later if reviewers ask for it.

**Effective state** is derived per relationship and scope (rules below). A relationship verdict always beats claim-derived state. Claim verdicts only change which evidence is live, and so the basis strength.

## b. Rejecting one stale source without losing the others

| Option | Trade-off |
|---|---|
| B1. Reject the **claim** (from A3), with a reason (for example "stale design v1") | Precise. The other claims stay live, and basis strength is recomputed |
| B2. Mark a whole **document version** as not authoritative | One action excludes many claims. Coarse, and adds a second review target |
| B3. Reject the relationship (rev 1) | Throws away valid support from the other sources |

*Recommendation:* **B1.** B2 is deferred: a bulk UI can write one claim event per claim. A claim rejection has no scope, because the claim is already bound to its document version. Rejecting the last live present claim of an unreviewed edge makes it `unsupported`, not `rejected`. "No live evidence" and "a human says it is false" stay distinct.

## c. Consistent supersession, and re-ingesting a new version

| Option | Trade-off |
|---|---|
| C1. **Claim** supersession is derived from document lineage. **Relationship** `superseded` is only a human correction verdict with a required successor | One meaning per level. No heuristic matching |
| C2. Keep `superseded_by_claim_id` (rev 1) | Needs old-to-new claim matching, which is a guess. A new version may simply drop a statement |
| C3. Auto-supersede relationships on re-ingest | Ingestion would change review state. That violates the human-only rule |

*Recommendation:* **C1.** A `Document` is a lineage; each upload is a `DocumentVersion` (sha256). An uploader declares "this version supersedes version X" explicitly. This is never guessed from file names, and it is recorded with the human actor. A claim is **superseded** if any of its locators sits in a version that has a successor.

**Re-ingesting a new version:**
1. Run extraction afresh on the new version. Claims are never copied forward.
2. Claims on the old version become superseded (derived). Their locators still resolve.
3. Recompute derived state. Show a **re-ingestion delta**: edges that gained support, lost all support, or became conflicted.
4. Human verdicts are untouched:
   - An accepted edge that lost all live support stays accepted and is flagged `SUPPORT LOST` for review.
   - A new claim that repeats a statement rejected on the old version starts unreviewed. It carries the hint "a matching claim on v1 was rejected: <reason>".

A correction ("A uses B is wrong; it is A uses C") is a relationship verdict `superseded`, with `successor_relationship_id` set to A→C and a reason.

## d. Snapshot and environment scope

A **Snapshot** is one configuration capture: profile, `environment` (dev, test, prod or a free label), a label and a capture time. Before/after and dev/prod comparisons are both just **pairs of snapshots**. A diff compares EntityVersions and edge presence between the two.

Entity types are catalogued as **snapshot-scoped** (configuration objects, mapping rows) or **unscoped** (requirements, tests, defects, documents). A relationship is *scoped* if both endpoints are snapshot-scoped.

| Option | Where scope lives | Trade-off |
|---|---|---|
| D1. On the Relationship (one row per snapshot) | Simple uniqueness | Claims from unscoped documents (design PDFs) must be copied into every snapshot or split onto an extra unscoped row. That fragments support and conflict detection |
| D2. On **Claim** (from its document version) **and on the relationship ReviewEvent**. Relationship rows are scope-free | One edge row. State is evaluated per snapshot | Effective state is a function of (relationship, snapshot), not a column |
| D3. Edges between EntityVersions | Precise per snapshot | Cross-snapshot edges (test verifies config) need duplication. Heaviest option |

*Recommendation:* **D2.**
- A claim's `scope_snapshot_id` is the snapshot of its locators' document versions. The constraint is at most one distinct snapshot per claim; null means unscoped.
- For a scoped relationship evaluated in snapshot S, the live claims are those scoped to S, plus unscoped claims.
- A verdict on a scoped relationship must name S. Verdicts on unscoped relationships have no scope.

**Carry-forward.** Options:
- (i) no carry;
- (ii) automatic carry when the evidence looks unchanged. This is a rule adjudicating, so it is rejected;
- (iii) no carry, plus a derived hint "accepted in snapshot S′", and a human **bulk re-accept** that writes one event per edge.

*Recommendation:* **(iii).** The hint never affects tiering. The burden is small: unreviewed explicit edges are already *established* (see the edge tier below), so only rule- or LLM-only edges need re-acceptance.

## e. Multiple claims on one relationship

- **Relationship key:** unique (`type`, `source_entity_id`, `target_entity_id`, `qualifier`). `qualifier` is null except for types that need it (`asserts_value` uses the attribute path). Use `NULLS NOT DISTINCT` (PostgreSQL 15 or later) or a non-null empty string.
- **Claim dedup key:** unique (`relationship_id`, `basis`, `method`, `polarity`, `locator_set_hash`). The hash is over the sorted locator ids. Re-running the same extractor on the same version is then idempotent.
- **Basis strength** = the strongest basis among **live present** claims in scope: explicit > rule > LLM.
- **Representative claim** for reports is the first after sorting by (basis rank, confidence descending, method, document sha256, locator). It is deterministic. Confidences are never summed or combined: corroboration arithmetic would be an invented number. Reports say "supported by n live claims from m documents".

## f. Conflicting claims

**Detection (deterministic, per scope).** Kinds:
- **Polarity:** the same relationship has live `present` and live `absent` claims. For example, one document says the link was removed.
- **Cardinality:** the catalogue marks a type as `single_valued` for a source and target type. One source then has more than one non-rejected, present edge of that type. Example: the workbook says A uses B, a later design document says A uses C.
- **Documentary-only:** a scoped edge in S is supported only by unscoped claims, while the source entity has an EntityVersion in S. In other words, the snapshot export does not state the edge. This is only meaningful where the export is complete for that entity. The M1 fixtures are complete by construction; for real profiles this is unverified.
- **Identity:** see g.

| Option | Representation | Trade-off |
|---|---|---|
| F1. **Derived conflict flags**, computed from claims, verdicts and the catalogue | No stored state, so nothing can go stale | Recomputed on every read (cheap at M1 scale; not measured) |
| F2. Stored conflict records with their own lifecycle | Can track "acknowledged" | A "resolve" button could hide a conflict while the evidence is unchanged |
| F3. A `contradicts` relationship between claims | Uniform with the graph | Overloads the graph with meta-edges |

*Recommendation:* **F1.** A conflict clears only when the evidence state changes: a claim is rejected or superseded, or a relationship is rejected. Accepting one side does not clear the conflict while the other side remains live and unreviewed.

**Surfacing.** Conflicts are shown on both edges, in the review queue, and on every impact path that uses a conflicted edge. **Effect on tiering:** an unreviewed conflicted edge is *possible*, never excluded, and both competing edges are traversed. For an **accepted** conflicted edge, the *recommendation* is that it stays *established* and is flagged. This is open question 3, not settled.

## g. Entity identity and `same_as`

- **Stable key:** (`product_profile`, `entity_type`, `natural_key`). Normalisation is deterministic and versioned. M1 trims whitespace only. Case and punctuation folding are not applied, because they would merge silently.
- The same key in two snapshots or environments is the same Entity. That is what lets diffs match. Which natural key is stable across real UKG environments is **unverified** and is decided per profile, with evidence.

| Option | Trade-off |
|---|---|
| G1. Physical merge | Destructive; loses per-source provenance. Rejected by the fixed constraints |
| G2. **`same_as` relationship** under the normal claim and review model. Clusters are computed at query time | Non-destructive and reversible. Traversal must handle clusters |
| G3. An alias column or table on Entity | Simple lookup, but aliases would need their own evidence and review, which duplicates G2 |

*Recommendation:* **G2.**
- `same_as` is symmetric. It is stored once, with source key < target key (check constraint), and only within one profile. A WFC-to-Pro WFM correspondence is a `maps_to`-style migration artefact with its own evidence, never `same_as`.
- **Accepted** `same_as` edges are combined with union-find into clusters. The representative is the smallest key. Traversal treats a cluster as one node, and edges stay on the original entities.
- An **unreviewed** `same_as` of any basis, even explicit, is a one-hop bridge that caps a path at *possible*. This is a deliberate exception to the explicit-is-established rule, because a wrong identity link corrupts everything downstream.
- A **rejected or superseded** `same_as` is not traversed.
- An **identity conflict**: accepted A~B and B~C, but rejected A~C. The conflict is flagged, the cluster is still formed (more inclusion is the safer error), and paths through it are capped at *possible*.

## h. Attribute values and attribute conflicts (added in coordinator review)

Relationship conflicts (f) do not cover two sources disagreeing on an **attribute value**: for example, the export says `threshold_hours = 40` and a design document in the same scope says 37.5. The snapshot diff compares attribute values, so it needs a deterministic rule for which value it uses.

| Option | Trade-off |
|---|---|
| H1. **Authoritative versions per snapshot.** Only EntityVersions from document versions *assigned to* snapshot S (`DocumentVersion.snapshot_id = S`, that is, the configuration export) define attribute values in S. Values from unscoped documents are documentary: shown as evidence, never diffed. Two authoritative versions in S that disagree on a semantic attribute raise an **attribute conflict** | Deterministic, and matches how configuration is captured. Needs the "assigned to snapshot" declaration (already in the schema) |
| H2. Latest upload wins | Silent resolution by upload order. Rejected |
| H3. A human picks the value | Correct, but one review per attribute is heavy, and adds a fourth review target |

*Recommendation:* **H1.**
- An attribute conflict is a derived flag, like f.
- The diff reports the attribute as **changed with conflict**, listing every value and its locator, and its propagation is capped at *possible*.
- A documentary value that disagrees with the snapshot's authoritative value is shown as a **documentation mismatch** under context, never silently ignored. This is a likely real-world signal: the design document says one thing, the build says another.
- Milestone 1 fixtures have exactly one authoritative export per snapshot. The mutation set adds one same-snapshot attribute conflict.

---

## Corrected schema

```
Actor(id, kind{human,service}, display_name NOT NULL, roles[])
Snapshot(id, product_profile, environment, label, captured_at)
Document(id, product_profile, title) 1──* DocumentVersion(id, document_id, sha256 UNIQUE,
        snapshot_id NULL→Snapshot, supersedes_version_id NULL UNIQUE→DocumentVersion,
        declared_by→Actor, uploaded_at)
EvidenceLocator(id, document_version_id, kind, locator jsonb, snippet, extractor@ver, extracted_at)
Entity(id, product_profile, entity_type, natural_key)  UNIQUE(profile,type,key)
EntityVersion(id, entity_id, document_version_id, snapshot_id NULL, attributes jsonb, locator_ids[])
        UNIQUE(entity_id, document_version_id)
Relationship(id, type, source_entity_id, target_entity_id, qualifier NULL, created_at)
        UNIQUE(type,source,target,qualifier)  CHECK(source≠target)
Claim(id, relationship_id, basis, polarity{present,absent}, method, confidence NULL,
        scope_snapshot_id NULL, locator_set_hash, created_at)  UNIQUE(dedup key, see e)
ClaimEvidence(claim_id, locator_id)  ≥1 per claim
ReviewEvent(id, target_kind{claim,relationship}, claim_id NULL, relationship_id NULL,
        scope_snapshot_id NULL, verdict, reason NULL, successor_relationship_id NULL,
        actor_id→Actor, at)
```

| Constraint | Enforced by |
|---|---|
| Claim, ClaimEvidence, EvidenceLocator, DocumentVersion and ReviewEvent are append-only | No UPDATE or DELETE privilege for any app role, plus a blocking trigger |
| Rule and LLM claims need `method` and `confidence`; explicit claims need extractor@version | CHECK |
| A claim's locators span at most one snapshot; `scope_snapshot_id` equals it | Trigger on ClaimEvidence |
| Exactly one review target; claim verdicts ∈ {rejected, reinstated} with null scope; relationship verdicts ∈ {accepted, rejected, superseded} | CHECK plus trigger |
| A scoped relationship's verdict names a snapshot of the same profile; an unscoped one has null scope | Trigger |
| `superseded` requires a successor ≠ self; every verdict except `accepted` requires a reason | CHECK |
| `same_as`: source key < target key, same profile | Trigger |
| Relationship and entity types exist in the profile's catalogue | FK to the catalogue |
| `supersedes_version_id` belongs to the same Document; `declared_by` is human | Trigger |

## Derived-state rules

For relationship R in scope S (S is ignored when R is unscoped):

1. **Live claims** = claims of R that are in scope (scoped to S, or unscoped), not superseded, and whose latest claim event is not `rejected`.
2. **Verdict V** = the latest relationship event for (R, S), ordered by `at` then `id`.
3. **Effective state:**
   - If V = rejected → `rejected`.
   - If V = superseded → `superseded`.
   - If V = accepted → `accepted`. Flag `SUPPORT LOST` if there are no live present claims.
   - With no verdict: if there are no live present claims → `unsupported`; otherwise `unreviewed`.
4. **Present in S** (used by the snapshot diff) means the effective state is `accepted` or `unreviewed`.
5. **Conflict flags:** see f and g.

| Display label (derived only) | When |
|---|---|
| CONFIRMED | accepted |
| OBSERVED | unreviewed, basis strength = explicit_source |
| INFERRED | unreviewed, basis strength ∈ {rule, LLM} |
| hidden, auditable | rejected, superseded, unsupported |

Badges: `CONFLICT`, `SUPPORT LOST`, `accepted in <snapshot>` (a hint only).

**Edge tier** (consumed by impact analysis):
- **Established:** the edge is accepted, or it is unreviewed with an explicit basis, has no conflict and is not `same_as`.
- **Possible:** any other unreviewed edge.
- **Excluded:** rejected, superseded or unsupported.

"Established" means documented or human-accepted. It does not mean verified against UKG runtime behaviour.

## "Only a named human decides": three layers

1. **Database:**
   - Every ReviewEvent insert, whatever its target or verdict, requires an actor with `kind = 'human'`, a non-null name and the `reviewer` role.
   - The ingestion role has no INSERT on `review_events`. No app role can UPDATE or DELETE it.
   - A lineage declaration (`supersedes_version_id`) requires a human `declared_by`, because it changes which evidence is live.
2. **API:** both review endpoints (claim and relationship) and the lineage declaration require an authenticated human session. No service tokens are accepted. The actor is taken from the session, never from the body. The scope is validated against the relationship's endpoints.
3. **Tests:** see below.

## Invariants to test

1. A service actor's insert of any ReviewEvent fails at the database, including claim rejection and `superseded`.
2. A claim with confidence 1.0 still leaves the relationship `unreviewed`.
3. Re-ingesting a new version never changes any verdict. An accepted edge that loses support shows `SUPPORT LOST`, still accepted.
4. Rejecting one of two claims keeps the edge present. Its basis strength drops if the stronger claim was rejected.
5. Rejecting the last live claim gives `unsupported`, not `rejected`.
6. Acceptance in snapshot S does not change the state in snapshot S′.
7. Every polarity, cardinality, documentary-only, identity and attribute conflict fixture is flagged on both sides, and none disappears without a claim or relationship verdict or a supersession.
8. An unreviewed explicit `same_as` yields *possible*. A rejected `same_as` is not traversed. No Entity row is ever deleted or rewritten.
9. Running the same extractor twice on the same version creates no duplicate claims.
10. Old-version locators still resolve to their snippets after supersession.
11. Derived state and conflicts are identical between the database and in-memory evaluation (differential check).

## Open questions (only you can decide)

1. **Engineer assertion** (basis `engineer_assertion`, with a written justification as evidence). Recommended: allow it, *possible* until a second human accepts it.
2. **Single reviewer** for Milestone 1. Recommended: yes, recorded. Revisit two-person review for payroll-affecting types with practitioners.
3. **Accepted conflicted edges** stay *established* (recommended) or drop to *possible* until the conflict clears.
4. **Bulk re-accept** across snapshots (recommended (iii) in d), or require edge-by-edge re-review.
5. Whether the Milestone 1 fixtures include explicit **`absent`** statements, so that polarity conflicts are exercised by the oracle (recommended: one mutation, not the base scenario).
6. Natural keys for real Pro WFM and WFC entities across environments. This needs evidence and is deferred until a real profile is in scope (after G-REAL).

## Builder-check resolutions (coordinator calls, open to your veto)

A fresh implementer read both documents as a builder and raised 45 questions. These are settled here as coordinator calls; the ones that change what gets built are in the open questions above.

| # | Topic | Call |
|---|---|---|
| 30a | **Security:** an actor's `kind` could be updated from service to human | `Actor.kind` and `roles` are **immutable** (blocking trigger). Granting the reviewer role creates a new actor row. Tests run as the application role, never the owner or migration role |
| 30c–e | Claim checks | `confidence` ∈ [0,1]. LLM claims require model id and prompt version. `absent` polarity is allowed for any basis |
| 17, 18 | Basis enum | Closed in Milestone 1: `explicit_source`, `deterministic_rule`, `llm_suggestion`. `engineer_assertion` stays open question 1, added only if approved |
| 14, 29 | Event ordering | Claim and relationship events are both ordered by (`at` DB default `now()`, then `id` bigint identity). `reinstated` after `rejected` makes a claim live again |
| 15 | Lineage across snapshots | `supersedes_version_id` requires the same Document **and** the same `snapshot_id` (both null, or equal). Dev and prod exports are different Documents, never versions of each other |
| 16, 19, 25 | What counts for conflicts | Cardinality and polarity count only edges whose effective state is `accepted` or `unreviewed`. An accepted edge whose only live claims are `absent` is accepted, flagged `SUPPORT LOST` and **also** `CONFLICT` (a human verdict against live contrary evidence). Rejecting the stale claim makes that edge `unsupported`, which clears a cardinality conflict |
| 20 | Documentary-only conflict | Checked for the stored source entity only, and only for `explicit_source` claims (rule and LLM edges are already *possible*) |
| 24, 39 | Dangling references and untyped links | Extraction writes **UnresolvedReference** rows (holder entity, raw reference text, locator, reason: `missing_target` or `uncatalogued_type`) instead of relationships. Impact analysis reports them as not modelled. They are evidence-backed, never silently dropped |
| 28 | Redundant scope columns | `EntityVersion.snapshot_id` must equal its DocumentVersion's (trigger) |
| 31 | Successor rules | The successor shares the source entity and profile, is not self, and supersession cannot form a cycle (trigger). If the successor is later rejected or superseded, the original stays superseded and is flagged `SUCCESSOR EXCLUDED` for review |
| 32 | Key ordering | Byte order (`COLLATE "C"`). `same_as` requires the same profile **and** entity type |
| 43 | PostgreSQL | Pin 16 (the `initdb` binaries here; `NULLS NOT DISTINCT` needs 15 or later) |
| 44 | Diff guard | A diff of two snapshots with different profiles is rejected |

Deferred: document-level "not authoritative" verdicts, claim-level accept, stored conflict records, bitemporal or effective-dated relationships (UKG effective dating is not modelled in Milestone 1).
