import { expect, test } from "@playwright/test";

test("browse → watch → broadcast flow", async ({ page }) => {
  // 1. Discovery
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Discover" })).toBeVisible();
  await expect(page.getByText("Live now")).toBeVisible();

  // 2. Watch a live stream
  await page
    .getByRole("link", { name: /Speedrunning Hollow Knight/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: /Speedrunning Hollow Knight/ }),
  ).toBeVisible();
  await expect(page.getByText("Viewers")).toBeVisible();

  // 3. Broadcast dashboard
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(
    page.getByRole("heading", { name: "Broadcaster Dashboard" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Start broadcast" }).click();
  await expect(
    page.getByRole("main").getByText("Live", { exact: true }),
  ).toBeVisible();
});

test("search filters streams", async ({ page }) => {
  await page.goto("/");
  const search = page.getByRole("searchbox", { name: "Search streams" });
  await search.fill("Hollow Knight");
  await expect(page.getByText(/Speedrunning Hollow Knight/)).toBeVisible();
  await expect(page.getByText(/Synthwave production/)).not.toBeVisible();
});
