---
type: task
description: Migrate working functionality, then optimize systematically
tags: [migration, implementation, roadmap, planning]
status: in_progress
version: 3.1
last_updated: 2025-12-19
owner: engineering
related:
  - PRD.md
  - docs/adr/
  - .claude/tasks/M01-M09-demand-migration.md
---

# Air Demand - Reconstruction Plan

**Approach**: Get it working first, optimize second.

**Phase 1 (Migration)**: Pull functionality across from old repo, maintain feature parity, minimal changes
**Phase 2 (Optimization)**: Systematic improvement with working baseline

---

## Migration Strategy

Copy working code → Validate parity → Deploy → Then optimize

**Why this order:**
- De-risk: Working system is evidence you understand it
- Faster: Deploy value sooner
- Safer: Optimize against known baseline
- Clearer: Separate "make it work" from "make it better"

---

## PHASE 1: MIGRATION

**Status**: 8/10 tasks complete (80%)

**Detailed Execution Plan**: See `.claude/tasks/M01-M09-demand-migration.md` for step-by-step instructions, progress tracking, and completion summaries.

### Migration Tasks Overview

- ✅ **M01**: Copy entire jobs directory (COMPLETED 2025-12-19)
  - Migrated ~150,000 lines of demand-side code
  - Full directory structure preserved

- ✅ **M02**: Update all import paths (COMPLETED 2025-12-19)
  - All `app.jobs.*` → `app.demand.*` conversions complete
  - Zero supply-side imports

- ✅ **M03**: Register demand router (COMPLETED 2025-12-19)
  - 13 endpoints registered at `/demand/*`
  - FastAPI running on port 8123

- ✅ **M04**: Database migration (COMPLETED 2025-12-19)
  - 9 tables created (8 demand + alembic_version)
  - Clean schema, no supply-side contamination

- ✅ **M05**: Run existing tests (COMPLETED 2025-12-19)
  - 186/188 tests passing (98.9%)
  - Core functionality validated

- ✅ **M06**: Type checking (COMPLETED 2025-12-19)
  - MyPy strict mode: 0 errors
  - Pyright: 218 warnings in tests only

- ✅ **M07**: Dashboard migration + cleanup (COMPLETED 2025-12-19)
  - Dashboard copied and configured
  - Obsidian template artifacts removed
  - Database cleanup: `obsidian_db` → `air_demand_db`
  - All branding updated to "Air Demand"
  - Production data synced (747 roles, 14.9K snapshots)

- ✅ **M08**: Deployment scripts (COMPLETED 2025-12-19)
  - 13 scripts migrated (deployment, operations, monitoring)
  - All paths updated (`/root/air` → `/root/air-demand`)
  - Service names updated (`air-*` → `air-demand-*`)
  - Port 8123 configured consistently
  - Python imports updated (`app.jobs.*` → `app.demand.*`)
  - All scripts validated and tested

- ⏳ **M09**: System validation & deployment (IN PROGRESS)
  - ✅ Local validation complete (tests, type checks, API)
  - ✅ GitHub repository configured
  - ⏳ Push to GitHub and deploy to production
  - ⏳ Archive old repository
  - See: `.claude/tasks/M09-validation-deployment.md`

- ⏳ **M10**: Dashboard Playwright testing (PENDING)
  - E2E testing setup for local and production dashboards
  - Automated test suite for continuous validation
  - Establishes testing workflow for future iterations
  - See: `.claude/tasks/M10-dashboard-playwright-testing.md`

**Migration Success Criteria**: Feature parity achieved, deployed, working in production with comprehensive testing.

---

## PHASE 2: OPTIMIZATION

Now improve systematically with working baseline to test against.

### O01: Type Safety

- [ ] O01-01: Add strict MyPy/Pyright config
- [ ] O01-02: Add type hints to all functions
- [ ] O01-03: Fix type errors
- [ ] O01-04: Remove `# type: ignore` suppressions

### O02: Testing

- [ ] O02-01: Add unit tests for qualification logic
- [ ] O02-02: Add unit tests for scoring formulas
- [ ] O02-03: Add integration tests for scraping
- [ ] O02-04: Add E2E tests for critical flows
- [ ] O02-05: Achieve >90% coverage

### O03: Documentation

- [ ] O03-01: Add YAML front matter to all files
- [ ] O03-02: Document all scoring formulas
- [ ] O03-03: Write ADRs for key decisions
- [ ] O03-04: Add docstrings to public APIs

### O04: Code Quality

- [ ] O04-01: Break down 824-line routes.py into modules
- [ ] O04-02: Extract reusable components from scraping code
- [ ] O04-03: Remove dead code and unused imports
- [ ] O04-04: Improve error handling and logging

### O05: Performance

- [ ] O05-01: Add database indexes
- [ ] O05-02: Optimize temporal storage (compression)
- [ ] O05-03: Add caching where appropriate
- [ ] O05-04: Profile and optimize slow queries

### O06: Observability

- [ ] O06-01: Improve structured logging
- [ ] O06-02: Add metrics/monitoring
- [ ] O06-03: Add alerting for failures
- [ ] O06-04: Enhance Langfuse integration

### O07: Features (Optional)

- [ ] O07-01: Improve scoring formulas based on learnings
- [ ] O07-02: Add new quality signals
- [ ] O07-03: Enhance briefing generation
- [ ] O07-04: Add personalization

**Optimization Success**: Code quality measurably improved, production remains stable.

---

## Success Criteria

**Migration Phase (Required)**:
- ✅ All functionality copied and working
- ✅ Feature parity validated
- ✅ Deployed to production
- ✅ Old repo decommissioned

**Optimization Phase (Ongoing)**:
- ✅ Type checking passes (strict mode)
- ✅ >90% test coverage
- ✅ All files documented
- ✅ Performance maintained or improved
- ✅ Zero production incidents from changes
