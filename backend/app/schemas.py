# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""API response models (tracer contract)."""

from typing import Literal

from pydantic import BaseModel


class LocatorOut(BaseModel):
    kind: str
    locator: dict[str, str]
    snippet: str


class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    role: Literal["seed", "linked"]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    locator: LocatorOut


class NeighbourhoodResponse(BaseModel):
    entity: str
    fictional: Literal[True]
    notice: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class KeyTriple(BaseModel):
    product_profile: str
    entity_type: str
    natural_key: str


class ReviewClaimOut(BaseModel):
    id: int
    basis: str
    polarity: str
    method: str
    confidence: str | None
    scope_snapshot_id: int | None
    live: bool
    locators: list[LocatorOut]


class ReviewItem(BaseModel):
    relationship_id: int
    type: str
    qualifier: str | None
    source: KeyTriple
    target: KeyTriple
    scoped: bool  # tells the client whether a verdict needs snapshot_id
    state: str
    label: str | None
    flags: list[str]
    conflict_kinds: list[str]
    claims: list[ReviewClaimOut]


class ReviewItemsResponse(BaseModel):
    snapshot_id: int
    items: list[ReviewItem]
