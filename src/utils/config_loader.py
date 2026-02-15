"""
Configuration loader for the Betting AI System
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """Configuration loader with environment variable support"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return
            
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Replace environment variables
            self.config = self._replace_env_vars(raw_config)
            
            logger.info(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _replace_env_vars(self, config: Any) -> Any:
        """
        Recursively replace environment variables in configuration
        
        Args:
            config: Configuration object (dict, list, or string)
        
        Returns:
            Configuration with environment variables replaced
        """
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Replace ${VAR_NAME} or ${VAR_NAME:default_value}
            if config.startswith('${') and config.endswith('}'):
                var_spec = config[2:-1]
                if ':' in var_spec:
                    var_name, default = var_spec.split(':', 1)
                    return os.getenv(var_name, default)
                else:
                    return os.getenv(var_spec, config)
        return config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key path
        
        Args:
            key_path: Dot-separated key path (e.g., 'ml_models.ensemble.models')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_database_url(self) -> str:
        """Get database URL"""
        return self.get('database.url', os.getenv('DATABASE_URL'))
    
    def get_sports_config(self) -> Dict[str, Any]:
        """Get sports configuration"""
        return self.get('sports', {})
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Get ML models configuration"""
        return self.get('ml_models', {})
    
    def get_recommendation_config(self) -> Dict[str, Any]:
        """Get recommendation configuration"""
        return self.get('recommendation', {})
    
    def get_betting_platform_config(self, platform: str = 'stake') -> Dict[str, Any]:
        """Get betting platform configuration"""
        return self.get(f'betting_platforms.{platform}', {})
    
    def get_crypto_config(self) -> Dict[str, Any]:
        """Get cryptocurrency configuration"""
        return self.get('cryptocurrency', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return self.get('api', {})
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()
        logger.info("Configuration reloaded")


# Global configuration instance
config = ConfigLoader()


def get_config() -> ConfigLoader:
    """
    Get global configuration instance
    
    Returns:
        Configuration loader instance
    """
    return config
