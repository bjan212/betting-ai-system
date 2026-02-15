# 🎯 AI-Powered Betting Analysis System

An advanced AI-driven betting analysis and recommendation system that leverages machine learning to identify optimal betting opportunities across multiple sports and provides seamless integration with Stake.com and cryptocurrency transactions.

## 🌟 Features

### Core Capabilities
- **Multi-Sport Analysis**: UFC, Tennis, Football, Soccer, Basketball, and Horse Racing
- **AI-Powered Predictions**: Ensemble ML models (XGBoost, Random Forest, Deep RL, Bayesian Inference)
- **Top 3 Recommendations**: Identifies the best 3 betting opportunities within 24 hours
- **Real-Time Data Processing**: 60-second update intervals for odds and statistics
- **Stake.com Integration**: Direct API integration with crypto-native betting platform
- **Cryptocurrency Support**: BSC (Binance Smart Chain) wallet integration for USDT, BNB, BUSD

### Advanced Features
- **Expected Value Calculation**: Sophisticated EV analysis for each bet
- **Kelly Criterion Staking**: Optimal stake sizing based on bankroll management
- **Risk Assessment**: Comprehensive risk scoring for each recommendation
- **Confidence Scoring**: 0-100% confidence levels with detailed rationale
- **Backtesting Framework**: Validate strategies with 10,000+ simulated bets
- **Continuous Learning**: Models improve from actual outcomes

## 🏗️ Architecture

```
betting-ai-system/
├── src/
│   ├── api/                    # FastAPI application
│   │   ├── main.py            # API entry point
│   │   └── routes/            # API endpoints
│   ├── ml_models/             # Machine learning models
│   │   ├── ensemble_predictor.py
│   │   ├── xgboost_model.py
│   │   ├── random_forest_model.py
│   │   ├── deep_rl_model.py
│   │   └── bayesian_inference.py
│   ├── recommendation/        # Recommendation engine
│   │   └── top3_selector.py
│   ├── integrations/          # External integrations
│   │   ├── stake_client.py    # Stake.com API
│   │   └── crypto_wallet.py   # BSC wallet
│   ├── data_ingestion/        # Data collection
│   ├── data_processing/       # Feature engineering
│   ├── database/              # Database models
│   ├── cli/                   # CLI commands
│   └── utils/                 # Utilities
├── config/                    # Configuration files
├── data/                      # Data storage
├── logs/                      # Application logs
├── tests/                     # Test suite
└── docker-compose.yml         # Docker setup
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Docker & Docker Compose (optional)
- Stake.com API credentials
- BSC wallet with private key

### Installation

1. **Clone the repository**
```bash
cd betting-ai-system
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Initialize database**
```bash
python -m src.cli.commands init-db
```

### Using Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f betting_api
```

## 💻 Usage

### CLI Commands

#### Get Top 3 Betting Recommendations
```bash
python -m src.cli.commands top3-bets
```

Filter by sport:
```bash
curl "http://localhost:8000/api/v1/betting/top3?sport=soccer"
```

This command analyzes all upcoming events in the next 24 hours and provides:
- Top 3 highest-value betting opportunities
- Detailed confidence scores and expected values
- Recommended stake amounts
- Comprehensive rationale for each bet

#### Check Wallet Balance
```bash
python -m src.cli.commands balance --currency USDT
```

#### View System Status
```bash
python -m src.cli.commands status
```

#### List Upcoming Events
```bash
python -m src.cli.commands upcoming-events --sport football --limit 20
```

#### Fetch Live Odds (One-Time, Default)
```bash
python -m src.cli.commands fetch-odds
```

#### Continuous Live Odds (Optional)
```bash
python -m src.cli.commands start-odds-service
```

#### Recommendation Filters (Probability + Return)
Set filters in `.env` to keep only high-probability, high-return bets:
```dotenv
MIN_CONFIDENCE_THRESHOLD=0.8
MIN_EXPECTED_VALUE=1.1
MAX_RISK_SCORE=0.7
```

### API Endpoints

Start the API server:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Get Top 3 Recommendations
```bash
curl http://localhost:8000/api/v1/betting/top3
```

#### Place Bet (Stake.com)
```bash
curl -X POST http://localhost:8000/api/v1/betting/place-bet \
  -H "Content-Type: application/json" \
  -d '{"event_id":"12345","selection":"home","stake":25,"odds":2.1,"currency":"USDT"}'
