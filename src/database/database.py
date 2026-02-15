"""
Database connection and session management
"""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

from src.database.models import Base
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Load environment variables early so DATABASE_URL is available
load_dotenv()


class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self, database_url: str = None, pool_size: int = 20, max_overflow: int = 10):
        """
        Initialize database manager
        
        Args:
            database_url: Database connection URL
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
        """
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql://betting_user:changeme@localhost:5432/betting_ai_db'
        )
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=False,
            future=True
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Set up connection event listeners
        self._setup_event_listeners()
        
        logger.info(f"Database manager initialized with pool_size={pool_size}")
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners"""
        
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Event listener for new connections"""
            logger.debug("New database connection established")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Event listener for connection checkout"""
            logger.debug("Connection checked out from pool")
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        
        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_db(self) -> Generator[Session, None, None]:
        """
        Dependency for FastAPI to get database session
        
        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """
        Check database connection health
        
        Returns:
            True if database is healthy, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        try:
            self.engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection
    
    Yields:
        Database session
    """
    yield from db_manager.get_db()


def init_database():
    """Initialize database tables"""
    db_manager.create_tables()


def close_database():
    """Close database connections"""
    db_manager.close()
