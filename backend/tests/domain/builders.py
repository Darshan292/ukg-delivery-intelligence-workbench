# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only builder with auto ids. FICTIONAL: not UKG behaviour.

Mutable on purpose; `build()` goes through `Records` so nothing bypasses validation.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domain.locators import EvidenceLocator, XlsxCell
from app.domain.model import (
    Actor,
    Attribute,
    Basis,
    Catalogue,
    Claim,
    ClaimReviewEvent,
    Document,
    DocumentVersion,
    Entity,
    EntityTypeSpec,
    EntityVersion,
    JsonScalar,
    Polarity,
    ProductProfile,
    Relationship,
    RelationshipReviewEvent,
    RelationshipTypeSpec,
    ReviewEvent,
    Snapshot,
    UnresolvedReference,
)
from app.domain.records import Records

# FICTIONAL: not UKG behaviour.
CATALOGUE = Catalogue(
    product_profile="synthetic",
    entity_types=(
        EntityTypeSpec(name="cfg", snapshot_scoped=True, display_only_attributes=("label",)),
        EntityTypeSpec(name="req", snapshot_scoped=False),
    ),
    relationship_types=(
        RelationshipTypeSpec(name="uses", single_valued_for=(("cfg", "cfg"),)),
        RelationshipTypeSpec(name="implements"),
        RelationshipTypeSpec(name="asserts_value", qualifier_required=True),
        RelationshipTypeSpec(name="same_as"),
    ),
)
T0 = datetime(2026, 1, 1, tzinfo=UTC)


