# System Architecture

## Overview

The Betting AI System is a comprehensive, AI-driven platform designed to analyze sports betting opportunities and provide data-backed recommendations. The system employs a microservices-inspired architecture with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                    (CLI / API / Web App)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                       │
│                        (FastAPI)                             │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│   Betting    │    │   Recommendation │    │    Crypto    │
│   Service    │    │     Engine       │    │   Service    │
└──────────────┘    └──────────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│  ML Models   │    │  Data Processing │    │  Blockchain  │
│  (Ensemble)  │    │    Pipeline      │    │  Integration │
└──────────────┘    └──────────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │    PostgreSQL    │
                    │     Database     │
                    └──────────────────┘
```

## Core Components

### 1. API Layer (`src/api/`)

**Purpose**: Provides RESTful API endpoints for all system functionality.

**Key Files**:
- `main.py`: FastAPI application setup, middleware, and lifecycle management
- `routes/betting_routes.py`: Betting-related endpoints (top3, predictions, events)
- `routes/crypto_routes.py`: Cryptocurrency transaction endpoints

**Responsibilities**:
- Request validation and authentication
- Rate limiting and security
- Response formatting
- Error handling

**Endpoints**:
```
GET  /api/v1/betting/top3              # Get top 3 recommendations
GET  /api/v1/betting/events            # List upcoming events
POST /api/v1/betting/predict           # Get prediction for event
GET  /api/v1/betting/recommendations/history
POST /api/v1/crypto/balance            # Check wallet balance
POST /api/v1/crypto/send               # Send transaction
```

### 2. ML Models Layer (`src/ml_models/`)

**Purpose**: Implements machine learning models for prediction and analysis.

**Architecture**:
```
EnsemblePredictor (Orchestrator)
    ├── XGBoostModel (35% weight)
    ├── RandomForestModel (25% weight)
    ├── DeepRLModel (25% weight)
    └── BayesianInference (15% weight)
```

**Key Components**:

#### Ensemble Predictor
- Combines predictions from multiple models
- Weighted voting system
- Confidence aggregation
- Expected value calculation

#### Individual Models
- **XGBoost**: Gradient boosting for pattern recognition
- **Random Forest**: Robust classification with feature importance
- **Deep RL**: Dynamic odds assessment and market adaptation
- **Bayesian**: Probabilistic outcome prediction

**Data Flow**:
```
Event Data → Feature Engineering → Model Predictions → 
Ensemble Aggregation → Confidence Score → Expected Value
```

### 3. Recommendation Engine (`src/recommendation/`)

**Purpose**: Analyzes predictions and selects optimal betting opportunities.

**Key Component**: `Top3Selector`

**Selection Process**:
1. **Data Collection**: Fetch upcoming events (24-hour window)
2. **Prediction**: Generate ML predictions for each event
3. **Filtering**: Apply minimum criteria
   - Confidence ≥ 65%
   - Expected Value ≥ 5%
   - Risk Score ≤ 0.7
4. **Scoring**: Calculate composite score
   - Confidence: 40%
   - Expected Value: 35%
   - Risk-Adjusted Return: 25%
5. **Ranking**: Sort by composite score
6. **Selection**: Return top 3 recommendations

**Output Format**:
```json
{
  "rank": 1,
  "event_name": "Manchester United vs Liverpool",
  "selection": "Manchester United",
  "recommended_odds": 2.45,
  "confidence_score": 78.5,
  "expected_value": 0.123,
  "recommended_stake": 125.00,
  "rationale": {
    "summary": "...",
    "key_reasons": [...],
    "value_analysis": {...}
  }
}
```

### 4. Integration Layer (`src/integrations/`)

**Purpose**: Connects to external services and platforms.

#### Stake.com Client (`stake_client.py`)
- API authentication with HMAC signatures
- Event and odds fetching
- Bet placement and tracking
- Balance management
- Transaction history

#### Crypto Wallet (`crypto_wallet.py`)
- Web3.py integration for BSC
- Native BNB transactions
- ERC-20 token transfers (USDT, BUSD)
- Gas estimation
- Transaction status tracking

**Security Features**:
- Private key encryption
- Secure key storage
- Transaction signing
- Rate limiting

### 5. Data Layer (`src/database/`)

**Purpose**: Persistent storage and data management.

**Database Schema**:

```sql
-- Core Tables
sports (id, name, category, is_active)
events (id, sport_id, name, start_time, status)
odds (id, event_id, bookmaker, odds_decimal, timestamp)
predictions (id, event_id, model_name, confidence_score)
recommendations (id, event_id, selection, confidence_score, status)

