// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import fixture from "@/lib/__fixtures__/impact.json";
import type { GraphEdge } from "@/lib/types";
import { EvidencePanel } from "./EvidencePanel";

const edge = fixture.edges[0] as GraphEdge;

describe("EvidencePanel", () => {
  it("is a region named Evidence with the prompt when nothing is selected", () => {
    render(<EvidencePanel edge={undefined} />);
    expect(screen.getByRole("region", { name: "Evidence" })).toHaveTextContent(
      "Select a link in the graph or the list to see where it comes from.",
    );
  });

  it("shows the citation breadcrumb, snippet and fake-locator tag", () => {
    render(<EvidencePanel edge={edge} />);
    expect(screen.getByRole("heading", { name: "Evidence for this link" })).toBeInTheDocument();
    expect(screen.getByText("tracer-fixture.xlsx › Links › B2")).toBeInTheDocument();
    expect(screen.getByText(edge.locator.snippet)).toBeInTheDocument();
    expect(screen.getByText("Fake locator: no real file behind it")).toBeInTheDocument();
  });

  it("renders a hostile snippet as literal text and creates no img", () => {
    const hostile = "<img src=x onerror=alert(1)>";
    const { container } = render(
      <EvidencePanel edge={{ ...edge, locator: { ...edge.locator, snippet: hostile } }} />,
    );
    expect(screen.getByText(hostile)).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });
});
