---
type: task
description: Deploy air-demand to new Digital Ocean staging droplet for testing
tags: [deployment, staging, digital-ocean, testing]
status: in_progress
---

# Staging Droplet Deployment

## Overview

Deploy air-demand to a **new Digital Ocean droplet** for independent testing before touching production.

**Benefits:**
- ✅ Test deployment process safely
- ✅ Validate everything works end-to-end
- ✅ Keep current production running
- ✅ No risk to existing system
- ✅ Clean migration path

---

## Step 1: Create New Digital Ocean Droplet

### Droplet Specifications

**Recommended Specs:**
- **Distribution:** Ubuntu 24.04 LTS
- **Plan:** Basic (sufficient for testing)
  - Regular: $6/mo (1GB RAM, 1 vCPU, 25GB SSD)
  - Or same as production if you want matching specs
- **Datacenter:** Same as production (likely NYC or SFO)
- **Authentication:** SSH key (use existing or create new)
- **Hostname:** `air-demand-staging` or `air-demand-test`

### Create Droplet via Dashboard

1. Go to https://cloud.digitalocean.com/droplets
2. Click "Create Droplet"
3. Select specifications above
4. Add your SSH key
5. Create droplet
6. Note the IP address (e.g., `xxx.xxx.xxx.xxx`)

### Or via CLI (doctl)

```bash
# Install doctl if not already installed
# brew install doctl  # macOS
# snap install doctl  # Ubuntu

# Authenticate
doctl auth init

# List available sizes
doctl compute size list

# Create droplet
doctl compute droplet create air-demand-staging \
  --image ubuntu-24-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc1 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -1) \
  --wait

# Get IP address
doctl compute droplet list air-demand-staging --format PublicIPv4 --no-header
```

---

## Step 2: Update Deployment Script for Staging

Create a staging-specific deployment script:

```bash
# Copy and modify deploy script
cp scripts/deploy-do-droplet.sh scripts/deploy-do-droplet-staging.sh
```

**Edit `scripts/deploy-do-droplet-staging.sh`:**

Change the database connection to use the **existing production database** (for testing with real data):

```bash
# Line ~47: Update DATABASE_URL to use production database
# NOTE: Set this to your actual production database URL
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database?ssl=require
```

**Important:**
- Use production database in READ-ONLY mode for testing
- Or create a copy of production database for staging
- This lets you test with real data without affecting production

**Other changes:**
```bash
# Update APP_NAME
APP_NAME="Air Demand Staging"

# Update DIGEST_RECIPIENT (send to yourself for testing)
DIGEST_RECIPIENT=your-email@example.com

# Keep other credentials the same
```

---

## Step 3: Push Code to GitHub

```bash
# Ensure all changes committed
git status

# Push to GitHub
git push origin main

# Verify
git log --oneline -3
```

---

## Step 4: Deploy to Staging Droplet

### Prepare Environment

```bash
# Set your GitHub personal access token
export GITHUB_TOKEN="your_github_token_here"

# Set staging droplet IP
export STAGING_IP="xxx.xxx.xxx.xxx"  # Your new droplet IP
```

### Option A: Run Script Locally (Recommended)

```bash
# Copy staging script to droplet
scp scripts/deploy-do-droplet-staging.sh root@$STAGING_IP:/tmp/

# Copy GitHub token (temporary)
echo $GITHUB_TOKEN | ssh root@$STAGING_IP "cat > /tmp/github_token.txt"

# If you need Paraform session:
# scp /path/to/paraform_session_b64.txt root@$STAGING_IP:/tmp/

# SSH to droplet and run
ssh root@$STAGING_IP "export GITHUB_TOKEN=\$(cat /tmp/github_token.txt) && bash /tmp/deploy-do-droplet-staging.sh"
```

### Option B: Run from Droplet

```bash
# SSH to droplet
ssh root@$STAGING_IP

# Set token
export GITHUB_TOKEN="your_token_here"

# Download and run script
curl -o /tmp/deploy.sh https://raw.githubusercontent.com/richroberts-prog/air-demand/main/scripts/deploy-do-droplet-staging.sh
bash /tmp/deploy.sh
```

---

## Step 5: Initial Validation

### Check Services Started

```bash
ssh root@$STAGING_IP "systemctl status air-demand-scheduler air-demand-api"
```

**Expected output:**
- Both services: `active (running)`
- No errors in status

