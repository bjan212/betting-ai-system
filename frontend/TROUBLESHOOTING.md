# 🔧 Troubleshooting: "Failed to Fetch Bets"

## Problem Identified

The frontend is running successfully at `http://localhost:4173`, but it's showing **"Failed to fetch bets"** because the **backend API is not running** on `http://localhost:8000`.

---

## ✅ Quick Fix - Start the Backend

### Option 1: Start Backend with Docker (Recommended)

```bash
# Navigate to project root
cd /Users/redabhaj/Desktop/betting-ai-system

# Start all services (backend + database)
docker-compose up -d

# Check if services are running
docker-compose ps

# View backend logs
docker-compose logs -f betting_api
```

### Option 2: Start Backend Manually

```bash
# Navigate to project root
cd /Users/redabhaj/Desktop/betting-ai-system

# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Quick Test Backend

```bash
# Navigate to project root
cd /Users/redabhaj/Desktop/betting-ai-system

# Start backend directly
python -m uvicorn src.api.main:app --reload
```

---

## 🧪 Verify Backend is Running

### Test 1: Health Check

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-02-14T..."
}
```

### Test 2: API Documentation

Open in browser: http://localhost:8000/docs

You should see the FastAPI Swagger documentation.

### Test 3: Top 3 Bets Endpoint

```bash
curl http://localhost:8000/api/v1/betting/top3
```

**Expected Response:**
```json
{
  "recommendations": [
    {
      "rank": 1,
      "event_name": "...",
      "confidence_score": 85.5,
      ...
    }
  ]
}
```

---

## 🔍 Common Issues & Solutions

### Issue 1: Backend Not Installed

**Symptom:** `ModuleNotFoundError` or `command not found: uvicorn`

**Solution:**
```bash
cd /Users/redabhaj/Desktop/betting-ai-system
pip install -r requirements.txt
```

### Issue 2: Database Not Running

**Symptom:** `Connection refused` or `database does not exist`

**Solution:**
```bash
# Start PostgreSQL with Docker
docker-compose up -d postgres

# Or start all services
docker-compose up -d
```

### Issue 3: Port 8000 Already in Use

**Symptom:** `Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn src.api.main:app --port 8001
# Then update frontend .env: VITE_API_URL=http://localhost:8001
```

### Issue 4: Missing API Keys

**Symptom:** Backend starts but endpoints return errors

**Solution:**
```bash
# Edit .env file in project root
cd /Users/redabhaj/Desktop/betting-ai-system
nano .env

# Add required keys:
ODDS_API_KEY=your_odds_api_key
STAKE_API_KEY=your_stake_api_key
DATABASE_URL=postgresql://betting_user:changeme@localhost:5432/betting_ai_db
```

### Issue 5: CORS Error

**Symptom:** Browser console shows CORS error

**Solution:**
Check `config/config.yaml`:
```yaml
api:
  cors:
    enabled: true
    origins:
      - "http://localhost:3000"
      - "http://localhost:4173"  # Add this for preview
```

---

## 📋 Complete Startup Checklist

### Step 1: Start Backend Services

```bash
# Navigate to project root
cd /Users/redabhaj/Desktop/betting-ai-system

# Option A: Docker (Recommended)
docker-compose up -d

# Option B: Manual
source venv/bin/activate
uvicorn src.api.main:app --reload
```

### Step 2: Verify Backend

```bash
# Test health endpoint
curl http://localhost:8000/health

# Should return: {"status":"healthy"}
```

### Step 3: Start Frontend

```bash
# Navigate to frontend
cd /Users/redabhaj/Desktop/betting-ai-system/frontend

# Start preview server
npm run preview

# Or development server
npm run dev
```

### Step 4: Test Frontend

Open browser: http://localhost:4173

You should now see:
- ✅ Top 3 betting recommendations
- ✅ Wallet balance
- ✅ Statistics cards
- ✅ No "Failed to fetch" errors

---

## 🐛 Debugging Steps

### 1. Check Backend Logs

