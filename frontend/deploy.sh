#!/bin/bash

# AI Betting Analysis Frontend - Deployment Script
# Usage: ./deploy.sh [option]
# Options: docker, vercel, netlify, build

set -e

echo "🚀 AI Betting Analysis Frontend Deployment"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if .env exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    print_info "Please edit .env with your configuration"
fi

# Parse command line argument
DEPLOY_TYPE=${1:-build}

case $DEPLOY_TYPE in
    build)
        print_info "Building application for production..."
        npm install
        npm run build
        print_success "Build completed! Output in dist/"
        print_info "Preview with: npm run preview"
        ;;
    
    docker)
        print_info "Building Docker image..."
        docker build -t betting-ai-frontend:latest .
        print_success "Docker image built!"
        
        print_info "Starting container..."
        docker run -d \
            -p 80:80 \
            --name betting-frontend \
            --env-file .env \
            betting-ai-frontend:latest
        
        print_success "Container started!"
        print_info "Access at: http://localhost"
        print_info "View logs: docker logs -f betting-frontend"
        ;;
    
    docker-compose)
        print_info "Deploying with Docker Compose..."
        docker-compose -f docker-compose.deploy.yml up -d
        print_success "Services started!"
        print_info "Access at: http://localhost"
        print_info "View logs: docker-compose -f docker-compose.deploy.yml logs -f"
        ;;
    
    vercel)
        print_info "Deploying to Vercel..."
        
        # Check if vercel CLI is installed
        if ! command -v vercel &> /dev/null; then
            print_error "Vercel CLI not found!"
            print_info "Install with: npm install -g vercel"
            exit 1
        fi
        
        vercel --prod
        print_success "Deployed to Vercel!"
        ;;
    
    netlify)
        print_info "Deploying to Netlify..."
        
        # Check if netlify CLI is installed
        if ! command -v netlify &> /dev/null; then
            print_error "Netlify CLI not found!"
            print_info "Install with: npm install -g netlify-cli"
            exit 1
        fi
        
        npm run build
        netlify deploy --prod --dir=dist
        print_success "Deployed to Netlify!"
        ;;
    
    preview)
        print_info "Starting preview server..."
        npm run build
        npm run preview
        ;;
    
    clean)
        print_info "Cleaning build artifacts..."
        rm -rf dist node_modules/.vite
        print_success "Clean completed!"
        ;;
    
    *)
        print_error "Unknown deployment type: $DEPLOY_TYPE"
        echo ""
        echo "Usage: ./deploy.sh [option]"
        echo ""
        echo "Options:"
        echo "  build           - Build for production (default)"
        echo "  docker          - Build and run Docker container"
        echo "  docker-compose  - Deploy with Docker Compose"
        echo "  vercel          - Deploy to Vercel"
        echo "  netlify         - Deploy to Netlify"
        echo "  preview         - Build and preview locally"
        echo "  clean           - Clean build artifacts"
        exit 1
        ;;
esac

echo ""
print_success "Deployment completed successfully! 🎉"
