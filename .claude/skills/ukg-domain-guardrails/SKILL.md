---
name: ukg-domain-guardrails
description: Guardrails for any work touching UKG product semantics in this repo. Use whenever code, schemas, parsers, fixtures, prompts, docs or answers mention UKG Pro Workforce Management (Pro WFM, formerly Dimensions), Workforce Central (WFC, Kronos), their exports, configuration objects (pay rules, work rules, pay codes, accrual policies, schedules, labor categories, org hierarchy, access profiles), APIs, or migration between them, even if the user does not say "UKG".
---

# UKG domain guardrails

This product helps engineers reason about real customer configurations. A wrong claim about how UKG behaves is worse than no claim: an engineer may act on it in a customer tenant. So the bar for domain statements is "backed by a source in this repo", not "sounds plausible".

## Two products, two profiles

UKG Pro WFM and Workforce Central are separate product profiles. They share vocabulary ("pay rule", "pay code", "work rule", "accrual") but not schemas, export formats, object identifiers or semantics.

- Every ingested document, extracted entity and parser carries an explicit `product_profile`: `ukg_pro_wfm`, `workforce_central`, or `unknown`. Never default it silently. Undetectable means `unknown`, which is a valid, visible state.
- Parsers, field mappings and fixtures are per profile. Do not write one parser that "handles both" by guessing field equivalence.
- A WFC→Pro WFM mapping is itself a modelled artifact: it needs its own evidence per mapped pair. Matching names are a hint, not a mapping.

## No invented compatibility

We have no live tenant, API or vendor documentation access. So:

- Do not write code against UKG API endpoints, payloads, auth flows or export layouts unless a source file in this repo (a sample export, a spec the user provided) shows them. Cite that file.
- Do not claim a feature, limit, version behaviour or integration capability of UKG, Boomi, Workday or ServiceNow from memory. If it matters, say it is unverified.
- Synthetic fixtures model the *shape we have evidence for*, and say so in a header comment naming the source. If there is no source, the fixture is labelled fictional and must not be presented as representative.

## Mark assumptions where they live

When you must proceed on an assumption, make it greppable and visible instead of burying it in prose:

- In code/fixtures: `# ASSUMPTION(unverified): <what>, <what would confirm it>`
- In data: a field `assumption: true` with a note, never a silently filled value.
- In replies: a short "Unverified assumptions" list.

## Configuration relationships

Never fabricate a relationship between configuration objects (e.g. "this pay rule uses that work rule"). Relationships come from the evidence pipeline with provenance and a status of Observed, Inferred or Confirmed; follow the `evidence-first-engineering` skill for that. If you cannot point to the row, cell, page or section a relationship came from, it does not exist in the graph.

## Quick self-check before finishing

1. Does every new entity/parser/fixture name its product profile?
2. Did I state any UKG behaviour I cannot cite from a repo file? Mark it or remove it.
3. Did I map anything across WFC and Pro WFM by name alone?
4. Did any data look like a real employee or customer? Replace it with synthetic data.
