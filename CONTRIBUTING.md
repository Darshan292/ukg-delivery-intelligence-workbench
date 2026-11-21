# Contributing

This is an independent community project. It is not affiliated with, endorsed by or sponsored by UKG Inc.

Development setup instructions arrive with the first runnable slice and will live in the README.

## Synthetic data only

Never attach real UKG exports, employee data, payroll data or client documents to issues, pull requests or test fixtures. Use synthetic data only. If you think you have posted real data by mistake, tell the maintainer straight away so it can be removed.

## Branch and pull request flow

1. Create a feature branch. Never push to `main`.
2. Commit and push your branch regularly.
3. Open a pull request against `main`. Changes reach `main` only through a reviewed pull request.

## Sign your commits (DCO)

Sign off every commit with `git commit -s`. This adds a `Signed-off-by:` line and certifies the [Developer Certificate of Origin](https://developercertificate.org/): you wrote the change or have the right to submit it under the project licence.

## Licence and SPDX headers

The project is licensed under Apache-2.0. Every new source file (Python, TypeScript/JavaScript, shell, SQL, CSS, config code) starts with these two lines, in the file's comment syntax:

```
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
```

Markdown and data fixtures are exempt.

## Dependency licence gate

- Allowed: MIT, BSD, Apache-2.0, ISC, PSF, MPL-2.0.
- LGPL: allowed for development-only dependencies.
- Rejected: GPL, AGPL, SSPL, BSL and non-commercial licences.

Check the licence of every new dependency before you add it.

## Reuse before you build

If a new component is over about 200 lines, the pull request description must name the open-source options you checked and why each was rejected.

## Claims need evidence

Do not claim accuracy, speed or time saved unless a test or a recorded pilot backs it up.
