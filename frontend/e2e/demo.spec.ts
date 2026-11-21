// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import { expect, test } from "@playwright/test";

// Slow walkthrough for recording (about 2 minutes). Run: E2E_DEMO=1 E2E_VIDEO=1 npx playwright test demo
test.skip(!process.env.E2E_DEMO, "demo walkthrough only runs with E2E_DEMO=1");
test.setTimeout(180_000);

const pause = (page: import("@playwright/test").Page, seconds: number) => page.waitForTimeout(seconds * 1000);

test("tracer walkthrough", async ({ page }) => {
  const evidence = page.getByRole("region", { name: "Evidence" });

  await page.goto("/");
  await pause(page, 5); // page loads
  await expect(page.getByRole("note").filter({ hasText: "FICTIONAL" })).toBeVisible();
  await pause(page, 6); // banner, notice and the three fictional entities

  const first = page.getByRole("button", { name: "RULE-T1 implements REQ-T1" });
  await pause(page, 5); // read before acting
  await first.click();
  await expect(evidence).toContainText("tracer-fixture.xlsx › Links › B2");
  await pause(page, 6); // locator and snippet for link 1

  const second = page.getByRole("button", { name: "TEST-T1 verifies RULE-T1" });
  await pause(page, 5); // read before acting
  await second.click();
  await expect(evidence).toContainText("tracer-fixture.xlsx › Links › B3");
  await pause(page, 6); // link 2 from the list

  await page.reload();
  await pause(page, 3);
  await pause(page, 5); // read before acting
  await page.locator(".react-flow__edge").filter({ hasText: "implements" }).locator(".react-flow__edge-textbg").click();
  await expect(evidence).toContainText("B2");
  await pause(page, 6); // link 1 from the graph edge label

  await pause(page, 5); // read before acting
  await page.locator(".react-flow__edge").filter({ hasText: "verifies" }).locator(".react-flow__edge-textbg").click();
  await expect(evidence).toContainText("B3");
  await pause(page, 6); // link 2 from the graph edge label

  await pause(page, 5); // read before acting
  await page.goto("/?entity=REQ-T1");
  await pause(page, 6); // a different entity: two nodes, one link
  await pause(page, 5);

  await pause(page, 5); // read before acting
  await page.goto("/?entity=NOPE");
  await expect(page.getByRole("alert").filter({ hasText: "No entity with key NOPE" })).toBeVisible();
  await pause(page, 6); // clear not-found state

  await page.goto("/");
  await expect(page.getByRole("button", { name: "RULE-T1 implements REQ-T1" })).toBeVisible();
  await pause(page, 6); // back to the default view
  await pause(page, 6); // closing: stored links only, not impact analysis
  await pause(page, 6);
});