```

Configure Stake credentials in `.env`:
```dotenv
STAKE_API_KEY=your_key_here
STAKE_API_SECRET=your_secret_here
STAKE_BASE_URL=https://api.stake.com
```

#### Get Upcoming Events
```bash
curl http://localhost:8000/api/v1/betting/events?sport=football&limit=50
```

#### Get Wallet Balance
```bash
curl -X POST http://localhost:8000/api/v1/crypto/balance \
  -H "Content-Type: application/json" \
  -d '{"token_symbol": "USDT"}'
```

#### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation.

## 🎲 How It Works

### 1. Data Ingestion
- Real-time odds from multiple bookmakers
- Sports statistics from Sportradar
- Historical performance data
- Market movement tracking

### 2. Feature Engineering
- Team/player performance metrics
- Head-to-head statistics
- Venue advantages
- Recent form analysis
- Odds movement patterns

### 3. ML Prediction
The ensemble predictor combines:
- **XGBoost** (35% weight): Gradient boosting for pattern recognition
- **Random Forest** (25% weight): Robust classification
- **Deep RL** (25% weight): Dynamic odds assessment
- **Bayesian Inference** (15% weight): Probabilistic outcomes

### 4. Value Analysis
- Expected Value (EV) calculation
- Risk-adjusted returns
- Kelly Criterion stake sizing
- Confidence scoring

### 5. Top 3 Selection
Recommendations ranked by composite score:
- Confidence: 40%
- Expected Value: 35%
- Risk-Adjusted Return: 25%

## 📊 Example Output

```
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

📝 Analysis:
High confidence bet with strong value vs market odds

Key Reasons:
  ✓ Very high model confidence (>75%)
  ✓ Excellent expected value (+12.3%)
  ✓ Significant value vs market odds
  ✓ Strong consensus across all models

💎 Value Analysis:
  • Edge vs Market: +11.2%
  • Model Probability: 52.1%
  • Implied Probability: 40.8%
```

## 🔧 Configuration

### Key Configuration Files

**config/config.yaml**: Main system configuration
- ML model parameters
- Recommendation criteria
- API settings
- Database configuration

**.env**: Environment variables
- API keys
- Database credentials
- Wallet private keys
- Security settings

### Recommendation Criteria

Adjust in `config/config.yaml`:
```yaml
recommendation:
  top3_selection:
    min_confidence: 0.65        # Minimum 65% confidence
    min_expected_value: 1.05    # Minimum 5% EV
    max_risk_score: 0.7         # Maximum risk threshold
    time_window_hours: 24       # Analysis window
```

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v --cov=src
```

Run backtesting:
```bash
python -m src.backtesting.simulator --samples 10000
```

## 📈 Performance Metrics

The system tracks:
- **ROI**: Return on investment
- **Win Rate**: Percentage of winning bets
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline
- **Profit Factor**: Gross profit / gross loss

## 🔐 Security

- Private keys stored in environment variables
- API authentication with HMAC signatures
- Rate limiting on all endpoints
- Encrypted database connections
- Audit logging for all transactions

## 🛠️ Development

### Adding New Sports
1. Add sport to `config/config.yaml`
2. Implement data fetcher in `src/data_ingestion/`
3. Add sport-specific features in `src/data_processing/`
4. Update database models if needed

### Adding New ML Models
1. Create model class in `src/ml_models/`
2. Implement `predict()` method
3. Register with ensemble predictor
4. Update model weights in config

## 📝 API Keys Required

1. **Stake.com API**: Get from Stake.com developer portal
2. **Odds API**: https://the-odds-api.com/
3. **Sportradar**: https://developer.sportradar.com/
4. **BSC RPC**: Use public endpoint or Infura/Alchemy

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## ⚠️ Disclaimer

This system is for educational and research purposes. Betting involves risk. Always:
- Bet responsibly
- Never bet more than you can afford to lose
- Understand that past performance doesn't guarantee future results
- Comply with local gambling regulations

## 🆘 Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Email: support@bettingai.example.com

## 🗺️ Roadmap

- [ ] Additional ML models (LSTM, Transformer)
- [ ] Live betting support
- [ ] Mobile app
- [ ] Advanced arbitrage detection
- [ ] Social features (bet sharing)
- [ ] Multi-language support
- [ ] Additional betting platforms

---

**Built with ❤️ using Python, FastAPI, XGBoost, and Web3.py**
