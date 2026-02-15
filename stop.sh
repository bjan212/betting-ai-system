#!/bin/bash

# Stop all betting AI system services

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

echo "🛑 Stopping AI Betting System"
echo "=============================="
echo ""

# Check if PM2 is running
if command -v pm2 &> /dev/null; then
    if pm2 list | grep -q "betting-"; then
        print_info "Stopping PM2 processes..."
        pm2 stop betting-api betting-frontend 2>/dev/null || true
        pm2 delete betting-api betting-frontend 2>/dev/null || true
        print_success "PM2 processes stopped"
    fi
fi

# Check for PID files
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        print_info "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
        rm .backend.pid
        print_success "Backend stopped"
    else
        print_info "Backend not running"
        rm .backend.pid
    fi
fi

if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        print_info "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
        rm .frontend.pid
        print_success "Frontend stopped"
    else
        print_info "Frontend not running"
        rm .frontend.pid
    fi
fi

# Kill any processes on ports 8000 and 3000
print_info "Checking ports..."

if lsof -ti:8000 > /dev/null 2>&1; then
    print_info "Killing process on port 8000..."
    kill -9 $(lsof -ti:8000) 2>/dev/null || true
    print_success "Port 8000 freed"
fi

if lsof -ti:3000 > /dev/null 2>&1; then
    print_info "Killing process on port 3000..."
    kill -9 $(lsof -ti:3000) 2>/dev/null || true
    print_success "Port 3000 freed"
fi

# Docker containers
if command -v docker &> /dev/null; then
    if docker ps | grep -q "betting_ai"; then
        print_info "Stopping Docker containers..."
        docker-compose down 2>/dev/null || true
        print_success "Docker containers stopped"
    fi
fi

print_success "All services stopped!"
