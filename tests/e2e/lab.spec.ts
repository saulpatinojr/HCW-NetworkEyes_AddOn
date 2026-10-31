import { expect, test } from "@playwright/test";

const HOST_PORT = Number(process.env.NA_E2E_HOST_PORT ?? 8096);
const API_PORT = Number(process.env.NA_E2E_PORT ?? 8097);

test("pane: sample → summary → filter → detail → unknowns → copy report → download → delete", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/");
  await expect(page.getByText("no cloud connectivity by design")).toBeVisible();
  await expect(page.locator("#status")).toHaveText("Ready");
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  await page.getByRole("button", { name: "Use the sample export" }).click();
  await expect(page.locator("#preview-summary")).toContainText("48 rows detected");
  await page.getByRole("button", { name: "Run assessment" }).click();
  await expect(page.getByRole("heading", { name: "2. Summary" })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("#topology")).toContainText("Topology: hub-spoke");
  await expect(page.locator("#tiles")).toContainText("Unknown rules");
  await expect(page.locator("#findings-count")).toContainText("45 of 45 findings");
  await page.locator("#f-severity").selectOption("critical");
  await expect(page.locator("#findings-count")).toContainText("3 of 45 findings");
  await page.locator("tr.finding").first().click();
  await expect(page.locator("#detail")).toBeVisible();
  await expect(page.locator("#detail-list")).toContainText("AZ-NET-003");
  await expect(page.locator("#detail-list")).toContainText("Facts the rules read");
  await page.locator("#f-severity").selectOption("");
  await page.locator("#f-category").selectOption("BC/DR");
  await expect(page.locator("#findings-count")).toContainText("8 of 45 findings");
  await expect(page.locator("#unknown-list")).toContainText("AZ-NET-008");
  await expect(page.getByRole("heading", { name: "What this cannot tell you" })).toBeVisible();
  await page.getByRole("button", { name: "Copy report" }).click();
  await expect(page.locator("#copy-note")).toContainText("copied");
  const clipboard = await page.evaluate(() => navigator.clipboard.readText());
  expect(clipboard).toContain("# Network assessment report");
  await page.getByRole("tab", { name: "Resources" }).click();
  await expect(page.locator("#resources")).toContainText("hcw-sample-vnet-hub");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download bundle" }).click();
  expect((await download).suggestedFilename()).toMatch(/^assessment-[0-9a-f]{8}\.zip$/);
  await page.getByRole("button", { name: "Open in lab workspace" }).click();
  await expect(page.locator("#copy-note")).toContainText("Lab workspace ready");
  const wsLink = page.locator("#copy-note a");
  await expect(wsLink).toHaveText("Open lab workspace");
  await expect(wsLink).toHaveAttribute("href", /\/templates\/na-guided-lab\/workspace\?/);
  const bodyAfterWs = (await page.locator("body").innerText()).toLowerCase();
  for (const word of ["cloudflare", "turnstile", "hostinger", "vps", "coder", "ttl"]) expect(bodyAfterWs, word).not.toContain(word);
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Delete my data now" }).click();
  await expect(page.getByRole("heading", { name: "2. Summary" })).toBeHidden();
  await expect(page.locator("#run-note")).toContainText("deleted");
});

test("pane copy never names vendors", async ({ page }) => {
  await page.goto("/");
  const text = (await page.locator("body").innerText()).toLowerCase();
  for (const word of ["cloudflare", "turnstile", "hostinger", "vps", "coder", "ttl"]) expect(text, word).not.toContain(word);
  await expect(page.locator("#notice")).toContainText("expires after two hours");
  await expect(page.locator("body")).toContainText("Not production");
});

test("framed pane posts loading → ready → working → ready to the site origin under the production sandbox", async ({ page }) => {
  await page.goto(`http://127.0.0.1:${HOST_PORT}/host-page.html?addon=http://127.0.0.1:${API_PORT}`);
  const frame = page.frameLocator("#pane");
  await expect(frame.locator("#status")).toHaveText("Ready");
  await expect.poll(() => page.evaluate(() => (window as unknown as { __messages: string[] }).__messages)).toEqual(["loading", "ready"]);
  await expect(frame.locator("html")).toHaveClass(/dark/);
  await frame.getByRole("button", { name: "Use the sample export" }).click();
  await frame.getByRole("button", { name: "Run assessment" }).click();
  await expect(frame.getByRole("heading", { name: "2. Summary" })).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => page.evaluate(() => (window as unknown as { __messages: string[] }).__messages)).toEqual(["loading", "ready", "working", "ready"]);
});

test("security headers and the health envelope", async ({ request }) => {
  const r = await request.get("/api/health");
  expect(r.status()).toBe(200);
  const body = await r.json();
  expect(body.id).toBe("network-assessment");
  expect(body.edition).toBe("lab");
  expect(body.azureConnectivity).toBe("disabled-by-design");
  expect(body.rules.version).toBe("2026.10.0");
  // The model marker is the active engine's (lab-1.0.0 for the interim port); tests/unit/test_engine.py pins it
  // per engine, so here it only has to agree with what GET /api/rules reports.
  const rules = await (await request.get("/api/rules")).json();
  expect(body.model.version).toBe(rules.modelVersion);
  expect(body.model.version).not.toBe("");
  expect(r.headers()["x-addon-id"]).toBe("network-assessment");
  expect(r.headers()["content-security-policy"]).toContain(`frame-ancestors http://127.0.0.1:${HOST_PORT}`);
  const invalid = await request.post("/api/assessments", { data: { format: "arg-json", content: "[]" } });
  expect(invalid.status()).toBe(400);
  expect((await invalid.json()).error.code).toBe("invalid_export");
});
