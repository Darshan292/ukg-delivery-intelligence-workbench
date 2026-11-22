// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { expect, test } from "@playwright/test";

const LINK1 = "RULE-T1 implements REQ-T1";
const LINK2 = "TEST-T1 verifies RULE-T1";

test("loads RULE-T1 with the fictional banner and the not-impact-analysis notice", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("note").filter({ hasText: "FICTIONAL" })).toBeVisible();
  await expect(page.getByText("This is not impact analysis").first()).toBeVisible();
  for (const key of ["REQ-T1", "RULE-T1", "TEST-T1"]) {
    await expect(page.getByText(key).first()).toBeVisible();
  }
  await expect(page.getByRole("button", { name: LINK1 })).toBeVisible();
  await expect(page.getByRole("button", { name: LINK2 })).toBeVisible();
  await expect(page.getByRole("region", { name: "Evidence" })).toContainText(
    "Select a link in the graph or the list to see where it comes from.",
  );
});

test("selecting a link in the list shows its source locator", async ({ page }) => {
  await page.goto("/");
  const first = page.getByRole("button", { name: LINK1 });
  await first.click();
  await expect(first).toHaveAttribute("aria-pressed", "true");
  const evidence = page.getByRole("region", { name: "Evidence" });
  await expect(evidence).toContainText("tracer-fixture.xlsx › Links › B2");
  await expect(evidence).toContainText("RULE-T1 implements REQ-T1 (FICTIONAL, fake locator)");
  await expect(evidence).toContainText("Fake locator");
});

test("selecting a link by its graph edge label shows its source locator", async ({ page }) => {
  await page.goto("/");
  // The label text sits under its own background rectangle, which takes the click.
  await page.locator(".react-flow__edge").filter({ hasText: "verifies" }).locator(".react-flow__edge-textbg").click();
  await expect(page.getByRole("region", { name: "Evidence" })).toContainText("tracer-fixture.xlsx › Links › B3");
});

test("unknown entity shows a not-found alert", async ({ page }) => {
  await page.goto("/?entity=NOPE");
  // Next adds its own role="alert" route announcer, so match ours by its text.
  await expect(page.getByRole("alert").filter({ hasText: "No entity with key NOPE" })).toBeVisible();
});

test("an over-long entity key shows a validation alert", async ({ page }) => {
  await page.goto(`/?entity=${"A".repeat(150)}`);
  await expect(page.getByRole("alert").filter({ hasText: "Entity keys use letters, digits" })).toBeVisible();
});

test("narrow viewport has no horizontal scroll and the Evidence region is reachable", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/");
  await expect(page.getByRole("button", { name: LINK1 })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  expect(overflow).toBe(true);
  const evidence = page.getByRole("region", { name: "Evidence" });
  await evidence.scrollIntoViewIfNeeded();
  await expect(evidence).toBeInViewport();
});
