---
document_type: implementation_plan
purpose: Migrate working functionality, then optimize systematically
status: draft
version: 3.0
last_updated: 2025-12-19
owner: engineering
related:
  - PRD.md
  - docs/adr/
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

## Task Notation

Format: `M{phase}-{task}` for Migration, `O{phase}-{task}` for Optimization
Status: `[ ]` pending, `[>]` in progress, `[x]` complete

---

## PHASE 1: MIGRATION

Get feature parity working in new repo structure. Copy code, adapt to new structure, validate behavior matches.

### M01: Foundation & Models

- [ ] M01-01: Copy `app/core/` (config, database, logging, middleware)
- [ ] M01-02: Copy `app/shared/` (constants, formatting, models, schemas)
- [ ] M01-03: Copy `app/jobs/models/` → `app/demand/models/`
- [ ] M01-04: Copy `app/jobs/schemas/` → `app/demand/schemas/`
- [ ] M01-05: Update imports for new structure
- [ ] M01-06: Create Alembic migration from existing schema
- [ ] M01-07: Test: DB connection, migrations, health endpoints work

### M02: Scraping

- [ ] M02-01: Copy `app/jobs/services/scraping.py` → `app/demand/services/scraping/`
- [ ] M02-02: Copy `app/jobs/services/incremental_scraping.py` → `app/demand/services/scraping/`
- [ ] M02-03: Update imports and paths
- [ ] M02-04: Test: Can scrape Paraform, data matches old repo output

### M03: Qualification & Scoring

- [ ] M03-01: Copy `app/jobs/services/qualification.py` → `app/demand/services/qualification/`
- [ ] M03-02: Copy `app/jobs/services/scoring.py` → `app/demand/services/scoring/`
- [ ] M03-03: Update imports
- [ ] M03-04: Test: Qualification/scores match old repo exactly

### M04: Enrichment

- [ ] M04-01: Copy `app/jobs/services/enrichment.py` → `app/demand/services/enrichment/`
- [ ] M04-02: Update imports, ensure prompts unchanged
- [ ] M04-03: Test: Enrichment extracts same data as old repo

### M05: Temporal Tracking

- [ ] M05-01: Copy `app/jobs/services/temporal_tracking.py` → `app/demand/services/temporal/`
- [ ] M05-02: Update imports
- [ ] M05-03: Test: Snapshots and change detection work

### M06: API & Dashboard

- [ ] M06-01: Copy `app/jobs/routes.py` → `app/demand/api/routes.py`
- [ ] M06-02: Copy `dashboard/` directory
- [ ] M06-03: Update API URLs in dashboard config
- [ ] M06-04: Test: Dashboard displays data correctly

### M07: Scheduler & Digest

- [ ] M07-01: Copy `app/jobs/scheduler.py` → `app/demand/scheduler/`
- [ ] M07-02: Copy digest generation code
- [ ] M07-03: Update imports and schedules
- [ ] M07-04: Test: Jobs run on schedule, digest emails send

### M08: Deployment

- [ ] M08-01: Copy `scripts/deploy.sh`
- [ ] M08-02: Copy systemd service files
- [ ] M08-03: Update paths for new repo
- [ ] M08-04: Test: Deployment works, services start

### M09: Validation

- [ ] M09-01: Run old and new side-by-side for 1 week
- [ ] M09-02: Compare scraping outputs
- [ ] M09-03: Compare qualification/scoring results
- [ ] M09-04: Compare digest emails
- [ ] M09-05: Fix any discrepancies
- [ ] M09-06: Cutover to new repo

**Migration Success**: Feature parity achieved, deployed, working in production.

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
