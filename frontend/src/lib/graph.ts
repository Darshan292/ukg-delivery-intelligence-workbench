// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import type { Edge, Node } from "@xyflow/react";

import type { NeighbourhoodResponse, LocatorOut } from "./types";

export type NodeData = {
  entityKey: string;
  entityType: string;
  seed: boolean;
  [k: string]: unknown;
};
export type EdgeData = { locator: LocatorOut; [k: string]: unknown };

export const VSTEP = 110;

const byId = (a: { id: string }, b: { id: string }) =>
  a.id < b.id ? -1 : a.id > b.id ? 1 : 0;

// shortcut: one column per node in id order, fine for the 3-node tracer; use a layout engine in Slice 1.
export type Orientation = "horizontal" | "vertical";

export function toFlow(
  resp: NeighbourhoodResponse,
  orientation: Orientation = "horizontal",
): {
  nodes: Node<NodeData>[];
  edges: Edge<EdgeData>[];
} {
  const vertical = orientation === "vertical";
  const nodes = [...resp.nodes].sort(byId).map((n, i) => ({
    id: n.id,
    type: "entity",
    position: vertical ? { x: 0, y: i * VSTEP } : { x: i * 210, y: 0 },
    data: {
      entityKey: n.id,
      entityType: n.entity_type,
      seed: n.role === "seed",
    },
    draggable: false,
    connectable: false,
  }));
  const x = new Map(nodes.map((n) => [n.id, vertical ? n.position.y : n.position.x]));
  const edges = [...resp.edges].sort(byId).map((e) => {
    // Layout is left to right, stored direction is kept: a backwards link leaves from the left side of its source.
    const forward = (x.get(e.source) ?? 0) <= (x.get(e.target) ?? 0);
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: forward ? (vertical ? "out-b" : "out-r") : vertical ? "out-t" : "out-l",
      targetHandle: forward ? (vertical ? "in-t" : "in-l") : vertical ? "in-b" : "in-r",
      label: e.type,
      data: { locator: e.locator },
    };
  });
  return { nodes, edges };
}
