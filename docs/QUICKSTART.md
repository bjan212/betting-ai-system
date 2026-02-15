# Quick Start Guide

Get your AI Betting Analysis System up and running in 10 minutes!

## 🎯 Prerequisites

Before you begin, ensure you have:
- Python 3.11 or higher
- PostgreSQL 16+ (or use Docker)
- Git
- 10 GB free disk space

## 📦 Installation

### Option 1: Docker (Recommended for Beginners)

1. **Clone and navigate to the project**
```bash
cd betting-ai-system
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Edit .env with your credentials**
```bash
nano .env  # or use your preferred editor
```

Required variables:
```env
# Database
DATABASE_URL=postgresql://betting_user:changeme@postgres:5432/betting_ai_db

# Stake.com (Get from https://stake.com/settings/api)
STAKE_API_KEY=your_stake_api_key
STAKE_API_SECRET=your_stake_secret

# Crypto Wallet (BSC)
WALLET_PRIVATE_KEY=your_private_key
WALLET_ADDRESS=your_wallet_address
BSC_RPC_URL=https://bsc-dataseed.binance.org/

# Sports Data APIs
ODDS_API_KEY=your_odds_api_key
```

4. **Start all services**
```bash
docker-compose up -d
```

5. **Verify installation**
```bash
docker-compose ps
```

You should see:
- ✅ betting_ai_postgres (healthy)
- ✅ betting_ai_redis (healthy)
- ✅ betting_ai_api (running)
- ✅ betting_ai_prometheus (running)
- ✅ betting_ai_grafana (running)

6. **Initialize database**
```bash
docker-compose exec betting_api python -m src.cli.commands init-db
```

### Option 2: Local Installation

1. **Clone the repository**
```bash
cd betting-ai-system
```

2. **Create virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL**
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE DATABASE betting_ai_db;
CREATE USER betting_user WITH PASSWORD 'changeme';
GRANT ALL PRIVILEGES ON DATABASE betting_ai_db TO betting_user;
\q
```

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

6. **Initialize database**
```bash
python -m src.cli.commands init-db
```

## 🚀 First Run

### Get Top 3 Betting Recommendations

```bash
# Using Docker
docker-compose exec betting_api python -m src.cli.commands top3-bets

# Using local installation
python -m src.cli.commands top3-bets
```

Expected output:
```
🎯 Analyzing Betting Opportunities...

Initializing ML models...
Connecting to database...

✅ Top 3 Betting Recommendations (Next 24 Hours)

🏆 Rank #1: Manchester United vs Liverpool
Sport: Football
Match Time: 2024-02-15 20:00:00

Recommended Bet: Manchester United @ 2.45
Bookmaker: Stake.com

📊 Metrics:
  • Confidence Score: 78.5%
  • Expected Value: +12.3%
  • Win Probability: 52.1%
  • Risk Score: 0.35

💰 Stake Recommendation:
  • Amount: $125.00
  • Percentage: 1.25% of bankroll
...
```

### Check System Status

```bash
# Docker
docker-compose exec betting_api python -m src.cli.commands status

# Local
python -m src.cli.commands status
```

### Check Wallet Balance

```bash
# Docker
docker-compose exec betting_api python -m src.cli.commands balance --currency USDT

# Local
python -m src.cli.commands balance --currency USDT
```

## 🌐 Using the API

### Start API Server

```bash
# Docker (already running)
# Access at http://localhost:8000

# Local
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Test API Endpoints

1. **Health Check**
```bash
curl http://localhost:8000/health
```

2. **Get Top 3 Recommendations**
```bash
curl http://localhost:8000/api/v1/betting/top3
```

3. **Get Upcoming Events**
```bash
curl http://localhost:8000/api/v1/betting/events?sport=football&limit=10
```

4. **Check Wallet Balance**
```bash
curl -X POST http://localhost:8000/api/v1/crypto/balance \
  -H "Content-Type: application/json" \
  -d '{"token_symbol": "USDT"}'
