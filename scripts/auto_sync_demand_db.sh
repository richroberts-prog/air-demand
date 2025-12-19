#!/bin/bash
set -e

# =============================================================================
# Auto Sync Demand DB (Smart Wrapper)
# =============================================================================
#
# Checks if local database is stale before syncing.
# Only syncs if data is older than threshold (default: 12 hours).
#
# Usage:
#   ./scripts/auto_sync_demand_db.sh [--force] [--max-age-hours N]
#
# Options:
#   --force              Sync regardless of staleness
#   --max-age-hours N    Consider stale if older than N hours (default: 12)
#
# Exit codes:
#   0 - Sync completed or data already fresh
#   1 - Sync failed
#   2 - Cannot determine staleness (safe to sync manually)
#

FORCE=false
MAX_AGE_HOURS=12

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --max-age-hours)
            MAX_AGE_HOURS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Auto Sync Demand DB ===${NC}"
echo ""

# Force sync if requested
if [[ "$FORCE" == "true" ]]; then
    echo -e "${YELLOW}Force mode: syncing regardless of staleness${NC}"
    exec ./scripts/sync_demand_db.sh
fi

# Check staleness
echo "Checking local database freshness..."
if ./scripts/check_demand_db_staleness.sh --max-age-hours "$MAX_AGE_HOURS"; then
    echo -e "${GREEN}✓ Local database is current, no sync needed${NC}"
    exit 0
fi

# If staleness check returned 2 (cannot determine), ask user
if [[ $? -eq 2 ]]; then
    echo -e "${YELLOW}Cannot determine staleness${NC}"
    echo "Sync anyway? (y/N): "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        exec ./scripts/sync_demand_db.sh
    else
        echo "Skipping sync"
        exit 0
    fi
fi

# Data is stale, sync now
echo -e "${YELLOW}Local database is stale, syncing...${NC}"
echo ""
exec ./scripts/sync_demand_db.sh
