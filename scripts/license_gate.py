# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Licence gate for dependency licences (stdlib only). Fails closed.

ALLOW: MIT, BSD (2/3-clause), Apache-2.0, ISC, PSF, MPL-2.0, 0BSD, Unlicense,
CC0-1.0, Python-2.0, Zlib.
DEV-ONLY: LGPL (any version); passes only with --dev.
DENY: GPL, AGPL, SSPL, BSL/BUSL, any "non-commercial" licence, and anything
blank, UNKNOWN, "SEE LICENSE IN ..." or not recognised.

SPDX expressions: `A OR B` passes if either side does; `A AND B` only if both
do; `X WITH exception` is judged on X. Several PyPI classifiers joined by ";"
and npm licence arrays are treated as AND (the conservative reading).

Usage: license_gate.py (--pip-json FILE | --npm-json FILE) [--dev]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

Verdict = Literal["allow", "dev_only", "deny"]
_RANK: dict[Verdict, int] = {"allow": 0, "dev_only": 1, "deny": 2}

_DENY = re.compile(
    r"non-?commercial|\bnc\b|(?<![a-z])(a|l)?gpl|general public|affero|sspl|server side public"
    r"|busl|\bbsl\b|business source|unknown|see license|proprietary|commercial|commons.?clause"
)
_DEV_ONLY = re.compile(r"\blgpl|lesser general public|library general public")
_ALLOW = re.compile(
    r"^(mit([- ]0)?( license)?|bsd([- ].*)?|apache([- ].*)?|isc( license.*)?|psf([- ].*)?"
    r"|python software foundation.*|python-2\.0.*|mpl[- ]2\.0.*|mozilla public license 2\.0.*"
    r"|0bsd|unlicense|the unlicense.*|cc0-1\.0|zlib( license)?)$"
)
_TOKENS = re.compile(r"(\(|\)|\s+AND\s+|\s+OR\s+|\s+WITH\s+)")


def _atom(text: str) -> Verdict:
    t = text.strip().rstrip("*").strip().lower()
    if not t:
        return "deny"
    if _DENY.search(_DEV_ONLY.sub(" ", t)):  # judge GPL/AGPL even beside LGPL
        return "deny"
    if _DEV_ONLY.search(t):
        return "dev_only"
    return "allow" if _ALLOW.match(t) else "deny"


class _Parser:
    def __init__(self, toks: list[str]) -> None:
        self.t, self.i = toks, 0

    def peek(self) -> str | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self) -> str:
        self.i += 1
        return self.t[self.i - 1]

    def expr(self) -> Verdict:  # OR: best alternative
        v = [self.term()]
        while self.peek() == "OR":
            self.take()
            v.append(self.term())
        return min(v, key=_RANK.__getitem__)

    def term(self) -> Verdict:  # AND: worst part
        v = [self.prim()]
        while self.peek() == "AND":
            self.take()
            v.append(self.prim())
        return max(v, key=_RANK.__getitem__)

    def prim(self) -> Verdict:
        tok = self.peek()
        if tok is None or tok in ("AND", "OR", "WITH", ")"):
            raise ValueError("malformed")
        self.take()
        if tok == "(":
            v = self.expr()
            if self.peek() != ")":
                raise ValueError("malformed")
            self.take()
        else:
            v = _atom(tok)
        if self.peek() == "WITH":
            self.take()
            if self.peek() is None:
                raise ValueError("malformed")
            if _DENY.search(_DEV_ONLY.sub(" ", self.take().lower())):  # e.g. Commons-Clause
                v = "deny"
        return v


def classify(license_text: str) -> Verdict:
    parts = [p for p in license_text.split(";") if p.strip()] or [""]
    verdicts: list[Verdict] = []
    for part in parts:
        if re.search(r"\s(AND|OR|WITH)\s", part):
            toks = [x.strip() for x in _TOKENS.split(part) if x.strip()]
            try:
                p = _Parser(toks)
                v = p.expr()
                if p.peek() is not None:
                    raise ValueError("malformed")
            except ValueError:
                v = "deny"
        else:
            v = _atom(re.sub(r"^\(([^()]*)\)$", r"\1", part.strip()))
        verdicts.append(v)
    return max(verdicts, key=_RANK.__getitem__)


def check(packages: list[dict[str, str]], dev: bool) -> list[str]:
    out: list[str] = []
    for p in packages:
        lic = p.get("license", "")
        v = classify(lic)
        if v == "deny" or (v == "dev_only" and not dev):
            why = "dev-only licence in runtime set" if v == "dev_only" else "denied or unknown licence"
            out.append(f"{p.get('name', '?')} {p.get('version', '')}: {lic!r} ({why})")
    return out


def load_pip(path: Path) -> list[dict[str, str]]:
    rows = json.loads(path.read_text())
    return [
        {"name": str(r.get("Name", "")), "version": str(r.get("Version", "")), "license": str(r.get("License") or "")}
        for r in rows
    ]


def load_npm(path: Path) -> list[dict[str, str]]:
    data: dict[str, Any] = json.loads(path.read_text())
    out: list[dict[str, str]] = []
    for key, val in data.items():
        name, _, version = key.rpartition("@")  # rpartition keeps scoped "@x/y"
        lic = val.get("licenses") if isinstance(val, dict) else None
        if isinstance(lic, list):
            lic = " AND ".join(str(x) for x in lic)
        out.append({"name": name or key, "version": version if name else "", "license": str(lic or "")})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pip-json", type=Path)
    g.add_argument("--npm-json", type=Path)
    ap.add_argument("--dev", action="store_true", help="allow dev-only (LGPL) licences")
    a = ap.parse_args(argv)
    pkgs = load_pip(a.pip_json) if a.pip_json else load_npm(a.npm_json)
    if not pkgs:
        print("LICENCE GATE: no packages in input; failing closed")
        return 1
    bad = check(pkgs, a.dev)
    for line in bad:
        print(f"LICENCE VIOLATION: {line}")
    print(f"checked {len(pkgs)} packages, {len(bad)} violation(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
