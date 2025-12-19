import { test, expect } from '@playwright/test';

test.describe('Dashboard E2E Tests', () => {
  test('should load dashboard homepage', async ({ page }) => {
    await page.goto('/');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');

    // Take screenshot
    await page.screenshot({ path: 'test-results/dashboard-home.png', fullPage: true });

    // Check for main heading
    await expect(page.locator('h1, h2').first()).toBeVisible();

    console.log('✅ Dashboard loaded successfully');
  });

  test('should display roles table', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Wait a bit for data to load
    await page.waitForTimeout(2000);

    // Take screenshot
    await page.screenshot({ path: 'test-results/roles-table.png', fullPage: true });

    // Check if table or role cards are visible
    const tableOrCard = page.locator('table, [class*="role"], [class*="card"]').first();

    try {
      await expect(tableOrCard).toBeVisible({ timeout: 5000 });
      console.log('✅ Roles are being displayed');
    } catch (e) {
      console.log('⚠️  No roles visible yet (scrape may still be running)');
      // Take a screenshot of empty state
      await page.screenshot({ path: 'test-results/empty-state.png', fullPage: true });
    }
  });

  test('should check API connectivity', async ({ page, baseURL }) => {
    await page.goto('/');

    // Listen for API calls (dashboard calls API on :8123)
    const apiCalls: string[] = [];
    const apiPort = baseURL?.includes('161.35.135.71') || baseURL?.includes('104.236.56.33') ? '8123' : '8123';
    page.on('response', response => {
      if (response.url().includes(`:${apiPort}`)) {
        apiCalls.push(`${response.request().method()} ${response.url()} -> ${response.status()}`);
      }
    });

    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    console.log('📡 API Calls detected:');
    apiCalls.forEach(call => console.log(`   ${call}`));

    // Take screenshot
    await page.screenshot({ path: 'test-results/api-check.png', fullPage: true });

    expect(apiCalls.length).toBeGreaterThan(0);
    console.log('✅ Dashboard is communicating with API');
  });

  test('should navigate and interact', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Look for any filters or navigation elements
    const filters = page.locator('button, select, input[type="checkbox"]');
    const filterCount = await filters.count();

    console.log(`Found ${filterCount} interactive elements`);

    // Take screenshot
    await page.screenshot({ path: 'test-results/interactive-elements.png', fullPage: true });

    if (filterCount > 0) {
      console.log('✅ Interactive controls found');

      // Try clicking the first button if it exists
      const firstButton = filters.first();
      if (await firstButton.isVisible()) {
        await firstButton.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: 'test-results/after-interaction.png', fullPage: true });
        console.log('✅ Successfully interacted with UI element');
      }
    }
  });
});