### Test Health Endpoints

```bash
# Database health
curl http://$STAGING_IP:8123/health/db

# Overall health
curl http://$STAGING_IP:8123/health

# Readiness
curl http://$STAGING_IP:8123/health/ready
```

**Expected:** All return healthy status

### Check API Documentation

```bash
# Open in browser
open http://$STAGING_IP:8123/docs

# Or test with curl
curl http://$STAGING_IP:8123/openapi.json | jq .info
```

### View Logs

```bash
# API logs
ssh root@$STAGING_IP "journalctl -u air-demand-api -n 50"

# Scheduler logs
ssh root@$STAGING_IP "journalctl -u air-demand-scheduler -n 50"
```

---

## Step 6: Functional Testing

### Test Database Connection

```bash
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.check_health"
```

**Expected:**
- Shows last scrape time
- Shows last digest time
- Both from production database

### Test API Endpoints

```bash
# List roles (paginated)
curl "http://$STAGING_IP:8123/demand/roles?limit=5" | jq .

# Get specific role (use ID from production)
curl "http://$STAGING_IP:8123/demand/roles/1" | jq .

# Get role counts
curl "http://$STAGING_IP:8123/demand/roles/stats" | jq .
```

### Test Manual Scrape (Optional - BE CAREFUL)

**WARNING:** Only do this if you want to test scraping. This will:
- Hit Paraform with the staging server
- Create new data in the database

```bash
# Only run if you want to test scraping
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.run_scrape_now"
```

**Alternative:** Just monitor the scheduled scrape
```bash
# Watch scheduler logs
ssh root@$STAGING_IP "journalctl -u air-demand-scheduler -f"
```

### Test Digest Generation (Send to yourself)

```bash
# Test digest email (goes to DIGEST_RECIPIENT in .env)
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.send_digest"
```

**Check your email** for the digest.

---

## Step 7: Monitor for 24-48 Hours

### Set Up Monitoring Cron

```bash
ssh root@$STAGING_IP

# Add health monitoring
crontab -e

# Add this line:
*/5 * * * * /root/air-demand/scripts/monitor_health.sh
```

### Check Logs Daily

```bash
# Check health log
ssh root@$STAGING_IP "tail -20 /var/log/air-demand-health.log"

# Check for errors in API
ssh root@$STAGING_IP "journalctl -u air-demand-api --since '1 day ago' | grep -i error"

# Check for errors in scheduler
ssh root@$STAGING_IP "journalctl -u air-demand-scheduler --since '1 day ago' | grep -i error"
```

### Monitor Scrapes

```bash
# Check recent scrapes
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.check_health"
```

**Expected:**
- Scrapes run on schedule (SCRAPE_HOURS in .env)
- Digests send on schedule (DIGEST_HOUR in .env)
- No errors in logs

---

## Step 8: Validation Checklist

After 24-48 hours of stable operation:

### Core Functionality
- [ ] Services stay running (no restarts/crashes)
- [ ] Health checks always return healthy
- [ ] Database queries work correctly
- [ ] No memory leaks (check with `htop`)

### Scraping
- [ ] Scheduled scrapes execute on time
- [ ] Roles are discovered and saved
- [ ] Change detection works
- [ ] No scraping errors

### Qualification & Scoring
- [ ] Roles are qualified correctly
- [ ] Scores are calculated
- [ ] Enrichment data is fetched

### Digest
- [ ] Digest emails send on schedule
- [ ] Email formatting is correct
- [ ] Right roles are selected
- [ ] Links work

### API
- [ ] All endpoints respond
- [ ] Pagination works
- [ ] Filtering works
- [ ] No timeout errors

### Performance
- [ ] Response times acceptable (<500ms)
- [ ] CPU usage reasonable (<50% average)
- [ ] Memory usage stable
- [ ] Disk usage acceptable

---

## Step 9: Production Cutover Plan

Once staging validates successfully, you have options:

### Option A: Promote Staging to Production (Recommended)

**Steps:**
1. **Update DNS/Load Balancer**
   - Point your domain to new staging IP
   - Update any external services

2. **Rename Droplet**
   - Rename `air-demand-staging` → `air-demand-production`
   - Update hostname: `hostnamectl set-hostname air-demand-production`

