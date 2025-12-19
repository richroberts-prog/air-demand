# Dashboard Testing Guide

## Quick Start

```bash
# Run all tests (headless)
npm test

# Run with UI mode (watch/debug)
npm run test:ui

# Run specific category
npm run test:smoke       # Basic functionality
npm run test:features    # Feature tests
npm run test:integration # API integration
npm run test:e2e         # End-to-end workflows

# View last test report
npm run test:report
```

---

## Test Organization

```
tests/
├── smoke/          Basic smoke tests (9 tests)
├── features/       Feature-specific tests (21 tests)
├── integration/    API integration tests (14 tests)
└── e2e/            End-to-end workflows (4 tests)

Total: 48 tests
```

---

## Development Workflow

### 1. Local Development

**Before starting:**
```bash
# Ensure Docker is running
docker-compose up -d

# Verify services are healthy
curl http://localhost:3000  # Dashboard
curl http://localhost:8123/health  # API
```

**While coding:**
```bash
# Run tests in UI mode (interactive, watch mode)
npm run test:ui

# Or run in headed mode (see browser)
npm run test:headed

# Debug specific test
npm run test:debug -- tests/smoke/basic.spec.ts
```

### 2. Before Committing

```bash
# Run full test suite
npm test

# Fix any failures before committing
```

### 3. Testing Against Staging

```bash
# Run all tests against staging
npm run test:staging

# Run smoke tests only
npm run test:staging -- tests/smoke/
```

### 4. Production Smoke Tests

```bash
# Run minimal smoke tests against production
npm run test:prod
```

---

## Test Commands Reference

| Command | Description |
|---------|-------------|
| `npm test` | Run all tests headless |
| `npm run test:ui` | Interactive UI mode |
| `npm run test:headed` | Run with visible browser |
| `npm run test:debug` | Debug mode (pause on failures) |
| `npm run test:smoke` | Run smoke tests only |
| `npm run test:features` | Run feature tests |
| `npm run test:integration` | Run API integration tests |
| `npm run test:e2e` | Run end-to-end workflows |
| `npm run test:report` | View last test report |
| `npm run test:staging` | Test against staging |
| `npm run test:prod` | Production smoke tests |

---

## Running Specific Tests

```bash
# Single test file
npx playwright test tests/smoke/basic.spec.ts

# Single test by name
npx playwright test -g "should load homepage"

# Specific browser
npx playwright test --project=chromium

# With specific baseURL
BASE_URL=http://localhost:3000 npx playwright test
```

---

## Configuration

### Environment Variables

```bash
# Override base URL
BASE_URL=http://161.35.135.71:3000 npm test

# Run with different browser
BROWSER=firefox npm test
```

### playwright.config.ts

Key settings:
- `baseURL`: Default `http://localhost:3000`
- `timeout`: 30 seconds per test
- `retries`: 2 on CI, 0 locally
- `workers`: Parallel on local, sequential on CI

---

## Troubleshooting

### Tests timeout waiting for table

**Problem:** `expect(table).toBeVisible()` times out

**Causes:**
1. No data in database
2. API not reachable
3. Dashboard can't connect to API

**Solutions:**
```bash
# Check API health
curl http://localhost:8123/health

# Check dashboard is running
curl http://localhost:3000

# Restart Docker
docker-compose restart

# Check API connectivity from dashboard
docker exec air-demand-dashboard-1 wget -q -O- http://app:8123/health
```

### Playwright browsers not installed

```bash
# Install browsers
npx playwright install

# Install system dependencies (if needed)
npx playwright install-deps
```

### Tests pass locally but fail on staging

**Likely causes:**
1. Staging dashboard can't reach staging API
2. Network latency (increase timeouts)
3. Production data differences

**Debug:**
```bash
# Check staging dashboard
curl http://161.35.135.71:3000

# Check staging API
curl http://161.35.135.71:8123/health

# Run with screenshots
npx playwright test --screenshot=on
```

---

## Best Practices

### 1. Write Resilient Tests

```typescript
// ❌ BAD: Assumes specific data
expect(await page.locator('tbody tr').count()).toBe(100)

// ✅ GOOD: Tests pattern, not specific data
expect(await page.locator('tbody tr').count()).toBeGreaterThan(0)
```

### 2. Wait for Elements Properly

```typescript
// ❌ BAD: Hard wait
await page.waitForTimeout(5000)

// ✅ GOOD: Wait for condition
await page.waitForSelector('table', { state: 'visible' })
```

### 3. Use baseURL

```typescript
// ❌ BAD: Hardcoded URL
await page.goto('http://localhost:3000')

// ✅ GOOD: Use relative path
await page.goto('/')
```

### 4. Handle Loading States

```typescript
// Wait for loading to finish
await page.waitForSelector('text=Loading', { state: 'hidden' })

// Then verify content loaded
await expect(page.locator('table')).toBeVisible()
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Dashboard Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 20
      - name: Install dependencies
        run: cd dashboard && npm ci
      - name: Install Playwright
        run: cd dashboard && npx playwright install --with-deps
      - name: Run tests
        run: cd dashboard && npm test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: dashboard/playwright-report/
```

---

## Test Data Management

### Local Development
- Uses local Docker database
- May have no data initially
- Some tests will timeout without data
- **Solution:** Sync data from staging or use test fixtures

### Staging
- Uses production database
- Has real data (747+ roles)
- Tests should pass with production data
- **Caution:** Staging dashboard must have correct `BACKEND_URL`

### Production
- Only run smoke tests
- Read-only operations
- Monitor for performance impact
- Run during low-traffic periods

---

## Reporting

### HTML Report

```bash
# Generate and view report
npm run test:report
```

### Screenshots

On failure, screenshots are saved to `test-results/`:
```
test-results/
└── smoke-basic-Paraform-Dashboard-should-load-chromium/
    ├── test-failed-1.png
    └── error-context.md
```

### CI/CD Integration

```bash
# Generate JSON report for parsing
npx playwright test --reporter=json > test-results.json

# Generate JUnit XML for CI systems
npx playwright test --reporter=junit > junit-results.xml
```

---

## Known Limitations

### Local Docker
- Empty database → data-dependent tests fail
- Fix: Sync data or use test fixtures

### Staging
- Dashboard may not reach API (config issue)
- Fix: Set `BACKEND_URL` in staging deployment

### System Dependencies
- Some libraries missing in WSL
- Tests run fine in headless mode
- Headed/UI mode may need additional deps

---

## Getting Help

- **Playwright docs:** https://playwright.dev
- **Test failures:** Check `test-results/` folder
- **CI issues:** Review GitHub Actions logs
- **Local issues:** Ensure Docker is running

---

## Maintenance

### Updating Tests

1. Make changes to test files in `tests/`
2. Run affected tests: `npm run test:smoke` etc.
3. Fix any failures
4. Run full suite: `npm test`
5. Commit changes

### Updating Baselines

```bash
# Update screenshots/snapshots
npx playwright test --update-snapshots
```

### Cleaning Up

```bash
# Remove test results
rm -rf test-results/ playwright-report/

# Remove screenshots
rm -rf screenshots/
```
