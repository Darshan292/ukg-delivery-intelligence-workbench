# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Save and load `Records`. The domain validates every load; SQL repeats only the RM rules.

Ids are the domain ids (writer-supplied, owner question S5-Q7). Review events are the
exception: the database assigns `id` and `at`, so they are inserted one per statement in
(at, id) order and without those columns. Insert order is the only ordering that survives.
"""

from collections.abc import Collection
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import Connection, insert, select
from sqlalchemy.orm import DeclarativeBase

from app import models as m
from app.domain import model as d
from app.domain.locators import LOCATOR_ADAPTER, EvidenceLocator
from app.domain.records import Records

ALL: Final = tuple(Records.model_fields)  # already in FK order: catalogues ... unresolved refs

_LOC_COLUMNS = ("id", "document_version_id", "kind", "snippet", "extractor", "extracted_at")


def _encode(v: d.JsonScalar) -> Any:
    # tagged decimal: a JSON number would round-trip through float (decision 0003 Q10)
    return {"n": str(v)} if isinstance(v, Decimal) else v


def _decode(v: Any) -> d.JsonScalar:
    return Decimal(v["n"]) if isinstance(v, dict) else v  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]


def _lineage_order(versions: tuple[d.DocumentVersion, ...]) -> list[d.DocumentVersion]:
    """Predecessors first, so the self-referencing FK holds row by row."""
    by_id = {v.id: v for v in versions}

    def depth(v: d.DocumentVersion) -> int:
        return 0 if v.supersedes_version_id is None else 1 + depth(by_id[v.supersedes_version_id])

    return sorted(versions, key=lambda v: (depth(v), v.id))


def _rows(r: Records, field: str) -> list[dict[str, Any]]:
    # columns equal the model fields, except where noted
    match field:
        case "catalogues":
            return []  # handled in save()
        case "document_versions":
            return [v.model_dump() for v in _lineage_order(r.document_versions)]
        case "locators":
            out: list[dict[str, Any]] = []
            for loc in r.locators:
                full = loc.model_dump(mode="json")
                row = {k: getattr(loc, k) for k in _LOC_COLUMNS}
                row["locator"] = {k: v for k, v in full.items() if k not in _LOC_COLUMNS}
                out.append(row)
            return out
        case "entity_versions":
            return [
                {
                    **ev.model_dump(exclude={"attributes", "locator_ids"}),
                    "locator_ids": list(ev.locator_ids),
                    "attributes": [
                        {"name": a.name, "value": _encode(a.value), "locator_id": a.locator_id}
                        for a in ev.attributes
                    ],
                }
                for ev in r.entity_versions
            ]
        case "claims":
            return [
                {
                    **c.model_dump(exclude={"locator_ids"}),
                    "locator_ids": list(c.locator_ids),
                }
                for c in r.claims
            ]
        case "actors":
            return [{**a.model_dump(exclude={"roles"}), "roles": sorted(a.roles)} for a in r.actors]
        case _:
            return [x.model_dump() for x in getattr(r, field)]


_TABLE: Final[dict[str, type[DeclarativeBase]]] = {
    "actors": m.Actor,
    "snapshots": m.Snapshot,
    "documents": m.Document,
    "document_versions": m.DocumentVersion,
    "locators": m.EvidenceLocator,
    "entities": m.Entity,
    "entity_versions": m.EntityVersion,
    "relationships": m.Relationship,
    "claims": m.Claim,
    "unresolved_references": m.UnresolvedReference,
}


def save(conn: Connection, r: Records, fields: Collection[str] = ALL) -> None:
    for field in ALL:  # Records field order is FK order
        if field not in fields:
            continue
        if field == "catalogues":
            _save_catalogues(conn, r)
        elif field == "review_events":
            # (at, id) order; one statement per row; id and at are never client-supplied
            for e in sorted(r.review_events, key=lambda e: (e.at, e.id)):
                row = e.model_dump(exclude={"id", "at"})
                conn.execute(insert(m.ReviewEvent), row)
        elif rows := _rows(r, field):
            conn.execute(insert(_TABLE[field]), rows)


def _save_catalogues(conn: Connection, r: Records) -> None:
    # an empty catalogue (no types) stores nothing: no entity could use it
    ets = [
        {
            "product_profile": c.product_profile,
            "name": t.name,
            "snapshot_scoped": t.snapshot_scoped,
            "display_only_attributes": list(t.display_only_attributes),
        }
        for c in r.catalogues
        for t in c.entity_types
    ]
    rts = [
        {
            "product_profile": c.product_profile,
            "name": t.name,
            "qualifier_required": t.qualifier_required,
            "single_valued_for": [list(p) for p in t.single_valued_for],
        }
        for c in r.catalogues
        for t in c.relationship_types
    ]
    if ets:
        conn.execute(insert(m.CatalogueEntityType), ets)
    if rts:
        conn.execute(insert(m.CatalogueRelationshipType), rts)


def _all(conn: Connection, model: type[DeclarativeBase], *order: Any) -> list[dict[str, Any]]:
    # shortcut: reads every row; fine at M1 synthetic scale (unmeasured), use scoped queries
    # when Slice 6 measures
    return [dict(x._mapping) for x in conn.execute(select(model).order_by(*order))]  # pyright: ignore[reportPrivateUsage]


def _catalogues(conn: Connection) -> tuple[d.Catalogue, ...]:
    ets = _all(
        conn,
        m.CatalogueEntityType,
        m.CatalogueEntityType.product_profile,
        m.CatalogueEntityType.name,
    )
    rts = _all(
        conn,
        m.CatalogueRelationshipType,
        m.CatalogueRelationshipType.product_profile,
        m.CatalogueRelationshipType.name,
    )
    profiles = sorted({x["product_profile"] for x in (*ets, *rts)})
    return tuple(
        d.Catalogue(
            product_profile=p,
            entity_types=tuple(
                d.EntityTypeSpec(
                    name=x["name"],
                    snapshot_scoped=x["snapshot_scoped"],
                    display_only_attributes=tuple(x["display_only_attributes"]),
                )
                for x in ets
                if x["product_profile"] == p
            ),
            relationship_types=tuple(
                d.RelationshipTypeSpec(
                    name=x["name"],
                    qualifier_required=x["qualifier_required"],
                    single_valued_for=tuple((a, b) for a, b in x["single_valued_for"]),
                )
                for x in rts
                if x["product_profile"] == p
            ),
        )
        for p in profiles
    )


def _locator(row: dict[str, Any]) -> EvidenceLocator:
    extra = row.pop("locator")
    return LOCATOR_ADAPTER.validate_python({**row, **extra})


def _event(row: dict[str, Any]) -> d.ReviewEvent:
    if row["target_kind"] == "claim":
        keep = ("id", "at", "actor_id", "target_kind", "claim_id", "verdict", "reason")
        return d.ClaimReviewEvent.model_validate({k: row[k] for k in keep})
    drop = ("claim_id",)
    return d.RelationshipReviewEvent.model_validate({k: v for k, v in row.items() if k not in drop})


def load(conn: Connection) -> Records:
    """Everything, re-validated by the domain (a stored row the domain refuses raises)."""

    def by_id(model: type[DeclarativeBase]) -> list[dict[str, Any]]:
        return _all(conn, model, model.id)  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]

    def build(cls: Any, model: type[DeclarativeBase], **tuples: str) -> tuple[Any, ...]:
        out: list[Any] = []
        for row in by_id(model):
            for col in tuples:
                row[col] = tuple(row[col])
            out.append(cls.model_validate(row))
        return tuple(out)

    entity_versions = tuple(
        d.EntityVersion(
            id=row["id"],
            entity_id=row["entity_id"],
            document_version_id=row["document_version_id"],
            snapshot_id=row["snapshot_id"],
            attributes=tuple(
                d.Attribute(name=a["name"], value=_decode(a["value"]), locator_id=a["locator_id"])
                for a in row["attributes"]
            ),
            locator_ids=tuple(row["locator_ids"]),
        )
        for row in by_id(m.EntityVersion)
    )
    actors = tuple(
        d.Actor(
            id=a["id"], kind=a["kind"], display_name=a["display_name"], roles=frozenset(a["roles"])
        )
        for a in by_id(m.Actor)
    )
    entities = tuple(
        d.Entity.model_validate(
            {k: row[k] for k in ("id", "product_profile", "entity_type", "natural_key")}
        )
        for row in by_id(m.Entity)
    )
    claims = tuple(
        d.Claim.model_validate(
            {
                k: (tuple(v) if k == "locator_ids" else v)
                for k, v in row.items()
                if k != "locator_set_hash"
            }
        )
        for row in by_id(m.Claim)
    )
    return Records(
        catalogues=_catalogues(conn),
        actors=actors,
        snapshots=build(d.Snapshot, m.Snapshot),
        documents=build(d.Document, m.Document),
        document_versions=build(d.DocumentVersion, m.DocumentVersion),
        locators=tuple(_locator(row) for row in by_id(m.EvidenceLocator)),
        entities=entities,
        entity_versions=entity_versions,
        relationships=build(d.Relationship, m.Relationship),
        claims=claims,
        review_events=tuple(_event(row) for row in by_id(m.ReviewEvent)),
        unresolved_references=build(d.UnresolvedReference, m.UnresolvedReference),
    )
