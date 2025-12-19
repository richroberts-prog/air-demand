---
type: task
description: Production cutover from old droplet to validated staging system
tags: [deployment, production, cutover, migration, M11]
status: in_progress
version: 1.1
created: 2025-12-19
updated: 2025-12-19
owner: engineering
priority: high
related:
  - M09-deployment-and-validation.md
  - M10-dashboard-playwright-testing.md
  - IMPLEMENTATION_PLAN.md
---

# M11: Production Cutover Plan

**Goal**: Promote staging droplet (161.35.135.71) to production, pause old production droplet (104.236.56.33) as 1-week backup, then delete.

**Strategy**: Low-risk cutover with full database backup, 1-week safety period, and documented rollback procedure.

---

## Critical Files to Modify

- `.env` on 161.35.135.71 (staging → production config)
- `app/core/config.py` (CORS allowed_origins cleanup)
- `scripts/deploy.sh` (update hardcoded production IP)
- `scripts/sync_demand_db.sh` (update production IP reference)
- `scripts/check_demand_db_staleness.sh` (update production IP reference)
- `.claude/tasks/IMPLEMENTATION_PLAN.md` (add M11 entry)

---

## Phase 1: Pre-Cutover Validation (1 hour)

### 1.1 Final Staging Health Check
```bash
# On staging (161.35.135.71)
ssh root@161.35.135.71

# Verify all health endpoints
curl http://localhost:8123/health | jq '.'
curl http://localhost:8123/health/db | jq '.'
curl http://localhost:8123/health/ready | jq '.'
curl http://localhost:8123/monitoring/errors | jq '.'

# Check service status
systemctl status air-demand-api
systemctl status air-demand-scheduler
systemctl status air-demand-dashboard

# Verify dashboard loads
curl -s http://localhost:3000 | grep "Paraform Roles"
```

**Success Criteria:**
- All health endpoints return 200 OK
- All services in "active (running)" state
- Dashboard renders without errors
- No errors in journalctl logs

### 1.2 Run Full Test Suite
```bash
# From local machine
BASE_URL=http://161.35.135.71:3000 npm test

# Expected: 40/48 tests passing (83%+)
```

### 1.3 Verify Database Connectivity
```bash
# Test production database from staging
ssh root@161.35.135.71 'cd /root/air-demand && uv run python -c "
from app.core.database import engine
import asyncio
from sqlalchemy import text

async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT COUNT(*) FROM roles\"))
        print(f\"Roles count: {result.scalar()}\")

asyncio.run(test())
"'
```

**Success Criteria:** Returns role count (expect ~747 roles)

---

## Phase 2: Database Backup (30 minutes)

### 2.1 Create Full Database Backup

**On staging droplet (which has production DB access):**
```bash
ssh root@161.35.135.71

# Install pg_dump if not present
apt-get update && apt-get install -y postgresql-client

# Create backup directory
mkdir -p /root/backups

# Extract DB credentials from .env
export $(grep DATABASE_URL /root/air-demand/.env | xargs)

# Create backup with timestamp
BACKUP_FILE="/root/backups/production_backup_$(date +%Y%m%d_%H%M%S).sql"

# Run pg_dump (will take ~5-10 minutes for production data)
pg_dump "${DATABASE_URL}" > "${BACKUP_FILE}"

# Verify backup was created
ls -lh "${BACKUP_FILE}"
wc -l "${BACKUP_FILE}"

# Optional: Compress backup
gzip "${BACKUP_FILE}"
ls -lh "${BACKUP_FILE}.gz"
```

### 2.2 Download Backup to Local Machine
```bash
# From local machine
mkdir -p ~/air-demand-backups
scp root@161.35.135.71:/root/backups/production_backup_*.sql.gz ~/air-demand-backups/

# Verify download
ls -lh ~/air-demand-backups/
```

**Success Criteria:**
- Backup file created (expect ~50-100MB compressed)
- Downloaded to local machine for safekeeping
- Backup contains all tables (9 tables: roles, role_briefings, companies, etc.)

---

## Phase 3: Configuration Updates (30 minutes)

### 3.1 Update Staging Environment to Production Config