3. **Disable Staging Labels**
   - Update `.env`: `APP_NAME="Air Demand"` (remove "Staging")
   - Update digest recipient to production email
   - Restart services: `systemctl restart air-demand-scheduler air-demand-api`

4. **Archive Old Droplet**
   - Power off old droplet (104.236.56.33)
   - Wait 1 week
   - Delete if no issues

### Option B: Deploy to Existing Production Droplet

**Steps:**
1. **Backup Current Production**
   ```bash
   ssh root@104.236.56.33 "cd /root && tar -czf air-backup-$(date +%Y%m%d).tar.gz air/"
   ```

2. **Deploy air-demand**
   ```bash
   # From local machine
   export PROD_IP="104.236.56.33"
   ./scripts/deploy.sh --migrate
   ```

3. **Validate Production**
   - Same validation steps as staging
   - Monitor closely for first 48 hours

4. **Destroy Staging Droplet**
   - Once production validates
   - Delete staging droplet

### Option C: Keep Both (Staging + Production)

**Steps:**
1. Promote staging to production (Option A)
2. Keep old droplet as backup
3. Eventually set up new staging for future changes

---

## Rollback Plan

If issues found during validation:

### Immediate Rollback
```bash
# Stop services on staging
ssh root@$STAGING_IP "systemctl stop air-demand-scheduler air-demand-api"

# No changes to production needed - it's still running
```

### Debug Issues
```bash
# Check logs
ssh root@$STAGING_IP "journalctl -u air-demand-api -n 200"
ssh root@$STAGING_IP "journalctl -u air-demand-scheduler -n 200"

# Check database connection
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -c 'from app.core.database import engine; print(engine.url)'"

# Check environment
ssh root@$STAGING_IP "cat /root/air-demand/.env | grep -v PASSWORD | grep -v TOKEN | grep -v KEY"
```

### Fix and Redeploy
```bash
# Make fixes locally
# Commit and push
git add .
git commit -m "fix: description"
git push origin main

# Pull on staging
ssh root@$STAGING_IP "cd /root/air-demand && git pull origin main && systemctl restart air-demand-scheduler air-demand-api"
```

---

## Cost Considerations

### Staging Droplet
- **$6/month** for smallest droplet (1GB RAM)
- Can delete after validation if not needed

### Production Options
1. **Single droplet:** $6-12/month (delete staging after cutover)
2. **Staging + Production:** $12-24/month (keep both)

### Database
- Current production database shared (no additional cost)
- Or create separate staging database if preferred

---

## Security Considerations

### SSH Access
```bash
# Only allow SSH key authentication (disable password)
ssh root@$STAGING_IP

# Edit sshd config
nano /etc/ssh/sshd_config

# Ensure these settings:
PasswordAuthentication no
PermitRootLogin prohibit-password

# Restart SSH
systemctl restart sshd
```

### Firewall
```bash
# Enable UFW firewall
ssh root@$STAGING_IP "ufw allow OpenSSH && ufw allow 8123/tcp && ufw --force enable"

# Check status
ssh root@$STAGING_IP "ufw status"
```

### Environment Variables
```bash
# Ensure .env has strict permissions
ssh root@$STAGING_IP "chmod 600 /root/air-demand/.env"
```

---

## Quick Reference

### Staging Droplet Commands

```bash
# Health check
curl http://$STAGING_IP:8123/health

# View logs
ssh root@$STAGING_IP "journalctl -u air-demand-api -f"

# Restart services
ssh root@$STAGING_IP "systemctl restart air-demand-scheduler air-demand-api"

# Check health script
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.check_health"

# Manual scrape
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.run_scrape_now"

# Send test digest
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.send_digest"
```

### Local Development

```bash
# Push changes
git push origin main

# Pull on staging
ssh root@$STAGING_IP "cd /root/air-demand && git pull origin main"

# Restart after pull
ssh root@$STAGING_IP "systemctl restart air-demand-scheduler air-demand-api"
```

---

## Next Steps

1. **Create Staging Droplet** on Digital Ocean
2. **Update Script** with staging-specific config
3. **Push to GitHub** (`git push origin main`)
4. **Deploy to Staging** using deploy script
5. **Validate** all functionality works
6. **Monitor** for 24-48 hours
7. **Choose Cutover Strategy** (A, B, or C above)
8. **Execute Cutover** when confident
9. **Archive Old System** after 1 week stable operation

**Ready to create the staging droplet?**
