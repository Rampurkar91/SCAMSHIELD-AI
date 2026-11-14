import { test, expect } from "@playwright/test";
import path from "node:path";
test("real QR and static-code uploads, assistant fallback and saved quiz", async ({
  page,
}) => {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Advanced E2E");
  await page
    .getByLabel("Email address")
    .fill(`advanced-${Date.now()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("Safe testing passphrase only 123!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back, Advanced" }),
  ).toBeVisible();
  await page.goto("/qr");
  await page
    .getByLabel(/Choose file/)
    .setInputFiles(path.resolve("e2e/fixtures/qr.png"));
  await page.getByRole("button", { name: "Analyze file" }).click();
  await expect(
    page.getByRole("heading", { name: "Your security assessment" }),
  ).toBeVisible();
  await expect(
    page
      .getByText("https://example.com/safe-test-fixture", { exact: true })
      .last(),
  ).toBeVisible();
  await page.goto("/code");
  await page
    .getByLabel(/Choose file/)
    .setInputFiles(path.resolve("e2e/fixtures/source.zip"));
  await page.getByRole("button", { name: "Analyze file" }).click();
  await expect(
    page.getByRole("heading", { name: "Your security assessment" }),
  ).toBeVisible();
  await expect(page.getByText(/unsafe_eval/)).toBeVisible();
  await page.goto("/assistant");
  await page
    .getByLabel("Your question")
    .fill("Why should I not share a UPI PIN?");
  await page.getByRole("button", { name: "Ask ScamShield" }).click();
  await expect(
    page.getByText(/Static safety fallback, not an AI answer/),
  ).toBeVisible();
  await page.goto("/learning");
  await page
    .getByRole("button", {
      name: "Decline and verify through the official app",
    })
    .click();
  await expect(page.getByText(/100\/100 · A UPI PIN/)).toBeVisible();
  await page.reload();
  await expect(page.getByText("upi-pin · 100/100")).toBeVisible();
});
