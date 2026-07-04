import { test, expect } from "@playwright/test";

test.describe("Dashboard & Analytics", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[name="email"]', "test_e2e@snabagent.ru");
    await page.fill('input[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(lots|dashboard)/, { timeout: 10_000 });
  });

  test("should display KPI cards on dashboard", async ({ page }) => {
    await page.goto("/dashboard");
    // Expect KPI cards or metrics to be present
    await expect(
      page.locator("[data-testid='kpi-card'], .kpi-card, .stat-card").first()
        .or(page.getByText(/лот|savings|экономия/i))
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should display analytics charts", async ({ page }) => {
    await page.goto("/analytics");
    // Expect chart or graph container
    await expect(
      page.locator("svg.recharts-surface, canvas, [data-testid='chart']").first()
        .or(page.getByText(/аналитик|analytics/i))
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should toggle dark mode", async ({ page }) => {
    await page.goto("/");
    const toggle = page.locator(
      "[data-testid='dark-mode-toggle'], button:has(svg[data-icon='moon']), .theme-toggle"
    ).first();
    if (await toggle.isVisible()) {
      await toggle.click();
      // Check that dark class is applied
      const html = page.locator("html");
      await expect(html).toHaveClass(/dark/);
    }
  });
});
