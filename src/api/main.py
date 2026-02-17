"""
FastAPI Main Application
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from contextlib import asynccontextmanager

from src.database.database import get_db_session, init_database, close_database
from src.api.routes import betting_routes, crypto_routes
from src.utils.logger import get_logger
from src.utils.config_loader import get_config

logger = get_logger(__name__)
config = get_config()


def _seed_demo_data_if_empty():
    """Seed demo events/odds when the database has no events (fresh deploy)."""
    from src.database.database import db_manager
    from src.database.models import Sport, Event, Odds
    from datetime import datetime, timedelta

    try:
        with db_manager.get_session() as db:
            event_count = db.query(Event).count()
            if event_count > 0:
                logger.info(f"Database already has {event_count} events — skipping seed")
                return

            logger.info("Empty database detected — seeding demo data")
            now = datetime.utcnow()

            demo_sports = [
                {"name": "soccer", "category": "team_sport"},
                {"name": "basketball", "category": "team_sport"},
                {"name": "tennis", "category": "individual_sport"},
            ]

            demo_events = [
                {"external_id": "demo-soccer-1", "sport": "soccer",
                 "name": "Demo FC vs Sample United", "home_team": "Demo FC",
                 "away_team": "Sample United", "hours": 24},
                {"external_id": "demo-soccer-2", "sport": "soccer",
                 "name": "Alpha City vs Beta Town", "home_team": "Alpha City",
                 "away_team": "Beta Town", "hours": 48},
                {"external_id": "demo-basketball-1", "sport": "basketball",
                 "name": "Example City vs Test Town", "home_team": "Example City",
                 "away_team": "Test Town", "hours": 36},
                {"external_id": "demo-basketball-2", "sport": "basketball",
                 "name": "Hoops United vs Net Masters", "home_team": "Hoops United",
                 "away_team": "Net Masters", "hours": 72},
                {"external_id": "demo-tennis-1", "sport": "tennis",
                 "name": "Player A vs Player B", "home_team": "Player A",
                 "away_team": "Player B", "hours": 12},
                {"external_id": "demo-tennis-2", "sport": "tennis",
                 "name": "Ace King vs Serve Pro", "home_team": "Ace King",
                 "away_team": "Serve Pro", "hours": 60},
            ]

            # bookmaker  →  { selection: odds }
            bookmaker_odds = {
                "DraftKings":  {"home": 2.10, "away": 2.60, "draw": 3.30},
                "FanDuel":     {"home": 2.20, "away": 2.50, "draw": 3.10},
                "BetMGM":      {"home": 1.95, "away": 2.75, "draw": 3.40},
                "Pinnacle":    {"home": 2.05, "away": 2.65, "draw": 3.25},
                "Betfair":     {"home": 2.30, "away": 2.40, "draw": 3.50},
            }

            sports_map = {}
            for s in demo_sports:
                existing = db.query(Sport).filter(Sport.name == s["name"]).first()
                if existing:
                    sports_map[s["name"]] = existing
                else:
                    new_sport = Sport(name=s["name"], category=s["category"], is_active=True)
                    db.add(new_sport)
                    db.flush()
                    sports_map[s["name"]] = new_sport

            events_created = 0
            odds_created = 0

            for ev in demo_events:
                existing = db.query(Event).filter(Event.external_id == ev["external_id"]).first()
                if existing:
                    continue

                db_event = Event(
                    sport_id=sports_map[ev["sport"]].id,
                    external_id=ev["external_id"],
                    name=ev["name"],
                    home_team=ev["home_team"],
                    away_team=ev["away_team"],
                    start_time=now + timedelta(hours=ev["hours"]),
                    status="upcoming",
                    venue="Demo Arena",
                )
                db.add(db_event)
                db.flush()
                events_created += 1

                for bookmaker, selections in bookmaker_odds.items():
                    for selection, odds_decimal in selections.items():
                        # Skip draw for tennis
                        if ev["sport"] == "tennis" and selection == "draw":
                            continue
                        db.add(Odds(
                            event_id=db_event.id,
                            bookmaker=bookmaker,
                            market_type="h2h",
                            selection=selection,
                            odds_decimal=odds_decimal,
                            is_current=True,
                        ))
                        odds_created += 1

            logger.info(f"Seeded {events_created} events, {odds_created} odds entries")

    except Exception as e:
        logger.error(f"Error seeding demo data: {e}")


async def _try_fetch_live_odds():
    """Attempt one-shot live odds fetch. Returns True if events were stored."""
    try:
        from src.data_ingestion.odds_ingestion_service import OddsIngestionService
        service = OddsIngestionService()
        await service.fetch_and_store_odds()
        logger.info("Live odds fetch completed")

        # Check if we actually got events
        from src.database.database import db_manager
        from src.database.models import Event
        with db_manager.get_session() as db:
            count = db.query(Event).count()
            logger.info(f"Database now has {count} events after live fetch")
            return count > 0
    except Exception as e:
        logger.warning(f"Live odds fetch failed: {e}")
        return False


def _ensure_trained_model():
    """Train or load the XGBoost model so predictions are real, not defaults."""
    import os
    from pathlib import Path

    model_path = Path("data/models/xgboost_latest.pkl")

    if model_path.exists():
        logger.info(f"Trained model found at {model_path}")
        return

    # No model on disk — train one from current odds data
    logger.info("No trained model found — training from current odds data...")
    try:
        from train_model import build_training_dataset, train_model, save_trained_model
        df = build_training_dataset()
        if len(df) < 20:
            logger.warning(f"Only {len(df)} training samples — skipping training")
            return
        model = train_model(df)
        save_trained_model(model)
        logger.info("Model trained and saved on startup")
    except Exception as e:
        logger.error(f"Auto-training failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Betting AI System API")
    init_database()
    logger.info("Database initialized")

    # Try fetching live odds first (await it so we have data before serving)
    live_success = await _try_fetch_live_odds()

    # Fall back to demo seed only if live fetch got nothing
    if not live_success:
        _seed_demo_data_if_empty()

    # Ensure ML model is trained (uses DB odds data)
    _ensure_trained_model()

    # Reset the predictor singleton so it picks up the trained model
    from src.api.routes.betting_routes import _ensemble_predictor
    import src.api.routes.betting_routes as br
    br._ensemble_predictor = None

    # ── Start auto-bet background loop ──
    import asyncio
    from src.services.auto_bet_service import auto_bet_loop, stop_auto_bet
    auto_bet_task = asyncio.create_task(auto_bet_loop())
    logger.info("Auto-bet background loop launched")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Betting AI System API")
    stop_auto_bet()
    auto_bet_task.cancel()
    try:
        await auto_bet_task
    except asyncio.CancelledError:
        pass
    close_database()


# Create FastAPI app
app = FastAPI(
    title="Betting AI System API",
    description="AI-powered betting analysis and recommendation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
import os
api_config = config.get_api_config()
cors_config = api_config.get('cors', {})

# Allow env override for CORS origins in production
cors_origins_env = os.getenv('CORS_ORIGINS', '')
if cors_origins_env:
    cors_origins = [o.strip() for o in cors_origins_env.split(',')]
else:
    cors_origins = cors_config.get('origins', ["*"])

if cors_config.get('enabled', True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(betting_routes.router, prefix="/api/v1/betting", tags=["betting"])
app.include_router(crypto_routes.router, prefix="/api/v1/crypto", tags=["crypto"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Betting AI System API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "betting": "/api/v1/betting",
            "crypto": "/api/v1/crypto",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db_session)):
    """Health check endpoint"""
    try:
        # Check database
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/api/v1/system/status")
async def system_status():
    """Get system status"""
    return {
        "status": "operational",
        "components": {
            "api": "running",
            "database": "connected",
            "ml_models": "loaded",
            "integrations": "active"
        },
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 8000)
    workers = api_config.get('workers', 4)
    
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        workers=workers,
        reload=True
    )
