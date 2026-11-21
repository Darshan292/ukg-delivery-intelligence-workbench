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


class ImpactResponse(BaseModel):
    entity: str
    fictional: Literal[True]
    notice: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
