# Migration Plan: Phase 1 (M01-M09) - Demand-Side Code Only

## Executive Summary

Migrate demand-side functionality from `/home/richr/air` to `/home/richr/air-demand` while ensuring **zero supply-side code contamination**.

**Status**:
- ✅ M01-01, M01-02: Foundation already migrated (`app/core/`, `app/shared/`)
- ⏳ M01-03 through M09: Pending (this plan)

**Key Safety Check**: No imports from `app.recruiting` found in `app/jobs/` - demand code is cleanly isolated.

---

## Pre-Migration Validation

Before copying anything, verify boundaries:

1. **Confirm isolation**: `app/jobs/` has NO dependencies on `app.recruiting/` ✅ (already verified)
2. **Structure check**: Old repo has better organization than RECONSTRUCTION_PLAN assumed
   - Actual: `app/jobs/services/`, `app/jobs/scraper/`, `app/jobs/scoring/`
   - Plan assumed: Flat structure with fewer files
3. **Target clean**: Current repo only has `app/core/`, `app/shared/`, `app/tests/`

---

## Migration Strategy: Comprehensive Copy-Then-Fix

**Approach**: Copy entire `app/jobs/` directory at once, then systematically fix imports and validate.

**Rationale**:
- Preserves all dependencies and relationships
- Avoids accidentally missing files
- Simpler than cherry-picking individual files
- Includes tests, queries, notifications, templates, scripts

---

## Migration Tasks (Strict Sequential Execution)

### M01: Copy Entire Jobs Directory

**M01-01: Comprehensive copy**
```bash
# Copy entire app/jobs/ → app/demand/
cp -r /home/richr/air/app/jobs /home/richr/air-demand/app/demand

# Verify copy succeeded
ls -la /home/richr/air-demand/app/demand/
```

Expected structure after copy:
```
app/demand/
├── __init__.py
├── api_types.py
├── briefing_extraction.py
├── digest.py
├── email_builder.py
├── email_service.py
├── enrichment.py
├── models.py
├── qualification.py
├── role_enrichment.py
├── routes.py
├── scheduler.py
├── schemas.py
├── temporal.py
├── notifications/
├── queries/
├── scraper/
├── scoring/
├── scripts/
├── services/
├── templates/
└── tests/
```

**M01-02: Verify no supply-side contamination**
```bash
# Search for any imports from app.recruiting in copied files
cd /home/richr/air-demand
grep -r "from app.recruiting" app/demand/ || echo "✓ Clean - no supply-side imports"
grep -r "import.*recruiting" app/demand/ || echo "✓ Clean - no supply-side imports"
```

If ANY supply-side imports found → STOP and investigate before proceeding.

---

### M02: Update All Import Paths

**M02-01: Global search/replace for imports**

Use careful find/replace across all files in `app/demand/`:
- `from app.jobs.` → `from app.demand.`
- `import app.jobs.` → `import app.demand.`

**M02-02: Update __init__.py files**
- Check all `__init__.py` files for correct exports
- Verify module paths are updated

**M02-03: Verify no old paths remain**
```bash
# Should return no results
grep -r "from app.jobs" app/demand/
grep -r "import app.jobs" app/demand/
```

---

### M03: Register Demand Router in Main App

**M03-01: Update app/main.py**
- Import demand router
- Register with FastAPI app
- Ensure proper prefix and tags

**M03-02: Validate app starts**
```bash
uv run uvicorn app.main:app --reload --port 8123
# Check: http://localhost:8123/docs
# Verify: All demand endpoints appear in Swagger docs
```

---

### M04: Database Migration

**M04-01: Create Alembic migration**
```bash
uv run alembic revision --autogenerate -m "Add demand models from jobs"
# Review generated migration
cat alembic/versions/<new_migration>.py
```

**M04-02: Apply migration**
```bash
uv run alembic upgrade head
```

**M04-03: Verify database schema**
```bash
# Connect to DB and verify tables exist
psql $DATABASE_URL -c "\dt"
```

---

### M05: Run Existing Tests

**M05-01: Update test imports**
- Update imports in `app/demand/tests/` to use `app.demand.*`

**M05-02: Run demand tests**
```bash
# Run just the demand tests
uv run pytest app/demand/tests/ -v

# Expected: Tests pass (may need minor fixes)
```

**M05-03: Run full test suite**
```bash
# Run ALL tests including core/shared
uv run pytest -v

# Expected: All tests pass
```

---

### M06: Type Checking

**M06-01: Fix type errors**
```bash
# Run MyPy
uv run mypy app/

# Fix any errors in app/demand/ code
```

**M06-02: Run Pyright**
```bash
# Run Pyright
uv run pyright app/

# Fix any errors
```

**M06-03: Validate strict mode passes**
- Both MyPy and Pyright must pass in strict mode
- Document any necessary suppressions

---

### M07: Dashboard Migration

**M07-01: Copy dashboard**
```bash
cp -r /home/richr/air/dashboard /home/richr/air-demand/
```

**M07-02: Update API configuration**
- Find API URL config in dashboard
- Change from port 8000 → 8123
- Update any hardcoded paths

