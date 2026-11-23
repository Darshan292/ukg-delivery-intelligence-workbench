# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Deterministic PDF rule claims: co-mention and value match (Group D).

A word is only a mention when, end-trimmed, it equals (case-sensitive) the natural key of an
entity already in `Records` for the document's profile. Text alone is never a claim: a rule from
the catalogue must apply. Claims are `deterministic_rule`, cite only PDF word boxes, and carry
the rule's declared confidence. Every word is either cited or structural (prose is not data).
No word text appears in an exception or a log line.

shortcut: a key containing whitespace is never matched (words are split on spaces); revisit
when a real key needs it.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import Field

from app.domain.locators import PdfWordBbox
from app.domain.model import (
    BoundaryReason,
    Claim,
    Entity,
    ExtractionBoundary,
    NonBlank,
    ProductProfile,
    Record,
    Relationship,
    Versioned,
    number_from_cell_text,
)
from app.domain.records import Records
from app.extract.catalogue import CatalogueMismatch
from app.extract.xlsx import AlreadyExtracted, Extracted
from app.ingest.fragments import ParsedDocument

log = logging.getLogger(__name__)


class MentionRule(Record):
    source_type: NonBlank
    target_type: NonBlank
    relationship_type: NonBlank
    # owner question S4-Q10 (team default): a declared constant per rule, ordinal and NOT a
    # measured probability; it only orders representative claims and never sets a tier.
    confidence: Annotated[Decimal, Field(ge=0, le=1)]


class PdfRuleCatalogue(Record):
    product_profile: ProductProfile
    comention_method: Versioned  # e.g. "pdf_comention@1"
    value_method: Versioned  # e.g. "pdf_value_match@1"
    comention: tuple[MentionRule, ...]
    value_holders: tuple[MentionRule, ...]  # the relationship type must be qualifier_required
    trim_chars: str = ".,;:()[]\"'"  # stripped from both word ends before matching
    line_tolerance: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 2.0  # points of `top`


@dataclass(frozen=True)
class _Word:
    id: int
    page: int
    top: float
    x0: float
    text: str


@dataclass(frozen=True)
class _Mention:
    word: _Word
    entity: Entity


_EdgeKey = tuple[str, tuple[str, str, str], tuple[str, str, str], str | None]


def _next(xs: tuple[object, ...]) -> int:
    return max((getattr(x, "id") for x in xs), default=0) + 1  # noqa: B009


def _check(records: Records, parsed: ParsedDocument, rules: PdfRuleCatalogue) -> None:
    if parsed.kind != "pdf" or parsed.product_profile != rules.product_profile:
        raise CatalogueMismatch("extract: document does not fit the rule catalogue")
    cat = records.catalogue_by_profile.get(rules.product_profile)
    if cat is None:
        raise CatalogueMismatch("extract: no domain catalogue for the profile")
    ents = {t.name for t in cat.entity_types}
    rels = {t.name: t for t in cat.relationship_types}
    for qualified, group in ((False, rules.comention), (True, rules.value_holders)):
        for r in group:
            if (
                {r.source_type, r.target_type} - ents
                or r.relationship_type not in rels
                or rels[r.relationship_type].qualifier_required != qualified
            ):
                raise CatalogueMismatch("extract: rule does not fit the domain catalogue")
    mine = set(parsed.locator_ids)
    vid = parsed.document_version_id
    if any(mine & set(c.locator_ids) for c in records.claims) or any(
        b.document_version_id == vid for b in records.extraction_boundaries
    ):
        raise AlreadyExtracted("extract: version already extracted")


def _words(records: Records, parsed: ParsedDocument) -> list[_Word]:
    out: list[_Word] = []
    for p in sorted(parsed.pages, key=lambda p: p.page):
        for i in p.word_locator_ids:
            loc = records.locator_by_id[i]
            if not isinstance(loc, PdfWordBbox):
                raise ValueError("extract: not a word locator")
            out.append(_Word(i, p.page, loc.top, loc.x0, loc.snippet))
    return out


def _lines(words: list[_Word], tol: float) -> list[list[_Word]]:
    """Greedy clusters of words on one page whose `top` is within `tol` of the line's first."""
    out: list[list[_Word]] = []
    for w in sorted(words, key=lambda w: (w.page, w.top, w.x0, w.id)):
        if out and out[-1][0].page == w.page and w.top - out[-1][0].top <= tol:
            out[-1].append(w)
        else:
            out.append([w])
    return out


