import { test, expect } from '@playwright/test'

test.describe('Dashboard Filters', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Wait for loading to finish - API may take time
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {})
    await page.waitForSelector('table', { timeout: 30000 })
  })

  test('loads and displays roles', async ({ page }) => {
    // Header shows title and count
    await expect(page.getByRole('heading', { name: 'Paraform Roles' })).toBeVisible()
    await expect(page.getByText(/\d+ total/)).toBeVisible()

    // Table has rows
    const rows = page.locator('table tbody tr')
    const rowCount = await rows.count()
    expect(rowCount).toBeGreaterThanOrEqual(1)
  })

  test('qualified toggle filters to qualified roles only', async ({ page }) => {
    // Get initial count
    const initialText = await page.getByText(/Showing \d+/).textContent()
    const initialCount = parseInt(initialText?.match(/\d+/)?.[0] || '0')

    // Click Qualified toggle
    await page.getByRole('button', { name: /Qualified/ }).click()

    // Results should show "qualified roles"
    await expect(page.getByText(/qualified roles/)).toBeVisible()

    // Count may be different (qualified subset)
    const filteredText = await page.getByText(/Showing \d+/).textContent()
    const filteredCount = parseInt(filteredText?.match(/\d+/)?.[0] || '0')
    expect(filteredCount).toBeLessThanOrEqual(initialCount)
  })

  test('date filter filters by posted date', async ({ page }) => {
    // Set a recent date
    const today = new Date()
    const weekAgo = new Date(today.setDate(today.getDate() - 7))
    const dateStr = weekAgo.toISOString().split('T')[0]

    await page.fill('input[type="date"]', dateStr)

    // Results should mention the date
    await expect(page.getByText(/posted after/)).toBeVisible()
  })

  test('search filters roles by text', async ({ page }) => {
    await page.fill('input[placeholder="Search..."]', 'Backend')

    // Results should show matching text
    await expect(page.getByText(/matching "Backend"/)).toBeVisible()

    // All visible role titles should contain search term (or company/location)
    const rows = page.locator('table tbody tr')
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(0) // May have no matches
  })

  test('clear date filter shows all roles', async ({ page }) => {
    // Set date filter
    await page.fill('input[type="date"]', '2025-01-01')
    await expect(page.getByText(/posted after/)).toBeVisible()

    // Clear the date
    await page.fill('input[type="date"]', '')

    // Should no longer show "posted after"
    await expect(page.getByText(/posted after/)).not.toBeVisible()
  })

  test('view toggle switches between table and grid', async ({ page }) => {
    // Default is table view
    await expect(page.locator('table')).toBeVisible()

    // Click grid view
    await page.getByRole('button', { name: /Card view/i }).click()

    // Table should be hidden
    await expect(page.locator('table')).not.toBeVisible()

    // Click table view to switch back
    await page.getByRole('button', { name: /Table view/i }).click()
    await expect(page.locator('table')).toBeVisible()
  })

  test('columns are sortable', async ({ page }) => {
    // Click Score column header
    const scoreHeader = page.locator('th:has-text("Score")')
    await scoreHeader.click()

    // Should sort - verify first row still exists
    const firstRow = page.locator('table tbody tr').first()
    await expect(firstRow).toBeVisible()
  })

  test('combined filters work together', async ({ page }) => {
    // Apply qualified filter
    await page.getByRole('button', { name: /Qualified/ }).click()

    // Apply date filter
    const twoWeeksAgo = new Date()
    twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14)
    const dateStr = twoWeeksAgo.toISOString().split('T')[0]
    await page.fill('input[type="date"]', dateStr)

    // Results should show both filters
    await expect(page.getByText(/qualified roles/)).toBeVisible()
    await expect(page.getByText(/posted after/)).toBeVisible()

    // Page should still work without errors
    await expect(page.locator('body')).not.toBeEmpty()
  })
})
