#!/bin/bash
set -e

# Deploy Next.js dashboard to remote server
# Usage: ./deploy-dashboard.sh [SERVER_IP]

SERVER_IP=${1:-"161.35.135.71"}
DASHBOARD_DIR="/root/air-demand/dashboard"
API_URL="http://localhost:8123"

echo "🚀 Deploying dashboard to $SERVER_IP..."

# SSH to server and deploy dashboard
ssh root@$SERVER_IP << 'ENDSSH'
set -e

# Navigate to dashboard directory
cd /root/air-demand/dashboard

echo "📦 Installing Node.js if needed..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "🔧 Installing dashboard dependencies..."
npm ci

echo "🏗️ Building dashboard..."
npm run build

echo "⚙️ Setting up systemd service..."
cat > /etc/systemd/system/air-demand-dashboard.service << 'EOF'
[Unit]
Description=Air Demand Dashboard
After=network.target air-demand-api.service
Requires=air-demand-api.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/air-demand/dashboard
Environment="NODE_ENV=production"
Environment="PORT=3000"
Environment="NEXT_PUBLIC_API_URL=http://localhost:8123"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=air-demand-dashboard

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Reloading systemd and starting dashboard..."
systemctl daemon-reload
systemctl enable air-demand-dashboard
systemctl restart air-demand-dashboard

echo "✅ Dashboard deployed successfully!"
systemctl status air-demand-dashboard --no-pager

ENDSSH

echo "✅ Dashboard deployment complete!"
echo "🌐 Dashboard should be accessible at: http://$SERVER_IP:3000"
echo ""
echo "Check status with: ssh root@$SERVER_IP 'systemctl status air-demand-dashboard'"
echo "View logs with: ssh root@$SERVER_IP 'journalctl -u air-demand-dashboard -f'"
