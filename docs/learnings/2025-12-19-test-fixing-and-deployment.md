---
type: learning
date: 2025-12-19
tags: [testing, deployment, debugging, migration, dashboard]
session: M11 Production Cutover Preparation
related:
  - .claude/tasks/M11-production-cutover.md
  - .claude/tasks/IMPLEMENTATION_PLAN.md
---

# Learnings: Test Fixing and Production Deployment

**Date**: 2025-12-19
**Context**: M11 Production Cutover - Test fixes, dashboard bug fix, deployment automation

---

## Key Learnings

### 1. Test Failures After Migration - App Name Mismatch

**Problem**: After migrating from "Obsidian Agent Project" to "Air Demand", 7 tests failed with assertion errors expecting the old app name.

**Root Cause**:
- `.env` file had `APP_NAME=Air Demand` (new name)
- Tests hardcoded expectations for `"Obsidian Agent Project"` (old name)
- Test mocks didn't account for .env overriding default values

**Files Affected**:
- `app/tests/test_main.py` - 3 tests
- `app/core/tests/test_config.py` - 1 test
- `app/core/tests/test_health.py` - 1 test (different issue)

**Fix**:
```python
# Before (broken)
assert data["message"] == "Obsidian Agent Project"

# After (fixed)
assert data["message"] == "Air Demand"
```

**Learning**: When migrating/renaming a project:
- ✅ Search for hardcoded project names in tests
- ✅ Update test expectations to match new .env values
- ✅ Consider using settings fixtures instead of hardcoded strings

### 2. Enhanced Health Check Breaking Old Test

**Problem**: `test_health_check_returns_healthy` failed because health check was enhanced from simple response to detailed checks.

**Evolution**:
```python
# Old (simple)
{"status": "healthy", "service": "api"}

# New (enhanced)
{
  "status": "healthy",
  "timestamp": "...",
  "checks": {
    "database": {"status": "ok", "latency_ms": 15},
    "last_scrape": {...},
    "email": {...},
    "disk": {...}
  }
}
```

**Fix**: Updated test to match new response structure and mock dependencies:
```python
# Mock database and settings
mock_db = AsyncMock()
with patch("app.core.health.get_settings") as mock_settings:
    response = await health_check(db=mock_db)

assert response["status"] in ["healthy", "degraded"]
assert "checks" in response
assert "database" in response["checks"]
```

**Learning**:
- ✅ When enhancing endpoints, update tests immediately
- ✅ Mock external dependencies properly (db, settings)
- ✅ Test for structure, not exact values (more flexible)

### 3. Database Schema Mismatch - Missing Columns

**Problem**: Briefing tests failed with `column role_briefings.detail_raw_response does not exist`.

**Root Cause**:
- Local database created from old migration
- New code expected columns added in later migration
- Database schema out of sync with model definitions

**Fix**:
```bash
# Drop and recreate database
docker exec air-demand-db-1 psql -U postgres -c "DROP DATABASE air_demand_db;"
docker exec air-demand-db-1 psql -U postgres -c "CREATE DATABASE air_demand_db;"

# Run migrations from scratch
uv run alembic upgrade head
```

**Learning**:
- ✅ When tests fail with "column does not exist", check migration state
- ✅ Fresh database + migrations = clean slate for testing
- ✅ Don't rely on incremental migrations for local testing databases

### 4. Dashboard API Endpoint Bug - Wrong Path After Migration

**Problem**: "View Briefing" button on dashboard didn't work - returned 404 errors.

**Root Cause**:
- Backend migrated from `/jobs/*` routes to `/demand/*` routes
- Frontend `BriefingModal.tsx` still had hardcoded `/api/jobs/` path
- No errors during build (string literal, not type-checked)

**File**: `dashboard/components/BriefingModal.tsx:92`

**Fix**:
```typescript
// Before (broken)
const res = await fetch(`/api/jobs/roles/${paraformId}/briefing`);

// After (fixed)
const res = await fetch(`/api/demand/roles/${paraformId}/briefing`);
```

**Learning**:
- ✅ Search entire codebase for old route paths after migration
- ✅ Use constants for API endpoints instead of string literals
- ✅ E2E tests would have caught this (add briefing button test)
- ✅ TypeScript can't type-check string URL paths

**Better Pattern**:
```typescript
// Future improvement: centralize API paths
const API_ENDPOINTS = {
  briefing: (paraformId: string) => `/api/demand/roles/${paraformId}/briefing`
}
```

