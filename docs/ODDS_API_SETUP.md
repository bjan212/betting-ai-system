# The Odds API Integration Setup Guide

## Overview

The Odds API provides real-time sports odds from multiple bookmakers. This guide covers setup, configuration, and usage.

## 🔑 Getting API Key

1. **Sign up at The Odds API**
   - Visit: https://the-odds-api.com/
   - Click "Get API Key"
   - Choose a plan (Free tier: 500 requests/month)

2. **Get your API key**
   - After signup, you'll receive an API key
   - Copy this key for configuration

## ⚙️ Configuration

### 1. Environment Variables

Add to your `.env` file:

```env
# The Odds API
ODDS_API_KEY=your_actual_api_key_here
```

### 2. Config File

The system is pre-configured in `config/config.yaml`:

```yaml
sports:
  data_sources:
    odds:
      provider: "odds_api"
      update_interval: 60  # seconds
      endpoints:
        - "https://api.the-odds-api.com/v4/sports"
```

## 📊 Supported Sports

The integration supports:
- ⚽ Soccer (EPL, La Liga, etc.)
- 🏈 American Football (NFL)
- 🏀 Basketball (NBA)
- ⚾ Baseball (MLB)
- 🏒 Ice Hockey (NHL)
- 🥊 MMA / UFC
- 🎾 Tennis (ATP, WTA)
- 🏏 Cricket

## 🚀 Usage

### CLI Commands

#### 1. Fetch Odds Data

Fetch odds for all sports:
```bash
python -m src.cli.commands fetch-odds
```

Fetch odds for specific sport:
```bash
python -m src.cli.commands fetch-odds --sport football
python -m src.cli.commands fetch-odds --sport soccer
python -m src.cli.commands fetch-odds --sport basketball
```

#### 2. Start Continuous Odds Service

Start background service that updates odds every 60 seconds:
```bash
python -m src.cli.commands start-odds-service
```

Press `Ctrl+C` to stop the service.

#### 3. Find Arbitrage Opportunities

Scan all events for arbitrage betting opportunities:
```bash
python -m src.cli.commands find-arbitrage
```

Example output:
```
💎 Finding Arbitrage Opportunities...

Found 2 arbitrage opportunities!

Opportunity #1:
  Event: Manchester United vs Liverpool
  Sport: Soccer
  Profit Margin: 2.34%
  Stakes: {'Manchester United': 48.5, 'Liverpool': 51.5}
  Best Odds: {...}
```

#### 4. Check API Usage

Monitor your API quota:
```bash
python -m src.cli.commands api-usage
```

Output:
```
📈 API Usage Statistics

Requests Used: 127
Requests Remaining: 373
Last Request: 2024-02-14T10:30:00Z
```

### Python API

#### Basic Usage

```python
import asyncio
from src.data_ingestion.odds_api_client import get_odds_client

async def main():
    client = get_odds_client()
    
    # Get available sports
    sports = await client.get_sports()
    print(f"Available sports: {len(sports)}")
    
    # Get odds for NFL
    events = await client.get_odds('football')
    print(f"NFL events: {len(events)}")
    
    # Parse and analyze
    for event in events:
        parsed = client.parse_odds_data(event)
        best_odds = client.get_best_odds(parsed)
        print(f"{parsed['home_team']} vs {parsed['away_team']}")
        print(f"Best odds: {best_odds}")
    
    await client.close()

asyncio.run(main())
```

#### Find Best Odds

```python
from src.data_ingestion.odds_api_client import get_odds_client

async def find_best_odds():
    client = get_odds_client()
    
    events = await client.get_odds('basketball')
    
    for event in events:
        parsed = client.parse_odds_data(event)
        best_odds = client.get_best_odds(parsed, market='h2h')
        
        print(f"\n{parsed['home_team']} vs {parsed['away_team']}")
        for outcome, data in best_odds.items():
            print(f"  {outcome}: {data['price']} @ {data['bookmaker_title']}")
    
    await client.close()
```

#### Detect Arbitrage

```python
from src.data_ingestion.odds_api_client import get_odds_client

async def detect_arbitrage():
    client = get_odds_client()
    
    events = await client.get_odds('soccer')
    
    for event in events:
        parsed = client.parse_odds_data(event)
        best_odds = client.get_best_odds(parsed)
        arbitrage = client.calculate_arbitrage(best_odds)
        
        if arbitrage['has_arbitrage']:
            print(f"\n🎯 ARBITRAGE FOUND!")
            print(f"Event: {parsed['home_team']} vs {parsed['away_team']}")
            print(f"Profit: {arbitrage['profit_margin']:.2f}%")
            print(f"Stakes: {arbitrage['stakes']}")
    
    await client.close()
```

### Using the Ingestion Service

```python
import asyncio
from src.data_ingestion.odds_ingestion_service import get_ingestion_service

async def main():
    service = get_ingestion_service(update_interval=60)
    
    # Fetch and store odds once
    await service.fetch_and_store_odds()
    
    # Or start continuous service
    # await service.start()  # Runs until stopped

asyncio.run(main())
```