**On staging droplet (161.35.135.71):**
```bash
ssh root@161.35.135.71
cd /root/air-demand

# Edit .env file
nano .env

# Change these values:
APP_NAME="Air Demand"  # Remove "Staging" suffix
ENVIRONMENT=production  # Change from "staging"

# Update scheduler times to production schedule:
SCRAPE_HOURS=5,17  # Production times (was 3,15 for staging)
DIGEST_HOUR=6      # Production time (was 4 for staging)

# Update digest recipient (if needed):
DIGEST_RECIPIENT=rich.roberts@talentpipe.ai  # Verify correct email

# Save and exit (Ctrl+X, Y, Enter)
```

### 3.2 Restart Services with New Config
```bash
# On staging droplet
systemctl restart air-demand-api
systemctl restart air-demand-scheduler
systemctl restart air-demand-dashboard

# Wait 5 seconds for startup
sleep 5

# Verify services restarted successfully
systemctl status air-demand-api
systemctl status air-demand-scheduler
systemctl status air-demand-dashboard
```

### 3.3 Update CORS Configuration (Repository Changes) ✅ COMPLETE

**Status**: Code changes committed locally, ready to push and deploy.

**Completed Changes:**
- ✅ Updated `app/core/config.py` - CORS allowed_origins (removed 104.236.56.33, added 161.35.135.71)
- ✅ Updated `scripts/deploy.sh` - PROD_HOST to 161.35.135.71
- ✅ Updated `scripts/sync_demand_db.sh` - PROD_SERVER to 161.35.135.71
- ✅ Updated `scripts/check_demand_db_staleness.sh` - SSH host to 161.35.135.71
- ✅ Updated `.claude/tasks/IMPLEMENTATION_PLAN.md` - M11 progress tracked

**Next Steps (manual execution required):**
```bash
cd /home/richr/air-demand

# Commit changes
git add app/core/config.py scripts/deploy.sh scripts/sync_demand_db.sh scripts/check_demand_db_staleness.sh .claude/tasks/IMPLEMENTATION_PLAN.md
git commit -m "chore: update production IP to 161.35.135.71 for M11 cutover"
git push origin main

# Deploy to new production
ssh root@161.35.135.71 'cd /root/air-demand && git pull && systemctl restart air-demand-api'
```

---

## Phase 4: Production Cutover (5 minutes)

### 4.1 Announce Cutover
**Action:** Inform team that 161.35.135.71 is now production.

**New Production URLs:**
- API: `http://161.35.135.71:8123`
- Dashboard: `http://161.35.135.71:3000`
- Health: `http://161.35.135.71:8123/health`

### 4.2 Verify Production is Live
```bash
# From local machine
curl -s http://161.35.135.71:8123/health | jq '.status'  # Should return "healthy"
curl -s http://161.35.135.71:3000 | grep "Paraform Roles"  # Should load dashboard

# Run production smoke tests
BASE_URL=http://161.35.135.71:3000 npx playwright test tests/smoke/production.spec.ts

# Expected: 5/5 tests passing
```

### 4.3 Monitor First Production Cycle
```bash
# Watch logs in real-time
ssh root@161.35.135.71 'journalctl -u air-demand-api -f'

# Monitor scheduler logs
ssh root@161.35.135.71 'journalctl -u air-demand-scheduler -f'

# Check for errors
ssh root@161.35.135.71 'curl -s http://localhost:8123/monitoring/errors | jq .'
```

**Success Criteria:**
- No errors in logs
- Health checks return 200
- Dashboard loads correctly
- Next scheduled scrape runs successfully (wait for 5am or 5pm UTC)

---

## Phase 5: Pause Old Production Droplet (10 minutes)

### 5.1 Stop Services on Old Production
```bash
ssh root@104.236.56.33

# Stop all services gracefully
systemctl stop air-demand-scheduler  # Stop scheduler first (prevents new scrapes)
sleep 10  # Wait for any in-progress scrapes to complete
systemctl stop air-demand-api
systemctl stop air-demand-dashboard  # If running

# Verify services stopped
systemctl status air-demand-api
systemctl status air-demand-scheduler

# Check no background processes
ps aux | grep -E "(uvicorn|python|air-demand)"
```

### 5.2 Pause Droplet via DigitalOcean Console

**Manual Steps:**
1. Log into DigitalOcean console: https://cloud.digitalocean.com/droplets
2. Find droplet with IP 104.236.56.33
3. Click "..." → "Power Off" → "Power Off Droplet"
4. **Do NOT select "Destroy"** - we want to keep it as backup

**Result:**
- Droplet is paused and not accessible
- No hourly charges while powered off
- Can power back on for emergency rollback
- Data preserved on disk

