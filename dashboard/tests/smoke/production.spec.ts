import { test, expect } from '@playwright/test'

/**
 * Production Smoke Tests
 *
 * Minimal, read-only tests safe to run against production.
 * These tests verify critical functionality without modifying data.
 *
 * Run with: npm run test:prod
 * Or: BASE_URL=http://production-url:3000 npx playwright test tests/smoke/production.spec.ts
 */

test.describe('Production Smoke Tests', () => {
  test('should load dashboard homepage', async ({ page }) => {
    await page.goto('/')

    // Verify page loads
    await expect(page).toHaveTitle(/Paraform/)
    await expect(page.locator('h1')).toContainText('Paraform')
  })

  test('should display header UI elements', async ({ page }) => {
    await page.goto('/')

    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Verify key UI elements exist (read-only check)
    await expect(page.locator('button:has-text("Qualified")')).toBeVisible()
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible()
    await expect(page.locator('input[type="date"]')).toBeVisible()
    await expect(page.locator('input[placeholder="Search..."]')).toBeVisible()
  })

  test('should have working view toggle buttons', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Verify view toggles exist
    await expect(page.locator('button[title="Table view"]')).toBeVisible()
    await expect(page.locator('button[title="Card view"]')).toBeVisible()
  })

  test('should display data without errors', async ({ page }) => {
    await page.goto('/')

    // Wait for loading to finish
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {})
    await page.waitForTimeout(3000)

    // Check that either table OR error message is visible (not stuck loading)
    const hasTable = await page.locator('table').isVisible().catch(() => false)
    const hasError = await page.locator('text=/error|Error/i').isVisible().catch(() => false)
    const isLoading = await page.locator('text=Loading').isVisible().catch(() => false)

    // Should not be perpetually loading
    expect(isLoading).toBe(false)

    // Should show either data or error (not blank)
    expect(hasTable || hasError).toBe(true)
  })

  test('should not have JavaScript errors', async ({ page }) => {
    const errors: string[] = []

    // Capture console errors
    page.on('pageerror', error => {
      errors.push(error.message)
    })

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Should have no JS errors
    expect(errors).toHaveLength(0)
  })
})
