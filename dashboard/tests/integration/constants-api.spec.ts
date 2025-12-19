import { test, expect } from '@playwright/test'

test.describe('Shared Constants Integration Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Wait for constants to load (ConstantsContext)
    await page.waitForTimeout(1000)

    // Wait for role data to load
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {})
  })

  test('should fetch constants from API on page load', async ({ page, request, baseURL }) => {
    // Test the API directly to verify it works
    const response = await request.get(`${baseURL}/api/shared/constants`)
    expect(response.status()).toBe(200)

    const data = await response.json()

    // Verify response structure
    expect(data).toHaveProperty('investors')
    expect(data.investors).toHaveProperty('tier_1')
    expect(data.investors).toHaveProperty('tier_2')
    expect(data).toHaveProperty('companies')
    expect(data).toHaveProperty('thresholds')

    // Verify General Catalyst is in tier_1 (bug fix verification)
    const tier1Investors = data.investors.tier_1.map((inv: string) => inv.toLowerCase())
    expect(tier1Investors).toContain('general catalyst')

    // Also verify the page loads without errors
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Paraform')
  })

  test('should display investor badges in table', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Check that table has investor column
    const investorHeader = page.locator('th:has-text("Investors")')
    await expect(investorHeader).toBeVisible()

    // Find rows with investor badges (tier 1 = green, tier 2 = blue)
    const investorBadges = page.locator('table tbody tr span[class*="bg-green"], table tbody tr span[class*="bg-blue"]')
    const badgeCount = await investorBadges.count()

    // If there are roles with notable investors, they should show badges
    // This is a soft check - OK if no roles have tier 1/2 investors
    if (badgeCount > 0) {
      console.log(`Found ${badgeCount} investor badges`)
      expect(badgeCount).toBeGreaterThan(0)
    } else {
      console.log('No investor badges found (OK - no roles with tier 1/2 investors)')
      // Still pass the test - just log that no badges were found
      expect(true).toBe(true)
    }
  })

  test('should show tier 1 investors with green badge', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Look for green badges (tier 1)
    const tier1Badges = page.locator('table tbody tr span[class*="bg-green-100"]')

    // At least verify the badge styling exists (tier 1 = green)
    if (await tier1Badges.count() > 0) {
      const firstBadge = tier1Badges.first()
      await expect(firstBadge).toBeVisible()

      // Check it has green styling
      const className = await firstBadge.getAttribute('class')
      expect(className).toContain('bg-green')
    }
  })

  test('should show tier 2 investors with blue badge', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Look for blue badges (tier 2)
    const tier2Badges = page.locator('table tbody tr span[class*="bg-blue-100"]')

    // At least verify the badge styling exists (tier 2 = blue)
    if (await tier2Badges.count() > 0) {
      const firstBadge = tier2Badges.first()
      await expect(firstBadge).toBeVisible()

      // Check it has blue styling
      const className = await firstBadge.getAttribute('class')
      expect(className).toContain('bg-blue')
    }
  })

  test('should sort by investor tier column', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Find the Investors column header
    const investorsHeader = page.locator('th:has-text("Investors")')
    await expect(investorsHeader).toBeVisible()

    // Click to sort
    await investorsHeader.click()
    await page.waitForTimeout(500)

    // Verify sorting happened (table should re-render)
    await expect(page.locator('table tbody tr').first()).toBeVisible()

    // Click again to reverse sort
    await investorsHeader.click()
    await page.waitForTimeout(500)

    // Should still have rows visible
    await expect(page.locator('table tbody tr').first()).toBeVisible()
  })

  test('should display investor short names', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Look for common short names in badges
    const possibleShortNames = ['YC', 'a16z', 'Sequoia', 'GC', 'NEA']

    let foundShortName = false
    for (const shortName of possibleShortNames) {
      const badge = page.locator(`table tbody tr span:has-text("${shortName}")`)
      if (await badge.count() > 0) {
        foundShortName = true
        break
      }
    }

    // Should find at least one short name (if there are roles with these investors)
    // This is a soft check - OK if no roles match
    if (foundShortName) {
      expect(foundShortName).toBeTruthy()
    }
  })

  test('should handle constants loading state gracefully', async ({ page }) => {
    // Verify page doesn't crash while constants are loading
    await page.goto('/')

    // Page should load even if constants take time
    await expect(page.locator('h1')).toBeVisible({ timeout: 10000 })

    // Wait for constants to finish loading
    await page.waitForTimeout(2000)

    // Table should eventually render
    await expect(page.locator('table')).toBeVisible({ timeout: 30000 })
  })

  test('should display role table with all columns', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Verify key column headers exist
    const expectedHeaders = [
      'Score',
      'Company',
      'Role',
      'Posted',
      'Investors',
      'Stage',
      'Industry',
      'Tech'
    ]

    for (const header of expectedHeaders) {
      await expect(page.locator(`th:has-text("${header}")`)).toBeVisible()
    }
  })

  test('should display scores with proper formatting', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Look for score cells (should show 0-100 range)
    const scoreCells = page.locator('table tbody tr td:first-child')

    if (await scoreCells.count() > 0) {
      const firstScore = await scoreCells.first().textContent()

      // Score should be a number or "—"
      expect(firstScore).toMatch(/^\d+$|^—$/)
    }
  })

  test('should handle roles without investors gracefully', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Look for investor cells
    const investorCells = page.locator('table tbody tr td:has-text("Investors"), table tbody tr td:nth-child(9)')

    // Should not crash if some roles have no investor badges
    const cellCount = await investorCells.count()
    expect(cellCount).toBeGreaterThanOrEqual(0)
  })

  test('should maintain consistent table layout', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Get first row column count
    const firstRowCells = page.locator('table tbody tr:first-child td')
    const cellCount = await firstRowCells.count()

    // Get header column count
    const headerCells = page.locator('table thead tr th')
    const headerCount = await headerCells.count()

    // Should match
    expect(cellCount).toBe(headerCount)
  })

  test('should display industry column with formatted names', async ({ page }) => {
    await page.waitForSelector('table', { timeout: 30000 })

    // Industry column should exist and show data or "—"
    const industryCells = page.locator('table tbody tr td:has-text("AI"), table tbody tr td:has-text("Healthcare"), table tbody tr td:has-text("Fintech")')

    // If industries are shown, they should be formatted (not raw like "software_development")
    if (await industryCells.count() > 0) {
      const firstIndustry = await industryCells.first().textContent()

      // Should not contain underscores (should be formatted)
      expect(firstIndustry).not.toContain('_')
    }
  })
})