### 5.3 Document Old Droplet Details

**Save this information:**
```
Old Production Droplet (PAUSED - Backup for 1 week)
- IP: 104.236.56.33
- Size: Basic / $6/month
- Region: NYC3
- Status: Powered Off (2025-12-19)
- Database: Same production DB (air-postgres-do-user-30258305-0)
- Delete After: 2025-12-26 (1 week from cutover)
```

---

## Phase 6: Post-Cutover Validation (1 hour)

### 6.1 Full System Health Check
```bash
# Health endpoints
curl http://161.35.135.71:8123/health
curl http://161.35.135.71:8123/health/db
curl http://161.35.135.71:8123/health/ready
curl http://161.35.135.71:8123/monitoring/errors

# API functionality
curl http://161.35.135.71:8123/demand/roles?page_size=5
curl http://161.35.135.71:8123/shared/constants

# Dashboard
curl http://161.35.135.71:3000 | grep "Paraform"
```

### 6.2 Run Full Test Suite
```bash
# From local machine
cd /home/richr/air-demand/dashboard
BASE_URL=http://161.35.135.71:3000 npm test

# Expected: 40/48 tests passing (83%+)
```

### 6.3 Monitor Production Metrics

**Set up continuous monitoring for 24 hours:**
```bash
# On production droplet (161.35.135.71)
ssh root@161.35.135.71

# Create monitoring cron job
echo "*/5 * * * * /root/air-demand/scripts/monitor_health.sh" | crontab -

# Verify cron installed
crontab -l

# Check health log
tail -f /var/log/air-demand-health.log
```

### 6.4 Verify Scheduled Jobs

**Wait for next scheduled scrape (5am or 5pm UTC):**
```bash
# Check scheduler status
ssh root@161.35.135.71 'cd /root/air-demand && uv run python scripts/check_health.py'

# After scrape runs, verify:
# - No errors in logs
# - New roles discovered
# - Database updated
# - No alerts triggered
```

---

## Phase 7: One-Week Monitoring Period (2025-12-19 to 2025-12-26)

### 7.1 Daily Health Checks

**Run daily for 7 days:**
```bash
# Morning check (after 6am UTC digest)
curl http://161.35.135.71:8123/health | jq '.'
curl http://161.35.135.71:8123/monitoring/errors | jq '.'

# Check scheduler ran successfully
ssh root@161.35.135.71 'cd /root/air-demand && uv run python scripts/check_health.py'

# Verify digest email received (if applicable)
# Check inbox for daily digest
```

### 7.2 Monitor for Issues

**Red Flags (trigger rollback):**
- Health checks fail for >1 hour
- Scraper failures for >2 consecutive runs
- Database connectivity issues
- Dashboard not loading
- Error rate >10 errors/hour

**If red flags occur:** See "Rollback Procedure" below.

### 7.3 Success Metrics

**After 7 days, verify:**
- ✅ All scheduled scrapes completed successfully (14 scrapes: 2/day × 7 days)
- ✅ All daily digests sent (7 emails)
- ✅ No database errors
- ✅ Dashboard accessible 24/7
- ✅ Health checks consistently return "healthy"
- ✅ No production incidents

---

## Phase 8: Delete Old Production Droplet (After 1 Week)

**Date:** 2025-12-26 (or later if confident earlier)

### 8.1 Final Pre-Deletion Check
```bash
# Verify new production is stable
curl http://161.35.135.71:8123/health

# Verify 7+ days of successful operation
ssh root@161.35.135.71 'cd /root/air-demand && uv run python scripts/check_health.py'

# Check error monitoring
curl http://161.35.135.71:8123/monitoring/errors | jq '.total_errors'
```

### 8.2 Verify Backup Exists
```bash
# Confirm database backup is downloaded locally
ls -lh ~/air-demand-backups/production_backup_*.sql.gz

# Verify backup is valid (optional - test restore to local DB)
```

### 8.3 Destroy Old Droplet

**Manual Steps:**
1. Log into DigitalOcean console
2. Find droplet 104.236.56.33
3. Click "..." → "Destroy"
4. Type droplet name to confirm
5. Check "I understand this is irreversible"
6. Click "Destroy"

**Result:**
- Old droplet permanently deleted
- IP 104.236.56.33 released back to pool
- Saves $6/month

