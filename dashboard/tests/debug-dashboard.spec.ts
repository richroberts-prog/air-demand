import { test } from '@playwright/test';

const DASHBOARD_URL = 'http://104.236.56.33:3000';

test('Debug dashboard API calls', async ({ page }) => {
  const consoleMessages: string[] = [];
  const errors: string[] = [];
  const apiCalls: string[] = [];
  const failedRequests: string[] = [];

  // Capture console messages
  page.on('console', msg => {
    const text = `[${msg.type()}] ${msg.text()}`;
    consoleMessages.push(text);
    console.log(text);
  });

  // Capture page errors
  page.on('pageerror', error => {
    const text = `PAGE ERROR: ${error.message}`;
    errors.push(text);
    console.log(text);
  });

  // Capture all network requests
  page.on('request', request => {
    if (request.url().includes('104.236.56.33')) {
      console.log(`→ REQUEST: ${request.method()} ${request.url()}`);
    }
  });

  // Capture all network responses
  page.on('response', response => {
    const url = response.url();
    if (url.includes('104.236.56.33:8000')) {
      const status = response.status();
      const call = `${response.request().method()} ${url} → ${status}`;
      apiCalls.push(call);
      console.log(`← RESPONSE: ${call}`);

      if (!response.ok()) {
        failedRequests.push(call);
      }
    }
  });

  // Capture failed requests
  page.on('requestfailed', request => {
    if (request.url().includes('104.236.56.33')) {
      const text = `FAILED: ${request.method()} ${request.url()} - ${request.failure()?.errorText}`;
      failedRequests.push(text);
      console.log(text);
    }
  });

  console.log(`\n=== Loading dashboard at ${DASHBOARD_URL} ===\n`);
  await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle', timeout: 30000 });

  // Wait a bit for React Query to initialize
  await page.waitForTimeout(5000);

  console.log('\n=== SUMMARY ===');
  console.log(`Console messages: ${consoleMessages.length}`);
  console.log(`Page errors: ${errors.length}`);
  console.log(`API calls to port 8000: ${apiCalls.length}`);
  console.log(`Failed requests: ${failedRequests.length}`);

  if (errors.length > 0) {
    console.log('\n=== PAGE ERRORS ===');
    errors.forEach(e => console.log(e));
  }

  if (failedRequests.length > 0) {
    console.log('\n=== FAILED REQUESTS ===');
    failedRequests.forEach(f => console.log(f));
  }

  if (apiCalls.length > 0) {
    console.log('\n=== API CALLS ===');
    apiCalls.forEach(c => console.log(c));
  }
});
