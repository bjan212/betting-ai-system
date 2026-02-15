#!/bin/bash

# Production Deployment Script for AI Betting System
# Supports both local and Docker deployment

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}\n"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ] || [ ! -d "src" ] || [ ! -d "frontend" ]; then
    print_error "Invalid directory structure!"
    echo "Please run this script from the betting-ai-system root directory"
    exit 1
fi

print_header "AI Betting System Deployment"

# Deployment mode selection
echo "Select deployment mode:"
echo "1) Local (Direct on machine)"
echo "2) Docker (Containerized)"
echo "3) Production PM2 (Process manager)"
read -p "Enter choice [1-3]: " DEPLOY_MODE

case $DEPLOY_MODE in
    1)
        print_info "Deploying locally..."
        ;;
    2)
        print_info "Deploying with Docker..."
        ;;
    3)
        print_info "Deploying with PM2..."
        ;;
    *)
        print_error "Invalid choice!"
        exit 1
        ;;
esac

# Check dependencies
print_header "Checking Dependencies"

if [ "$DEPLOY_MODE" == "2" ]; then
    # Docker deployment
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found! Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker: $(docker --version)"
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose not found!"
        exit 1
    fi
    print_success "Docker Compose: Available"
else
    # Local deployment
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found! Please install Python 3.9+"
        exit 1
    fi
    print_success "Python: $(python3 --version)"
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js not found! Please install Node.js 18+"
        exit 1
    fi
    print_success "Node.js: $(node --version)"
    
    if [ "$DEPLOY_MODE" == "3" ]; then
        if ! command -v pm2 &> /dev/null; then
            print_warning "PM2 not found. Installing..."
            npm install -g pm2
            print_success "PM2 installed"
        else
            print_success "PM2: $(pm2 --version)"
        fi
    fi
fi

# Environment setup
print_header "Environment Configuration"

if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env file with your configuration before continuing"
        read -p "Press enter when ready..."
    else
        print_error ".env.example not found!"
        exit 1
    fi
else
    print_success ".env file exists"
fi

# Docker deployment
if [ "$DEPLOY_MODE" == "2" ]; then
    print_header "Building Docker Images"
    
    # Stop existing containers
    print_info "Stopping existing containers..."
    docker-compose down 2>/dev/null || true
    
    # Build and start
    print_info "Building images..."
    docker-compose build
    
    print_info "Starting services..."
    docker-compose up -d
    
    # Wait for services
    print_info "Waiting for services to be ready..."
    sleep 10
    
    # Check health
    print_info "Checking service health..."
    docker-compose ps
    
    print_success "Docker deployment complete!"
    print_info "Access the system at:"
    echo "  - API: http://localhost:8000"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Grafana: http://localhost:3000 (admin/admin)"
    echo "  - Prometheus: http://localhost:9090"
    
    print_info "View logs: docker-compose logs -f"
    print_info "Stop services: docker-compose down"
    
    exit 0
fi

# Local deployment
print_header "Backend Setup"

# Create virtual environment
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
print_success "Backend dependencies installed"

# Install Polymarket client
print_info "Installing Polymarket client..."
pip install -q py-clob-client
print_success "Polymarket client installed"

# Database setup
print_header "Database Setup"

if [ ! -f "betting_ai.db" ]; then
    print_info "Initializing database..."
    python3 -c "
from src.database.database import init_database
init_database()
print('Database initialized')
" || print_warning "Database initialization failed (may need manual setup)"
else
    print_success "Database already exists"
fi

# Frontend setup
print_header "Frontend Setup"

cd frontend

if [ ! -d "node_modules" ]; then
    print_info "Installing frontend dependencies..."
    npm install
    print_success "Frontend dependencies installed"
else
    print_success "Frontend dependencies already installed"
fi

print_info "Building frontend for production..."
npm run build
print_success "Frontend built"

cd ..

# PM2 deployment
if [ "$DEPLOY_MODE" == "3" ]; then
    print_header "PM2 Deployment"
    
    # Stop existing processes
    print_info "Stopping existing PM2 processes..."
    pm2 delete betting-api 2>/dev/null || true
    pm2 delete betting-frontend 2>/dev/null || true
    
    # Start backend
    print_info "Starting backend with PM2..."
    pm2 start "venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000" \
        --name betting-api \
        --interpreter none \
        --watch src \
        --ignore-watch "logs/*"
    
    # Start frontend (preview mode)
    print_info "Starting frontend with PM2..."
    cd frontend
    pm2 start "npm run preview -- --port 3000 --host 0.0.0.0" \
        --name betting-frontend \
        --interpreter bash
    cd ..
    
    # Save PM2 configuration
    pm2 save
    
    print_success "PM2 deployment complete!"
    print_info "PM2 commands:"
    echo "  - View logs: pm2 logs"
    echo "  - Restart: pm2 restart all"
    echo "  - Stop: pm2 stop all"
    echo "  - Status: pm2 status"
    echo "  - Monitor: pm2 monit"
    
    # Setup startup script
    print_info "Setting up PM2 to start on boot..."
    pm2 startup | tail -n 1 | bash || print_warning "Could not setup startup script (may need sudo)"
    
else
    # Local development mode
    print_header "Starting Services"
    
    print_success "Setup complete!"
    print_info "To start the system, run:"
    echo ""
    echo "Terminal 1 (Backend):"
    echo "  source venv/bin/activate"
    echo "  python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
    echo "Terminal 2 (Frontend):"
    echo "  cd frontend"
    echo "  npm run preview -- --port 3000 --host 0.0.0.0"
    echo ""
    
    read -p "Start services now? (y/n): " START_NOW
    
    if [ "$START_NOW" == "y" ] || [ "$START_NOW" == "Y" ]; then
        print_info "Starting services in background..."
        
        # Start backend in background
        nohup venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > .backend.pid
        print_success "Backend started (PID: $BACKEND_PID)"
        
        # Start frontend in background
        cd frontend
        nohup npm run preview -- --port 3000 --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo $FRONTEND_PID > ../.frontend.pid
        cd ..
        print_success "Frontend started (PID: $FRONTEND_PID)"
        
        sleep 3
        
        print_success "System is running!"
        print_info "Access the system at:"
        echo "  - API: http://localhost:8000"
        echo "  - Docs: http://localhost:8000/docs"
        echo "  - Frontend: http://localhost:3000"
        echo ""
        print_info "View logs:"
        echo "  - Backend: tail -f logs/backend.log"
        echo "  - Frontend: tail -f logs/frontend.log"
        echo ""
        print_info "Stop services:"
        echo "  kill $(cat .backend.pid) $(cat .frontend.pid)"
    fi
fi

print_header "Deployment Complete! 🚀"

# Health check
print_info "Performing health check..."
sleep 5

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Backend is healthy!"
else
    print_warning "Backend health check failed (may still be starting)"
fi

echo ""
print_info "Next steps:"
echo "1. Configure Polymarket credentials in the dashboard"
echo "2. Set environment variables in .env file"
echo "3. Monitor logs for any issues"
echo "4. Access dashboard at http://localhost:3000"
echo ""
print_success "Happy betting! 🎯"
