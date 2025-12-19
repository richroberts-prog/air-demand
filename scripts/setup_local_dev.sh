#!/bin/bash
# Local Development Environment Setup
# Run this on a fresh machine to set up the development environment

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Air Demand Local Setup ===${NC}"
echo ""

# Check if running in WSL on Windows
if grep -qEi "(Microsoft|WSL)" /proc/version &> /dev/null; then
    echo -e "${YELLOW}Detected WSL environment${NC}"
    IS_WSL=true
else
    IS_WSL=false
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Check Docker
echo -e "${YELLOW}[1/7] Checking Docker...${NC}"
if ! command_exists docker; then
    echo -e "${RED}ERROR: Docker not found${NC}"
    if [ "$IS_WSL" = true ]; then
        echo "Install Docker Desktop for Windows and enable WSL2 integration"
        echo "https://www.docker.com/products/docker-desktop"
    else
        echo "Install Docker: https://docs.docker.com/get-docker/"
    fi
    exit 1
fi

if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to Docker daemon${NC}"
    echo "Ensure Docker Desktop is running (Windows) or docker service is started (Linux)"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# 2. Check Python 3.12
echo ""
echo -e "${YELLOW}[2/7] Checking Python 3.12...${NC}"
if ! command_exists python3.12; then
    echo -e "${YELLOW}Python 3.12 not found. Installing...${NC}"
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.12 python3.12-venv python3.12-dev
fi
echo -e "${GREEN}✓ Python 3.12 installed${NC}"

# 3. Check uv
echo ""
echo -e "${YELLOW}[3/7] Checking uv (Python package manager)...${NC}"
if ! command_exists uv; then
    echo -e "${YELLOW}uv not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi
echo -e "${GREEN}✓ uv installed${NC}"

# 4. Create .env if doesn't exist
echo ""
echo -e "${YELLOW}[4/7] Setting up .env file...${NC}"
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env already exists${NC}"
else
    cat > .env << 'EOF'
# =============================================================================
# Local Development Environment Configuration
# =============================================================================

# =============================================================================
# Database Configuration
# =============================================================================

# Local PostgreSQL - Demand database
# Port 5432 - air-demand-db-1 container
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/air_demand_db

# =============================================================================
# LLM Configuration (Pydantic AI + OpenRouter)
# =============================================================================

# OpenRouter API key (get from https://openrouter.ai/keys)
OPENROUTER_API_KEY=your_key_here

# OpenRouter HTTP referer (for tracking)
OPENROUTER_HTTP_REFERER=http://localhost:8123

# OpenRouter app title
OPENROUTER_APP_TITLE=Air Demand Local Dev

# =============================================================================
# Email Configuration (Resend)
# =============================================================================

# Resend API key (get from https://resend.com/api-keys)
RESEND_API_KEY=your_key_here

# Email addresses
EMAIL_FROM=noreply@yourdomain.com
EMAIL_TO=you@example.com

# =============================================================================
# Application Configuration
# =============================================================================

# Environment (development, staging, production)
ENVIRONMENT=development

# API port
PORT=8123

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ Created .env file${NC}"
    echo -e "${YELLOW}⚠ Update .env with your API keys (OPENROUTER_API_KEY, RESEND_API_KEY)${NC}"
fi

# 5. Install Python dependencies
echo ""
echo -e "${YELLOW}[5/7] Installing Python dependencies...${NC}"
uv sync
echo -e "${GREEN}✓ Dependencies installed${NC}"

# 6. Start Docker containers
echo ""
echo -e "${YELLOW}[6/7] Starting Docker containers...${NC}"
docker compose up -d
echo "Waiting for databases to be healthy..."
sleep 10

# Check health
if docker ps | grep -q "air-demand-db-1"; then
    echo -e "${GREEN}✓ Database is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Container started but may not be fully healthy yet. Wait 10 more seconds.${NC}"
    sleep 10
fi

# 7. Run migrations
echo ""
echo -e "${YELLOW}[7/7] Running database migrations...${NC}"
uv run alembic upgrade head
echo -e "${GREEN}✓ Migrations complete${NC}"

# Summary
echo ""
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo ""
echo "Database running:"
docker ps --format "  - {{.Names}}: {{.Status}}" | grep "air-demand-db-1"
echo ""
echo "Next steps:"
echo "  1. Update .env with API keys if needed"
echo "  2. Sync demand database: ./scripts/sync_demand_db.sh"
echo "  3. Run tests: uv run pytest -v"
echo "  4. Start dev server: uv run uvicorn app.main:app --reload --port 8123"
echo ""
echo "Documentation:"
echo "  - Dev guidelines: CLAUDE.md"
echo "  - README: README.md"
