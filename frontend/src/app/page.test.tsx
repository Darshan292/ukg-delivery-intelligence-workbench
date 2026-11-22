// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Home from "./page";

vi.mock("@/components/GraphView", () => ({ GraphView: () => null }));

afterEach(() => vi.unstubAllGlobals());

async function renderHome(entity?: string | string[]) {
  vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
  render(await Home({ searchParams: Promise.resolve(entity === undefined ? {} : { entity }) }));
}

describe("Home page", () => {
  it("shows the banner and title", async () => {
    await renderHome();
    expect(screen.getByRole("note")).toHaveTextContent("FICTIONAL synthetic data");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Evidence-first impact workbench (working title)",
    );
  });

  it("defaults to RULE-T1", async () => {
    await renderHome();
    expect(screen.getByRole("status")).toHaveTextContent("Loading links for RULE-T1");
  });

  it("reads ?entity=", async () => {
    await renderHome("REQ-T1");
    expect(screen.getByRole("status")).toHaveTextContent("Loading links for REQ-T1");
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe("/api/impact?entity=REQ-T1");
  });

  it("uses the first value when entity is repeated", async () => {
    await renderHome(["A", "B"]);
    expect(screen.getByRole("status")).toHaveTextContent("Loading links for A");
  });
});
