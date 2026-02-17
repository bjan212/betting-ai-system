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
from src.integrations.sportsbook_links import generate_bet_link, generate_all_book_links
from src.integrations.polymarket_sports import fetch_polymarket_sports_markets, search_polymarket_markets
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


class DirectBetRequest(BaseModel):
    """Direct bet request — uses tiered stake based on probability"""
    token_id: str           # Polymarket CLOB token ID
    outcome: str            # e.g. "Yes" or "No"
    market_price: float     # Current market price (0.01 – 0.99)
    question: str = ""      # Market question (for logging)
    side: str = "BUY"       # BUY or SELL


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

TRAINED_MODEL_PATH = "data/models/xgboost_latest.pkl"


def get_ensemble_predictor() -> EnsemblePredictor:
    """Get or create ensemble predictor, loading trained model if available."""
    global _ensemble_predictor
    if _ensemble_predictor is None:
        _ensemble_predictor = EnsemblePredictor()
        xgboost_model = XGBoostModel()

        # Load trained model from disk if it exists
        import os
        if os.path.exists(TRAINED_MODEL_PATH):
            try:
                xgboost_model.load_model(TRAINED_MODEL_PATH)
                logger.info(f"Loaded trained XGBoost model from {TRAINED_MODEL_PATH}")
            except Exception as e:
                logger.warning(f"Failed to load trained model: {e} — using untrained")
        else:
            logger.warning("No trained model found — predictions will use defaults")

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

        # Enrich each recommendation with sportsbook deep links
        for rec in recommendations:
            bet_link = generate_bet_link(
                bookmaker=rec.get('bookmaker', ''),
                home_team=rec.get('event_name', '').split(' vs ')[0] if ' vs ' in rec.get('event_name', '') else '',
                away_team=rec.get('event_name', '').split(' vs ')[-1] if ' vs ' in rec.get('event_name', '') else '',
                sport=rec.get('sport', ''),
                event_name=rec.get('event_name', ''),
            )
            rec['bet_link'] = bet_link

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


# Tiered stake amounts matching the recommendation engine
STAKE_TIERS = [
    (0.60, 0.70, 1.0),   # 60-70% → $1
    (0.70, 0.80, 3.0),   # 70-80% → $3
    (0.80, 0.90, 5.0),   # 80-90% → $5
    (0.90, 1.00, 22.0),  # 90-99% → $22
]


def _tiered_stake(probability: float) -> float:
    """Return the tiered stake amount for a given probability."""
    for low, high, amount in STAKE_TIERS:
        if low <= probability < high:
            return amount
    if probability >= 1.0:
        return 22.0
    return 0.0


@router.post("/direct-bet")
async def direct_bet(request: DirectBetRequest):
    """
    Place a bet directly on Polymarket using tiered stake sizing.

    The stake is determined automatically by the market price (treated as
    probability):
        60-70%  → $1
        70-80%  → $3
        80-90%  → $5
        90-99%  → $22
    """
    try:
        client = get_polymarket_client()
        if not client.private_key:
            raise HTTPException(
                status_code=400,
                detail="Polymarket wallet not configured. Go to Settings → Polymarket Settings to add your key.",
            )

        probability = request.market_price
        stake = _tiered_stake(probability)
        if stake <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Market price {probability:.0%} is below the 60% minimum threshold for auto-betting.",
            )

        # Place a market order (Fill-or-Kill) for the tiered dollar amount
        result = await client.place_bet(
            token_id=request.token_id,
            side=request.side,
            amount=stake,
        )

        if not result.get("success"):
            raise HTTPException(status_code=502, detail=result.get("error", "Order rejected by Polymarket"))

        tier_label = f"{int(probability*100)}%"
        for low, high, _ in STAKE_TIERS:
            if low <= probability < high:
                tier_label = f"{int(low*100)}-{int(high*100)}%"
                break

        return {
            **result,
            "stake": stake,
            "tier": tier_label,
            "probability": probability,
            "outcome": request.outcome,
            "question": request.question,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing direct bet: {e}")
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

        # Credentials are saved even if the API is unreachable (e.g. US geo-block)
        result = {"success": True, "credentials_saved": True}
        if client._api_reachable is False:
            result["warning"] = (
                "Credentials saved but Polymarket API is currently unreachable. "
                "This is often due to US geo-restrictions. "
                "Your credentials will work when accessed from an allowed region or via VPN."
            )
            result["api_reachable"] = False
        else:
            result["api_reachable"] = True
        return result

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
                "credentials_saved": connection.get('credentials_saved', False),
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


@router.get("/polymarket/markets")
async def get_polymarket_sports_markets(query: Optional[str] = None):
    """
    Get active sports prediction markets on Polymarket.
    These are futures/outright markets (e.g. NBA Champion, EPL Winner).
    """
    try:
        if query:
            markets = search_polymarket_markets(query)
        else:
            markets = fetch_polymarket_sports_markets()
        return {
            "markets": markets,
            "count": len(markets),
            "source": "polymarket",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching Polymarket markets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh-odds")
async def refresh_odds():
    """Trigger a live odds refresh from The Odds API"""
    try:
        from src.data_ingestion.odds_ingestion_service import OddsIngestionService
        from src.database.models import Event

        service = OddsIngestionService()
        await service.fetch_and_store_odds()

        from src.database.database import db_manager
        with db_manager.get_session() as db:
            event_count = db.query(Event).count()

        return {
            "success": True,
            "message": f"Live odds refreshed — {event_count} events in database",
            "event_count": event_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error refreshing odds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────── Ledger endpoints ───────────────────

@router.get("/ledger")
async def get_ledger(
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """Return the bet ledger (recorded & graded bets)."""
    try:
        from src.services.auto_bet_service import get_ledger as _get_ledger
        entries = _get_ledger(db, limit=limit, status_filter=status)
        return {
            "entries": entries,
            "count": len(entries),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger/stats")
async def get_ledger_stats(db: Session = Depends(get_db_session)):
    """Return aggregate P&L stats from the ledger."""
    try:
        from src.services.auto_bet_service import get_ledger_summary
        summary = get_ledger_summary(db)
        return {
            **summary,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching ledger stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-bet/trigger")
async def trigger_auto_bet(db: Session = Depends(get_db_session)):
    """Manually trigger one auto-bet cycle (find bets + record)."""
    try:
        from src.services.auto_bet_service import record_top3_bets
        recorded = record_top3_bets(db)
        return {
            "success": True,
            "recorded": len(recorded),
            "bets": recorded,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error triggering auto-bet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-bet/grade")
async def trigger_grade():
    """Manually trigger result grading for pending bets."""
    try:
        from src.services.auto_bet_service import grade_pending_bets
        result = await grade_pending_bets()
        return {
            "success": True,
            **result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error grading bets: {e}")
        raise HTTPException(status_code=500, detail=str(e))
