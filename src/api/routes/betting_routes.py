"""
Betting API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.database.database import get_db_session
from src.database.models import Event, Recommendation
from src.ml_models.ensemble_predictor import EnsemblePredictor
from src.ml_models.xgboost_model import XGBoostModel
from src.recommendation.top3_selector import Top3Selector
from src.integrations.polymarket_client import get_polymarket_client
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models
class Top3Response(BaseModel):
    """Top 3 recommendations response"""
    recommendations: List[dict]
    generated_at: str
    time_window_hours: int


class EventResponse(BaseModel):
    """Event response model"""
    id: int
    name: str
    sport: str
    start_time: str
    status: str
    home_team: Optional[str]
    away_team: Optional[str]


class PredictionRequest(BaseModel):
    """Prediction request model"""
    event_id: int


class PredictionResponse(BaseModel):
    """Prediction response model"""
    event_id: int
    prediction: dict
    timestamp: str


class PlaceBetRequest(BaseModel):
    """Place bet request model"""
    token_id: str  # Polymarket token ID
    side: str  # 'BUY' or 'SELL'
    amount: Optional[float] = None  # Dollar amount for market order
    price: Optional[float] = None  # Price for limit order (0.00-1.00)
    size: Optional[float] = None  # Share size for limit order


class PolymarketConfigRequest(BaseModel):
    """Polymarket API configuration request model"""
    private_key: str  # Polygon wallet private key
    funder_address: Optional[str] = None  # For proxy wallets
    signature_type: Optional[int] = 0  # 0=EOA, 1=Magic, 2=Proxy


class PolymarketBalanceResponse(BaseModel):
    """Polymarket balance response model"""
    connected: bool = False
    balance: Optional[str] = None
    currency: Optional[str] = None
    chain: Optional[str] = None
    message: Optional[str] = None
    raw: Optional[dict] = None


# Initialize ensemble predictor (singleton pattern)
_ensemble_predictor = None


def get_ensemble_predictor() -> EnsemblePredictor:
    """Get or create ensemble predictor"""
    global _ensemble_predictor
    if _ensemble_predictor is None:
        _ensemble_predictor = EnsemblePredictor()
        xgboost_model = XGBoostModel()
        _ensemble_predictor.register_model('xgboost', xgboost_model)
        logger.info("Ensemble predictor initialized")
    return _ensemble_predictor


@router.get("/top3", response_model=Top3Response)
async def get_top3_bets(
    sport: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    Get top 3 betting recommendations for next 24 hours
    
    This endpoint analyzes all upcoming events and returns the 3 most
    promising betting opportunities based on ML predictions and value analysis.
    """
    try:
        logger.info("API request: top3 bets")
        
        ensemble = get_ensemble_predictor()
        selector = Top3Selector(ensemble)
        
        recommendations = selector.get_top3_bets(db, sport=sport)
        
        return {
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat(),
            "time_window_hours": selector.time_window_hours
        }
        
    except Exception as e:
        logger.error(f"Error getting top3 bets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/place-bet")
