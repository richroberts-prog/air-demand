---
type: guide
description: Quick-start guide for deploying to staging droplet
tags: [staging, deployment, quickstart]
status: ready
---

# Staging Deployment Quick-Start

Deploy air-demand to a new Digital Ocean droplet for safe testing.

---

## TL;DR

```bash
# 1. Create droplet on Digital Ocean (Ubuntu 24.04, $6/mo minimum)
# 2. Note the IP address
# 3. Push code to GitHub
git push origin main

# 4. Set up staging droplet
export GITHUB_TOKEN="your_github_token"
export STAGING_IP="xxx.xxx.xxx.xxx"  # Your new droplet IP

# 5. Copy script to droplet
scp scripts/deploy-do-droplet-staging.sh root@$STAGING_IP:/tmp/

# 6. Copy GitHub token
echo $GITHUB_TOKEN | ssh root@$STAGING_IP "cat > /tmp/github_token.txt"

# 7. Deploy
ssh root@$STAGING_IP "export GITHUB_TOKEN=\$(cat /tmp/github_token.txt) && bash /tmp/deploy-do-droplet-staging.sh"

# 8. Test
curl http://$STAGING_IP:8123/health
```

---

## Step-by-Step

### 1. Create Digital Ocean Droplet

**Via Dashboard:**
1. Go to https://cloud.digitalocean.com/droplets
2. Click "Create Droplet"
3. Choose:
   - Ubuntu 24.04 LTS
   - Basic plan: $6/mo (1GB RAM)
   - Same datacenter as production
   - Add your SSH key
   - Hostname: `air-demand-staging`
4. Click "Create Droplet"
5. **Copy the IP address** (shown after creation)

**Via CLI:**
```bash
doctl compute droplet create air-demand-staging \
  --image ubuntu-24-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc1 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -1) \
  --wait

# Get IP
doctl compute droplet list air-demand-staging --format PublicIPv4 --no-header
```

### 2. Push Code to GitHub

```bash
# Ensure all commits are pushed
git status
git push origin main
```

### 3. Set Environment Variables

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"  # Your GitHub PAT
export STAGING_IP="xxx.xxx.xxx.xxx"     # Your droplet IP
```

### 4. Deploy to Staging

```bash
# Copy deployment script
scp scripts/deploy-do-droplet-staging.sh root@$STAGING_IP:/tmp/

# Copy GitHub token (temporary, will be deleted after use)
echo $GITHUB_TOKEN | ssh root@$STAGING_IP "cat > /tmp/github_token.txt"

# Run deployment
ssh root@$STAGING_IP "export GITHUB_TOKEN=\$(cat /tmp/github_token.txt) && bash /tmp/deploy-do-droplet-staging.sh"
```

**This will take 5-10 minutes** and will:
- Install Python 3.12, uv, Git
- Clone air-demand from GitHub
- Install dependencies
- Set up database
- Create systemd services
- Start API and scheduler

### 5. Validate Deployment

```bash
# Health check
curl http://$STAGING_IP:8123/health

# Database health
curl http://$STAGING_IP:8123/health/db

# API docs
open http://$STAGING_IP:8123/docs

# Check services
ssh root@$STAGING_IP "systemctl status air-demand-scheduler air-demand-api"

# View logs
ssh root@$STAGING_IP "journalctl -u air-demand-api -n 50"
```

### 6. Test Functionality

```bash
# Check system health
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.check_health"

# List roles
curl "http://$STAGING_IP:8123/demand/roles?limit=5" | jq .

# Test digest (sends to staging email)
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.send_digest"
```

### 7. Monitor

```bash
# Set up health monitoring
ssh root@$STAGING_IP "crontab -e"
# Add: */5 * * * * /root/air-demand/scripts/monitor_health.sh

# Check health log
ssh root@$STAGING_IP "tail -f /var/log/air-demand-health.log"

