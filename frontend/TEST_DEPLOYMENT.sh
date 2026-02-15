#!/bin/bash

# Comprehensive Deployment Testing Script
# Tests both backend API and frontend integration

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing: $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        print_success "PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        print_error "FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# ============================================
# BACKEND API TESTS
# ============================================

print_header "BACKEND API TESTS"

# Test 1: Backend is running
run_test "Backend server is running" "curl -s http://localhost:8000/health"

# Test 2: Health endpoint returns correct status
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    print_success "Health endpoint returns 'healthy'"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "Health endpoint does not return 'healthy'"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 3: API documentation is accessible
run_test "API documentation (/docs)" "curl -s http://localhost:8000/docs | grep -q 'Swagger'"

# Test 4: Top 3 bets endpoint
print_info "Testing /api/v1/betting/top3 endpoint..."
RESPONSE=$(curl -s http://localhost:8000/api/v1/betting/top3)
if [ $? -eq 0 ]; then
    print_success "Top 3 bets endpoint is accessible"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "Response preview: ${RESPONSE:0:100}..."
else
    print_error "Top 3 bets endpoint failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 5: Crypto balance endpoint
print_info "Testing /api/v1/crypto/balance endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/crypto/balance \
    -H "Content-Type: application/json" \
    -d '{"token_symbol":"USDT"}')
if [ $? -eq 0 ]; then
    print_success "Crypto balance endpoint is accessible"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "Crypto balance endpoint failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 6: Betting stats endpoint
run_test "Betting stats endpoint" "curl -s http://localhost:8000/api/v1/betting/stats/summary"

# Test 7: Sports list endpoint
run_test "Sports list endpoint" "curl -s http://localhost:8000/api/v1/betting/sports"

# Test 8: System status endpoint
run_test "System status endpoint" "curl -s http://localhost:8000/api/v1/system/status"

# ============================================
# FRONTEND BUILD TESTS
# ============================================

print_header "FRONTEND BUILD TESTS"

# Test 9: Frontend build exists
if [ -d "dist" ]; then
    print_success "Frontend build directory exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "Frontend build directory not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 10: index.html exists
if [ -f "dist/index.html" ]; then
    print_success "index.html exists in build"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "index.html not found in build"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 11: Assets directory exists
if [ -d "dist/assets" ]; then
    print_success "Assets directory exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    # Count assets
    CSS_COUNT=$(find dist/assets -name "*.css" | wc -l)
    JS_COUNT=$(find dist/assets -name "*.js" | wc -l)
    print_info "Found $CSS_COUNT CSS file(s) and $JS_COUNT JS file(s)"
else
    print_error "Assets directory not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# ============================================
# DEPLOYMENT FILES TESTS
# ============================================

print_header "DEPLOYMENT FILES TESTS"

# Test 12: Dockerfile exists
if [ -f "Dockerfile" ]; then
    print_success "Dockerfile exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "Dockerfile not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 13: nginx.conf exists
if [ -f "nginx.conf" ]; then
    print_success "nginx.conf exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "nginx.conf not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 14: docker-compose.deploy.yml exists
if [ -f "docker-compose.deploy.yml" ]; then
    print_success "docker-compose.deploy.yml exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "docker-compose.deploy.yml not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 15: vercel.json exists
if [ -f "vercel.json" ]; then
    print_success "vercel.json exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "vercel.json not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 16: netlify.toml exists
if [ -f "netlify.toml" ]; then
    print_success "netlify.toml exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "netlify.toml not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 17: deploy.sh exists and is executable
if [ -x "deploy.sh" ]; then
    print_success "deploy.sh exists and is executable"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "deploy.sh not found or not executable"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# ============================================
# ENVIRONMENT CONFIGURATION TESTS
# ============================================

print_header "ENVIRONMENT CONFIGURATION TESTS"

# Test 18: .env file exists
if [ -f ".env" ]; then
    print_success ".env file exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    # Check if VITE_API_URL is set
    if grep -q "VITE_API_URL" .env; then
        print_success "VITE_API_URL is configured"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_warning "VITE_API_URL not found in .env"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    print_warning ".env file not found (optional for production)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 19: .env.production exists
if [ -f ".env.production" ]; then
    print_success ".env.production file exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_warning ".env.production not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# ============================================
# DOCUMENTATION TESTS
# ============================================

print_header "DOCUMENTATION TESTS"

# Test 20: DEPLOYMENT.md exists
if [ -f "DEPLOYMENT.md" ]; then
    print_success "DEPLOYMENT.md exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "DEPLOYMENT.md not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 21: TROUBLESHOOTING.md exists
if [ -f "TROUBLESHOOTING.md" ]; then
    print_success "TROUBLESHOOTING.md exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "TROUBLESHOOTING.md not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 22: QUICK_START.md exists
if [ -f "QUICK_START.md" ]; then
    print_success "QUICK_START.md exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "QUICK_START.md not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 23: README.md exists
if [ -f "README.md" ]; then
    print_success "README.md exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    print_error "README.md not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# ============================================
# FRONTEND PREVIEW SERVER TEST
# ============================================

print_header "FRONTEND PREVIEW SERVER TEST"

print_info "Checking if preview server is accessible..."
if curl -s http://localhost:4173 > /dev/null 2>&1; then
    print_success "Frontend preview server is running"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    # Check if it returns HTML
    if curl -s http://localhost:4173 | grep -q "<!DOCTYPE html>"; then
        print_success "Frontend returns valid HTML"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        print_error "Frontend does not return valid HTML"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
else
    print_warning "Frontend preview server not running (start with: npm run preview)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# ============================================
# SUMMARY
# ============================================

print_header "TEST SUMMARY"

echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo ""

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "Pass Rate: $PASS_RATE%"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    print_success "ALL TESTS PASSED! 🎉"
    echo ""
    echo "Your deployment is ready for production!"
    exit 0
elif [ $PASS_RATE -ge 80 ]; then
    print_warning "MOST TESTS PASSED"
    echo ""
    echo "Your deployment is mostly ready. Review failed tests above."
    exit 0
else
    print_error "MULTIPLE TESTS FAILED"
    echo ""
    echo "Please review the failed tests and fix issues before deploying."
    exit 1
fi
