// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { describe, expect, it } from "vitest";

import fixture from "./__fixtures__/impact.json";
import { toFlow } from "./graph";
import type { ImpactResponse } from "./types";

const resp = fixture as ImpactResponse;

describe("toFlow", () => {
  it("maps nodes and edges and marks the seed", () => {
    const { nodes, edges } = toFlow(resp);
    expect(nodes.map((n) => n.id)).toEqual(["REQ-T1", "RULE-T1", "TEST-T1"]);
    expect(nodes.find((n) => n.id === "RULE-T1")?.data.seed).toBe(true);
    expect(nodes.find((n) => n.id === "REQ-T1")?.data.seed).toBe(false);
    expect(edges).toHaveLength(2);
    expect(edges[0]).toMatchObject({
      id: "RULE-T1|implements|REQ-T1",
      source: "RULE-T1",
      target: "REQ-T1",
      label: "implements",
    });
    expect(edges[0].data?.locator).toEqual(resp.edges[0].locator);
  });

  it("keeps stored direction by choosing the handle side", () => {
    const { edges } = toFlow(resp);
    expect(edges[0]).toMatchObject({ source: "RULE-T1", target: "REQ-T1", sourceHandle: "out-l", targetHandle: "in-r" });
    expect(edges[1]).toMatchObject({ source: "TEST-T1", target: "RULE-T1", sourceHandle: "out-l", targetHandle: "in-r" });
  });

  it("is deterministic for shuffled input", () => {
    const shuffled: ImpactResponse = {
      ...resp,
      nodes: [...resp.nodes].reverse(),
      edges: [...resp.edges].reverse(),
    };
    expect(toFlow(shuffled)).toEqual(toFlow(resp));
  });

  it("lays nodes out left to right", () => {
    const xs = toFlow(resp).nodes.map((n) => n.position.x);
    expect(xs).toEqual([...xs].sort((a, b) => a - b));
    expect(new Set(xs).size).toBe(3);
  });
});
