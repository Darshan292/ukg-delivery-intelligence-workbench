// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import fixture from "@/lib/__fixtures__/impact.json";
import type { ImpactResponse } from "@/lib/types";
import { GraphView } from "./GraphView";

// Capture what GraphView hands to React Flow; jsdom cannot lay it out.
vi.mock("@xyflow/react", () => ({
  MarkerType: { ArrowClosed: "arrowclosed" },
  Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
  Handle: () => null,
  ReactFlow: (p: { nodes: { position: { x: number; y: number } }[] }) => (
    <div data-testid="rf">{JSON.stringify(p.nodes.map((n) => n.position))}</div>
  ),
}));

afterEach(() => vi.unstubAllGlobals());

function mockMedia(matches: boolean) {
  const add = vi.fn();
  const remove = vi.fn();
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches, addEventListener: add, removeEventListener: remove }));
  return { add, remove };
}

const renderIt = () =>
  render(<GraphView data={fixture as ImpactResponse} selectedId={undefined} onSelect={() => {}} />);

describe("GraphView orientation", () => {
  it("is vertical when the narrow media query matches", () => {
    mockMedia(true);
    renderIt();
    const pos = JSON.parse(screen.getByTestId("rf").textContent ?? "[]");
    expect(pos.map((p: { x: number }) => p.x)).toEqual([0, 0, 0]);
  });

  it("is horizontal otherwise", () => {
    mockMedia(false);
    renderIt();
    const pos = JSON.parse(screen.getByTestId("rf").textContent ?? "[]");
    expect(pos.map((p: { y: number }) => p.y)).toEqual([0, 0, 0]);
  });

  it("defaults to horizontal without matchMedia", () => {
    renderIt();
    const pos = JSON.parse(screen.getByTestId("rf").textContent ?? "[]");
    expect(pos.map((p: { y: number }) => p.y)).toEqual([0, 0, 0]);
  });

  it("removes its listener on unmount", () => {
    const m = mockMedia(false);
    renderIt().unmount();
    expect(m.add).toHaveBeenCalled();
    expect(m.remove).toHaveBeenCalled();
  });
});
