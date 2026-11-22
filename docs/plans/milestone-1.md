# Milestone 1: synthetic evidence-to-impact slice (proposal, revision 2)

Status: approved 2026-11-20 (D6), not started (`docs/decisions-for-approval.md`). Each slice becomes its own superpowers `writing-plans` plan and is built test-first.

Revision 2 reconciles the plan with the research report (`docs/research/research-report.md`) and the UKG Developer Policy note: PyMuPDF removed, impact tiers renamed and extended, an independent oracle, messy fixtures and mutation tests, a two-snapshot diff, fictional labelling, hostile-input requirements, and a synthetic-only scope with a future approval gate.

## Goal

Prove the engine on synthetic data. Two configuration snapshots and supporting documents go in. What comes out is a deterministic, evidence-backed impact report with established, possible and not-modelled categories, coverage gaps, and every node and edge clickable back to its cell or page. Nothing beyond that.

## Data boundary: synthetic only

- Milestone 1 uses **synthetic data only**. No real customer artefacts, no UKG tenant connection, no UKG Data Interface, no LLM.
- **Future approval gate (G-REAL)** before any authorised, sanitised real artefact enters the system, all of:
  1. written customer consent and a DPA naming the purpose, retention and deletion terms;
  2. Legal clarification of the UKG Developer Policy's applicability to offline customer-supplied exports, and of the competitive-product clause (independent legal review, and where needed UKG's own interpretation);
  3. a sanitisation procedure (no person records, no PII, customer identifiers pseudonymised), checked by a second person;
  4. per-customer isolated storage with tested purge, including backups and derived data;
  5. no LLM processing of real artefacts until the provider is an authorised sub-processor (Developer Policy §5), and no model evaluation on real data without customer and UKG written consent (§4).

## Demo scenario: fictional

> **FICTIONAL ASSUMPTION.** "Harborline Logistics", its objects (`OT-WEEKLY`, `WR-HOURLY`, `PR-STANDARD`, `ET-HOURLY`, `INT-PAYROLL-01` and others), its relationship types, and the structure "an overtime rule with a weekly threshold, contained in a work rule, used by a pay rule" are **invented for testing**. They do not describe UKG Pro WFM or Workforce Central behaviour. UKG documents "Overtime Rules" as their own API resource group, and the real containment is **unverified**. Every fixture file carries this label in its header or first sheet, and the product profile is `synthetic`, not `ukg_pro_wfm`.

Sources, generated deterministically:

- `harborline-config-before.xlsx` and `harborline-config-after.xlsx`: two **separate snapshots**. They differ in one semantic attribute: `OT-WEEKLY.threshold_hours` goes from 40 to 37.5. Sheets: OvertimeRules, WorkRules, PayRules, EmploymentTerms, Integrations, MappingRows, Requirements, Tests. Cross-references live in cells.
- `harborline-design.pdf`: prose and a table that mention objects by ID. These yield rule-based claims (`deterministic_rule` basis).
- `harborline-tests.xlsx` includes one test whose expected result hard-codes "40" (`asserts_value`).
- **Messy variants** (`harborline-config-before-messy.xlsx` and others): renamed sheets, merged header cells, a hidden row, a dangling ID reference, an alias spelling of an object ID, a formula with no cached value, trailing whitespace, and an unknown sheet. These test robustness and boundary reporting.

The change set is **derived by diffing the two snapshots**. It is never written by hand.

## Validation design (no self-certification)

- **Independent oracle.** `tests/oracle/harborline-expected-impact.yaml` is **authored by hand** from the fictional scenario description, **before** the generator and parser exist, by someone not writing the generator. It lists the expected change set, impact candidates by tier, upstream constraints, context, coverage gaps and not-modelled boundaries (see `docs/architecture/impact-propagation.md`, worked example). The generator must not read it, and it must not be generated from the generator's spec.
- **Mutation tests.** At least 20 mutations of the fixtures or graph, each with a hand-stated expected effect. Examples:
  - delete a `uses` reference;
  - break an ID (dangling reference);
  - flip an edge's review state to rejected;
  - add an unreviewed rule edge;
  - remove a test link (new coverage gap);
  - change a display-only attribute (no propagation);
  - introduce a cycle;
  - set an entity's profile to unknown;
  - exceed the depth limit.

  Every mutation must change the report exactly as stated.
- **Differential check.** Database traversal and an in-memory traversal of the same graph must give identical results.

## Slices (in order) and who builds them