-- Performance Tracking
historical_performance (id, entity_type, entity_id, metrics)
model_performance (id, model_name, accuracy, roi)
betting_sessions (id, start_time, total_bets, roi)

-- Transactions
transactions (id, transaction_hash, amount, currency, status)
```

**Key Features**:
- Connection pooling (20 connections)
- Automatic reconnection
- Transaction management
- Query optimization with indexes

### 6. Data Processing Pipeline (`src/data_processing/`)

**Purpose**: Transform raw data into ML-ready features.

**Pipeline Stages**:
1. **Data Ingestion**: Collect from multiple sources
2. **Cleaning**: Handle missing values, outliers
3. **Feature Engineering**: Create predictive features
4. **Normalization**: Scale features appropriately
5. **Storage**: Save to database

**Feature Categories**:
- Team/Player Statistics
- Head-to-Head Records
- Recent Form
- Venue Advantages
- Market Movements
- Time-based Features

## Data Flow

### Top 3 Bets Command Flow

```
1. User executes: python -m src.cli.commands top3-bets

2. CLI Layer
   └─> Initialize components (Ensemble, Selector)

3. Database Query
   └─> Fetch upcoming events (next 24 hours)

4. For each event:
   ├─> Get current odds
   ├─> Prepare features
   ├─> ML Prediction
   │   ├─> XGBoost prediction
   │   ├─> Random Forest prediction
   │   ├─> Deep RL prediction
   │   ├─> Bayesian prediction
   │   └─> Ensemble aggregation
   └─> Create recommendation

5. Recommendation Engine
   ├─> Filter by criteria
   ├─> Calculate composite scores
   ├─> Rank recommendations
   └─> Select top 3

6. Output
   └─> Display formatted results to user
```

### API Request Flow

```
1. HTTP Request → FastAPI

2. Middleware
   ├─> CORS validation
   ├─> Rate limiting
   └─> Authentication

3. Route Handler
   ├─> Request validation (Pydantic)
   ├─> Database session injection
   └─> Business logic execution

4. Service Layer
   ├─> ML predictions
   ├─> Data processing
   └─> External API calls

5. Response
   ├─> Format response
   ├─> Add metadata
   └─> Return JSON
```

## Scalability Considerations

### Horizontal Scaling
- Stateless API design
- Database connection pooling
- Redis caching layer (future)
- Load balancer ready

### Performance Optimization
- Async/await for I/O operations
- Batch predictions
- Model caching
- Database query optimization
- Index usage

### Monitoring
- Prometheus metrics
- Grafana dashboards
- Sentry error tracking
- Custom logging

## Security Architecture

### Authentication & Authorization
- API key authentication
- HMAC request signing
- Rate limiting per endpoint
- IP whitelisting (optional)

### Data Security
- Encrypted database connections
- Environment variable secrets
- Private key encryption
- Secure key management

### Transaction Security
- Multi-signature support (future)
- Transaction confirmation
- Gas price validation
- Slippage protection

## Deployment Architecture

### Docker Compose Setup
```yaml
services:
  - postgres: Database
  - redis: Caching (future)
  - betting_api: Main application
  - prometheus: Metrics
  - grafana: Visualization
```

### Production Considerations
- Load balancer (Nginx/Traefik)
- SSL/TLS certificates
- Database replication
- Backup strategy
- Monitoring and alerting

## Future Enhancements

1. **Microservices Split**
   - Separate prediction service
   - Dedicated data ingestion service
   - Independent crypto service

2. **Event-Driven Architecture**
   - Message queue (RabbitMQ/Kafka)
   - Event sourcing
   - CQRS pattern

3. **Advanced ML**
   - Real-time model updates
   - A/B testing framework
   - AutoML integration

4. **Enhanced Integrations**
   - Multiple betting platforms
   - Additional blockchains
   - Social features

## Technology Stack

- **Backend**: Python 3.11, FastAPI
- **ML**: XGBoost, Scikit-learn, TensorFlow
- **Database**: PostgreSQL 16
- **Blockchain**: Web3.py, BSC
- **Containerization**: Docker, Docker Compose
- **Monitoring**: Prometheus, Grafana
- **Testing**: Pytest
- **Documentation**: OpenAPI/Swagger

## Performance Metrics

- API Response Time: < 200ms (p95)
- Prediction Latency: < 500ms
- Database Query Time: < 50ms
- Concurrent Users: 1000+
- Requests/Second: 100+

---

This architecture provides a solid foundation for a production-grade betting analysis system with room for growth and enhancement.
