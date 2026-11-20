# UKG Delivery Intelligence Workbench

An evidence-first engineering intelligence platform for UKG implementation, migration and support engineers. It helps them understand configurations, dependencies, changes and their delivery impact. Every fact it shows must trace back to a source.

Status: research done; no application code yet. Read before building: `docs/plans/milestone-1.md` (revision 2), `docs/decisions-for-approval.md` (open decisions), `docs/risk-register.md`, `reports/UKG delivery intelligence research.md`.

## Architecture direction

- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui, React Flow
- Backend: Python, FastAPI, Pydantic
- Data: PostgreSQL with full-text search; pgvector only when a measured need justifies it
- Document processing: openpyxl (cell-level provenance), pdfplumber (page and word bounding boxes), defusedxml; pandas only after locators are captured. **No PyMuPDF** (AGPL / commercial licence). Docling deferred until layout-heavy PDFs need it

## Engineering rules

1. Deterministic code establishes structural truth.
2. AI is for extraction, explanations and suggestions, never the authority for configuration relationships.
3. Preserve provenance end to end (see skill `evidence-first-engineering`).
4. Build a canonical intermediate representation (IR) before constructing the graph.
5. Keep business rules out of presentation code.
6. Typed interfaces and explicit validation at every boundary.
7. Tests are written alongside implementation (TDD).
8. Secure coding throughout: validate untrusted files, no secrets in code, least privilege.
9. Never invent savings, performance numbers or product capabilities.
10. Synthetic data only. No real employee or customer data until gate G-REAL (Milestone 1 plan) is approved, and never person records.

Relationships: follow the model in `docs/architecture/relationship-model.md` (rev 2, binding: decisions D3 and D4 approved 2026-11-20). Evidence basis (explicit source, deterministic rule, LLM suggestion) is separate from review state (unreviewed, accepted, rejected, superseded). Only a human can accept or reject, and this is enforced in the database. Impact analysis is directional (`docs/architecture/impact-propagation.md`): established, possible and not-modelled categories, never "confirmed impacts", never "safe".

UKG Pro WFM and Workforce Central are separate product profiles (skill `ukg-domain-guardrails`). Change-impact logic follows skill `configuration-change-impact-review`. There is no live access to UKG tenants, Workday, Boomi or ServiceNow: do not build or test against them.

UKG Developer Policy (`research_notes/UKG delivery intelligence research/verified_ukg_developer_policy.md`) constrains future work:
- no UKG Data Interface use without registration, customer consent and UKG approval;
- no AI agents calling UKG APIs;
- no cross-customer aggregation or benchmarking;
- no model training or evaluation on customer data;
- no LLM or host as a sub-processor of customer data without UKG written authorisation.

Whether the product is a "competitive product" is for independent legal review (decision D1, open). Never assert that it is permitted or prohibited.

## How we work

- Process: superpowers. Plan with `writing-plans`, build with `test-driven-development`, finish with `verification-before-completion`. Use `brainstorming` only for genuinely open design questions.
- Solution size: ponytail. When the two pull different ways, superpowers decides the process and the tests; ponytail decides how much code. Ponytail never removes tests, validation, provenance or security.
- Docs: use Context7 for current framework docs when it is connected; otherwise read the official docs and note the version checked.
- Frontend tasks use `frontend-design`; `security-guidance` applies everywhere.
- Branching (Dev Team Directive 01, rule 3): work happens on a feature branch, which is committed and pushed at least daily; changes reach `main` only through a reviewed pull request. Never push directly to `main` and never rewrite history without asking.
- No new planning documents until Step 1 (Slice 0 plus the tracer bullet) ships. A design question that blocks code gets a decision record of at most one page.

## Delegating by complexity

Give each delegated task to the cheapest agent that can do it reliably, and pass the agent's model when spawning:

| Agent (`.claude/agents/`) | Model | Use for |
|---|---|---|
| `scout` | haiku | Read-only lookups, file/symbol search, summaries, running given checks, reading docs |
| `implementer` | sonnet | One well-specified plan task with tests, spec-compliance review, routine refactors |
| `architect` | opus | IR/provenance/graph data model, LLM boundary, impact traversal design, security review, milestone review |

Escalate when a lower tier reports ambiguity; never let a lower tier make an architectural decision.

## Tooling

- Graphify: when `graphify-out/graph.json` exists, `graphify query "<question>"` before broad grep; run `graphify update .` after code changes (no API cost).
- Playwright CLI (skill `playwright-cli`) for UI checks against a localhost server (`file://` is blocked). No Playwright MCP.
- LSP: Pyright and typescript-language-server (TypeScript pinned to 6.x: TypeScript 7 has no tsserver).
- Fresh cloud machine: `scripts/setup-claude-tools.sh` installs or verifies all CLI tools (`--check` to verify only).

## Licensing

Apache-2.0 (`LICENSE`, `NOTICE`). Every new source file (Python, TypeScript/JavaScript, shell, SQL, CSS, config code) starts with:

```
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
```

in the file's comment syntax. Markdown and data fixtures are exempt. Every dependency must pass the licence gate: MIT, BSD, Apache-2.0, ISC, PSF and MPL-2.0 are allowed, and LGPL is allowed for dev-only use. GPL, AGPL, SSPL, BSL and non-commercial licences are rejected. No paid services, no real data, and no claims that haven't been measured.
