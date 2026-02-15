"""
Database models for the Betting AI System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Sport(Base):
    """Sports table"""
    __tablename__ = 'sports'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    category = Column(String(50))  # team_sport, individual_sport, racing
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    events = relationship("Event", back_populates="sport")


class Event(Base):
    """Sports events table"""
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    sport_id = Column(Integer, ForeignKey('sports.id'), nullable=False)
    external_id = Column(String(100), unique=True)
    name = Column(String(255), nullable=False)
    home_team = Column(String(100))
    away_team = Column(String(100))
    start_time = Column(DateTime, nullable=False)
    status = Column(String(50))  # upcoming, live, finished, cancelled
    venue = Column(String(255))
    extra_metadata = Column("metadata", JSON)  # Additional event-specific data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sport = relationship("Sport", back_populates="events")
    odds = relationship("Odds", back_populates="event")
    predictions = relationship("Prediction", back_populates="event")
    
    __table_args__ = (
        Index('idx_event_start_time', 'start_time'),
        Index('idx_event_status', 'status'),
    )


class Odds(Base):
    """Betting odds table"""
    __tablename__ = 'odds'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    bookmaker = Column(String(100), nullable=False)
    market_type = Column(String(50))  # moneyline, spread, total, etc.
    selection = Column(String(100))  # home, away, over, under, etc.
    odds_decimal = Column(Float, nullable=False)
    odds_american = Column(Float)
    odds_fractional = Column(String(20))
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_current = Column(Boolean, default=True)
    
    event = relationship("Event", back_populates="odds")
    
    __table_args__ = (
        Index('idx_odds_event_current', 'event_id', 'is_current'),
        Index('idx_odds_timestamp', 'timestamp'),
    )


class Prediction(Base):
    """ML model predictions table"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    model_name = Column(String(50), nullable=False)
    prediction_type = Column(String(50))  # winner, score, total, etc.
    predicted_outcome = Column(String(100))
    confidence_score = Column(Float)  # 0-1
    expected_value = Column(Float)
    probability = Column(Float)  # 0-1
    features_used = Column(JSON)
    model_version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    event = relationship("Event", back_populates="predictions")
    
    __table_args__ = (
        Index('idx_prediction_event', 'event_id'),
        Index('idx_prediction_confidence', 'confidence_score'),
    )


class Recommendation(Base):
    """Betting recommendations table"""
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    recommendation_type = Column(String(50))  # top3, value_bet, arbitrage
    selection = Column(String(100))
    recommended_odds = Column(Float)
    confidence_score = Column(Float)  # 0-100
    expected_value = Column(Float)
    risk_score = Column(Float)  # 0-1
    recommended_stake = Column(Float)
    recommended_stake_percentage = Column(Float)
    rationale = Column(JSON)  # Detailed reasoning
    ensemble_scores = Column(JSON)  # Individual model scores
    status = Column(String(50))  # pending, placed, won, lost, void
    actual_outcome = Column(String(100))
    actual_return = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    event = relationship("Event")
    
    __table_args__ = (
        Index('idx_recommendation_type', 'recommendation_type'),
        Index('idx_recommendation_created', 'created_at'),
        Index('idx_recommendation_status', 'status'),
    )


class HistoricalPerformance(Base):
    """Historical performance tracking"""
    __tablename__ = 'historical_performance'
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50))  # team, player, horse, jockey
    entity_id = Column(String(100))
    entity_name = Column(String(255))
    sport_id = Column(Integer, ForeignKey('sports.id'))
    performance_date = Column(DateTime)
    metrics = Column(JSON)  # Sport-specific metrics
    opponent = Column(String(255))
    result = Column(String(50))  # win, loss, draw
    score = Column(String(50))
    conditions = Column(JSON)  # Weather, venue, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_perf_entity', 'entity_type', 'entity_id'),
        Index('idx_perf_date', 'performance_date'),
    )


class ModelPerformance(Base):
    """ML model performance tracking"""
    __tablename__ = 'model_performance'
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(50), nullable=False)
    model_version = Column(String(20))
    evaluation_date = Column(DateTime, default=datetime.utcnow)
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    roc_auc = Column(Float)
    log_loss = Column(Float)
    predictions_count = Column(Integer)
    correct_predictions = Column(Integer)
    avg_confidence = Column(Float)
    avg_expected_value = Column(Float)
    roi = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    extra_metadata = Column("metadata", JSON)
    
    __table_args__ = (
        Index('idx_model_perf_date', 'evaluation_date'),
        Index('idx_model_perf_name', 'model_name'),
    )


class Transaction(Base):
    """Cryptocurrency transactions table"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    transaction_hash = Column(String(100), unique=True)
    transaction_type = Column(String(50))  # deposit, withdrawal, bet_placement
    from_address = Column(String(100))
    to_address = Column(String(100))
    amount = Column(Float)
    currency = Column(String(20))
    gas_used = Column(Float)
    gas_price = Column(Float)
    status = Column(String(50))  # pending, confirmed, failed
    block_number = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    extra_metadata = Column("metadata", JSON)
    
    __table_args__ = (
        Index('idx_transaction_hash', 'transaction_hash'),
        Index('idx_transaction_status', 'status'),
        Index('idx_transaction_timestamp', 'timestamp'),
    )


class BettingSession(Base):
    """Betting session tracking"""
    __tablename__ = 'betting_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    initial_bankroll = Column(Float)
    final_bankroll = Column(Float)
    total_bets = Column(Integer, default=0)
    winning_bets = Column(Integer, default=0)
    losing_bets = Column(Integer, default=0)
    void_bets = Column(Integer, default=0)
    total_staked = Column(Float, default=0.0)
    total_returned = Column(Float, default=0.0)
    roi = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    extra_metadata = Column("metadata", JSON)
    
    __table_args__ = (
        Index('idx_session_start', 'start_time'),
    )