```

### Interactive API Documentation

Visit: http://localhost:8000/docs

This provides:
- Interactive API testing
- Request/response schemas
- Authentication details
- Example requests

## 📊 Monitoring

### Prometheus Metrics
Visit: http://localhost:9090

### Grafana Dashboards
Visit: http://localhost:3000
- Default credentials: admin/admin (change on first login)

## 🎓 Common Commands

### CLI Commands

```bash
# Get top 3 bets
python -m src.cli.commands top3-bets

# Check balance
python -m src.cli.commands balance --currency USDT

# System status
python -m src.cli.commands status

# List upcoming events
python -m src.cli.commands upcoming-events --sport football --limit 20

# Initialize database
python -m src.cli.commands init-db
```

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f betting_api

# Restart a service
docker-compose restart betting_api

# Execute command in container
docker-compose exec betting_api python -m src.cli.commands top3-bets

# Access database
docker-compose exec postgres psql -U betting_user -d betting_ai_db
```

## 🔧 Configuration

### Adjust Recommendation Criteria

Edit `config/config.yaml`:

```yaml
recommendation:
  top3_selection:
    min_confidence: 0.65        # Minimum confidence (0-1)
    min_expected_value: 1.05    # Minimum EV (1.05 = 5%)
    max_risk_score: 0.7         # Maximum risk (0-1)
    time_window_hours: 24       # Analysis window
```

### Adjust ML Model Weights

```yaml
ml_models:
  ensemble:
    models:
      - name: "xgboost"
        weight: 0.35
      - name: "random_forest"
        weight: 0.25
      - name: "deep_rl"
        weight: 0.25
      - name: "bayesian"
        weight: 0.15
```

### Adjust Stake Sizing

```yaml
recommendation:
  stake_sizing:
    method: "kelly_criterion"
    max_stake_percentage: 0.05  # 5% max
    min_stake_amount: 10
    max_stake_amount: 1000
```

## 🐛 Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### API Not Starting

```bash
# Check logs
docker-compose logs betting_api

# Verify environment variables
docker-compose exec betting_api env | grep DATABASE_URL

# Restart API
docker-compose restart betting_api
```

### No Recommendations Found

This is normal if:
- No upcoming events in next 24 hours
- No events meet minimum criteria
- Database is empty (need to populate with events)

To populate test data:
```bash
python -m src.data_ingestion.populate_test_data
```

### Crypto Wallet Connection Error

```bash
# Verify BSC RPC URL
curl https://bsc-dataseed.binance.org/

# Check wallet address format
# Should be: 0x... (42 characters)

# Verify private key is set
echo $WALLET_PRIVATE_KEY
```

## 📚 Next Steps

1. **Populate Historical Data**
   - Import past events and outcomes
   - Train ML models on historical data

2. **Configure Data Sources**
   - Set up Odds API integration
   - Configure Sportradar access
   - Add additional data providers

3. **Customize Models**
   - Adjust hyperparameters
   - Add sport-specific features
   - Implement custom models

4. **Set Up Monitoring**
   - Configure Grafana dashboards
   - Set up alerts
   - Enable Sentry error tracking

5. **Production Deployment**
   - Set up SSL/TLS
   - Configure load balancer
   - Implement backup strategy
   - Set up CI/CD pipeline

## 🆘 Getting Help

- **Documentation**: Check `/docs` directory
- **API Docs**: http://localhost:8000/docs
- **Logs**: `docker-compose logs -f`
- **Issues**: GitHub Issues
- **Community**: Discord/Slack (if available)

## ⚠️ Important Notes

1. **API Keys**: Never commit API keys to version control
2. **Private Keys**: Store securely, never share
3. **Testing**: Always test with small amounts first
4. **Compliance**: Ensure compliance with local regulations
5. **Responsible Betting**: Never bet more than you can afford to lose

## ✅ Verification Checklist

- [ ] Docker containers running
- [ ] Database initialized
- [ ] API responding to health checks
- [ ] CLI commands working
- [ ] Wallet connected
- [ ] API keys configured
- [ ] Monitoring accessible

Congratulations! Your AI Betting Analysis System is ready to use! 🎉

---

**Next**: Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system design.
