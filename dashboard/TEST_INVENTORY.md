# Dashboard Test Suite Inventory

**Date:** 2025-12-19
**Status:** Audit complete, cleanup in progress

## Summary

- **Total test files:** 9
- **Tests to keep:** 5 (56%)
- **Tests to delete:** 4 (44%)
- **Issues found:** Hardcoded URLs, outdated selectors

---

## Test Categorization

### ✅ Keep - Production Tests (5 files)

#### 1. **v0.1-smoke.spec.ts** - Smoke Tests
- **Category:** Smoke
- **Tests:** 9 tests
- **Status:** ✅ Good to keep
- **Coverage:**
  - Homepage loads and displays roles
  - Qualified toggle button works
  - Role table displays
  - Qualified filter functionality
  - Search functionality
  - Refresh button exists
  - Role count display
  - Date filter exists
  - View toggle buttons (table/card)
- **Issues:** None
- **Action:** Move to `tests/smoke/basic.spec.ts`

#### 2. **new-roles.spec.ts** - Dashboard Filters
- **Category:** Feature
- **Tests:** 8 tests
- **Status:** ✅ Good to keep
- **Coverage:**
  - Loads and displays roles
  - Qualified toggle filters
  - Date filter
  - Search filter
  - Clear date filter
  - View toggle (table/grid)
  - Column sorting
  - Combined filters
- **Issues:** None
- **Action:** Move to `tests/features/filtering.spec.ts`

#### 3. **scoring.spec.ts** - Scoring System
- **Category:** Feature
- **Tests:** 13 tests
- **Status:** ✅ Good to keep
- **Coverage:**
  - Score column headers display
  - Score values in rows
  - Sorting by Score/Eng/HH columns
  - Visual styling for scores
  - Tooltips on hover
  - Arrow icons for sorting
  - Star icons for high scores
  - Column ordering verification
- **Issues:** None
- **Action:** Move to `tests/features/scoring.spec.ts`

#### 4. **shared-constants.spec.ts** - API Integration
- **Category:** Integration
- **Tests:** 14 tests
- **Status:** ✅ Good to keep
- **Coverage:**
  - API endpoint connectivity
  - Constants structure validation
  - Investor badge display (tier 1/2)
  - Badge styling (green/blue)
  - Investor column sorting
  - Short name display
  - Loading state handling
  - All column headers present
  - Score formatting
  - Graceful handling of missing data
  - Table layout consistency
  - Industry column formatting
- **Issues:** Hardcoded `http://localhost:3000` in API test (line 17)
- **Action:**
  - Move to `tests/integration/constants-api.spec.ts`
  - Update to use `baseURL` from config

#### 5. **e2e-dashboard.spec.ts** - E2E Workflow
- **Category:** E2E
- **Tests:** 4 tests
- **Status:** ⚠️ Keep but needs updates
- **Coverage:**
  - Dashboard homepage loads
  - Roles table displays
  - API connectivity check
  - Navigate and interact with UI
- **Issues:**
  - **CRITICAL:** Hardcoded production URL `http://104.236.56.33:3000` (line 3)
  - Uses old API port `:8000` instead of `:8123` (line 50)
  - Screenshots saved to `screenshots/` (should be in `test-results/`)
- **Action:**
  - Move to `tests/e2e/dashboard.spec.ts`
  - Remove hardcoded URL, use `baseURL` from config
  - Update API port from 8000 → 8123
  - Fix screenshot paths

---

### ❌ Delete - Debug Tests (4 files)

#### 6. **debug-dashboard.spec.ts**
- **Category:** Debug
- **Reason:** Development debugging only
- **Action:** DELETE

#### 7. **debug-location.spec.ts**
- **Category:** Debug
- **Reason:** Development debugging only
- **Action:** DELETE

#### 8. **debug-ui.spec.ts**
- **Category:** Debug
- **Reason:** Development debugging only
- **Action:** DELETE

#### 9. **test-location-local.spec.ts**
- **Category:** Debug
- **Reason:** Local testing only, covered by other tests
- **Action:** DELETE

---

## Issues Found

### Critical Issues
1. **Hardcoded URLs in e2e-dashboard.spec.ts** (line 3)
   - Uses `http://104.236.56.33:3000` instead of `baseURL`
   - Solution: Use config-based URL

2. **Wrong API port in e2e-dashboard.spec.ts** (line 50)
   - Uses `:8000` but API runs on `:8123`
   - Solution: Update to `:8123`

### Minor Issues
1. **Hardcoded localhost in shared-constants.spec.ts** (line 17)
   - Direct API call uses hardcoded `http://localhost:3000`
   - Solution: Use `baseURL` from config

2. **Screenshot directories inconsistent**
   - Some use `screenshots/`, some use `test-results/`
   - Solution: Standardize on `test-results/` (auto-created by Playwright)

---

## Proposed Directory Structure

```
dashboard/tests/
├── smoke/
│   └── basic.spec.ts              (from v0.1-smoke.spec.ts)
├── features/
│   ├── filtering.spec.ts          (from new-roles.spec.ts)
│   └── scoring.spec.ts            (from scoring.spec.ts)
├── integration/
│   └── constants-api.spec.ts      (from shared-constants.spec.ts)
└── e2e/
    └── dashboard.spec.ts           (from e2e-dashboard.spec.ts - NEEDS FIXES)
```

---

## Coverage Analysis

### Covered ✅
- Basic page loading
- Role table rendering
- Filtering (qualified, date, search)
- Sorting (all columns)
- View modes (table/card)
- Scoring display and styling
- API integration
- Constants loading
- Investor badges
- Column formatting

### Gaps ⚠️
- **Briefing modal interaction** (not tested)
- **Refresh button functionality** (only checks existence)
- **Error states** (API failures, network errors)
- **Loading states** (only waits, doesn't verify)
- **Empty state** (no roles scenario)
- **Mobile/responsive** (no viewport tests)
- **Accessibility** (no a11y tests)

---

## Recommendations

### Phase 2: Cleanup
1. Delete 4 debug test files
2. Create new directory structure
3. Move and rename 5 production test files
4. Fix hardcoded URLs in e2e-dashboard.spec.ts
5. Update API port from 8000 → 8123
6. Standardize screenshot paths
7. Update .gitignore for test artifacts

### Phase 3: Fix Tests
1. Run tests against local Docker
2. Fix any broken selectors
3. Update timeouts if needed
4. Verify all tests pass

### Phase 4: Expand Coverage
1. Add briefing modal test
2. Add error state tests
3. Add loading state tests
4. Add empty state test

---

## Test Execution Estimate

- **Smoke tests:** ~20 seconds (9 tests)
- **Feature tests:** ~40 seconds (21 tests)
- **Integration tests:** ~30 seconds (14 tests)
- **E2E tests:** ~20 seconds (4 tests)
- **Total:** ~2 minutes for full suite

---

## Next Steps

1. ✅ Phase 1 complete - Audit done
2. ⏳ Phase 2 - Clean up test suite (in progress)
3. 📋 Phase 3 - Run against local Docker
4. 📋 Phase 4 - Run against staging
5. 📋 Phase 5 - Set up workflow
6. 📋 Phase 6 - Production testing