class World:
    def __init__(self) -> None:
        self._ids: dict[str, int] = {}
        self._clock = 0
        self.catalogues: list[Catalogue] = [CATALOGUE]
        self.actors: list[Actor] = []
        self.snapshots: list[Snapshot] = []
        self.documents: list[Document] = []
        self.document_versions: list[DocumentVersion] = []
        self.locators: list[EvidenceLocator] = []
        self.entities: list[Entity] = []
        self.entity_versions: list[EntityVersion] = []
        self.relationships: list[Relationship] = []
        self.claims: list[Claim] = []
        self.review_events: list[ReviewEvent] = []
        self.unresolved_references: list[UnresolvedReference] = []
        self._reviewer: Actor | None = None
        self._service: Actor | None = None

    def _id(self, kind: str) -> int:
        self._ids[kind] = self._ids.get(kind, 0) + 1
        return self._ids[kind]

    def _now(self) -> datetime:
        self._clock += 1
        return T0 + timedelta(seconds=self._clock)

    def reviewer(self) -> Actor:
        a = Actor(
            id=self._id("actor"),
            kind="human",
            display_name="Reviewer",
            roles=frozenset({"reviewer"}),
        )
        self.actors.append(a)
        return a

    def service(self) -> Actor:
        a = Actor(id=self._id("actor"), kind="service", display_name="Service", roles=frozenset())
        self.actors.append(a)
        return a

    def default_reviewer(self) -> Actor:
        self._reviewer = self._reviewer or self.reviewer()
        return self._reviewer

    def _default_service(self) -> Actor:
        self._service = self._service or self.service()
        return self._service

    def snapshot(self, label: str, profile: ProductProfile = "synthetic") -> Snapshot:
        s = Snapshot(
            id=self._id("snapshot"),
            product_profile=profile,
            environment="dev",
            label=label,
            captured_at=self._now(),
        )
        self.snapshots.append(s)
        return s

    def _doc_version(
        self,
        title: str,
        snapshot: Snapshot | None,
        profile: ProductProfile = "synthetic",
    ) -> DocumentVersion:
        d = Document(id=self._id("document"), product_profile=profile, title=title)
        self.documents.append(d)
        return self._version_of(d, snapshot, None, self._default_service())

    def _version_of(
        self,
        doc: Document,
        snapshot: Snapshot | None,
        supersedes: DocumentVersion | None,
        by: Actor,
    ) -> DocumentVersion:
        n = self._id("dv")
        dv = DocumentVersion(
            id=n,
            document_id=doc.id,
            sha256=hashlib.sha256(f"doc{n}".encode()).hexdigest(),
            snapshot_id=snapshot.id if snapshot else None,
            supersedes_version_id=supersedes.id if supersedes else None,
            declared_by=by.id,
            uploaded_at=self._now(),
        )
        self.document_versions.append(dv)
        return dv

    def export(self, snapshot: Snapshot) -> DocumentVersion:
        return self._doc_version("export", snapshot, snapshot.product_profile)

    def design(self) -> DocumentVersion:
        return self._doc_version("design", None)

    def new_version(self, dv: DocumentVersion, by: Actor | None = None) -> DocumentVersion:
        doc = next(d for d in self.documents if d.id == dv.document_id)
        snap = next((s for s in self.snapshots if s.id == dv.snapshot_id), None)
        return self._version_of(doc, snap, dv, by or self.default_reviewer())

    def entity(self, type: str, key: str, profile: ProductProfile = "synthetic") -> Entity:  # noqa: A002
        e = Entity(
            id=self._id("entity"), product_profile=profile, entity_type=type, natural_key=key
        )
        self.entities.append(e)
        return e

    def rel(
        self,
        type: str,
        src: Entity,
        tgt: Entity,
        qualifier: str | None = None,  # noqa: A002
    ) -> Relationship:
        r = Relationship(
            id=self._id("relationship"),
            type=type,
            source_entity_id=src.id,
            target_entity_id=tgt.id,
            qualifier=qualifier,
            created_at=self._now(),
        )
        self.relationships.append(r)
        return r

    def locator(self, dv: DocumentVersion) -> XlsxCell:
        n = self._id("locator")
        loc = XlsxCell(
            id=n,
            document_version_id=dv.id,
            snippet=f"v{n}",
            extractor="openpyxl@1",
            extracted_at=self._now(),
            kind="xlsx_cell",
            sheet="S",
            cell=f"A{n}",
        )
        self.locators.append(loc)
        return loc

    def claim(
        self,
        rel: Relationship,
        dv: DocumentVersion,
        basis: Basis = "explicit_source",
        polarity: Polarity = "present",
        confidence: Decimal | None = None,
    ) -> Claim:
        loc = self.locator(dv)
        explicit = basis == "explicit_source"
        c = Claim(
            id=self._id("claim"),
            relationship_id=rel.id,
            basis=basis,
            polarity=polarity,
            method=f"{basis}-m@1",
            confidence=None if explicit else (confidence or Decimal("0.5")),
            model_id="m" if basis == "llm_suggestion" else None,
            prompt_version="p1" if basis == "llm_suggestion" else None,
            scope_snapshot_id=dv.snapshot_id,
            locator_ids=(loc.id,),
            created_at=self._now(),
        )
        self.claims.append(c)
        return c

    def version(self, entity: Entity, dv: DocumentVersion, **attrs: JsonScalar) -> EntityVersion:
        loc = self.locator(dv)
        ev = EntityVersion(
            id=self._id("entity_version"),
            entity_id=entity.id,
            document_version_id=dv.id,
            snapshot_id=dv.snapshot_id,
            attributes=tuple(
                Attribute(name=k, value=v, locator_id=loc.id) for k, v in attrs.items()
            ),
            locator_ids=(loc.id,),
        )
        self.entity_versions.append(ev)
        return ev

    def _rel_event(
        self,
        rel: Relationship,
        scope: Snapshot | None,
        verdict: str,
        reason: str | None,
        successor: Relationship | None,
        by: Actor | None,
    ) -> RelationshipReviewEvent:
        ev = RelationshipReviewEvent.model_validate(
            {
                "id": self._id("event"),
                "at": self._now(),
                "actor_id": (by or self.default_reviewer()).id,
                "target_kind": "relationship",
                "relationship_id": rel.id,
                "scope_snapshot_id": scope.id if scope else None,
                "verdict": verdict,
                "reason": reason,
                "successor_relationship_id": successor.id if successor else None,
            }
        )
        self.review_events.append(ev)
        return ev

    def accept(
        self, rel: Relationship, scope: Snapshot | None, by: Actor | None = None
    ) -> RelationshipReviewEvent:
        return self._rel_event(rel, scope, "accepted", None, None, by)

    def reject(
        self, rel: Relationship, scope: Snapshot | None, reason: str = "r", by: Actor | None = None
    ) -> RelationshipReviewEvent:
        return self._rel_event(rel, scope, "rejected", reason, None, by)

    def supersede(
        self,
        rel: Relationship,
        scope: Snapshot | None,
        successor: Relationship,
        by: Actor | None = None,
    ) -> RelationshipReviewEvent:
        return self._rel_event(rel, scope, "superseded", "r", successor, by)

    def _claim_event(self, claim: Claim, verdict: str, by: Actor | None) -> ClaimReviewEvent:
        ev = ClaimReviewEvent.model_validate(
            {
                "id": self._id("event"),
                "at": self._now(),
                "actor_id": (by or self.default_reviewer()).id,
                "target_kind": "claim",
                "claim_id": claim.id,
                "verdict": verdict,
                "reason": "r",
            }
        )
        self.review_events.append(ev)
        return ev

    def reject_claim(self, claim: Claim, by: Actor | None = None) -> ClaimReviewEvent:
        return self._claim_event(claim, "rejected", by)

    def reinstate_claim(self, claim: Claim, by: Actor | None = None) -> ClaimReviewEvent:
        return self._claim_event(claim, "reinstated", by)

    def build(self) -> Records:
        return Records(
            catalogues=tuple(self.catalogues),
            actors=tuple(self.actors),
            snapshots=tuple(self.snapshots),
            documents=tuple(self.documents),
            document_versions=tuple(self.document_versions),
            locators=tuple(self.locators),
            entities=tuple(self.entities),
            entity_versions=tuple(self.entity_versions),
            relationships=tuple(self.relationships),
            claims=tuple(self.claims),
            review_events=tuple(self.review_events),
            unresolved_references=tuple(self.unresolved_references),
        )


def _next_event(r: Records) -> tuple[int, datetime, int]:
    """(id, at, reviewer actor id) for an event that sorts after every existing one."""
    eid = max((e.id for e in r.review_events), default=0) + 1
    at = max((e.at for e in r.review_events), default=T0 + timedelta(days=365))
    return eid, at + timedelta(seconds=1), next(a.id for a in r.actors if a.is_reviewer)


def with_claim_event(r: Records, claim_id: int, verdict: str) -> Records:
    eid, at, actor = _next_event(r)
    ev = ClaimReviewEvent.model_validate(
        {
            "id": eid, "at": at, "actor_id": actor, "target_kind": "claim",
            "claim_id": claim_id, "verdict": verdict, "reason": "r",
        }
    )  # fmt: skip
    return r.extended(review_events=(ev,))


def with_rel_event(
    r: Records,
    rel_id: int,
    verdict: str,
    scope: int | None,
    successor: int | None = None,
) -> Records:
    eid, at, actor = _next_event(r)
    ev = RelationshipReviewEvent.model_validate(
        {
            "id": eid, "at": at, "actor_id": actor, "target_kind": "relationship",
            "relationship_id": rel_id, "scope_snapshot_id": scope, "verdict": verdict,
            "reason": None if verdict == "accepted" else "r",
            "successor_relationship_id": successor,
        }
    )  # fmt: skip
    return r.extended(review_events=(ev,))