# Watch API logs
ssh root@$STAGING_IP "journalctl -u air-demand-api -f"
```

---

## Configuration

### Staging vs Production

**Staging Environment:**
- `APP_NAME="Air Demand Staging"`
- `ENVIRONMENT=staging`
- `SCRAPE_HOURS=3,15` (different times than production)
- `DIGEST_HOUR=4` (different time than production)
- `DIGEST_RECIPIENT=your-test-email` (sends to you, not users)

**Same as Production:**
- Database connection (uses production database)
- API keys (OpenRouter, SMTP, etc.)
- Paraform session

**Why share production database?**
- Test with real data
- Validate queries work correctly
- No need to duplicate data

**Be careful:**
- Staging can write to production database
- Scrapes run at different times to avoid conflicts
- Digests go to test email, not production users

---

## Troubleshooting

### Deployment Failed

```bash
# Check logs
ssh root@$STAGING_IP "cat /tmp/deploy.log"

# Restart deployment
ssh root@$STAGING_IP "bash /tmp/deploy-do-droplet-staging.sh"
```

### Services Not Starting

```bash
# Check service status
ssh root@$STAGING_IP "systemctl status air-demand-api -l"
ssh root@$STAGING_IP "systemctl status air-demand-scheduler -l"

# Check logs
ssh root@$STAGING_IP "journalctl -u air-demand-api -n 100"

# Restart services
ssh root@$STAGING_IP "systemctl restart air-demand-scheduler air-demand-api"
```

### Database Connection Issues

```bash
# Test connection
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -c \"
from app.core.database import engine
print(engine.url)
\""

# Check .env
ssh root@$STAGING_IP "cat /root/air-demand/.env | grep DATABASE_URL"
```

### Port 8123 Not Accessible

```bash
# Check firewall
ssh root@$STAGING_IP "ufw status"

# Open port
ssh root@$STAGING_IP "ufw allow 8123/tcp"

# Check if API is listening
ssh root@$STAGING_IP "netstat -tulpn | grep 8123"
```

---

## Next Steps After Validation

Once staging has been running successfully for 24-48 hours:

### Option A: Promote Staging to Production (Recommended)

1. Update DNS to point to staging IP
2. Update `.env`: Remove "Staging" from APP_NAME
3. Update digest recipient to production email
4. Restart services
5. Retire old production droplet

### Option B: Deploy to Existing Production

1. Use `./scripts/deploy.sh` to update production
2. Delete staging droplet

### Option C: Keep Both

1. Use staging IP as new production
2. Keep old production as backup
3. Set up new staging for future testing

---

## Cost

- **Staging droplet:** $6/month (can delete after testing)
- **Production database:** No additional cost (already exists)
- **Total cost during testing:** $6/month
- **After cutover:** Can delete staging to return to $6/month

---

## Security

### Recommended After Deployment

```bash
# Disable password auth
ssh root@$STAGING_IP "sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && systemctl restart sshd"

# Enable firewall
ssh root@$STAGING_IP "ufw allow OpenSSH && ufw allow 8123/tcp && ufw --force enable"

# Set hostname
ssh root@$STAGING_IP "hostnamectl set-hostname air-demand-staging"
```

---

## Quick Reference

```bash
# Environment
export STAGING_IP="xxx.xxx.xxx.xxx"

# Health check
curl http://$STAGING_IP:8123/health

# View logs
ssh root@$STAGING_IP "journalctl -u air-demand-api -f"

# Restart services
ssh root@$STAGING_IP "systemctl restart air-demand-scheduler air-demand-api"

# Check system health
ssh root@$STAGING_IP "cd /root/air-demand && uv run python -m scripts.check_health"

# Pull latest code
ssh root@$STAGING_IP "cd /root/air-demand && git pull origin main && systemctl restart air-demand-scheduler air-demand-api"

# Delete droplet (after testing)
doctl compute droplet delete air-demand-staging
```

---

## Full Documentation

See `.claude/tasks/staging-droplet-deployment.md` for complete details.
