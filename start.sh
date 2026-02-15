#!/bin/bash

# Quick Start Script - Start both backend and frontend

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

echo "🚀 Starting AI Betting System"
echo "=============================="
echo ""

# Check if already running
if [ -f ".backend.pid" ] && ps -p $(cat .backend.pid) > /dev/null 2>&1; then
    print_warning "Backend already running!"
    read -p "Restart? (y/n): " RESTART
    if [ "$RESTART" == "y" ]; then
        ./stop.sh
        sleep 2
    else
        exit 0
    fi
fi

# Ensure logs directory exists
mkdir -p logs

# Check for venv
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Run ./deploy.sh first!"
    exit 1
fi

# Check PM2
if command -v pm2 &> /dev/null; then
    print_info "Starting with PM2..."
    pm2 start pm2.config.json
    pm2 save
    print_success "Services started with PM2"
    print_info "View logs: pm2 logs"
    print_info "Monitor: pm2 monit"
else
    # Start without PM2
    print_info "Starting backend..."
    nohup venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > .backend.pid
    print_success "Backend started (PID: $BACKEND_PID)"
    
    print_info "Starting frontend..."
    cd frontend
    nohup npm run preview -- --port 3000 --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../.frontend.pid
    cd ..
    print_success "Frontend started (PID: $FRONTEND_PID)"
    
    print_info "View logs:"
    echo "  - Backend: tail -f logs/backend.log"
    echo "  - Frontend: tail -f logs/frontend.log"
fi

# Wait for services
print_info "Waiting for services to start..."
sleep 5

# Health check
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Backend is healthy!"
else
    print_warning "Backend health check failed"
fi

echo ""
print_success "System is running! 🎯"
print_info "Access at:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/docs"
echo "  - Frontend: http://localhost:3000"
echo ""
print_info "Stop services: ./stop.sh"