### 5. Proactive Execution vs Asking Permission

**Problem**: Claude was providing instructions ("Next, run this command") instead of executing directly.

**Solution**: Added explicit guidance to CLAUDE.md:
```markdown
## ⚡ CRITICAL: Be Proactive and Execute

**DO THINGS INSTEAD OF ASKING THE USER TO DO THEM**

- ✅ DO: Run git commands, commit changes, push to GitHub
- ✅ DO: Run deployment scripts, restart services
- ❌ DON'T: Provide copy-paste commands when you can run them
```

**Learning**:
- ✅ AI agents should default to action when they have the tools
- ✅ Only ask for confirmation on destructive operations
- ✅ Documentation should guide AI behavior explicitly
- ✅ Users expect tools to be used, not just suggested

---

## Test Results

**Before Fixes**: 7 failed, 181 passed, 3 errors (96.3% pass rate)

**After Fixes**: 186 passed, 2 skipped, 1 warning (98.9% pass rate)

**Improvements**:
- ✅ All app name tests passing
- ✅ Enhanced health check test updated
- ✅ Database schema synchronized
- ✅ Briefing modal endpoint fixed
- ✅ Type checking: MyPy 0 errors, Pyright 0 errors on modified files

---

## Deployment Automation

### What Worked Well

1. **Sequential Execution**:
   ```bash
   git add -A
   git commit -m "..."
   git push origin main
   ssh root@161.35.135.71 'cd /root/air-demand && git pull && systemctl restart air-demand-api'
   ssh root@161.35.135.71 'cd /root/air-demand/dashboard && npm run build && systemctl restart air-demand-dashboard'
   ```

2. **Verification Steps**:
   - Health check endpoint validation
   - Service status checks
   - Dashboard accessibility test
   - API endpoint smoke test

3. **Immediate Deployment**:
   - No waiting for manual steps
   - Full automation from code → production
   - ~3 minutes from commit to deployed

### Deployment Checklist

- ✅ Update code (CORS, scripts, dashboard)
- ✅ Fix tests (app name, health check, database)
- ✅ Commit changes with detailed message
- ✅ Push to GitHub
- ✅ Deploy backend (git pull + restart)
- ✅ Deploy dashboard (rebuild + restart)
- ✅ Verify health checks
- ✅ Test critical endpoints
- ✅ Update task tracking

---

## Best Practices Established

### Testing
1. **Always read files before modifying tests** - understand current behavior
2. **Update tests immediately when enhancing features** - don't let them drift
3. **Use fresh databases for schema changes** - avoid migration conflicts
4. **Mock external dependencies properly** - AsyncMock for async functions

### Migration
1. **Search for hardcoded references** - project names, URLs, paths
2. **Update frontend and backend together** - API routes must match
3. **Test after migration** - catch mismatches early
4. **Document breaking changes** - help future developers

### Deployment
1. **Automate everything possible** - git, build, deploy, verify
2. **Verify after each step** - health checks, service status
3. **Document what was deployed** - commit hash, timestamp, changes
4. **Update tracking immediately** - keep plans current

### AI Collaboration
1. **Be explicit in documentation** - guide AI behavior clearly
2. **Default to action** - only ask for destructive operations
3. **Provide tools** - enable automation, don't just describe it
4. **Document learnings** - build institutional knowledge

---

## Action Items for Future

### Code Quality
- [ ] Consider creating API endpoint constants in dashboard
- [ ] Add E2E test for "View Briefing" button flow
- [ ] Extract test fixtures for common mocks (db, settings)

### Documentation
- [ ] Document common test failure patterns
- [ ] Create migration troubleshooting guide
- [ ] Add deployment runbook

### Process
- [ ] Consider pre-commit hook to check for hardcoded URLs
- [ ] Add CI check for API endpoint consistency
- [ ] Create test data fixtures for local development

---

## Summary

**Successes**:
- Fixed 7 test failures systematically
- Resolved dashboard bug (View Briefing button)
- Automated full deployment pipeline
- Documented learnings for future reference
- Improved CLAUDE.md guidance for proactive execution

**Time Investment**:
- Test debugging: ~20 minutes
- Dashboard fix: ~5 minutes
- Deployment: ~3 minutes
- Documentation: ~15 minutes
- **Total**: ~43 minutes

**ROI**: Prevented production bugs, improved test coverage, streamlined deployment, documented knowledge.
