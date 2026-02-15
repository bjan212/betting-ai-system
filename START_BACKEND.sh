#!/bin/bash

# Quick Start Script for Backend API
# This will install dependencies and start the backend

set -e

echo "🚀 Starting AI Betting Analysis Backend"
echo "========================================"

# Colors
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

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found!"
    echo "Please run this script from the betting-ai-system directory"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

print_info "Python version: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_info "Installing dependencies (this may take a few minutes)..."
pip install --upgrade pip
pip install -r requirements.txt

print_success "Dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env file..."
    cp .env.example .env
    print_success ".env file created"
    print_info "⚠️  Please edit .env and add your API keys"
fi

# Start the backend
print_info "Starting backend API on http://localhost:8000..."
echo ""
print_success "Backend is starting!"
echo ""
echo "📍 API will be available at:"
echo "   - Health: http://localhost:8000/health"
echo "   - Docs:   http://localhost:8000/docs"
echo "   - Top 3:  http://localhost:8000/api/v1/betting/top3"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start uvicorn
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