def extract_pdf_rules(
    records: Records, parsed: ParsedDocument, rules: PdfRuleCatalogue, *, now: datetime
) -> Extracted:
    _check(records, parsed, rules)
    vid = parsed.document_version_id
    snapshot = records.version_by_id[vid].snapshot_id
    words = _words(records, parsed)
    by_key: dict[str, list[Entity]] = {}
    for e in records.entities:
        if e.product_profile == rules.product_profile and not any(
            c.isspace() for c in e.natural_key
        ):
            by_key.setdefault(e.natural_key, []).append(e)
    bounds: set[tuple[BoundaryReason, tuple[int, ...]]] = set()
    edges: dict[_EdgeKey, tuple[Decimal, str, set[tuple[int, ...]]]] = {}

    def add(
        rule: MentionRule, method: str, src: Entity, tgt: Entity, q: str | None, ids: list[int]
    ) -> None:
        key: _EdgeKey = (rule.relationship_type, src.key, tgt.key, q)
        edges.setdefault(key, (rule.confidence, method, set()))[2].add(tuple(sorted(ids)))

    values: dict[int, dict[str, set[Decimal]]] = {}  # entity id -> attribute name -> numbers
    for ev in records.entity_versions:
        for a in ev.attributes:
            if isinstance(a.value, Decimal):
                values.setdefault(ev.entity_id, {}).setdefault(a.name, set()).add(a.value)

    for line in _lines(words, rules.line_tolerance):
        ms: list[_Mention] = []
        for w in line:
            hit = by_key.get(w.text.strip(rules.trim_chars), [])
            if len({e.entity_type for e in hit}) > 1:
                bounds.add(("ambiguous_target", (w.id,)))
            elif hit:
                ms.append(_Mention(w, hit[0]))
        mention_ids = {m.word.id for m in ms}
        for i, a in enumerate(ms):
            for b in ms[i + 1 :]:
                if a.entity.id == b.entity.id:
                    continue
                for r in rules.comention:
                    for s, t in ((a, b), (b, a)):
                        same = r.source_type == r.target_type
                        if (s.entity.entity_type, t.entity.entity_type) != (
                            r.source_type,
                            r.target_type,
                        ) or (same and s.entity.natural_key > t.entity.natural_key):
                            continue
                        add(
                            r,
                            rules.comention_method,
                            s.entity,
                            t.entity,
                            None,
                            [s.word.id, t.word.id],
                        )
        for w in line:
            if w.id in mention_ids:
                continue
            try:
                n = number_from_cell_text(w.text.strip(rules.trim_chars))
            except ValueError:
                continue
            for r in rules.value_holders:
                for x in ms:
                    for y in ms:
                        if x.entity.id == y.entity.id or (
                            (x.entity.entity_type, y.entity.entity_type)
                            != (r.source_type, r.target_type)
                        ):
                            continue
                        names = sorted(k for k, v in values.get(y.entity.id, {}).items() if n in v)
                        ids = [x.word.id, y.word.id, w.id]
                        if len(names) > 1:
                            bounds.add(("ambiguous_target", tuple(sorted(ids))))
                        elif names:
                            add(r, rules.value_method, x.entity, y.entity, names[0], ids)

    def sort_key(k: _EdgeKey) -> tuple[str, tuple[str, ...], tuple[str, ...], str]:
        return (k[0], k[1], k[2], k[3] or "")

    have = {rel.key: rel.id for rel in records.relationships}
    ent = {e.key: e.id for e in records.entities}
    rel_id: dict[_EdgeKey, int] = {}
    new: list[_EdgeKey] = []
    for k in sorted(edges, key=sort_key):
        known = have.get((k[0], ent[k[1]], ent[k[2]], k[3]))
        if known is None:
            new.append(k)
        else:
            rel_id[k] = known
    for i, k in enumerate(new, _next(records.relationships)):
        rel_id[k] = i
    pairs = [(k, ids) for k in sorted(edges, key=sort_key) for ids in sorted(edges[k][2])]
    claims = tuple(
        Claim(
            id=i,
            relationship_id=rel_id[k],
            basis="deterministic_rule",
            polarity="present",
            method=edges[k][1],
            confidence=edges[k][0],
            scope_snapshot_id=snapshot,
            locator_ids=ids,
            created_at=now,
        )
        for i, (k, ids) in enumerate(pairs, _next(records.claims))
    )
    boundaries = tuple(
        ExtractionBoundary(id=i, document_version_id=vid, reason=reason, locator_ids=ids)
        for i, (reason, ids) in enumerate(
            sorted(bounds, key=lambda b: (b[1], b[0])), _next(records.extraction_boundaries)
        )
    )
    out = records.extended(
        relationships=tuple(
            Relationship(
                id=rel_id[k],
                type=k[0],
                source_entity_id=ent[k[1]],
                target_entity_id=ent[k[2]],
                qualifier=k[3],
                created_at=now,
            )
            for k in new
        ),
        claims=claims,
        extraction_boundaries=boundaries,
    )
    cited = {i for c in claims for i in c.locator_ids} | {
        i for b in boundaries for i in b.locator_ids
    }
    structural = tuple(sorted({w.id for w in words} - cited))
    log.info("pdf rules: %d claims, %d boundaries", len(claims), len(boundaries))
    return Extracted(records=out, document_version_id=vid, structural_locator_ids=structural)
