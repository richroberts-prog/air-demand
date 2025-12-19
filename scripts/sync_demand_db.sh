#!/bin/bash
set -e  # Exit on any error

# =============================================================================
# Simple Demand DB Sync (via SSH Tunnel to Production Server)
# =============================================================================
#
# Usage:
#   ./scripts/sync_demand_db.sh
#
# Requirements:
#   - SSH access to production server (root@161.35.135.71)
#   - Database container running locally (air-demand-db-1)
#
# What it does:
#   1. Dumps demand database from production server (already connected to DO)
#   2. Copies dump to local machine
#   3. Restores to local demand-db container
#
# Why this is simpler:
#   - No need to handle Digital Ocean database credentials
#   - Production server already has DB connection configured
#   - Single SSH connection does everything
#
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Syncing Demand DB from Production (Simple Mode) ===${NC}"
echo ""

# Check if database container is running
if ! docker ps --format '{{.Names}}' | grep -q "air-demand-db-1"; then
    echo -e "${RED}ERROR: air-demand-db-1 container not running${NC}"
    echo "Start it with: docker compose up -d db"
    exit 1
fi

PROD_SERVER="root@161.35.135.71"
DUMP_FILE="demand_sync_$(date +%Y%m%d_%H%M%S).dump"
REMOTE_DUMP="/tmp/$DUMP_FILE"
LOCAL_DUMP="/tmp/$DUMP_FILE"

# Step 1: Create dump on production server
echo -e "${GREEN}[1/4] Creating dump on production server...${NC}"

ssh $PROD_SERVER << EOF
    # Use production's database connection (from .env)
    source /root/air-demand/.env

    # Dump demand tables
    cd /root/air-demand

    # Extract DB connection details
    PGHOST=\$(echo \$DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    PGPORT=\$(echo \$DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    PGUSER=\$(echo \$DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    PGPASSWORD=\$(echo \$DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    PGDATABASE=\$(echo \$DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

    export PGPASSWORD

    # Dump demand tables (data + schema)
    # Use pg_dump 18 to match database version
    /usr/lib/postgresql/18/bin/pg_dump -h \$PGHOST -p \$PGPORT -U \$PGUSER -d \$PGDATABASE \
        -Fc \
        -t roles \
        -t role_snapshots \
        -t role_changes \
        -t role_enrichments \
        -t role_briefings \
        -t role_scrape_runs \
        -t companies \
        -t company_enrichments \
        -t user_settings \
        -f $REMOTE_DUMP

    echo "Dump created: $REMOTE_DUMP (\$(ls -lh $REMOTE_DUMP | awk '{print \$5}'))"
EOF

echo -e "${GREEN}✓ Dump created on production${NC}"
echo ""

# Step 2: Copy dump to local machine
echo -e "${GREEN}[2/4] Copying dump to local machine...${NC}"

scp $PROD_SERVER:$REMOTE_DUMP $LOCAL_DUMP

DUMP_SIZE=$(ls -lh "$LOCAL_DUMP" | awk '{print $5}')
echo -e "${GREEN}✓ Dump copied locally ($DUMP_SIZE)${NC}"
echo ""

# Step 3: Drop and recreate local database
echo -e "${GREEN}[3/4] Resetting local demand database...${NC}"

docker exec air-demand-db-1 psql -U postgres -c "DROP DATABASE IF EXISTS air_demand_db;" postgres
docker exec air-demand-db-1 psql -U postgres -c "CREATE DATABASE air_demand_db;" postgres

echo -e "${GREEN}✓ Local database recreated${NC}"
echo ""

# Step 4: Restore to local database
echo -e "${GREEN}[4/4] Restoring to local database...${NC}"

# Copy dump into container
docker cp "$LOCAL_DUMP" air-demand-db-1:/tmp/dump.dump

# Restore (schema + data)
docker exec air-demand-db-1 pg_restore \
    -U postgres \
    -d air_demand_db \
    --no-owner \
    --no-acl \
    /tmp/dump.dump 2>&1 | grep -v "ERROR.*already exists" || true

# Cleanup
docker exec air-demand-db-1 rm /tmp/dump.dump
rm "$LOCAL_DUMP"
ssh $PROD_SERVER "rm $REMOTE_DUMP"

echo -e "${GREEN}✓ Data restored${NC}"
echo ""

# Verification
echo -e "${GREEN}=== Verification ===${NC}"
ROLE_COUNT=$(docker exec air-demand-db-1 psql -U postgres -d air_demand_db -t -c "SELECT COUNT(*) FROM roles;" 2>/dev/null | xargs || echo "0")
SCRAPE_COUNT=$(docker exec air-demand-db-1 psql -U postgres -d air_demand_db -t -c "SELECT COUNT(*) FROM role_scrape_runs;" 2>/dev/null | xargs || echo "0")
CHANGE_COUNT=$(docker exec air-demand-db-1 psql -U postgres -d air_demand_db -t -c "SELECT COUNT(*) FROM role_changes;" 2>/dev/null | xargs || echo "0")

echo "Roles: $ROLE_COUNT"
echo "Scrape Runs: $SCRAPE_COUNT"
echo "Role Changes: $CHANGE_COUNT"
echo ""

if [[ "$ROLE_COUNT" -gt "0" ]]; then
    echo -e "${GREEN}✓ Sync complete!${NC}"
    echo ""
    echo "Local demand database now matches production (as of $(date))."
    echo ""
    echo "Next steps:"
    echo "  - Run tests: uv run pytest app/demand/tests/ -v"
    echo "  - Start dev server: uv run uvicorn app.main:app --reload --port 8123"
else
    echo -e "${RED}⚠ Warning: No roles found in database${NC}"
    echo "Check if dump was successful or if production database has data."
fi
