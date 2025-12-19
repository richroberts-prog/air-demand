import { test, expect } from '@playwright/test'

test.describe('Debug UI - Live Test', () => {
  test('should navigate to dashboard and check basic functionality', async ({ page }) => {
    // Set longer timeout
    test.setTimeout(60000)

    console.log('Navigating to http://localhost:3000')
    await page.goto('http://localhost:3000', { waitUntil: 'domcontentloaded' })

    // Take a screenshot
    await page.screenshot({ path: 'test-results/dashboard-initial.png', fullPage: true })
    console.log('Screenshot saved: dashboard-initial.png')

    // Wait a bit for React to hydrate
    await page.waitForTimeout(2000)

    // Check title
    const title = await page.title()
    console.log('Page title:', title)

    // Check for main heading
    const heading = page.locator('h1')
    await expect(heading).toBeVisible({ timeout: 10000 })
    const headingText = await heading.textContent()
    console.log('Heading text:', headingText)

    // Wait for loading to finish
    console.log('Waiting for loading spinner to disappear...')
    await page.waitForSelector('text=Loading', { state: 'hidden', timeout: 30000 }).catch(() => {
      console.log('No loading spinner found or already hidden')
    })

    await page.waitForTimeout(2000)
    await page.screenshot({ path: 'test-results/dashboard-after-load.png', fullPage: true })
    console.log('Screenshot saved: dashboard-after-load.png')

    // Check for table or error message
    const hasTable = await page.locator('table').isVisible().catch(() => false)
    console.log('Table visible:', hasTable)

    if (hasTable) {
      const rowCount = await page.locator('tbody tr').count()
      console.log('Number of rows:', rowCount)
    }

    // Check for error messages
    const errorMessages = await page.locator('text=/error|failed|404/i').allTextContents()
    if (errorMessages.length > 0) {
      console.log('Error messages found:', errorMessages)
    }

    // Check network requests
    const requests = []
    page.on('request', request => {
      requests.push({
        url: request.url(),
        method: request.method()
      })
    })

    // Reload to capture requests
    await page.reload({ waitUntil: 'networkidle' })
    await page.waitForTimeout(3000)

    console.log('Network requests:', requests.filter(r => r.url.includes('localhost')))

    await page.screenshot({ path: 'test-results/dashboard-final.png', fullPage: true })
    console.log('Screenshot saved: dashboard-final.png')

    // Check console logs
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('Browser console error:', msg.text())
      }
    })

    // Check for constants API call
    const constantsUrl = 'http://localhost:3000/api/shared/constants'
    console.log('Checking if constants API is being called...')

    const response = await page.waitForResponse(
      response => response.url().includes('/shared/constants'),
      { timeout: 5000 }
    ).catch(() => null)

    if (response) {
      console.log('Constants API response status:', response.status())
      const data = await response.json().catch(() => null)
      if (data) {
        console.log('Constants data keys:', Object.keys(data))
      }
    } else {
      console.log('No constants API call detected')
    }
  })
})