## 📈 Data Flow

```
The Odds API
     ↓
OddsAPIClient (fetch)
     ↓
OddsIngestionService (process)
     ↓
Database (store)
     ↓
ML Models (analyze)
     ↓
Recommendations (output)
```

## 🗄️ Database Schema

Odds data is stored in these tables:

### Events Table
```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(100) UNIQUE,
    sport_id INTEGER,
    name VARCHAR(255),
    home_team VARCHAR(100),
    away_team VARCHAR(100),
    start_time TIMESTAMP,
    status VARCHAR(50)
);
```

### Odds Table
```sql
CREATE TABLE odds (
    id SERIAL PRIMARY KEY,
    event_id INTEGER,
    bookmaker VARCHAR(100),
    market_type VARCHAR(50),
    selection VARCHAR(100),
    odds_decimal FLOAT,
    odds_american FLOAT,
    timestamp TIMESTAMP,
    is_current BOOLEAN
);
```

## 🔍 Features

### 1. Multi-Bookmaker Support

Tracks odds from major bookmakers:
- DraftKings
- FanDuel
- BetMGM
- PointsBet
- Bovada
- MyBookie
- BetUS
- BetOnline

### 2. Multiple Markets

Supports different bet types:
- **h2h**: Head-to-head (moneyline)
- **spreads**: Point spreads
- **totals**: Over/under

### 3. Real-Time Updates

- Configurable update interval (default: 60 seconds)
- Automatic odds refresh
- Historical odds tracking

### 4. Arbitrage Detection

Automatically identifies:
- Cross-bookmaker arbitrage
- Profit margin calculation
- Optimal stake distribution

### 5. Best Odds Finder

- Compares odds across all bookmakers
- Identifies best value for each outcome
- Tracks odds movement

## 💡 Best Practices

### 1. API Rate Limiting

Free tier: 500 requests/month
- Each sport query = 1 request
- Monitor usage with `api-usage` command
- Optimize by fetching multiple sports less frequently

### 2. Update Frequency

Recommended intervals:
- **Live betting**: 30-60 seconds
- **Pre-match**: 5-10 minutes
- **Long-term**: 1 hour

### 3. Data Storage

- Keep historical odds for analysis
- Mark old odds as `is_current=False`
- Archive old data periodically

### 4. Error Handling

The system handles:
- API timeouts
- Rate limit errors
- Invalid responses
- Network failures

## 🐛 Troubleshooting

### Issue: "API key invalid"

**Solution:**
1. Check `.env` file has correct key
2. Verify key at https://the-odds-api.com/account
3. Ensure no extra spaces in key

### Issue: "No events found"

**Possible causes:**
1. No upcoming events for that sport
2. Time window too narrow
3. Sport key incorrect

**Solution:**
```bash
# Check available sports
python -m src.cli.commands fetch-odds --sport soccer

# Try different sport
python -m src.cli.commands fetch-odds --sport football
```

### Issue: "Rate limit exceeded"

**Solution:**
1. Check usage: `python -m src.cli.commands api-usage`
2. Reduce update frequency
3. Upgrade API plan if needed

### Issue: "Database connection error"

**Solution:**
1. Ensure PostgreSQL is running
2. Check DATABASE_URL in `.env`
3. Initialize database: `python -m src.cli.commands init-db`

## 📊 Example Workflow

### Complete Setup and First Fetch

```bash
# 1. Initialize database
python -m src.cli.commands init-db

# 2. Check API status
python -m src.cli.commands api-usage

# 3. Fetch odds for all sports
python -m src.cli.commands fetch-odds

# 4. Check what was fetched
python -m src.cli.commands upcoming-events --limit 20

# 5. Find arbitrage opportunities
python -m src.cli.commands find-arbitrage

# 6. Get top 3 recommendations
python -m src.cli.commands top3-bets
```

### Continuous Operation

```bash
# Terminal 1: Start odds service
python -m src.cli.commands start-odds-service

# Terminal 2: Start API server
uvicorn src.api.main:app --reload

# Terminal 3: Monitor
watch -n 60 'python -m src.cli.commands api-usage'
```

## 🔗 Resources

- **The Odds API Docs**: https://the-odds-api.com/liveapi/guides/v4/
- **API Dashboard**: https://the-odds-api.com/account
- **Supported Sports**: https://the-odds-api.com/sports-odds-data/sports-apis.html
- **Pricing**: https://the-odds-api.com/pricing

## 🎯 Next Steps

After setting up odds integration:

1. **Configure other data sources** (Sportradar for stats)
2. **Train ML models** with historical data
3. **Set up automated betting** via Stake.com
4. **Monitor performance** with dashboards
5. **Optimize strategies** based on results

---

**Note**: Always comply with local gambling regulations and bet responsibly.
