// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import fixture from "@/lib/__fixtures__/impact.json";
import { Workspace } from "./Workspace";

// React Flow needs layout APIs jsdom lacks; the list is the accessible twin and carries the logic under test.
vi.mock("./GraphView", () => ({ GraphView: () => <div data-testid="graph" /> }));

function respond(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("Workspace", () => {
  it("shows loading, then links; selecting a link shows evidence and aria-pressed", async () => {
    respond(200, fixture);
    render(<Workspace entity="RULE-T1" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading links for RULE-T1");

    const first = await screen.findByRole("button", { name: "RULE-T1 implements REQ-T1" });
    expect(screen.getByRole("heading", { name: "Links (2)" })).toBeInTheDocument();
    expect(first).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(first);
    expect(first).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "TEST-T1 verifies RULE-T1" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("region", { name: "Evidence" })).toHaveTextContent("tracer-fixture.xlsx › Links › B2");
    expect(screen.getByText(/This is not impact analysis/)).toBeInTheDocument();
  });

  it("shows the 404 message as an alert and no stale graph", async () => {
    respond(404, { detail: "entity not found" });
    render(<Workspace entity="NOPE" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No entity with key NOPE. Check the key in the address (?entity=...).",
    );
    expect(screen.queryByTestId("graph")).toBeNull();
  });

  it("shows the empty state when there are no edges", async () => {
    respond(200, { ...fixture, edges: [] });
    render(<Workspace entity="RULE-T1" />);
    await waitFor(() => expect(screen.getByText((_, el) => el?.tagName === "P" && el.textContent === "RULE-T1 has no stored links yet.")).toBeInTheDocument());
  });

  it("drops the previous graph when the entity changes", async () => {
    respond(200, fixture);
    const { rerender } = render(<Workspace entity="RULE-T1" />);
    await screen.findByTestId("graph");
    respond(404, {});
    rerender(<Workspace entity="NOPE" />);
    expect(screen.queryByTestId("graph")).toBeNull();
    await screen.findByRole("alert");
  });
});
