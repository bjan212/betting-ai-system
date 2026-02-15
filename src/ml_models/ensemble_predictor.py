"""
Ensemble ML Predictor - Combines multiple models for robust predictions
"""
from typing import Dict, List, Any, Tuple
import numpy as np
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.config_loader import get_config

logger = get_logger(__name__)
config = get_config()


class EnsemblePredictor:
    """
    Ensemble predictor combining multiple ML models
    """
    
    def __init__(self):
        """Initialize ensemble predictor"""
        self.models = {}
        self.model_weights = {}
        self.ml_config = config.get_ml_config()
        
        # Load model configurations
        ensemble_config = self.ml_config.get('ensemble', {})
        self.model_configs = ensemble_config.get('models', [])
        
        # Initialize model weights
        for model_config in self.model_configs:
            if model_config.get('enabled', True):
                model_name = model_config['name']
                self.model_weights[model_name] = model_config.get('weight', 0.25)
        
        logger.info(f"Ensemble predictor initialized with models: {list(self.model_weights.keys())}")
    
    def register_model(self, model_name: str, model_instance: Any):
        """
        Register a model with the ensemble
        
        Args:
            model_name: Name of the model
            model_instance: Model instance
        """
        self.models[model_name] = model_instance
        logger.info(f"Model registered: {model_name}")
    
    def predict(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate ensemble prediction for an event
        
        Args:
            event_data: Event data including features
        
        Returns:
            Ensemble prediction with confidence scores
        """
        try:
            predictions = {}
            confidences = {}
            probabilities = {}
            
            # Get predictions from each model
            for model_name, model in self.models.items():
                if model_name in self.model_weights:
                    try:
                        pred = model.predict(event_data)
                        predictions[model_name] = pred['prediction']
                        confidences[model_name] = pred.get('confidence', 0.5)
                        probabilities[model_name] = pred.get('probability', 0.5)
                    except Exception as e:
                        logger.error(f"Error in {model_name} prediction: {e}")
                        continue
            
            if not predictions:
                logger.warning("No valid predictions from models")
                return self._default_prediction()
            
            # Calculate weighted ensemble prediction
            ensemble_result = self._calculate_ensemble(
                predictions, confidences, probabilities
            )
            
            return ensemble_result
            
        except Exception as e:
            logger.error(f"Error in ensemble prediction: {e}")
            return self._default_prediction()
    
    def _calculate_ensemble(
        self,
        predictions: Dict[str, Any],
        confidences: Dict[str, float],
        probabilities: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate weighted ensemble prediction
        
        Args:
            predictions: Individual model predictions
            confidences: Model confidence scores
            probabilities: Model probability estimates
        
        Returns:
            Ensemble prediction result
        """
        # Normalize weights for available models
        available_weights = {
            name: self.model_weights[name]
            for name in predictions.keys()
            if name in self.model_weights
        }
        
        total_weight = sum(available_weights.values())
        normalized_weights = {
            name: weight / total_weight
            for name, weight in available_weights.items()
        }
        
        # Calculate weighted confidence
        weighted_confidence = sum(
            confidences[name] * normalized_weights[name]
            for name in predictions.keys()
        )
        
        # Calculate weighted probability
        weighted_probability = sum(
            probabilities[name] * normalized_weights[name]
            for name in predictions.keys()
        )
        
        # Determine consensus prediction
        prediction_counts = {}
        for name, pred in predictions.items():
            pred_str = str(pred)
            if pred_str not in prediction_counts:
                prediction_counts[pred_str] = 0
            prediction_counts[pred_str] += normalized_weights[name]
        
        # Get prediction with highest weighted vote
        consensus_prediction = max(
            prediction_counts.items(),
            key=lambda x: x[1]
        )[0]
        
        # Calculate expected value
        expected_value = self._calculate_expected_value(
            weighted_probability,
            event_data={}  # Would include odds data
        )
        
        return {
            'prediction': consensus_prediction,
            'confidence': weighted_confidence,
            'probability': weighted_probability,
            'expected_value': expected_value,
            'individual_predictions': predictions,
            'individual_confidences': confidences,
            'model_weights': normalized_weights,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_expected_value(
        self,
        probability: float,
        event_data: Dict[str, Any]
    ) -> float:
        """
        Calculate expected value of a bet
        
        Args:
            probability: Win probability
            event_data: Event data including odds
        
        Returns:
            Expected value (EV)
        """
        # Get odds from event data (default to 2.0 if not available)
        odds = event_data.get('odds', 2.0)
        
        # EV = (probability * (odds - 1)) - (1 - probability)
        ev = (probability * (odds - 1)) - (1 - probability)
        
        return ev
    
    def _default_prediction(self) -> Dict[str, Any]:
        """
        Return default prediction when models fail
        
        Returns:
            Default prediction structure
        """
        return {
            'prediction': 'unknown',
            'confidence': 0.0,
            'probability': 0.5,
            'expected_value': 0.0,
            'individual_predictions': {},
            'individual_confidences': {},
            'model_weights': {},
            'timestamp': datetime.utcnow().isoformat(),
            'error': 'No valid predictions available'
        }
    
    def batch_predict(
        self,
        events_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate predictions for multiple events
        
        Args:
            events_data: List of event data
        
        Returns:
            List of predictions
        """
        predictions = []
        
        for event_data in events_data:
            try:
                pred = self.predict(event_data)
                predictions.append(pred)
            except Exception as e:
                logger.error(f"Error predicting event {event_data.get('id')}: {e}")
                predictions.append(self._default_prediction())
        
        return predictions
    
    def get_model_performance(self) -> Dict[str, Any]:
        """
        Get performance metrics for each model
        
        Returns:
            Model performance statistics
        """
        performance = {}
        
        for model_name, model in self.models.items():
            try:
                if hasattr(model, 'get_performance'):
                    performance[model_name] = model.get_performance()
                else:
                    performance[model_name] = {'status': 'no_metrics_available'}
            except Exception as e:
                logger.error(f"Error getting performance for {model_name}: {e}")
                performance[model_name] = {'error': str(e)}
        
        return performance
    
    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update model weights based on performance
        
        Args:
            new_weights: New weight assignments
        """
        for model_name, weight in new_weights.items():
            if model_name in self.model_weights:
                self.model_weights[model_name] = weight
                logger.info(f"Updated weight for {model_name}: {weight}")
        
        # Normalize weights
        total = sum(self.model_weights.values())
        self.model_weights = {
            name: weight / total
            for name, weight in self.model_weights.items()
        }
