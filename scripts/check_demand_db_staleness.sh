#!/bin/bash
set -e

# =============================================================================
# Check Demand DB Staleness
# =============================================================================
#
# Returns exit codes:
#   0 - Data is fresh (no sync needed)
#   1 - Data is stale (sync recommended)
#   2 - Cannot determine (local DB not initialized or production unreachable)
#
# Usage:
#   ./scripts/check_demand_db_staleness.sh [--max-age-hours N]
#
# Options:
#   --max-age-hours N   Consider data stale if older than N hours (default: 12)
#

MAX_AGE_HOURS=12
QUIET=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --max-age-hours)
            MAX_AGE_HOURS="$2"
            shift 2
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 2
            ;;
    esac
done

# Check if local DB is running
if ! docker ps --format '{{.Names}}' | grep -q "demand-db"; then
    if [[ "$QUIET" != "true" ]]; then
        echo "❌ Local demand-db container not running"
        echo "Start with: docker compose up -d demand-db"
    fi
    exit 2
fi

# Get latest scrape time from production
PROD_SCRAPE_TIME=$(ssh root@161.35.135.71 "docker exec air-demand-api-1 python -c \"
import asyncio
from app.core.database import AsyncSessionLocal
from app.demand.models import RoleScrapeRun
from sqlalchemy import select

async def get_latest_scrape():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RoleScrapeRun.started_at)
            .where(RoleScrapeRun.status == 'completed')
            .order_by(RoleScrapeRun.started_at.desc())
            .limit(1)
        )
        scrape = result.scalar_one_or_none()
        if scrape:
            print(scrape.isoformat())

asyncio.run(get_latest_scrape())
\"" 2>/dev/null || echo "")

if [[ -z "$PROD_SCRAPE_TIME" ]]; then
    if [[ "$QUIET" != "true" ]]; then
        echo "⚠️  Cannot determine production scrape time"
    fi
    exit 2
fi

# Get latest scrape time from local DB
LOCAL_SCRAPE_TIME=$(docker exec air-demand-db-1 psql -U postgres -d air_demand_db -t -c \
    "SELECT started_at FROM role_scrape_runs WHERE status = 'completed' ORDER BY started_at DESC LIMIT 1;" \
    2>/dev/null | xargs || echo "")

if [[ -z "$LOCAL_SCRAPE_TIME" ]]; then
    if [[ "$QUIET" != "true" ]]; then
        echo "⚠️  Local database has no scrape data (needs initial sync)"
    fi
    exit 1
fi

# Calculate age in hours
PROD_EPOCH=$(date -d "$PROD_SCRAPE_TIME" +%s)
LOCAL_EPOCH=$(date -d "$LOCAL_SCRAPE_TIME" +%s)
AGE_SECONDS=$((PROD_EPOCH - LOCAL_EPOCH))
AGE_HOURS=$((AGE_SECONDS / 3600))

if [[ $AGE_HOURS -lt 0 ]]; then
    # Local is newer than production (shouldn't happen, but handle it)
    if [[ "$QUIET" != "true" ]]; then
        echo "✓ Local database is current"
        echo "  Production: $PROD_SCRAPE_TIME"
        echo "  Local:      $LOCAL_SCRAPE_TIME"
    fi
    exit 0
fi

if [[ $AGE_HOURS -ge $MAX_AGE_HOURS ]]; then
    if [[ "$QUIET" != "true" ]]; then
        echo "❌ Local database is stale ($AGE_HOURS hours old)"
        echo "  Production: $PROD_SCRAPE_TIME"
        echo "  Local:      $LOCAL_SCRAPE_TIME"
        echo ""
        echo "Recommendation: ./scripts/sync_demand_db.sh"
    fi
    exit 1
else
    if [[ "$QUIET" != "true" ]]; then
        echo "✓ Local database is fresh ($AGE_HOURS hours old)"
        echo "  Production: $PROD_SCRAPE_TIME"
        echo "  Local:      $LOCAL_SCRAPE_TIME"
    fi
    exit 0
fi
