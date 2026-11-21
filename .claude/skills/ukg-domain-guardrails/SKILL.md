---
name: ukg-domain-guardrails
description: Guardrails for any work touching UKG product semantics in this repo. Use whenever code, schemas, parsers, fixtures, synthetic data, prompts, docs or answers mention UKG Pro Workforce Management (Pro WFM, formerly Dimensions), Workforce Central (WFC, Kronos), the fictional Harborline synthetic dataset, their exports, configuration objects (pay rules, work rules, overtime rules, pay codes, accrual policies, schedules, labor categories, org hierarchy, access profiles), APIs, or migration between them, even if the user does not say "UKG".
---

# UKG domain guardrails

This product helps engineers reason about real customer configurations. A wrong claim about how UKG behaves is worse than no claim: an engineer may act on it in a customer tenant. So the bar for domain statements is "backed by a source in this repo", not "sounds plausible".

## Product profiles

UKG Pro WFM and Workforce Central are separate product profiles. They share vocabulary ("pay rule", "pay code", "work rule", "accrual") but not schemas, export formats, object identifiers or semantics.

Every ingested document, extracted entity, relationship type catalogue and parser carries an explicit `product_profile`:

| Profile | Meaning |
|---|---|
| `ukg_pro_wfm` | Real UKG Pro WFM artefacts. Not used until gate G-REAL (Milestone 1 plan) is approved |
| `workforce_central` | Real Workforce Central artefacts. Same gate |
| `synthetic` | Fictional data invented for development and demos (for example Harborline Logistics). Milestone 1 uses only this |
| `unknown` | The profile could not be determined. A valid, visible state; never silently defaulted |

Never default a profile silently, and never change one by inference.

- Parsers, field mappings and fixtures are per profile. Do not write one parser that "handles both" by guessing field equivalence.
- A WFC→Pro WFM mapping is itself a modelled artifact: it needs its own evidence per mapped pair. Matching names are a hint, not a mapping.

## Synthetic is not UKG

Synthetic data exists to exercise the pipeline, not to describe UKG. Its object names may echo UKG vocabulary ("work rule", "overtime rule") because that is what engineers recognise, but its structure and relationships are invented.

- Label every synthetic fixture, catalogue, report and UI view as fictional ("FICTIONAL: not UKG behaviour"). The `synthetic` profile is the machine-readable form of that label.
- Never present a synthetic relationship, containment or propagation rule as how Pro WFM or WFC works, in code comments, docs, tests, demos or answers. Example: "in Harborline the overtime rule sits inside a work rule" is fine; "in UKG the overtime rule sits inside a work rule" is not, unless a cited source says so.
- The `synthetic` relationship catalogue never migrates into the `ukg_pro_wfm` or `workforce_central` profiles. Real profiles get their own catalogues, built from evidence.
- Never mix profiles in one graph or one impact analysis. Never map synthetic entities to real ones.

## No invented compatibility

We have **no live UKG tenant access** and no customer artefacts. We **may** use documented vendor sources that are cited in the repository: the verified research notes under `docs/research/notes/` (for example `verified_ukg_technical.md` and `verified_ukg_developer_policy.md`) and the public UKG pages they quote, with URL and retrieval date. So:

- Do not write code against UKG API endpoints, payloads, auth flows or export layouts unless a cited source in this repo (a verified research note, a sample export, a spec the user provided) shows them. Cite it, and label the claim as documented vendor fact, distinct from inference.
- A documented source tells you what UKG publishes, not how a particular customer configured it. Never infer a customer's configuration from vendor documentation.
- No UKG Data Interface use (APIs, webhooks, MCP Gateway) without the registration, customer consent and UKG approval the Developer Policy requires (`verified_ukg_developer_policy.md`).
- Do not claim a feature, limit, version behaviour or integration capability of UKG, Boomi, Workday or ServiceNow from memory. If it matters, say it is unverified.
- Synthetic fixtures are fictional by default. If a fixture deliberately imitates a documented shape (for example the field names in a documented API response), its header names the cited source and states that only that shape, not the data or relationships, comes from it.

## Mark assumptions where they live

When you must proceed on an assumption, make it greppable and visible instead of burying it in prose:

- In code/fixtures: `# ASSUMPTION(unverified): <what>, <what would confirm it>`
- In data: a field `assumption: true` with a note, never a silently filled value.
- In replies: a short "Unverified assumptions" list.

## Configuration relationships

Never fabricate a relationship between configuration objects (e.g. "this pay rule uses that work rule"). Relationships come from the evidence pipeline as claims with immutable source locators, an evidence basis and a human review state; follow the `evidence-first-engineering` skill and `docs/architecture/relationship-model.md` for that. If you cannot point to the row, cell, page or section a relationship came from, it does not exist in the graph.

## Quick self-check before finishing

1. Does every new entity/parser/fixture name its product profile, and is synthetic material labelled fictional?
2. Did I state any UKG behaviour I cannot cite from a repo file? Mark it or remove it.
3. Did I map anything across WFC and Pro WFM by name alone?
4. Did any data look like a real employee or customer? Replace it with synthetic data.
