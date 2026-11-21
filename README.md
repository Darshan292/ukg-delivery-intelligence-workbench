# Evidence-first configuration change-impact workbench (working name; final name pending)

> **Independent community project. Not affiliated with, endorsed by, or sponsored by UKG Inc. UKG and related marks are trademarks of UKG Inc.**

> **Synthetic data only.** This repository contains no real UKG exports, employee records, payroll data or client documents, and must never receive any. The demonstration organisation, "Harborline Logistics", is fictional. Its configuration structures do not describe how UKG Pro WFM or Workforce Central behave.

An open-source tool for UKG implementation, migration and support practitioners at any firm. It reads project artefacts (configuration workbooks, requirement lists, test inventories, mapping specifications), keeps an immutable source location for every fact it extracts, builds a typed dependency graph, and reports the directional impact of a configuration change. Every relationship carries its evidence, and only a named human can accept one. It never declares a change "safe".

## Status

**Pre-alpha.** The backend and frontend scaffolds and a three-node tracer bullet exist: it shows stored links around one fictional entity, each with its source locator. It is not impact analysis and its locators are fake. Nothing in this repository has been measured for accuracy, speed or time saved, and no such claims are made.

## Quick start (about 5 minutes)

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), Node 22 or newer, and make.

```bash
git clone https://github.com/Darshan292/ukg-delivery-intelligence-workbench   # the repository may be renamed
cd ukg-delivery-intelligence-workbench
make dev
```

`make dev` starts Postgres in Docker, applies the migrations, loads the fictional seed data, then runs the API on port 8000 and the web app on port 3000. Open <http://127.0.0.1:3000>. Ctrl-C stops the servers (`make db-down` stops the database).

You should see a FICTIONAL banner, a graph of three fictional entities (`REQ-T1`, `RULE-T1`, `TEST-T1`) and a list of two links. Click a link, in the list or on the graph, to see the source locator it came from.

| Command | What it does |
|---|---|
| `make dev-local` | Same as `make dev`, with a throwaway local Postgres (`scripts/pg-local.sh`) for machines without Docker |
| `make test` | Backend pytest and frontend vitest |
| `make lint` | ruff, pyright, eslint and tsc |
| `make e2e` | Starts the stack, runs the Playwright browser tests, tears everything down |

**What this is not:** the tracer bullet shows stored links only. It is not impact analysis, and it uses fake locators and fictional data.

## Where to start reading

| Document | What it is |
|---|---|
| [`docs/plans/milestone-1.md`](docs/plans/milestone-1.md) | The first milestone: synthetic evidence-to-impact slice |
| [`docs/architecture/relationship-model.md`](docs/architecture/relationship-model.md) | Claims, evidence locators and human review |
| [`docs/architecture/impact-propagation.md`](docs/architecture/impact-propagation.md) | Directional change-impact rules |
| [`docs/decisions-for-approval.md`](docs/decisions-for-approval.md) | Decisions made and still open |
| [`docs/risk-register.md`](docs/risk-register.md) | Risks and assumptions, including UKG Developer Policy constraints |
| [`reports/UKG delivery intelligence research.md`](reports/UKG%20delivery%20intelligence%20research.md) | The research behind the design |

## Boundaries

- No connection to any live UKG tenant, Workday, Boomi or ServiceNow.
- No AI agents calling UKG APIs, no cross-customer aggregation, and no model training or evaluation on customer data (see the UKG Developer Policy notes).
- Using real artefacts, or any commercial use, requires independent legal review first.

## Contributing

Contributions must use synthetic data only. Never attach real exports, employee data or client documents to issues, pull requests or fixtures. Every source file carries an SPDX header (`SPDX-License-Identifier: Apache-2.0`).

## Licence

[Apache License 2.0](LICENSE). See [`NOTICE`](NOTICE).
