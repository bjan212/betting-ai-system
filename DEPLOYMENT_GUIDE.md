# 🚀 Deployment Guide - AI Betting System

Complete guide to deploy the AI Betting System on your machine.

---

## 📋 Prerequisites

### Required Software

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **PostgreSQL 16+** (Optional, SQLite used by default)

### Optional Software

- **Docker & Docker Compose** - For containerized deployment
- **PM2** - For process management (`npm install -g pm2`)

---

## 🎯 Quick Start (3 Minutes)

### Option 1: Automated Deployment

```bash
cd /Users/redabhaj/Desktop/betting-ai-system

# Run deployment script
./deploy.sh

# Choose deployment mode:
# 1 - Local (Direct)
# 2 - Docker (Containerized)
# 3 - PM2 (Process Manager)
```

The script will:
- ✅ Check all dependencies
- ✅ Set up virtual environment
- ✅ Install Python & Node packages
- ✅ Build frontend
- ✅ Initialize database
- ✅ Start services

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

### Option 2: Manual Deployment

#### Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install py-clob-client

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database (optional, auto-created)
python -c "from src.database.database import init_database; init_database()"

# Start backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
# In new terminal
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Start preview server
npm run preview -- --port 3000 --host 0.0.0.0
```

---

## 🐳 Docker Deployment

### Prerequisites
- Docker & Docker Compose installed

### Deploy with Docker

```bash
cd /Users/redabhaj/Desktop/betting-ai-system

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Services Started:**
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Prometheus (port 9090)
- Grafana (port 3000)

---

## 🔧 PM2 Deployment (Recommended for Production)

### Install PM2

```bash
npm install -g pm2
```

### Deploy with PM2

```bash
cd /Users/redabhaj/Desktop/betting-ai-system

# Option 1: Use deployment script
./deploy.sh
# Choose option 3 (PM2)

# Option 2: Manual PM2 start
pm2 start pm2.config.json
pm2 save

# Setup auto-start on boot
pm2 startup
# Run the command it outputs
```

### PM2 Commands

```bash
# View status
pm2 status

# View logs
pm2 logs

# Real-time monitoring
pm2 monit

# Restart services
pm2 restart all

# Stop services
pm2 stop all

# Delete services
pm2 delete all
```

---

## 📝 Configuration

### Environment Variables (.env)

```bash
# Copy example
cp .env.example .env

# Edit with your settings
nano .env
```

### Key Configuration

#### Polymarket (Betting Platform)

```env
POLYMARKET_PRIVATE_KEY=0x...  # Your Polygon wallet private key
POLYMARKET_FUNDER_ADDRESS=0x...  # Optional, only for proxy wallets
POLYMARKET_SIGNATURE_TYPE=0  # 0=EOA, 1=Magic, 2=Proxy
```

**Get Polygon Wallet:**
1. Install MetaMask
2. Switch to Polygon network
3. Fund with USDC
4. Export private key

#### Sports Data API

```env
ODDS_API_KEY=your_api_key  # Get from https://the-odds-api.com
```

#### ML Model Thresholds

```env
MIN_CONFIDENCE_THRESHOLD=0.70  # 70% minimum confidence
MIN_EXPECTED_VALUE=1.08  # 8% edge after vig
MAX_RISK_SCORE=0.65  # Maximum 65% risk
```

---

## 🎮 Usage

### Start Services

```bash
# Automated start
./start.sh

# Or manually with PM2
pm2 start pm2.config.json

# Or Docker
docker-compose up -d
```

### Stop Services

```bash
# Automated stop
./stop.sh

# Or PM2
pm2 stop all

# Or Docker
docker-compose down
```

### View Logs

```bash
# Local deployment
tail -f logs/backend.log
tail -f logs/frontend.log

# PM2
pm2 logs

# Docker
docker-compose logs -f
```

---

## 🔐 Security Setup

### 1. Configure Polymarket

1. Open dashboard: http://localhost:3000
2. Click "Polymarket Settings"
3. Enter your Polygon private key
4. Save settings

