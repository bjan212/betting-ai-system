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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Betting AI System API")
    init_database()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Betting AI System API")
    close_database()


# Create FastAPI app
app = FastAPI(
    title="Betting AI System API",
    description="AI-powered betting analysis and recommendation system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
api_config = config.get_api_config()
cors_config = api_config.get('cors', {})

if cors_config.get('enabled', True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get('origins', ["*"]),
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
