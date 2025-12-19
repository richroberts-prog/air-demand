#!/bin/bash
set -e

echo "🚀 Air Demand - Staging Droplet Setup"
echo "=============================================="
echo ""

# Check for required env var
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ ERROR: GITHUB_TOKEN environment variable required"
    echo "Usage: GITHUB_TOKEN=your_token bash deploy-do-droplet-staging.sh"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Python 3.12
echo "🐍 Installing Python 3.12..."
apt-get install -y python3.12 python3.12-venv python3-pip git

# Install uv
echo "📥 Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:$PATH"

# Verify installations
echo "✅ Verifying installations..."
uv --version
python3.12 --version

# Clone repository
echo "📂 Cloning repository..."
cd /root
if [ -d "air-demand" ]; then
    echo "Repository already exists, pulling latest..."
    cd air-demand
    git pull origin main
else
    git clone https://${GITHUB_TOKEN}@github.com/richroberts-prog/air-demand.git
    cd air-demand
fi

# Create .env file for STAGING
echo "⚙️  Creating .env file for STAGING environment..."
cat > /root/air-demand/.env <<'ENVEOF'
# =============================================================================
# STAGING ENVIRONMENT CONFIGURATION
# =============================================================================

APP_NAME="Air Demand Staging"
ENVIRONMENT=staging
PORT=8123

# =============================================================================
# Database Configuration (Production DB - Read/Write for staging testing)
# =============================================================================
# NOTE: Set this to your actual database URL
DATABASE_URL=${DATABASE_URL:-"postgresql+asyncpg://user:pass@host:port/db"}

# =============================================================================
# LLM Configuration
# =============================================================================
# NOTE: Set this to your actual OpenRouter API key
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-"your_openrouter_key_here"}

# =============================================================================
# Email Configuration (STAGING - sends to test email)
# =============================================================================
# NOTE: Set these to your actual SMTP credentials
SMTP_USER=${SMTP_USER:-"your_smtp_user@example.com"}
SMTP_PASSWORD=${SMTP_PASSWORD:-"your_smtp_password"}
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# IMPORTANT: Set this to YOUR email for testing
DIGEST_RECIPIENT=${DIGEST_RECIPIENT:-"your-email@example.com"}

# =============================================================================
# Scheduler Configuration
# =============================================================================
SCHEDULER_TIMEZONE=Europe/London

# Scrape schedule (hours in 24h format, comma-separated)
# STAGING: Less frequent scraping to avoid conflicts with production
SCRAPE_HOURS=3,15

# Digest hour (24h format)
# STAGING: Different time from production
DIGEST_HOUR=4

# =============================================================================
# Paraform Session (STAGING - same as production for testing)
# =============================================================================
PARAFORM_SESSION_JSON=$(cat /tmp/paraform_session_b64.txt 2>/dev/null || echo "")

ENVEOF

chmod 600 /root/air-demand/.env
echo "✅ .env file created for STAGING"

# Install dependencies
echo "📚 Installing dependencies..."
uv sync

# Install Playwright with system dependencies
echo "🌐 Installing Playwright chromium and system dependencies..."
uv run playwright install --with-deps chromium

# Run database migrations
echo "🗄️  Running database migrations..."
uv run alembic upgrade head

# Create systemd service files for STAGING
echo "⚙️  Creating systemd services for STAGING..."

# Scheduler service
cat > /etc/systemd/system/air-demand-scheduler.service <<'EOF'
[Unit]
Description=Air Demand Scheduler (Staging)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/air-demand
Environment="PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/.local/bin/uv run python -m app.demand.scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# API service
cat > /etc/systemd/system/air-demand-api.service <<'EOF'
[Unit]
Description=Air Demand API (Staging)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/air-demand
Environment="PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/.local/bin/uv run uvicorn app.main:app --host 0.0.0.0 --port 8123
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable and start services
echo "🚀 Starting services..."
systemctl enable air-demand-scheduler
systemctl enable air-demand-api
systemctl restart air-demand-scheduler
systemctl restart air-demand-api

# Wait for services to start
sleep 5

# Check status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service Status:"
systemctl status air-demand-scheduler --no-pager -l | head -15
echo ""
systemctl status air-demand-api --no-pager -l | head -15
echo ""

# Get droplet IP
DROPLET_IP=$(hostname -I | awk '{print $1}')

echo "🎯 STAGING Environment Deployed!"
echo ""
echo "🌐 API available at: http://$DROPLET_IP:8123"
echo "📖 API docs: http://$DROPLET_IP:8123/docs"
echo "💚 Health check: http://$DROPLET_IP:8123/health"
echo ""
echo "📋 Check logs:"
echo "   journalctl -u air-demand-api -f"
echo "   journalctl -u air-demand-scheduler -f"
echo ""
echo "⚠️  IMPORTANT:"
echo "   1. This is a STAGING environment"
echo "   2. Using PRODUCTION database (be careful!)"
echo "   3. Digest emails go to: $DIGEST_RECIPIENT"
echo "   4. Scrapes run at different times than production (hours: 3,15)"
echo "   5. Update DIGEST_RECIPIENT in .env if needed"
echo ""
echo "🧪 Test commands:"
echo "   cd /root/air-demand && uv run python -m scripts.check_health"
echo "   curl http://$DROPLET_IP:8123/health"
echo "   curl http://$DROPLET_IP:8123/demand/roles?limit=5"
echo ""