| # | Slice | Done when | Design | Build | Check |
|---|---|---|---|---|---|
| 0 | Repo scaffold: `backend/` (uv, FastAPI, Pydantic, pytest, ruff, pyright), `frontend/` (Next.js, TS, Tailwind, shadcn/ui, React Flow), CI, Postgres via `initdb` test fixture (Docker unavailable in cloud) | All checks pass in CI | architect | implementer | scout |
| 1 | Domain model per `docs/architecture/relationship-model.md` rev 2 (after D3): Actor (immutable kind), Snapshot, Document, DocumentVersion (lineage), EvidenceLocator (immutable; xlsx_cell, pdf_bbox, docx_paragraph, csv_row, xml_xpath, json_pointer), Entity, EntityVersion, Relationship, Claim (basis, polarity, scope), ReviewEvent (claim and relationship targets, append-only), UnresolvedReference; product profiles include `synthetic` and `unknown` | Validators and tests per the model's "invariants to test" | architect | implementer | architect |
| 2a | **Oracle first:** hand-authored expected impact set and mutation catalogue | Reviewed and frozen before 2b starts | architect | (human or architect) | — |
| 2b | Synthetic generator: before and after snapshots, messy variants, PDF, test inventory, all fictional-labelled | Byte-stable regeneration (test); the generator never reads the oracle | — | implementer | scout |
| 3 | Ingestion foundation with hostile-input defences (see below); parse xlsx with **openpyxl** (cell coordinates, formula text and cached value read separately), PDF with **pdfplumber** (page and word bounding box) into IR fragments | Every fragment has a resolvable locator; all hostile-input tests pass | architect (trust boundary) | implementer | architect security review |
| 4 | Deterministic extraction: explicit claims from workbook references; rule claims from PDF ID mentions and value matches; boundaries for dangling or unknown references | Messy variants produce the stated boundaries, not crashes and not silent drops | architect (catalogue) | implementer | implementer |
| 5 | Storage: Postgres schema plus Alembic migrations; review endpoint; **database-enforced human-only accept and reject** (constraint trigger plus role privileges) | A direct SQL insert of an accept by a service actor fails (test) | architect | implementer | architect |
| 6 | Snapshot diff (stable keys, field-level) plus directional traversal per `impact-propagation.md`; API endpoints `/graph`, `/entities/{id}/evidence`, `/impact` | Oracle exact match; 20+ mutations detected; deterministic hash; differential check | architect | implementer | architect |
| 7 | Graph view: React Flow for **bounded subgraphs only** (impact neighbourhood); line style by display label; evidence panel (document, locator, snippet) | Playwright CLI on localhost: renders, click shows evidence, statuses distinguishable | implementer (`frontend-design`) | implementer | scout |
| 8 | Impact report (API and UI) in the skill's report shape: change set; impact candidates (established, possible); **re-validation tasks**; coverage gaps; upstream constraints; context; not modelled | Oracle match; no "safe" wording (string test); no pay amounts | architect | implementer | architect milestone review |

## Ingestion security requirements (slice 3)

- **Allow-list** by detected content type, not extension: xlsx, csv, pdf, docx, xml, json. Size cap per file and per upload.
- **ZIP-based formats (xlsx, docx):**
  - cap the entry count and total uncompressed size;
  - reject a compression ratio above 100×;
  - reject nested archives and path-traversal entry names.

  Check the archive before handing it to openpyxl.
- **Macros:** reject macro-enabled types (`.xlsm`, `.docm`, and `vbaProject.bin` inside any package). Never execute embedded content. Do not evaluate formulas: read cached values and formula text only.
- **XML:** parse with `defusedxml` (no DTDs, no external entities, no entity expansion). This applies to standalone XML and to XML inside OOXML packages where we parse it ourselves.
- **PDF:** page-count and per-page time limits; parse in a worker process with memory and time limits; no JavaScript or embedded-file handling.
- **Hostile-file tests (required):** ZIP bomb, path-traversal ZIP entry, XXE payload, billion-laughs, macro-enabled workbook, extension spoofing (a PDF renamed `.xlsx`), oversized file, truncated or corrupt PDF, deeply nested JSON. Each is rejected with a clear, logged reason, and nothing is written to the evidence store.

## Measurable acceptance criteria

| # | Criterion | Measure |
|---|---|---|
| 1 | Locator integrity | 100% of claims resolve to a locator that reopens the stored snippet (automated) |
| 2 | Determinism | Two runs give byte-identical reports (hash) |
| 3 | Independent correctness | Exact match to the hand-authored oracle; 100% of at least 20 mutations detected as stated |
| 4 | Output kinds | Report has the change set, established and possible impact candidates (weakest edge and any conflict shown), re-validation tasks, coverage gaps, upstream constraints, context and not modelled; no "safe" wording; no pay amounts |
| 5 | Coverage and re-validation | A requirement with no live test is reported as a coverage gap; the test hard-coding "40" is reported as a re-validation task (update expected value 40 → 37.5) |
| 6 | Human-only review | The database rejects any review event (claim or relationship) and any lineage declaration by a non-human actor, and rejects changing an actor's kind; every event has actor, timestamp and reason where required |
| 7 | Hostile input | All hostile-file tests reject safely |
| 8 | Messy input | Every messy variant yields the stated boundaries or claims; no crash, no silent drop |
| 9 | Performance | Traversal on a synthetic hub-heavy graph of about 10⁵ edges meets a team-set p95 target on CI hardware (target to be set in D8) |
| 10 | UI | Playwright CLI: graph renders, evidence panel shows document, locator and snippet |
| 11 | Usefulness signal (with the interview guide) | Demo walkthroughs with practitioners recorded under `docs/research/practitioner-interview-guide.md`; decision thresholds per D7 |

## Out of scope for Milestone 1

Real artefacts (gate G-REAL), LLM extraction (Milestone 2, behind the claim and review model, synthetic evaluation only), Docling, pgvector, Workforce Central and Pro WFM parsers, any UKG API or Data Interface, authentication beyond a single local reviewer identity, multi-tenancy, and cross-customer features (Developer Policy §4 cross-tenant aggregation).

## Risks specific to this milestone
- **Synthetic is not real.** The demo proves the pipeline, not fidelity to UKG. Say so in every demo.
- **The propagation catalogue is a modelling choice.** It is fictional, and needs per-profile evidence before any real use.
- **pdfplumber pulls in a native binary (pypdfium2).** It is only needed for rendering; keep it pinned and covered by the dependency licence review.
