"""
XGBoost Model for betting predictions
"""
from __future__ import annotations
try:
    import numpy as np
    import pandas as pd
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    HAS_ML = True
except ImportError:
    np = None
    pd = None
    xgb = None
    HAS_ML = False
from typing import Dict, Any, List
from datetime import datetime
import pickle
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.config_loader import get_config

logger = get_logger(__name__)
config = get_config()


class XGBoostModel:
    """
    XGBoost model for sports betting predictions
    """
    
    # Canonical feature order — MUST match between training and inference
    FEATURE_NAMES = [
        'home_win_rate', 'away_win_rate', 'home_recent_form', 'away_recent_form',
        'h2h_home_wins', 'h2h_away_wins', 'h2h_draws',
        'home_odds', 'away_odds', 'draw_odds',
        'odds_movement_home', 'odds_movement_away',
        'is_home_game', 'venue_advantage',
        'days_since_last_game_home', 'days_since_last_game_away',
        'home_goals_scored_avg', 'away_goals_scored_avg',
        'home_goals_conceded_avg', 'away_goals_conceded_avg',
        'home_ranking', 'away_ranking', 'ranking_difference',
    ]

    def __init__(self, model_name: str = "xgboost"):
        """Initialize XGBoost model"""
        self.model_name = model_name
        self.model = None
        self.feature_names = list(self.FEATURE_NAMES)
        self.is_trained = False
        
        # Load hyperparameters from config
        ml_config = config.get_ml_config()
        self.hyperparameters = ml_config.get('hyperparameters', {}).get('xgboost', {})
        
        # Default hyperparameters — tuned to reduce overfitting
        self.params = {
            'max_depth': self.hyperparameters.get('max_depth', 4),
            'learning_rate': self.hyperparameters.get('learning_rate', 0.05),
            'n_estimators': self.hyperparameters.get('n_estimators', 300),
            'subsample': self.hyperparameters.get('subsample', 0.7),
            'colsample_bytree': self.hyperparameters.get('colsample_bytree', 0.7),
            'min_child_weight': 5,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'random_state': 42
        }
        
        logger.info(f"XGBoost model initialized with params: {self.params}")
    
    def prepare_features(self, event_data: Dict[str, Any]) -> np.ndarray:
        """
        Prepare features from event data
        
        Args:
            event_data: Raw event data
        
        Returns:
            Feature array
        """
        features = []
        
        # Extract relevant features
        # Team/Player statistics
        features.append(event_data.get('home_win_rate', 0.5))
        features.append(event_data.get('away_win_rate', 0.5))
        features.append(event_data.get('home_recent_form', 0.5))
        features.append(event_data.get('away_recent_form', 0.5))
        
        # Head-to-head statistics
        features.append(event_data.get('h2h_home_wins', 0))
        features.append(event_data.get('h2h_away_wins', 0))
        features.append(event_data.get('h2h_draws', 0))
        
        # Odds-based features
        features.append(event_data.get('home_odds', 2.0))
        features.append(event_data.get('away_odds', 2.0))
        features.append(event_data.get('draw_odds', 3.0))
        
        # Market movement
        features.append(event_data.get('odds_movement_home', 0.0))
        features.append(event_data.get('odds_movement_away', 0.0))
        
        # Venue and conditions
        features.append(event_data.get('is_home_game', 1))
        features.append(event_data.get('venue_advantage', 0.0))
        
        # Time-based features
        features.append(event_data.get('days_since_last_game_home', 7))
        features.append(event_data.get('days_since_last_game_away', 7))
        
        # Performance metrics
        features.append(event_data.get('home_goals_scored_avg', 1.5))
        features.append(event_data.get('away_goals_scored_avg', 1.5))
        features.append(event_data.get('home_goals_conceded_avg', 1.5))
        features.append(event_data.get('away_goals_conceded_avg', 1.5))
        
        # Ranking/Rating
        features.append(event_data.get('home_ranking', 50))
        features.append(event_data.get('away_ranking', 50))
        features.append(event_data.get('ranking_difference', 0))
        
        return np.array(features).reshape(1, -1)
    
    def train(
        self,
        training_data: pd.DataFrame,
        target_column: str = 'outcome'
    ) -> Dict[str, float]:
        """
        Train the XGBoost model
        
        Args:
            training_data: Training dataset
            target_column: Name of target column
        
        Returns:
            Training metrics
        """
        try:
            logger.info(f"Training XGBoost model with {len(training_data)} samples")
            
            # Separate features and target, enforcing canonical column order
            X = training_data[self.FEATURE_NAMES]
            y = training_data[target_column]
            
            # Store feature names
            self.feature_names = list(self.FEATURE_NAMES)
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Create and train model
            self.model = xgb.XGBClassifier(**self.params)
            
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
            
            self.is_trained = True
            
            # Calculate metrics
            train_score = self.model.score(X_train, y_train)
            val_score = self.model.score(X_val, y_val)
            
            metrics = {
                'train_accuracy': train_score,
                'val_accuracy': val_score,
                'n_samples': len(training_data),
                'n_features': len(self.feature_names)
            }
            
            logger.info(f"XGBoost training complete. Val accuracy: {val_score:.4f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error training XGBoost model: {e}")
            raise
    
    def predict(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make prediction for an event
        
        Args:
            event_data: Event data
        
        Returns:
            Prediction with confidence
        """
        try:
            if not self.is_trained:
                logger.warning("Model not trained, using default prediction")
                return self._default_prediction()
            
            # Prepare features
            features = self.prepare_features(event_data)
            
            # Get prediction and probability
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            
            # Get confidence (max probability)
            confidence = float(np.max(probabilities))
            probability = float(probabilities[1])  # Probability of positive class
            
            return {
                'prediction': int(prediction),
                'confidence': confidence,
                'probability': probability,
                'model': self.model_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in XGBoost prediction: {e}")
            return self._default_prediction()
    
    def _default_prediction(self) -> Dict[str, Any]:
        """Return default prediction"""
        return {
            'prediction': 0,
            'confidence': 0.5,
            'probability': 0.5,
            'model': self.model_name,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores
        
        Returns:
            Feature importance dictionary
        """
        if not self.is_trained or not self.feature_names:
            return {}
        
        importance = self.model.feature_importances_
        return dict(zip(self.feature_names, importance))
    
    def save_model(self, path: str = None):
        """
        Save model to disk
        
        Args:
            path: Save path
        """
        if not self.is_trained:
            logger.warning("Cannot save untrained model")
            return
        
        if path is None:
            path = f"data/models/{self.model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'params': self.params
            }, f)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """
        Load model from disk
        
        Args:
            path: Model path
        """
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            self.model = data['model']
            self.feature_names = data['feature_names']
            self.params = data['params']
            self.is_trained = True
            
            logger.info(f"Model loaded from {path}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def get_performance(self) -> Dict[str, Any]:
        """
        Get model performance metrics
        
        Returns:
            Performance metrics
        """
        return {
            'model_name': self.model_name,
            'is_trained': self.is_trained,
            'n_features': len(self.feature_names),
            'params': self.params
        }
