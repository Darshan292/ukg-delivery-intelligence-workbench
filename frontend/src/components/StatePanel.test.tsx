// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatePanel } from "./StatePanel";

describe("StatePanel", () => {
  it("loading is a status", () => {
    render(<StatePanel kind="loading" entity="RULE-T1" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading links for RULE-T1");
  });

  it("error is an alert carrying the message", () => {
    render(<StatePanel kind="error" entity="X" message="The API is not reachable. Start the backend and reload." />);
    expect(screen.getByRole("alert")).toHaveTextContent("The API is not reachable. Start the backend and reload.");
  });

  it("empty names the entity", () => {
    render(<StatePanel kind="empty" entity="RULE-T1" />);
    expect(screen.getByText((_, el) => el?.tagName === "P" && el.textContent === "RULE-T1 has no stored links yet.")).toBeInTheDocument();
  });
});
