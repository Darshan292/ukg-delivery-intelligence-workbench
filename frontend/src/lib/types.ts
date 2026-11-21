// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

export type LocatorOut = {
  kind: string;
  locator: Record<string, string>;
  snippet: string;
};

export type GraphNode = {
  id: string;
  label: string;
  entity_type: string;
  role: "seed" | "linked";
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  locator: LocatorOut;
};

export type ImpactResponse = {
  entity: string;
  fictional: true;
  notice: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};
