"""
Logging configuration for the Betting AI System
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger


def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Get configured logger instance
    
    Args:
        name: Logger name (typically __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Console formatter
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with JSON formatting (skip on serverless/read-only filesystems)
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_dir / "betting_ai.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
    
        # JSON formatter for structured logging
        json_formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            timestamp=True
        )
        file_handler.setFormatter(json_formatter)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # Serverless / read-only filesystem — console only
        logger.addHandler(console_handler)
    
    return logger


class BettingLogger:
    """Specialized logger for betting operations"""
    
    def __init__(self, name: str = "betting"):
        self.logger = get_logger(name)
        
        # Create separate log file for betting operations (skip on serverless)
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            betting_handler = RotatingFileHandler(
                log_dir / "betting_operations.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=10
            )
            
            json_formatter = jsonlogger.JsonFormatter(
                '%(asctime)s %(name)s %(levelname)s %(message)s',
                timestamp=True
            )
            betting_handler.setFormatter(json_formatter)
            self.logger.addHandler(betting_handler)
        except (OSError, PermissionError):
            pass  # Serverless / read-only filesystem
    
    def log_prediction(self, event_id: int, model_name: str, prediction: dict):
        """Log prediction details"""
        self.logger.info(
            "Prediction made",
            extra={
                "event_id": event_id,
                "model_name": model_name,
                "prediction": prediction
            }
        )
    
    def log_recommendation(self, recommendation: dict):
        """Log betting recommendation"""
        self.logger.info(
            "Recommendation generated",
            extra={"recommendation": recommendation}
        )
    
    def log_bet_placement(self, bet_details: dict):
        """Log bet placement"""
        self.logger.info(
            "Bet placed",
            extra={"bet_details": bet_details}
        )
    
    def log_bet_outcome(self, bet_id: int, outcome: str, return_amount: float):
        """Log bet outcome"""
        self.logger.info(
            "Bet outcome recorded",
            extra={
                "bet_id": bet_id,
                "outcome": outcome,
                "return_amount": return_amount
            }
        )
    
    def log_transaction(self, transaction: dict):
        """Log cryptocurrency transaction"""
        self.logger.info(
            "Crypto transaction",
            extra={"transaction": transaction}
        )
    
    def log_error(self, error_type: str, error_message: str, context: dict = None):
        """Log error with context"""
        self.logger.error(
            f"{error_type}: {error_message}",
            extra={"context": context or {}}
        )


# Global betting logger instance
betting_logger = BettingLogger()
