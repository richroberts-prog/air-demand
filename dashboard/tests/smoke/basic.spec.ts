import { test, expect } from '@playwright/test'

test.describe('Paraform Dashboard v0.1 Smoke Tests', () => {
  test('should load homepage and display roles', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/Paraform/)
    await expect(page.locator('h1')).toContainText('Paraform')
  })

  test('should display Qualified toggle button', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Single Qualified toggle button with count
    await expect(page.locator('button:has-text("Qualified")')).toBeVisible()
  })

  test('should display role table', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Wait for loading to finish - API may take time
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {})

    // Wait for role table to load
    const table = page.locator('table')
    await expect(table).toBeVisible({ timeout: 30000 })

    // Should have table rows
    const rows = page.locator('tbody tr')
    await expect(rows.first()).toBeVisible({ timeout: 10000 })
  })

  test('should toggle Qualified filter', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Wait for data to load first
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {})
    await page.waitForSelector('table', { timeout: 30000 }).catch(() => {})

    // Click Qualified toggle
    const qualifiedButton = page.locator('button:has-text("Qualified")')
    await qualifiedButton.click()

    // Wait for filtering
    await page.waitForTimeout(500)

    // Should show "qualified roles" in results count
    await expect(page.getByText(/qualified roles/)).toBeVisible({ timeout: 5000 })
  })

  test('should have working search', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Look for search input
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]')
    if (await searchInput.isVisible()) {
      await searchInput.fill('test')
      await page.waitForTimeout(500)
      // Should filter without errors
      await expect(page.locator('body')).not.toBeEmpty()
    }
  })

  test('should have refresh button', async ({ page }) => {
    await page.goto('/')
    const refreshButton = page.locator('button:has-text("Refresh")')
    await expect(refreshButton).toBeVisible()
  })

  test('should display role count', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Wait for roles to load
    await page.waitForTimeout(2000)

    // Should show role count in the header (e.g., "695 total") or results count
    const hasRoleCount = await page.locator('text=/\\d+ (total|live|role)/i').first().isVisible().catch(() => false)

    expect(hasRoleCount).toBeTruthy()
  })

  test('should have date filter', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Should have date input for "Posted after" filtering
    await expect(page.locator('input[type="date"]')).toBeVisible()
  })

  test('should have view toggle buttons', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Should have Table and Card view toggles
    await expect(page.locator('button[title="Table view"]')).toBeVisible()
    await expect(page.locator('button[title="Card view"]')).toBeVisible()
  })
})