### 2. Set API Keys

Edit `.env`:
```env
ODDS_API_KEY=your_key
SECRET_KEY=generate_random_key_here
```

### 3. Database Security (Production)

If using PostgreSQL:
```env
DATABASE_URL=postgresql://user:strong_password@localhost:5432/betting_ai_db
```

---

## 📊 Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Get recommendations
curl http://localhost:8000/api/v1/betting/top3

# Check Polymarket connection
curl http://localhost:8000/api/v1/betting/polymarket/balance
```

### Prometheus & Grafana (Docker only)

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

---

## 🚨 Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -ti:8000

# Kill process
kill -9 $(lsof -ti:8000)

# Or use stop script
./stop.sh
```

### Backend Not Starting

```bash
# Check Python version
python3 --version  # Should be 3.9+

# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
pip install py-clob-client

# Check logs
tail -f logs/backend.log
```

### Frontend Build Fails

```bash
cd frontend

# Clear cache
rm -rf node_modules dist .vite

# Reinstall
npm install
npm run build
```

### Polymarket Connection Failed

1. Check private key format (must start with 0x)
2. Ensure wallet has USDC on Polygon
3. Verify Polygon RPC is accessible
4. Check firewall settings

### Database Issues

```bash
# Reinitialize database
rm betting_ai.db
python -c "from src.database.database import init_database; init_database()"
```

---

## 🔄 Updates & Maintenance

### Update Code

```bash
# Pull latest changes
git pull origin main

# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

# Restart services
./stop.sh
./start.sh
```

### Backup Database

```bash
# SQLite
cp betting_ai.db betting_ai_backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump betting_ai_db > backup_$(date +%Y%m%d).sql
```

---

## 📈 Performance Tuning

### Backend

**CPU-bound tasks:** Increase workers
```bash
uvicorn src.api.main:app --workers 4 --host 0.0.0.0 --port 8000
```

**Memory:** Adjust in PM2 config
```json
{
  "max_memory_restart": "2G"
}
```

### Frontend

**Build optimization:**
```bash
cd frontend
npm run build -- --mode production
```

---

## 🎯 Production Checklist

- [ ] Set strong `SECRET_KEY` in .env
- [ ] Configure PostgreSQL with strong password
- [ ] Set up SSL/TLS (use nginx reverse proxy)
- [ ] Enable CORS properly in production
- [ ] Set up monitoring (Sentry, Prometheus)
- [ ] Configure backup schedule
- [ ] Set resource limits (PM2/Docker)
- [ ] Review and secure API endpoints
- [ ] Enable rate limiting
- [ ] Set up log rotation
- [ ] Configure firewall rules
- [ ] Test disaster recovery plan

---

## 🌐 Production Deployment (VPS/Cloud)

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Systemd Service (Linux)

```bash
# Copy service file
sudo cp betting-ai.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/betting-ai.service

# Enable and start
sudo systemctl enable betting-ai
sudo systemctl start betting-ai

# Check status
sudo systemctl status betting-ai
```

---

## 📞 Support

### Logs Location

- Backend: `logs/backend.log`
- Frontend: `logs/frontend.log`
- PM2: `~/.pm2/logs/`
- Docker: `docker-compose logs`

### Common Issues

**Issue:** "Module not found"
**Solution:** `pip install -r requirements.txt`

**Issue:** "Port in use"
**Solution:** `./stop.sh` then `./start.sh`

**Issue:** "Permission denied"
**Solution:** `chmod +x deploy.sh start.sh stop.sh`

**Issue:** "Polymarket connection failed"
**Solution:** Check private key, USDC balance, Polygon RPC

---

## 🎉 Success!

Your AI Betting System is now deployed!

**Access Dashboard:** http://localhost:3000

**Next Steps:**
1. Configure Polymarket credentials
2. Set up sports data API keys
3. Monitor first recommendations
4. Place test bet
5. Track performance

**Happy Betting! 🎯**
