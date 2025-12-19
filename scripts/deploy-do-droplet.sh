#!/bin/bash
set -e

echo "🚀 Air Demand - DigitalOcean Droplet Setup"
echo "=============================================="
echo ""

# Check for required env var
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ ERROR: GITHUB_TOKEN environment variable required"
    echo "Usage: GITHUB_TOKEN=your_token bash deploy-do-droplet.sh"
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

# Create .env file
echo "⚙️  Creating .env file..."
cat > /root/air-demand/.env <<ENVEOF
# NOTE: Replace these with your actual credentials before running
DATABASE_URL=${DATABASE_URL:-"postgresql+asyncpg://user:pass@host:port/db"}
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-"your_openrouter_key_here"}
SMTP_USER=${SMTP_USER:-"your_smtp_user@example.com"}
SMTP_PASSWORD=${SMTP_PASSWORD:-"your_smtp_password"}
DIGEST_RECIPIENT=${DIGEST_RECIPIENT:-"your-email@example.com"}
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SCHEDULER_TIMEZONE=Europe/London
SCRAPE_HOURS=5,17
DIGEST_HOUR=6
PARAFORM_SESSION_JSON=\$(cat /tmp/paraform_session_b64.txt 2>/dev/null || echo "")
ENVEOF

chmod 600 /root/air-demand/.env
echo "✅ .env file created"

# Install dependencies
echo "📚 Installing dependencies..."
uv sync

# Install Playwright with system dependencies
echo "🌐 Installing Playwright chromium and system dependencies..."
uv run playwright install --with-deps chromium

# Run database migrations
echo "🗄️  Running database migrations..."
uv run alembic upgrade head

# Create systemd service files
echo "⚙️  Creating systemd services..."

# Scheduler service
cat > /etc/systemd/system/air-demand-scheduler.service <<'EOF'
[Unit]
Description=Air Demand Scheduler
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
Description=Air Demand API
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

# Check status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service Status:"
systemctl status air-demand-scheduler --no-pager -l | head -15
echo ""
systemctl status air-demand-api --no-pager -l | head -15
echo ""
echo "🌐 API available at: http://104.236.56.33:8123"
echo "📋 Check logs: journalctl -u air-demand-api -f"
echo "📋 Check logs: journalctl -u air-demand-scheduler -f"