**M07-03: Test dashboard**
- Start FastAPI: `uv run uvicorn app.main:app --reload --port 8123`
- Open dashboard
- Verify all pages load
- Verify API calls succeed

---

### M08: Deployment Scripts

**M08-01: Identify relevant scripts**
```bash
# List what's in old repo scripts/
ls -la /home/richr/air/scripts/
```

**M08-02: Copy deployment scripts**
```bash
# Copy demand-related deployment scripts only
# Review each script before copying to avoid supply-side contamination
```

**M08-03: Update paths in scripts**
- Change `/path/to/air` → `/path/to/air-demand`
- Update service names
- Verify environment variables

---

### M09: Side-by-Side Validation

**M09-01: Run both systems in parallel**
- Old: `/home/richr/air` on port 8000
- New: `/home/richr/air-demand` on port 8123
- Duration: 1 week minimum

**M09-02: Compare scraping results**
- Run scraper in both repos
- Export data from both
- Diff the outputs
- Investigate discrepancies

**M09-03: Compare qualification/scoring**
- Process identical job list through both systems
- Compare Q1/Q2 gate decisions
- Compare profitability scores
- Must match exactly

**M09-04: Compare digest generation**
- Generate digest in both systems
- Diff HTML output
- Verify same jobs selected
- Verify same ordering

**M09-05: Fix any discrepancies**
- Document differences
- Root cause analysis
- Fix new repo to match old behavior
- Re-validate

**M09-06: Production cutover**
- Stop old system
- Redirect traffic to new system
- Monitor for issues
- Keep old system available for 48h as backup

---

## Rollback Strategy

At any step, if critical issues arise:

1. **Stop immediately** - Don't proceed to next task
2. **Document the issue** - What broke? What was the symptom?
3. **Rollback**: Use `git reset --hard <previous-commit>` to undo changes
4. **Investigate root cause** before retrying
5. **Update this plan** with lessons learned

---

## Success Criteria

**Per Task**:
- ✅ Files copied without modification (preserve working behavior)
- ✅ Imports updated correctly
- ✅ No supply-side dependencies introduced
- ✅ Tests pass (existing tests remain green)
- ✅ Type checking passes (MyPy + Pyright)

**Overall Migration**:
- ✅ All M01-M09 tasks completed
- ✅ Side-by-side validation shows identical behavior
- ✅ New repo deployed to production
- ✅ Old repo decommissioned

---

## Key Files Summary

**Already migrated** (M01-01, M01-02):
- ✅ `/home/richr/air/app/core/` → `/home/richr/air-demand/app/core/`
- ✅ `/home/richr/air/app/shared/` → `/home/richr/air-demand/app/shared/`

**To migrate** (this plan):
- 📁 `/home/richr/air/app/jobs/` → `/home/richr/air-demand/app/demand/` (entire directory)
- 📁 `/home/richr/air/dashboard/` → `/home/richr/air-demand/dashboard/` (entire directory)
- 📁 `/home/richr/air/scripts/` → `/home/richr/air-demand/scripts/` (demand-related scripts only)

**Migration approach**: Comprehensive copy of entire `app/jobs/` directory preserving all structure, then systematic import updates.

**Contents of app/jobs/ to migrate**:
- Core files: models.py, schemas.py, routes.py, scheduler.py, temporal.py, qualification.py, enrichment.py, role_enrichment.py
- Email/digest: digest.py, briefing_extraction.py, email_builder.py, email_service.py
- Subdirectories: scraper/, scoring/, services/, queries/, notifications/, templates/, scripts/, tests/
- Supporting: api_types.py, __init__.py

**Total size estimate**: ~150,000 lines of demand-side Python code + full dashboard + tests

---

## Validation Checkpoints

After each major task (M01-M09), verify:

**✅ Code Quality**:
- [ ] No syntax errors
- [ ] No supply-side imports (`app.recruiting`)
- [ ] All imports updated to `app.demand.*`

**✅ Tests**:
- [ ] All tests pass (`uv run pytest -v`)
- [ ] No test failures or errors
- [ ] Test imports updated

**✅ Type Safety**:
- [ ] MyPy passes strict mode (`uv run mypy app/`)
- [ ] Pyright passes strict mode (`uv run pyright app/`)

**✅ Application**:
- [ ] FastAPI starts without errors
- [ ] Swagger docs accessible at `/docs`
- [ ] Health check passes at `/health`

**✅ Git**:
- [ ] Changes committed with descriptive message
- [ ] Working tree clean after each task

---

## Notes

- **Supply-side protection**: At each step, grep for `from app.recruiting` imports - if found, STOP and investigate
- **Testing strategy**: Run full test suite after completing each M01-M09 section before moving to next
- **Import updates**: Use global find/replace with verification - don't proceed if imports remain broken
- **Dashboard**: Update API URLs from port 8000 → 8123 in config
- **Scheduler**: Review cron schedules for appropriateness in new environment
- **Commit frequently**: After each successful task validation, commit changes
- **No shortcuts**: If validation fails, fix immediately before proceeding