async def place_bet(request: PlaceBetRequest):
    """
    Place a bet via Polymarket
    """
    try:
        client = get_polymarket_client()
        if not client.private_key:
            raise HTTPException(status_code=400, detail="Polymarket private key is not configured")

        result = await client.place_bet(
            token_id=request.token_id,
            side=request.side,
            amount=request.amount,
            price=request.price,
            size=request.size
        )

        if not result.get('success'):
            raise HTTPException(status_code=502, detail=result.get('error', 'Unknown error'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polymarket-config")
async def update_polymarket_config(request: PolymarketConfigRequest):
    """
    Update Polymarket credentials at runtime
    """
    try:
        client = get_polymarket_client()
        await client.update_credentials(
            private_key=request.private_key,
            funder_address=request.funder_address,
            signature_type=request.signature_type
        )

        return {"success": True}

    except Exception as e:
        logger.error(f"Error updating Polymarket config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/polymarket/balance", response_model=PolymarketBalanceResponse)
async def get_polymarket_balance():
    """
    Get Polymarket connection status and balance
    """
    try:
        client = get_polymarket_client()
        
        # Check connection
        connection = await client.check_connection()
        if not connection.get('connected'):
            return {
                "connected": False,
                "message": connection.get('error', 'Connection failed'),
                "raw": connection
            }
        
        # Get balance
        balance = await client.get_balance()
        
        return {
            "connected": balance.get('connected', False),
            "balance": balance.get('balance'),
            "currency": balance.get('currency', 'USDC'),
            "chain": balance.get('chain', 'Polygon'),
            "message": "Polymarket connected" if balance.get('connected') else balance.get('error'),
            "raw": balance
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Polymarket balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events", response_model=List[EventResponse])
async def get_upcoming_events(
    sport: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db_session)
):
    """
    Get upcoming events
    
    Args:
        sport: Filter by sport name
        limit: Maximum number of events to return
    """
    try:
        query = db.query(Event).filter(
            Event.status == 'upcoming',
            Event.start_time >= datetime.utcnow()
        )
        
        if sport:
            from src.database.models import Sport
            query = query.join(Event.sport).filter(Sport.name == sport)
        
        events = query.order_by(Event.start_time).limit(limit).all()
        
        return [
            {
                "id": event.id,
                "name": event.name,
                "sport": event.sport.name if event.sport else "unknown",
                "start_time": event.start_time.isoformat(),
                "status": event.status,
                "home_team": event.home_team,
                "away_team": event.away_team
            }
            for event in events
        ]
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=PredictionResponse)
async def predict_event(
    request: PredictionRequest,
    db: Session = Depends(get_db_session)
):
    """
    Get prediction for a specific event
    
    Args:
        request: Prediction request with event_id
    """
    try:
        # Get event
        event = db.query(Event).filter(Event.id == request.event_id).first()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Get odds
        from src.database.models import Odds
        odds = db.query(Odds).filter(
            Odds.event_id == event.id,
            Odds.is_current == True
        ).all()
        
        # Prepare event data
        event_data = {
            'event_id': event.id,
            'event_name': event.name,
            'sport': event.sport.name if event.sport else 'unknown',
            'home_team': event.home_team,
            'away_team': event.away_team,
            'home_odds': 2.0,
            'away_odds': 2.0,
            'draw_odds': 3.0
        }
        
        # Get prediction
        ensemble = get_ensemble_predictor()
        prediction = ensemble.predict(event_data)
        
        return {
            "event_id": event.id,
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/history")
async def get_recommendation_history(
    limit: int = 50,
    db: Session = Depends(get_db_session)
):
    """
    Get historical recommendations
    
    Args:
        limit: Maximum number of recommendations to return
    """
    try:
        recommendations = db.query(Recommendation).order_by(
            Recommendation.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": rec.id,
                "event_id": rec.event_id,
                "selection": rec.selection,
                "recommended_odds": rec.recommended_odds,
                "confidence_score": rec.confidence_score,
                "expected_value": rec.expected_value,
                "status": rec.status,
                "actual_outcome": rec.actual_outcome,
                "actual_return": rec.actual_return,
                "created_at": rec.created_at.isoformat()
            }
            for rec in recommendations
        ]
        
    except Exception as e:
        logger.error(f"Error getting recommendation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sports")
async def get_available_sports(db: Session = Depends(get_db_session)):
    """Get list of available sports"""
    try:
        from src.database.models import Sport
        
        sports = db.query(Sport).filter(Sport.is_active == True).all()
        
        return [
            {
                "id": sport.id,
                "name": sport.name,
                "category": sport.category
            }
            for sport in sports
        ]
        
    except Exception as e:
        logger.error(f"Error getting sports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/models")
async def get_model_performance():
    """Get ML model performance metrics"""
    try:
        ensemble = get_ensemble_predictor()
        performance = ensemble.get_model_performance()
        
        return {
            "models": performance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting model performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_betting_stats(db: Session = Depends(get_db_session)):
    """Get betting statistics summary"""
    try:
        # Get recommendation stats
        total_recommendations = db.query(Recommendation).count()
        
        won_bets = db.query(Recommendation).filter(
            Recommendation.status == 'won'
        ).count()
        
        lost_bets = db.query(Recommendation).filter(
            Recommendation.status == 'lost'
        ).count()
        
        pending_bets = db.query(Recommendation).filter(
            Recommendation.status == 'pending'
        ).count()
        
        # Calculate win rate
        completed_bets = won_bets + lost_bets
        win_rate = (won_bets / completed_bets * 100) if completed_bets > 0 else 0
        
        return {
            "total_recommendations": total_recommendations,
            "won_bets": won_bets,
            "lost_bets": lost_bets,
            "pending_bets": pending_bets,
            "win_rate": round(win_rate, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting betting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
