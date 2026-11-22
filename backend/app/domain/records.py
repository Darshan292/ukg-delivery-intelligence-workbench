# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""`Records`: the append-only container. Cross-record rules are checked on construction.

Error messages name the rule, the record kind and the id only; never an input string.
"""

from collections.abc import Callable, Iterable, Mapping
from functools import cached_property
from typing import Any, Final, Self

from pydantic import model_validator

from app.domain.locators import EvidenceLocator, content_key
from app.domain.model import (
    SAME_AS,
    Actor,
    Catalogue,
    Claim,
    ClaimReviewEvent,
    Document,
    DocumentVersion,
    Entity,
    EntityTypeSpec,
    EntityVersion,
    ProductProfile,
    Record,
    Relationship,
    RelationshipReviewEvent,
    ReviewEvent,
    Snapshot,
    UnresolvedReference,
    normalise_key_v1,
)


def _fail(rule: str, kind: str, i: int) -> ValueError:
    return ValueError(f"{rule}: {kind} id {i}")


class Records(Record):
    catalogues: tuple[Catalogue, ...] = ()
    actors: tuple[Actor, ...] = ()
    snapshots: tuple[Snapshot, ...] = ()
    documents: tuple[Document, ...] = ()
    document_versions: tuple[DocumentVersion, ...] = ()
    locators: tuple[EvidenceLocator, ...] = ()
    entities: tuple[Entity, ...] = ()
    entity_versions: tuple[EntityVersion, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    claims: tuple[Claim, ...] = ()
    review_events: tuple[ReviewEvent, ...] = ()
    unresolved_references: tuple[UnresolvedReference, ...] = ()

    @model_validator(mode="after")
    def _validate(self) -> Self:
        for check in _CHECKS:
            check(self)
        return self

    @cached_property
    def actor_by_id(self) -> dict[int, Actor]:
        return {x.id: x for x in self.actors}

    @cached_property
    def snapshot_by_id(self) -> dict[int, Snapshot]:
        return {x.id: x for x in self.snapshots}

    @cached_property
    def document_by_id(self) -> dict[int, Document]:
        return {x.id: x for x in self.documents}

    @cached_property
    def version_by_id(self) -> dict[int, DocumentVersion]:
        return {x.id: x for x in self.document_versions}

    @cached_property
    def locator_by_id(self) -> dict[int, EvidenceLocator]:
        return {x.id: x for x in self.locators}

    @cached_property
    def entity_by_id(self) -> dict[int, Entity]:
        return {x.id: x for x in self.entities}

    @cached_property
    def relationship_by_id(self) -> dict[int, Relationship]:
        return {x.id: x for x in self.relationships}

    @cached_property
    def claim_by_id(self) -> dict[int, Claim]:
        return {x.id: x for x in self.claims}

    @cached_property
    def catalogue_by_profile(self) -> dict[ProductProfile, Catalogue]:
        return {x.product_profile: x for x in self.catalogues}

    @cached_property
    def claims_by_relationship(self) -> dict[int, tuple[Claim, ...]]:
        out: dict[int, list[Claim]] = {}
        for c in sorted(self.claims, key=lambda c: c.id):
            out.setdefault(c.relationship_id, []).append(c)
        return {k: tuple(v) for k, v in out.items()}

    @cached_property
    def claim_events_by_claim(self) -> dict[int, tuple[ClaimReviewEvent, ...]]:
        out: dict[int, list[ClaimReviewEvent]] = {}
        for e in sorted(self.review_events, key=lambda e: (e.at, e.id)):
            if e.target_kind == "claim":
                out.setdefault(e.claim_id, []).append(e)
        return {k: tuple(v) for k, v in out.items()}

    @cached_property
    def relationship_events_by_relationship(self) -> dict[int, tuple[RelationshipReviewEvent, ...]]:
        out: dict[int, list[RelationshipReviewEvent]] = {}
        for e in sorted(self.review_events, key=lambda e: (e.at, e.id)):
            if e.target_kind == "relationship":
                out.setdefault(e.relationship_id, []).append(e)
        return {k: tuple(v) for k, v in out.items()}

    @cached_property
    def superseded_version_ids(self) -> frozenset[int]:
        return frozenset(
            v.supersedes_version_id for v in self.document_versions if v.supersedes_version_id
        )

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        raise TypeError("Records is append-only: use extended()")

    def extended(self, **more: tuple[object, ...]) -> Self:
        """Append records and re-validate everything (an in-place copy would skip the checks)."""
        unknown = set(more) - set(Records.model_fields)
        if unknown:
            raise TypeError("extended: unknown record field")
        return type(self).model_validate(
            {f: getattr(self, f) + more.get(f, ()) for f in Records.model_fields}
        )

    def relationship_profile(self, rel: Relationship) -> ProductProfile:
        """The endpoint profile that is not `unknown`, else `unknown`."""
        for e in (self.entity_by_id[rel.source_entity_id], self.entity_by_id[rel.target_entity_id]):
            if e.product_profile != "unknown":
                return e.product_profile
        return "unknown"

    def entity_spec(self, entity: Entity) -> EntityTypeSpec | None:
        """None for the `unknown` profile (its types are not validated)."""
        cat = self.catalogue_by_profile.get(entity.product_profile)
        if cat is None:
            return None
        return next((t for t in cat.entity_types if t.name == entity.entity_type), None)


def is_scoped(r: Records, rel: Relationship) -> bool:
    """Both endpoint types are snapshot-scoped. An `unknown`-profile endpoint counts as scoped."""
    # owner question Q7 (pending): unknown endpoints count as snapshot-scoped (conservative)
    for e in (r.entity_by_id[rel.source_entity_id], r.entity_by_id[rel.target_entity_id]):
        spec = r.entity_spec(e)
        if spec is not None and not spec.snapshot_scoped:
            return False
    return True


def _ids(r: Records) -> None:
    groups: list[tuple[str, Iterable[int]]] = [
        ("actor", (x.id for x in r.actors)),
        ("snapshot", (x.id for x in r.snapshots)),
        ("document", (x.id for x in r.documents)),
        ("document_version", (x.id for x in r.document_versions)),
        ("locator", (x.id for x in r.locators)),
        ("entity", (x.id for x in r.entities)),
        ("entity_version", (x.id for x in r.entity_versions)),
        ("relationship", (x.id for x in r.relationships)),
        ("claim", (x.id for x in r.claims)),
        ("review_event", (x.id for x in r.review_events)),  # one id space for both targets
        ("unresolved_reference", (x.id for x in r.unresolved_references)),
    ]
    for kind, ids in groups:
        seen: set[int] = set()
        for i in ids:
            if i in seen:
                raise _fail("ids: duplicate", kind, i)
            seen.add(i)


def _references(r: Records) -> None:
    def need(ok: bool, kind: str, i: int) -> None:
        if not ok:
            raise _fail("references: dangling", kind, i)

    for v in r.document_versions:
        need(v.document_id in r.document_by_id, "document_version", v.id)
        need(v.snapshot_id is None or v.snapshot_id in r.snapshot_by_id, "document_version", v.id)
        need(v.declared_by in r.actor_by_id, "document_version", v.id)
        need(
            v.supersedes_version_id is None or v.supersedes_version_id in r.version_by_id,
            "document_version",
            v.id,
        )
    for loc in r.locators:
        need(loc.document_version_id in r.version_by_id, "locator", loc.id)
    for ev in r.entity_versions:
        need(ev.entity_id in r.entity_by_id, "entity_version", ev.id)
        need(ev.document_version_id in r.version_by_id, "entity_version", ev.id)
        need(
            all(
                i in r.locator_by_id
                for i in (*ev.locator_ids, *(a.locator_id for a in ev.attributes))
            ),
            "entity_version",
            ev.id,
        )
    for rel in r.relationships:
        need(
            rel.source_entity_id in r.entity_by_id and rel.target_entity_id in r.entity_by_id,
            "relationship",
            rel.id,
        )
    for c in r.claims:
        need(c.relationship_id in r.relationship_by_id, "claim", c.id)
        need(all(i in r.locator_by_id for i in c.locator_ids), "claim", c.id)
    for e in r.review_events:
        need(e.actor_id in r.actor_by_id, "review_event", e.id)
        if e.target_kind == "claim":
            need(e.claim_id in r.claim_by_id, "review_event", e.id)
        else:
            need(e.relationship_id in r.relationship_by_id, "review_event", e.id)
            need(
                e.successor_relationship_id is None
                or e.successor_relationship_id in r.relationship_by_id,
                "review_event",
                e.id,
            )
    for u in r.unresolved_references:
        need(u.holder_entity_id in r.entity_by_id, "unresolved_reference", u.id)
        need(u.locator_id in r.locator_by_id, "unresolved_reference", u.id)


def _unique(rule: str, kind: str, items: Iterable[tuple[object, int]]) -> None:
    seen: set[object] = set()
    for key, i in items:
        if key in seen:
            raise _fail(f"uniqueness: {rule}", kind, i)
        seen.add(key)


def _uniqueness(r: Records) -> None:
    _unique("entity key", "entity", ((e.key, e.id) for e in r.entities))
    _unique("relationship key", "relationship", ((x.key, x.id) for x in r.relationships))
    _unique(
        "entity version",
        "entity_version",
        (((v.entity_id, v.document_version_id), v.id) for v in r.entity_versions),
    )
    _unique("sha256", "document_version", ((v.sha256, v.id) for v in r.document_versions))
    _unique(
        "successor",
        "document_version",
        ((v.supersedes_version_id, v.id) for v in r.document_versions if v.supersedes_version_id),
    )
    _unique("locator content_key", "locator", ((content_key(x), x.id) for x in r.locators))
    _unique("claim dedup_key", "claim", ((c.dedup_key, c.id) for c in r.claims))


def _catalogue(r: Records) -> None:
    _unique("profile", "catalogue", ((c.product_profile, i) for i, c in enumerate(r.catalogues, 1)))
    for e in r.entities:
        if e.product_profile != "unknown" and r.entity_spec(e) is None:
            raise _fail("catalogue: entity type", "entity", e.id)
    for rel in r.relationships:
        profile = r.relationship_profile(rel)
        if profile == "unknown":
            # owner question Q7 (pending): unknown-to-unknown edges rejected (no catalogue to type them)  # noqa: E501
            raise _fail("catalogue: relationship between unknown entities", "relationship", rel.id)
        cat = r.catalogue_by_profile.get(profile)
        spec = (
            next((t for t in cat.relationship_types if t.name == rel.type), None) if cat else None
        )
        if spec is None:
            raise _fail("catalogue: relationship type", "relationship", rel.id)
        if spec.qualifier_required != (rel.qualifier is not None):
            raise _fail("catalogue: qualifier", "relationship", rel.id)


def _profiles(r: Records) -> None:
    for v in r.document_versions:
        if v.snapshot_id is not None and (
            r.snapshot_by_id[v.snapshot_id].product_profile
            != r.document_by_id[v.document_id].product_profile
        ):
            raise _fail("profiles: document version snapshot", "document_version", v.id)
    for ev in r.entity_versions:
        doc = r.document_by_id[r.version_by_id[ev.document_version_id].document_id]
        if r.entity_by_id[ev.entity_id].product_profile not in (doc.product_profile, "unknown"):
            raise _fail("profiles: entity version", "entity_version", ev.id)
    for rel in r.relationships:
        a = r.entity_by_id[rel.source_entity_id].product_profile
        b = r.entity_by_id[rel.target_entity_id].product_profile
        # owner question Q7 (pending): endpoints share a profile unless one is `unknown`
        if a != b and "unknown" not in (a, b):
            raise _fail("profiles: relationship endpoints", "relationship", rel.id)


def _same_as(r: Records) -> None:
    for rel in r.relationships:
        if rel.type != SAME_AS:
            continue
        s, t = r.entity_by_id[rel.source_entity_id], r.entity_by_id[rel.target_entity_id]
        if (s.product_profile, s.entity_type) != (t.product_profile, t.entity_type) or not (
            s.natural_key < t.natural_key
        ):
            raise _fail("same_as: profile, type and key order", "relationship", rel.id)


def _lineage(r: Records) -> None:
    for v in r.document_versions:
        if v.supersedes_version_id is None:
            continue
        old = r.version_by_id[v.supersedes_version_id]
        if r.actor_by_id[v.declared_by].kind != "human":
            raise _fail("lineage: declarer must be human", "document_version", v.id)
        if old.document_id != v.document_id:
            raise _fail("lineage: document differs", "document_version", v.id)
        if old.snapshot_id != v.snapshot_id:
            raise _fail("lineage: snapshot differs", "document_version", v.id)


def _entity_versions(r: Records) -> None:
    for ev in r.entity_versions:
        dv = r.version_by_id[ev.document_version_id]
        if ev.snapshot_id != dv.snapshot_id:
            raise _fail(
                "entity_version: snapshot differs from its version", "entity_version", ev.id
            )
        if any(r.locator_by_id[i].document_version_id != dv.id for i in ev.locator_ids):
            raise _fail("entity_version: locator in another version", "entity_version", ev.id)


def _claim_scope(r: Records) -> None:
    for c in r.claims:
        scopes = {
            r.version_by_id[r.locator_by_id[i].document_version_id].snapshot_id
            for i in c.locator_ids
        }
        if len(scopes) > 1 and None in scopes:
            # owner Q5: reject mixing scoped and unscoped locators
            raise _fail("claim: mixed scoped and unscoped locators", "claim", c.id)
        if len(scopes) > 1:
            raise _fail("claim: locators span more than one snapshot", "claim", c.id)
        if c.scope_snapshot_id not in scopes:
            raise _fail("claim: scope differs from locator snapshot", "claim", c.id)


def _review_events(r: Records) -> None:
    for e in r.review_events:
        if not r.actor_by_id[e.actor_id].is_reviewer:
            raise _fail("review: actor is not a human reviewer", "review_event", e.id)
        if e.target_kind == "claim":
            continue
        rel = r.relationship_by_id[e.relationship_id]
        if is_scoped(r, rel):
            snap = None if e.scope_snapshot_id is None else r.snapshot_by_id[e.scope_snapshot_id]
            if snap is None or snap.product_profile != r.relationship_profile(rel):
                raise _fail(
                    "review: scope must name a snapshot of the profile", "review_event", e.id
                )
        elif e.scope_snapshot_id is not None:
            raise _fail(
                "review: scope must be null for unscoped relationship", "review_event", e.id
            )
        if e.successor_relationship_id is not None and (
            r.relationship_by_id[e.successor_relationship_id].source_entity_id
            != rel.source_entity_id
        ):
            raise _fail("review: successor must share the source entity", "review_event", e.id)


_CHECKS: Final[tuple[Callable[[Records], None], ...]] = (
    _ids,
    _references,
    _uniqueness,
    _catalogue,
    _profiles,
    _same_as,
    _lineage,
    _entity_versions,
    _claim_scope,
    _review_events,
)


class EntityNotFound(LookupError):
    """No entity matches. Carries no input: the queried key is untrusted."""


class AmbiguousEntity(LookupError):
    """More than one entity matches; candidates are store data (sorted key triples)."""

    def __init__(self, candidates: tuple[tuple[str, str, str], ...]) -> None:
        super().__init__(candidates)
        self.candidates = candidates

    def __str__(self) -> str:
        return f"ambiguous entity: {len(self.candidates)} candidates"


def resolve_entity(
    r: Records,
    natural_key: str,
    *,
    product_profile: ProductProfile | None = None,
    entity_type: str | None = None,
) -> Entity:
    key = normalise_key_v1(natural_key)
    hits = [
        e
        for e in r.entities
        if e.natural_key == key
        and product_profile in (None, e.product_profile)
        and entity_type in (None, e.entity_type)
    ]
    if not hits:
        raise EntityNotFound
    if len(hits) > 1:
        raise AmbiguousEntity(tuple(sorted(e.key for e in hits)))
    return hits[0]
