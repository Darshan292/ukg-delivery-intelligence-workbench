# Risk and assumptions register

Updated 2026-11-18 after the UKG Developer Policy review. Sources: `reports/UKG delivery intelligence research.md` and `research_notes/UKG delivery intelligence research/verified_ukg_developer_policy.md`. Status labels: **Verified** (primary source read), **Partly verified**, **Unverified**, **Assumption** (a deliberate modelling choice).

## A. Legal, policy and commercial access

| ID | Risk or assumption | Status | Consequence if wrong | Mitigation / gate |
|---|---|---|---|---|
| L1 | The product may be read as a "Competitive Product or Service" or as "Competitive Intelligence" under the UKG Developer Policy §4 (and possibly the MSA) | **Verified clause; interpretation open** | Loss of interface access; commercial and legal exposure; partner relationship damage | **Decision D1:** independent legal review (and, where needed, UKG's own interpretation) before any commercial positioning or real data. Keep positioning as an assurance layer over artefacts UKG does not hold |
| L2 | Cross-customer features (pattern libraries, benchmarks, cross-project comparison) breach the cross-tenant aggregation clause (§4) | Verified clause | Policy breach | Not in the roadmap. Per-customer isolation by design. Any cross-customer feature needs a Data Sharing Agreement and consent from all tenants |
| L3 | LLM, cloud host and database providers are sub-processors needing prior written UKG authorisation (§5) | Verified clause; applicability to offline files unclear | Policy breach on the first real deployment | No LLM on real data before authorisation; sub-processor list maintained from day one; gate G-REAL |
| L4 | Evaluating extraction models on real artefacts counts as "evaluate AI … on Customer Data" (§4) | Verified clause | Policy breach | Evaluation sets are synthetic unless customer **and** UKG written consent exists |
| L5 | AI agents that call UKG APIs are prohibited without MCP Gateway registration or authorisation (§4, §7) | Verified | Breach; full liability for agent actions | No agentic UKG API access in the roadmap |
| L6 | Offline processing of customer-supplied UKG exports is outside the Developer Policy | **Unverified (inference)**; "Developer" undefined; customer MSA unread | Offline route may carry the same obligations, or be restricted by the customer's MSA | **Decision D2:** Legal clarification; customer DPA; never design offline ingestion as a workaround to consent flows |
| L7 | MSA, AUP and API Call Pack terms are consistent with the Developer Policy | **Unverified** (Cloudflare-blocked) | Additional restrictions | Obtain the PDFs (from UKG or a customer); Legal review |
| L8 | API route obligations are achievable: Partner Portal registration, consent flow, 90-day rotation, residency, FIPS-validated crypto, 24-hour incident reporting, deletion including backups and derivatives, 12-month logs, audit | Verified requirements; our capability is untested | API route blocked or non-compliant | Design for per-customer key-based purge and audit logging before any API work; this belongs to Milestone 3 or later |
| L9 | The Developer Policy is stable | Verified that it may change on posting (§12); v1.0 has drafting defects | Requirements shift silently | Re-check the policy's `updatedAt` before each gate; record the hash |

## B. Problem and market

| ID | Risk or assumption | Status | Consequence | Mitigation |
|---|---|---|---|---|
| M1 | Practitioners spend meaningful time manually cross-referencing artefacts | **Unverified; no source** | No buyer | P0 interviews (`docs/research/practitioner-interview-guide.md`) |
| M2 | Real artefacts carry explicit, parseable cross-references | Unverified; the Fayetteville audit shows rules set from verbal guidance | Most edges become rule- or LLM-based, so review burden erodes value | Measure the explicit-claim ratio on the first sanitised samples |
| M3 | Someone has budget and authority to buy | Unverified | No revenue path | Interview section H; signal levels |
| M4 | UKG extends Setup Data Manager compare, or ships configuration-assistant features | Plausible | Drift and explanation are commoditised | Anchor value in provenance, history and cross-tool coverage |
| M5 | Test vendors (Opkey, TestAssure) deepen configuration-level impact | Medium | Overlap with E and D | Integrate as data sources |
| M6 | The WFC to Pro WFM migration market closes on 31 March 2027 | Secondary sources agree; UKG page unread | Migration investment stranded | Migration capability kept conditional and narrow |

## C. Technical

| ID | Risk or assumption | Status | Consequence | Mitigation |
|---|---|---|---|---|
| T1 | The Milestone 1 configuration structure (overtime rule in a work rule, used by a pay rule) | **Assumption, fictional** | The demo misleads if presented as UKG behaviour | Fictional labels on every fixture and report; profile `synthetic` |
| T2 | Propagation rules per relationship type are correct | **Assumption** (`impact-propagation.md`) | Missed or spurious impacts | Per-profile catalogue built from evidence; mutation tests; validation against real outcomes later |
| T3 | Static impact analysis has limited recall (literature reports 50–56% for dynamic analysis) | Research finding | Missed impacts read as "safe" | Not-modelled category; never "safe"; no pay amounts |
| T4 | A self-certifying oracle hides parser errors | Identified | False confidence | Hand-authored oracle, messy fixtures, 20+ mutations, differential check |
| T5 | pdfplumber on real PDFs (scanned or complex layout) | Unverified at scale; works on generated PDFs | Missing or garbled locators | OCR and layout-heavy PDFs out of scope for Milestone 1; Docling or ML only later, with output kept rule- or LLM-based |
| T6 | Hostile files (ZIP bombs, XXE, macros, crafted PDFs) | Known threat class | Denial of service or code execution | Slice 3 requirements and tests; sandboxed parsing worker |
| T7 | Tenant graph scale (10³–10⁵ nodes, 10⁴–10⁶ edges, estimated) | Unverified | Traversal performance | Hub-heavy synthetic benchmark; measure on first real data |
| T8 | Setup GET responses contain enough to rebuild relationships | Only the employment-terms sample seen | Shallow graph from API data | Validate on a permitted non-production response |
| T9 | Setup Data Manager export is parseable | Format undocumented | Dead end | Do not build against it without a UKG specification |
| T10 | LLM extraction precision on HR/WFM prose | No domain benchmark | Review burden | Rule- or LLM-based claims only; span verifier; synthetic evaluation set |
| T11 | Customers require customer-hosted or single-tenant deployment and certifications | Unverified | Sales blocked | Containerised single-tenant first; SOC 2 later |
| T12 | Licence compliance of dependencies | pdfplumber (MIT), pdfminer.six (MIT), pypdfium2 (BSD-3 / Apache-2.0 plus bundled permissive licences) checked; full tree not audited | Licence breach | Licence scan in CI before release |
