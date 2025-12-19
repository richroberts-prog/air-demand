import { test, expect } from '@playwright/test'

test('Debug location display', async ({ page }) => {
  // Navigate to production dashboard
  await page.goto('http://104.236.56.33:3000')

  // Wait for table to load
  await page.waitForSelector('table', { timeout: 10000 })

  // Take a screenshot
  await page.screenshot({ path: 'screenshots/location-debug.png', fullPage: true })

  // Get first few location cells
  const locationCells = await page.locator('table tbody tr td:nth-child(5)').all()

  console.log('\n=== Location Cell Values ===')
  for (let i = 0; i < Math.min(5, locationCells.length); i++) {
    const text = await locationCells[i].textContent()
    const title = await locationCells[i].locator('span').getAttribute('title')
    console.log(`Row ${i+1}:`)
    console.log(`  Text: ${text}`)
    console.log(`  Tooltip: ${title}`)
  }

  // Get workplace type cells (new column 6)
  const typeCells = await page.locator('table tbody tr td:nth-child(6)').all()

  console.log('\n=== Workplace Type Cell Values ===')
  for (let i = 0; i < Math.min(5, typeCells.length); i++) {
    const text = await typeCells[i].textContent()
    console.log(`Row ${i+1}: ${text}`)
  }

  console.log('\n=== Screenshot saved to screenshots/location-debug.png ===')
})
