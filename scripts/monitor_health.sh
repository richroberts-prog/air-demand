#!/bin/bash
# Health monitoring script for Air Demand production system
# Run via cron: */5 * * * * /root/air-demand/scripts/monitor_health.sh

HEALTH_URL="http://localhost:8123/health"
LOG_FILE="/var/log/air-demand-health.log"

# Fetch health endpoint with timeout
response=$(curl -s -w "\n%{http_code}" --max-time 10 "$HEALTH_URL" 2>&1)
exit_code=$?

# Extract HTTP status code (last line) and body (everything else)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

# Log with timestamp
timestamp=$(date -Iseconds)

if [ $exit_code -ne 0 ]; then
    # Curl failed (network error, timeout, etc.)
    echo "[$timestamp] CURL_FAILED (exit code $exit_code): $body" >> "$LOG_FILE"
elif [ "$http_code" != "200" ]; then
    # HTTP error (503, 500, etc.)
    echo "[$timestamp] UNHEALTHY (HTTP $http_code): $body" >> "$LOG_FILE"
else
    # Healthy
    echo "[$timestamp] OK" >> "$LOG_FILE"
fi
