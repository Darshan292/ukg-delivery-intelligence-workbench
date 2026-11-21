// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FictionalBanner } from "./FictionalBanner";

const DEFAULT_TEXT =
  "FICTIONAL synthetic data. Not UKG behaviour. Independent community project, not affiliated with UKG Inc.";

describe("FictionalBanner", () => {
  it("renders the fictional banner with role note", () => {
    render(<FictionalBanner />);
    expect(screen.getByRole("note")).toHaveTextContent(DEFAULT_TEXT);
  });

  it("accepts custom text", () => {
    render(<FictionalBanner text="Custom notice" />);
    expect(screen.getByRole("note")).toHaveTextContent("Custom notice");
  });
});
