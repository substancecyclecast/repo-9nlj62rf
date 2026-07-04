import { test, expect } from "@playwright/test";

test.describe("Authentication flow", () => {
  test("should show login page by default", async ({ page }) => {
    await page.goto("/");
    // Expect redirect to login or login form visible
    await expect(
      page.getByRole("heading", { name: /вход|login/i }).or(page.locator("input[type=email]"))
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should register a new user", async ({ page }) => {
    await page.goto("/register");
    await page.fill('input[name="email"]', "test_e2e@snabagent.ru");
    await page.fill('input[name="password"]', "TestPass123!");
    await page.fill('input[name="company_name"]', "E2E Test Corp");
    await page.fill('input[name="full_name"]', "E2E User");
    await page.click('button[type="submit"]');
    // Should succeed or show success message
    await expect(
      page.getByText(/успешн|success|добро пожаловать/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should login with valid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[name="email"]', "test_e2e@snabagent.ru");
    await page.fill('input[name="password"]', "TestPass123!");
    await page.click('button[type="submit"]');
    // Expect dashboard or lots page
    await expect(
      page.getByText(/лот|dashboard|закупк/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should reject login with wrong password", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[name="email"]', "test_e2e@snabagent.ru");
    await page.fill('input[name="password"]', "WrongPass999!");
    await page.click('button[type="submit"]');
    await expect(
      page.getByText(/ошибк|invalid|неверн/i)
    ).toBeVisible({ timeout: 5_000 });
  });
});
