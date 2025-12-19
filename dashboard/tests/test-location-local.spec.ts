import { test, expect } from '@playwright/test'

test('Test location shorthand locally', async ({ page }) => {
  // Navigate to local dev server
  await page.goto('http://localhost:3000')

  // Wait for table to load
  await page.waitForSelector('table tbody tr', { timeout: 15000 })

  // Get first few location cells
  const locationCells = await page.locator('table tbody tr td:nth-child(5)').all()

  console.log('\n=== Location Display Test ===')
  for (let i = 0; i < Math.min(5, locationCells.length); i++) {
    const text = await locationCells[i].textContent()
    const title = await locationCells[i].locator('span').getAttribute('title')
    console.log(`\nRow ${i+1}:`)
    console.log(`  Display: "${text}"`)
    console.log(`  Tooltip: ${title}`)

    // Check that it's shorthand (should be 3-6 chars, not full snake_case)
    const isShorthand = text && text.length <= 6 && !text.includes('_')
    console.log(`  Is Shorthand: ${isShorthand ? '✓' : '✗'}`)
  }
})