### 8.4 Update Documentation
```bash
# Update IMPLEMENTATION_PLAN.md
# Mark M11 as completed
# Update production IP references throughout docs
```

---

## Rollback Procedure (Emergency Only)

**If new production fails and old droplet needed:**

### Step 1: Power On Old Droplet
1. DigitalOcean console → Droplets
2. Find 104.236.56.33
3. Click "Power On"
4. Wait ~2 minutes for boot

### Step 2: Start Old Services
```bash
ssh root@104.236.56.33

# Start services
systemctl start air-demand-api
systemctl start air-demand-scheduler

# Verify running
systemctl status air-demand-api
curl http://localhost:8123/health
```

### Step 3: Pause New Production
```bash
ssh root@161.35.135.71

# Stop services to avoid dual-scraping
systemctl stop air-demand-scheduler
systemctl stop air-demand-api
```

### Step 4: Investigate New Production Issues
- Check logs: `journalctl -u air-demand-api -n 1000`
- Check errors: `curl http://localhost:8123/monitoring/errors`
- Review database connectivity
- Fix issues before retry

### Step 5: Re-attempt Cutover
- Address root cause
- Re-run Phase 4 (Production Cutover)
- Continue monitoring

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| New production fails | Low | High | Old droplet kept as 1-week backup; database backup created |
| Data loss | Very Low | Critical | Full pg_dump backup before cutover; DigitalOcean automatic backups |
| Scheduler runs on both droplets | Low | Medium | Stop old scheduler before power off; verify times don't overlap |
| Dashboard downtime | Low | Low | Pre-validated on staging; <5 min cutover window |
| Database connectivity issues | Very Low | High | Already tested on staging; same production DB |

**Overall Risk Level:** Low (validated staging + backup strategy + rollback plan)

---

## Timeline Summary

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** | 1 hour | Pre-cutover validation and testing |
| **Phase 2** | 30 mins | Database backup creation and download |
| **Phase 3** | 30 mins | Configuration updates (env, CORS, scripts) |
| **Phase 4** | 5 mins | Production cutover announcement |
| **Phase 5** | 10 mins | Pause old production droplet |
| **Phase 6** | 1 hour | Post-cutover validation |
| **Phase 7** | 7 days | Monitoring period with daily checks |
| **Phase 8** | 5 mins | Delete old droplet (after 1 week) |

**Total Active Time:** ~3 hours (Phases 1-6)
**Total Calendar Time:** 7-14 days (monitoring + confidence period)

---

## Success Criteria

**Immediate (Day 1):**
- ✅ 161.35.135.71 is serving production traffic
- ✅ All health checks passing
- ✅ Full test suite passing (40/48+)
- ✅ Database backup created and downloaded
- ✅ Old droplet paused successfully

**Week 1 (Days 1-7):**
- ✅ All scheduled scrapes successful (14 runs)
- ✅ All digests sent successfully (7 emails)
- ✅ Zero production incidents
- ✅ Dashboard accessible 24/7
- ✅ Error rate <5/hour

**Final (Day 7+):**
- ✅ Old droplet destroyed
- ✅ Documentation updated
- ✅ M11 marked complete
- ✅ Production running smoothly on 161.35.135.71

---

## Execution Checklist

### Pre-Cutover
- [ ] Staging health checks passing
- [ ] Full test suite passing (40/48+)
- [ ] Database connectivity verified
- [ ] Team notified of cutover window

### Cutover Execution
- [ ] Database backup created
- [ ] Backup downloaded locally
- [ ] .env updated (APP_NAME, ENVIRONMENT, scheduler times)
- [ ] Services restarted with new config
- [x] CORS configuration updated
- [x] Scripts updated (production IP references)
- [ ] Changes committed and deployed

### Post-Cutover
- [ ] Old droplet services stopped
- [ ] Old droplet powered off (not destroyed)
- [ ] New production health checks passing
- [ ] Full test suite passing
- [ ] Monitoring cron job installed
- [ ] First scheduled scrape successful

### Monitoring Period (7 Days)
- [ ] Day 1 health check ✅
- [ ] Day 2 health check ✅
- [ ] Day 3 health check ✅
- [ ] Day 4 health check ✅
- [ ] Day 5 health check ✅
- [ ] Day 6 health check ✅
- [ ] Day 7 health check ✅

### Cleanup
- [ ] Backup verified and stored safely
- [ ] Old droplet destroyed
- [ ] Documentation updated
- [ ] M11 task marked complete
