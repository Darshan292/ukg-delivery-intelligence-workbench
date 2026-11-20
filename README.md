# Evidence-first configuration change-impact workbench (working name; final name pending)

> **Independent community project. Not affiliated with, endorsed by, or sponsored by UKG Inc. UKG and related marks are trademarks of UKG Inc.**

> **Synthetic data only.** This repository contains no real UKG exports, employee records, payroll data or client documents, and must never receive any. The demonstration organisation, "Harborline Logistics", is fictional. Its configuration structures do not describe how UKG Pro WFM or Workforce Central behave.

An open-source tool for UKG implementation, migration and support practitioners at any firm. It reads project artefacts (configuration workbooks, requirement lists, test inventories, mapping specifications), keeps an immutable source location for every fact it extracts, builds a typed dependency graph, and reports the directional impact of a configuration change. Every relationship carries its evidence, and only a named human can accept one. It never declares a change "safe".

## Status

**Pre-alpha. No application code yet.** The research and architecture are done, and Step 1 (scaffold, CI and a three-node tracer bullet) starts next. Nothing in this repository has been measured for accuracy, speed or time saved, and no such claims are made.

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