```bash
# If using Docker
docker-compose logs -f betting_api

# If running manually
# Logs will appear in terminal where uvicorn is running
```

### 2. Check Frontend Console

Open browser DevTools (F12) → Console tab

Look for errors like:
- `Failed to fetch`
- `Network Error`
- `CORS policy`
- `404 Not Found`

### 3. Check Network Tab

Browser DevTools → Network tab

Filter by "XHR" or "Fetch"

Look for failed requests to `http://localhost:8000`

### 4. Test API Directly

```bash
# Test each endpoint
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/betting/top3
curl -X POST http://localhost:8000/api/v1/crypto/balance \
  -H "Content-Type: application/json" \
  -d '{"token_symbol":"USDT"}'
```

---

## 🔄 Full System Restart

If nothing works, try a complete restart:

```bash
# 1. Stop everything
cd /Users/redabhaj/Desktop/betting-ai-system
docker-compose down
# Kill any manual processes (Ctrl+C)

# 2. Clean up
docker-compose down -v  # Remove volumes
rm -rf frontend/node_modules/.vite  # Clear Vite cache

# 3. Start fresh
docker-compose up -d
cd frontend
npm run preview
```

---

## 📊 System Status Check

Run this script to check everything:

```bash
#!/bin/bash

echo "🔍 System Status Check"
echo "====================="

# Check backend
echo -n "Backend (port 8000): "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

# Check database
echo -n "Database (port 5432): "
if nc -z localhost 5432 2>/dev/null; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

# Check frontend
echo -n "Frontend (port 4173): "
if curl -s http://localhost:4173 > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

# Check Docker
echo -n "Docker: "
if docker ps > /dev/null 2>&1; then
    echo "✅ Running"
    docker ps --format "table {{.Names}}\t{{.Status}}"
else
    echo "❌ Not running"
fi
```

---

## 🎯 Expected Working State

When everything is working correctly:

### Backend (http://localhost:8000)
- ✅ `/health` returns `{"status":"healthy"}`
- ✅ `/docs` shows Swagger UI
- ✅ `/api/v1/betting/top3` returns recommendations

### Frontend (http://localhost:4173)
- ✅ Dashboard loads
- ✅ Top 3 bets display
- ✅ Wallet balance shows
- ✅ Statistics render
- ✅ No console errors

### Docker Services
```
NAME                STATUS
betting_ai_postgres  Up
betting_ai_redis     Up
betting_ai_api       Up
```

---

## 📞 Still Having Issues?

### Check These Files:

1. **Backend .env** (`/Users/redabhaj/Desktop/betting-ai-system/.env`)
   - DATABASE_URL set correctly
   - API keys configured

2. **Frontend .env** (`/Users/redabhaj/Desktop/betting-ai-system/frontend/.env`)
   - VITE_API_URL=http://localhost:8000

3. **Docker Compose** (`/Users/redabhaj/Desktop/betting-ai-system/docker-compose.yml`)
   - Services defined correctly
   - Ports not conflicting

### Get Detailed Logs:

```bash
# Backend logs
docker-compose logs betting_api --tail=100

# Database logs
docker-compose logs postgres --tail=50

# All logs
docker-compose logs --tail=100
```

---

## ✅ Quick Resolution

**Most Common Fix:**

```bash
# 1. Start backend
cd /Users/redabhaj/Desktop/betting-ai-system
docker-compose up -d

# 2. Wait 10 seconds for services to start
sleep 10

# 3. Test backend
curl http://localhost:8000/health

# 4. Refresh frontend
# Open http://localhost:4173 in browser
```

**That's it! Your "Failed to fetch bets" error should be resolved! 🎉**

---

## 📚 Additional Resources

- Backend README: `/Users/redabhaj/Desktop/betting-ai-system/README.md`
- API Documentation: http://localhost:8000/docs
- Frontend Guide: `DEPLOYMENT.md`
- Architecture: `/Users/redabhaj/Desktop/betting-ai-system/docs/ARCHITECTURE.md`
