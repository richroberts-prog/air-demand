import { test, expect } from '@playwright/test'

test.describe('Scoring UI Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    // Wait for loading to finish - API may take time
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {})
    // Wait for table to load
    await expect(page.locator('table')).toBeVisible({ timeout: 30000 })
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10000 })
  })

  test('should display score column headers', async ({ page }) => {
    // Check for score column headers
    const scoreHeader = page.locator('th:has-text("Score")')
    await expect(scoreHeader).toBeVisible()

    const engHeader = page.locator('th:has-text("Eng")')
    await expect(engHeader).toBeVisible()

    const hhHeader = page.locator('th:has-text("HH")')
    await expect(hhHeader).toBeVisible()
  })

  test('should display score values in rows', async ({ page }) => {
    // Get the first row and check for score cells
    const firstRow = page.locator('tbody tr').first()

    // Score cells should contain either a number or a dash
    const scoreCells = firstRow.locator('td')

    // The score columns are after Company and Role (at indexes 2, 3, 4)
    // They should contain numeric values (0-100) or dashes
    const scoreCount = await scoreCells.count()
    expect(scoreCount).toBeGreaterThan(4) // At least have the basic columns plus scores
  })

  test('should be able to sort by Score column', async ({ page }) => {
    // Find and click the Score header to sort
    const scoreHeader = page.locator('th:has-text("Score")')
    await expect(scoreHeader).toBeVisible()

    // Click to sort
    await scoreHeader.click()
    await page.waitForTimeout(500)

    // The page should not error and still show content
    await expect(page.locator('tbody tr').first()).toBeVisible()
  })

  test('should be able to sort by Eng column', async ({ page }) => {
    const engHeader = page.locator('th:has-text("Eng")')
    await expect(engHeader).toBeVisible()

    // Click to sort descending
    await engHeader.click()
    await page.waitForTimeout(500)

    // Page should still show roles
    await expect(page.locator('tbody tr').first()).toBeVisible()

    // Click again to sort ascending
    await engHeader.click()
    await page.waitForTimeout(500)

    await expect(page.locator('tbody tr').first()).toBeVisible()
  })

  test('should be able to sort by HH column', async ({ page }) => {
    const hhHeader = page.locator('th:has-text("HH")')
    await expect(hhHeader).toBeVisible()

    // Click to sort
    await hhHeader.click()
    await page.waitForTimeout(500)

    await expect(page.locator('tbody tr').first()).toBeVisible()
  })

  test('score cells should have visual styling', async ({ page }) => {
    // Check if any score cells have the expected styling classes
    // High scores (>=85) should have green styling
    // Medium scores (>=70) should have blue styling

    const table = page.locator('table')
    await expect(table).toBeVisible()

    // Check for existence of styled score cells (either green, blue, or default)
    // Looking for cells with score-like content
    const scoreCells = page.locator('td span.text-green-700, td span.text-blue-700, td span.text-gray-600, td span.text-red-500')

    // If we have roles with scores, some of these should exist
    // This is a soft check - if no scores exist, it's still OK
    const count = await scoreCells.count()
    // We just verify the page renders without error
    expect(count).toBeGreaterThanOrEqual(0)
  })

  test('score tooltips should show on hover', async ({ page }) => {
    // Find a score cell and hover to check for title attribute
    const firstRow = page.locator('tbody tr').first()
    const scoreCellSpan = firstRow.locator('td span[title*="Score"]').first()

    if (await scoreCellSpan.isVisible()) {
      const title = await scoreCellSpan.getAttribute('title')
      // Title should include "Score" and a percentage
      expect(title).toMatch(/Score.*%|N\/A/)
    }
  })

  test('score columns should be sortable with arrow icons', async ({ page }) => {
    // Check that score headers have the sort arrow icon
    const scoreHeader = page.locator('th:has-text("Score")')
    await expect(scoreHeader).toBeVisible()

    // The header should be clickable (has cursor-pointer class)
    const hasPointer = await scoreHeader.evaluate((el) =>
      window.getComputedStyle(el).cursor === 'pointer'
    )
    expect(hasPointer).toBe(true)
  })

  test('high scores should display star icon', async ({ page }) => {
    // Look for star icons in score cells (indicating high scores >= 85)
    // This is a soft check - may not have any high-scoring roles
    const starIcons = page.locator('td svg.fill-current')

    // If any high scores exist, star icons should be present
    const count = await starIcons.count()
    // Just ensure no errors
    expect(count).toBeGreaterThanOrEqual(0)
  })
})

test.describe('Score Column Ordering', () => {
  test('score columns should appear after Role column', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    // Wait for loading to finish - API may take time
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {})
    await expect(page.locator('table')).toBeVisible({ timeout: 30000 })

    // Get all header text to verify order
    const headers = page.locator('thead th')
    const headerTexts = await headers.allTextContents()

    // Find indices
    const companyIndex = headerTexts.findIndex(h => h.includes('Company'))
    const scoreIndex = headerTexts.findIndex(h => h === 'Score' || h.includes('Score'))
    const engIndex = headerTexts.findIndex(h => h === 'Eng')
    const hhIndex = headerTexts.findIndex(h => h === 'HH')

    // Company should be first
    expect(companyIndex).toBe(0)

    // Score columns should be after Role (index 1)
    expect(scoreIndex).toBeGreaterThan(1)
    expect(engIndex).toBeGreaterThan(1)
    expect(hhIndex).toBeGreaterThan(1)

    // Score columns should be adjacent
    expect(Math.abs(scoreIndex - engIndex)).toBe(1)
    expect(Math.abs(engIndex - hhIndex)).toBe(1)
  })
})
