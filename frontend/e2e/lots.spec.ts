import { test, expect } from "@playwright/test";

test.describe("Lots management", () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto("/login");
    await page.fill('input[name="email"]', "test_e2e@snabagent.ru");
    await page.fill('input[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(lots|dashboard)/, { timeout: 10_000 });
  });

  test("should create a new lot", async ({ page }) => {
    await page.goto("/lots/new");
    const textarea = page.locator("textarea, input[name='raw_request']").first();
    await textarea.fill("Нужны трубы стальные 100 шт, ГОСТ 3262-75");
    // Submit form
    await page.click('button[type="submit"]');
    // Should see confirmation or redirect to lot detail
    await expect(
      page.getByText(/создан|draft|лот/i)
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should display lots list", async ({ page }) => {
    await page.goto("/lots");
    // Should show at least the table/list container
    await expect(
      page.locator("table, [data-testid='lots-list'], .lots-list").first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should view lot details", async ({ page }) => {
    await page.goto("/lots");
    // Click first lot in the list
    const firstLot = page.locator("tr a, [data-testid='lot-row']").first();
    if (await firstLot.isVisible()) {
      await firstLot.click();
      await expect(
        page.getByText(/статус|status|phase/i)
      ).toBeVisible({ timeout: 10_000 });
    }
  });
});
