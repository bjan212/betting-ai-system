# 🚀 Quick Start Guide - Fix "Failed to Fetch Bets"

## Problem
Frontend is running but shows **"Failed to fetch bets"** because the backend API is not running.

---

## ✅ Solution: Start the Backend (3 Steps)

### Step 1: Navigate to Backend Directory
```bash
cd /Users/redabhaj/Desktop/betting-ai-system
```

### Step 2: Run the Start Script
```bash
bash START_BACKEND.sh
```

**That's it!** The script will:
- ✅ Create virtual environment (if needed)
- ✅ Install all dependencies
- ✅ Create .env file
- ✅ Start the backend on port 8000

### Step 3: Verify Backend is Running
Open a new terminal and test:
```bash
curl http://localhost:8000/healthcurl http://localhost:8000/health§
```

Expected response:
```json
{"status":"healthy"}
```

---

## 🎯 Alternative: Manual Setup

If the script doesn't work, follow these manual steps:

### 1. Create & Activate Virtual Environment
```bash
cd /Users/redabhaj/Desktop/betting-ai-system

# Create venv (you already did this!)
python3 -m venv venv

# Activate it
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- FastAPI
- Uvicorn
- SQLAlchemy
- Pandas, NumPy
- Scikit-learn, XGBoost
- Web3.py
- And all other dependencies

### 3. Create Environment File
```bash
cp .env.example .env
```

### 4. Start the Backend
```bash
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

## 🧪 Test the Backend

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

### Test 2: API Documentation
Open in browser: **http://localhost:8000/docs**

### Test 3: Top 3 Bets Endpoint
```bash
curl http://localhost:8000/api/v1/betting/top3
```

---

## 🌐 Now Test the Frontend

### Option 1: Preview Server (Already Running)
```bash
cd /Users/redabhaj/Desktop/betting-ai-system/frontend
npm run preview
```

Open: **http://localhost:4173**

### Option 2: Development Server
```bash
cd /Users/redabhaj/Desktop/betting-ai-system/frontend
npm run dev
```

Open: **http://localhost:5173**

---

## ✅ Success Checklist

When everything works, you should see:

### Backend (http://localhost:8000)
- ✅ Terminal shows "Uvicorn running on http://0.0.0.0:8000"
- ✅ `/health` returns `{"status":"healthy"}`
- ✅ `/docs` shows Swagger UI

### Frontend (http://localhost:4173)
- ✅ Dashboard loads
- ✅ Top 3 betting recommendations display
- ✅ Wallet balance shows (may be 0 if not configured)
- ✅ Statistics cards render
- ✅ **NO "Failed to fetch bets" error!**

---

## 🐛 Common Issues

### Issue 1: "ModuleNotFoundError"
**Solution:** Make sure virtual environment is activated
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue 2: "Port 8000 already in use"
**Solution:** Kill the process or use different port
```bash
# Find process
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port
python -m uvicorn src.api.main:app --port 8001
# Then update frontend/.env: VITE_API_URL=http://localhost:8001
```

### Issue 3: Backend starts but endpoints return errors
**Solution:** Check if database is needed
```bash
# The MVP should work without database for basic testing
# If you need full functionality, you'll need to set up PostgreSQL
```

---

## 📊 Two Terminal Setup

For best experience, use two terminals:

### Terminal 1: Backend
```bash
cd /Users/redabhaj/Desktop/betting-ai-system
source venv/bin/activate
python -m uvicorn src.api.main:app --reload
```

### Terminal 2: Frontend
```bash
cd /Users/redabhaj/Desktop/betting-ai-system/frontend
npm run preview
```

---

## 🎉 Quick Commands Reference

```bash
# Start backend (from betting-ai-system/)
bash START_BACKEND.sh

# Or manually:
source venv/bin/activate
python -m uvicorn src.api.main:app --reload

# Start frontend (from betting-ai-system/frontend/)
npm run preview

# Test backend
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# View frontend
open http://localhost:4173
```

---

## 🔄 Restart Everything

If something goes wrong:

```bash
# Stop backend (Ctrl+C in backend terminal)
# Stop frontend (Ctrl+C in frontend terminal)

# Restart backend
cd /Users/redabhaj/Desktop/betting-ai-system
source venv/bin/activate
python -m uvicorn src.api.main:app --reload

# Restart frontend
cd /Users/redabhaj/Desktop/betting-ai-system/frontend
npm run preview
```

---

## 📞 Need More Help?

Check these files:
- **TROUBLESHOOTING.md** - Detailed troubleshooting guide
- **DEPLOYMENT.md** - Full deployment documentation
- **README.md** - Project overview
- **Backend README** - `/Users/redabhaj/Desktop/betting-ai-system/README.md`

---

## 🎯 Expected Result

After following these steps:

1. **Backend running** on http://localhost:8000
2. **Frontend running** on http://localhost:4173
3. **Frontend shows:**
   - Top 3 betting recommendations
   - Wallet balance
   - Statistics
   - **NO errors!**

**Your AI Betting Analysis system is now fully operational! 🎉**
