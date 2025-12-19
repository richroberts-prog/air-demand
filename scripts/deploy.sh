#!/bin/bash
# Deploy to Digital Ocean production server
# Usage: ./scripts/deploy.sh [--migrate]
#
# This script:
# 1. Checks for uncommitted changes (fails if any)
# 2. Pulls latest from GitHub on production
# 3. Optionally runs migrations
# 4. Restarts services

set -e

PROD_HOST="root@104.236.56.33"
PROD_DIR="/root/air-demand"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Air Demand Deploy ===${NC}"

# Check for uncommitted local changes
if ! git diff --quiet HEAD; then
    echo -e "${RED}ERROR: You have uncommitted changes locally.${NC}"
    echo "Commit and push before deploying:"
    echo "  git add . && git commit -m 'your message' && git push"
    exit 1
fi

# Check if local is ahead of origin
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" != "$REMOTE" ]; then
    echo -e "${RED}ERROR: Local HEAD differs from origin/main.${NC}"
    echo "Push your changes first: git push origin main"
    exit 1
fi

echo -e "${GREEN}Local is clean and synced with origin${NC}"
echo "Deploying commit: $(git log -1 --oneline)"

# Check production for uncommitted changes
echo ""
echo -e "${YELLOW}Checking production...${NC}"
PROD_STATUS=$(ssh $PROD_HOST "cd $PROD_DIR && git status --porcelain")
if [ -n "$PROD_STATUS" ]; then
    echo -e "${RED}WARNING: Production has uncommitted changes:${NC}"
    echo "$PROD_STATUS"
    read -p "Discard production changes and continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    ssh $PROD_HOST "cd $PROD_DIR && git checkout -- . && git clean -fd"
fi

# Pull on production
echo ""
echo -e "${YELLOW}Pulling latest on production...${NC}"
ssh $PROD_HOST "cd $PROD_DIR && git pull origin main"

# Run migrations if requested
if [ "$1" == "--migrate" ]; then
    echo ""
    echo -e "${YELLOW}Running migrations...${NC}"
    ssh $PROD_HOST "cd $PROD_DIR && /root/.local/bin/uv run alembic upgrade head"
fi

# Restart services
echo ""
echo -e "${YELLOW}Restarting services...${NC}"
ssh $PROD_HOST "systemctl restart air-demand-scheduler air-demand-api"
sleep 2

# Verify
echo ""
echo -e "${YELLOW}Verifying services...${NC}"
ssh $PROD_HOST "systemctl status air-demand-scheduler air-demand-api --no-pager | grep -E 'Active:|●'"

echo ""
echo -e "${GREEN}Deploy complete!${NC}"
echo "Production is now at: $(ssh $PROD_HOST "cd $PROD_DIR && git log -1 --oneline")"
