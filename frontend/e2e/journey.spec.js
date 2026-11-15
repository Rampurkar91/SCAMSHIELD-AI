import { test, expect } from "@playwright/test";
test("register, scan, review history, export, and sign out", async ({
  page,
}) => {
  const email = `e2e-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Full name").fill("E2E Test User");
  await page.getByLabel("Email address").fill(email);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Test-only long passphrase 123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back, E2E" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "New scan" }).click();
  await page
    .getByLabel("Website address")
    .fill("http://paypal-verify.xyz/login");
  await page.getByRole("button", { name: "Analyze URL" }).click();
  await expect(
    page.getByRole("heading", { name: "Your security assessment" }),
  ).toBeVisible();
  await expect(page.getByText("Estimated risk", { exact: true })).toBeVisible();
  const pdf = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF report" }).click();
  expect((await pdf).suggestedFilename()).toMatch(/scan-\d+.pdf/);
  await page.getByRole("link", { name: "Scan history", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "http://paypal-verify.xyz/login" }),
  ).toBeVisible();
  const csv = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  expect((await csv).suggestedFilename()).toContain(".csv");
  await page.getByRole("button", { name: /E2E Test User/ }).click();
  await expect(
    page.getByRole("heading", { name: "Your security, in one private space." }),
  ).toBeVisible();
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Test-only long passphrase 123!");
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back, E2E" }),
  ).toBeVisible();
});
test("mobile overview fits and navigation opens", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your digital safety starts here." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByLabel("Toggle menu").click();
  await page.getByRole("link", { name: "Security scanner" }).click();
  await expect(
    page.getByRole("heading", { name: "Security scanner", exact: true }),
  ).toBeVisible();
});
