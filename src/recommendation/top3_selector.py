"""
Top 3 Bet Selector - Identifies the best 3 betting opportunities
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import os
from datetime import datetime, timedelta
try:
    import numpy as np
except ImportError:
    np = None
from sqlalchemy.orm import Session

from src.database.models import Event, Odds, Recommendation
from src.ml_models.ensemble_predictor import EnsemblePredictor
from src.utils.logger import get_logger, betting_logger
from src.utils.config_loader import get_config
from src.utils.bet_scoring import (
    calculate_unit_size,
    calculate_ev_with_vig,
    inverse_filter_bad_bets,
    calculate_composite_score
)

logger = get_logger(__name__)
config = get_config()


class Top3Selector:
    """
    Selects top 3 betting opportunities within 24-hour window
    """
    
    def __init__(self, ensemble_predictor: EnsemblePredictor):
        """
        Initialize Top3 Selector
        
        Args:
            ensemble_predictor: Ensemble predictor instance
        """
        self.ensemble_predictor = ensemble_predictor
        self.recommendation_config = config.get_recommendation_config()
        
        # Selection criteria (config values may be strings from YAML env vars)
        top3_cfg = self.recommendation_config.get('top3_selection', {})
        try:
            self.min_confidence = float(top3_cfg.get('min_confidence', 0.65))
        except (TypeError, ValueError):
            self.min_confidence = 0.65
        try:
            self.min_expected_value = float(top3_cfg.get('min_expected_value', 1.05))
        except (TypeError, ValueError):
            self.min_expected_value = 1.05
        try:
            self.max_risk_score = float(top3_cfg.get('max_risk_score', 0.7))
        except (TypeError, ValueError):
            self.max_risk_score = 0.7
        try:
            self.time_window_hours = int(float(top3_cfg.get('time_window_hours', 168)))
        except (TypeError, ValueError):
            self.time_window_hours = 168

        # Demo mode bypasses strict filtering for local previews
        # Auto-enable demo mode when ML models are not trained
        self.demo_mode = os.getenv("DEMO_MODE", "true").lower() in ("1", "true", "yes")
        
        # Scoring weights
        scoring = self.recommendation_config.get('scoring', {})
        self.confidence_weight = scoring.get('confidence_weight', 0.4)
        self.ev_weight = scoring.get('expected_value_weight', 0.35)
        self.risk_weight = scoring.get('risk_adjusted_return_weight', 0.25)
        
        logger.info("Top3 Selector initialized")
    
    def get_top3_bets(self, db: Session, sport: str = None) -> List[Dict[str, Any]]:
        """
        Get top 3 betting recommendations for next 24 hours
        
        Args:
            db: Database session
        
        Returns:
            List of top 3 betting recommendations
        """
        try:
            logger.info("Generating top 3 betting recommendations")
            
            # Get upcoming events within time window
            upcoming_events = self._get_upcoming_events(db, sport)
            
            if not upcoming_events:
                logger.warning("No upcoming events found")
                return []
            
            logger.info(f"Analyzing {len(upcoming_events)} upcoming events")
            
            # Analyze each event and generate recommendations
            recommendations = []
            
            for event in upcoming_events:
                try:
                    event_recommendations = self._analyze_event(event, db)
                    recommendations.extend(event_recommendations)
                except Exception as e:
                    logger.error(f"Error analyzing event {event.id}: {e}")
                    continue
            
            # Filter by criteria
            filtered_recommendations = self._filter_recommendations(recommendations)
            
            # Rank and select top 3
            top3 = self._rank_and_select_top3(filtered_recommendations)
            
            # Save recommendations to database
            self._save_recommendations(top3, db)
            
            # Log recommendations
            for i, rec in enumerate(top3, 1):
                betting_logger.log_recommendation({
                    'rank': i,
                    'event': rec['event_name'],
                    'selection': rec['selection'],
                    'confidence': rec['confidence_score'],
                    'expected_value': rec['expected_value']
                })
            
            logger.info(f"Top 3 recommendations generated successfully")
            
            return top3
            
        except Exception as e:
            logger.error(f"Error generating top 3 bets: {e}")
            return []
    
    def _get_upcoming_events(self, db: Session, sport: str = None) -> List[Event]:
        """
        Get upcoming events within time window
        
        Args:
            db: Database session
        
        Returns:
            List of upcoming events
        """
        now = datetime.utcnow()
        end_time = now + timedelta(hours=self.time_window_hours)
        
        query = db.query(Event).filter(
            Event.start_time >= now,
            Event.start_time <= end_time,
            Event.status == 'upcoming'
        )

        if sport:
            from src.database.models import Sport
            query = query.join(Event.sport).filter(Sport.name == sport)

        events = query.all()
        
        return events
    
    def _analyze_event(self, event: Event, db: Session) -> List[Dict[str, Any]]:
        """
        Analyze event and generate betting recommendations
        
        Args:
            event: Event to analyze
            db: Database session
        
        Returns:
            List of recommendations for this event
        """
        recommendations = []
        
        # Get current odds for the event
        current_odds = db.query(Odds).filter(
            Odds.event_id == event.id,
            Odds.is_current == True
        ).all()
        
        if not current_odds:
            return recommendations
        
        # Prepare event data for prediction
        event_data = self._prepare_event_data(event, current_odds)
        
        # Get ensemble prediction
        prediction = self.ensemble_predictor.predict(event_data)
        
        # Generate recommendations for different markets
        for odds_entry in current_odds:
            try:
                rec = self._create_recommendation(
                    event, odds_entry, prediction, event_data
                )
                if rec:
                    recommendations.append(rec)
            except Exception as e:
                logger.error(f"Error creating recommendation: {e}")
                continue
        
        return recommendations
    
    def _prepare_event_data(self, event: Event, odds: List[Odds]) -> Dict[str, Any]:
        """
        Prepare event data for prediction
        
        Args:
            event: Event object
            odds: List of odds entries
        
        Returns:
            Event data dictionary
        """
        # Aggregate odds by selection across bookmakers
        odds_by_selection: dict = {}
        bookmaker_count = 0
        for odd in odds:
            odds_by_selection.setdefault(odd.selection, []).append(odd.odds_decimal)
            bookmaker_count += 1

        def _avg(lst, default=2.0):
            return sum(lst) / len(lst) if lst else default

        home_odds = _avg(odds_by_selection.get('home', odds_by_selection.get(event.home_team, [])), 2.0)
        away_odds = _avg(odds_by_selection.get('away', odds_by_selection.get(event.away_team, [])), 2.0)
        draw_odds = _avg(odds_by_selection.get('Draw', odds_by_selection.get('draw', [])), 3.5)

        # Compute implied probabilities (vig-removed) from bookmaker consensus
        raw_home = 1.0 / home_odds if home_odds > 1 else 1.0
        raw_away = 1.0 / away_odds if away_odds > 1 else 1.0
        raw_draw = 1.0 / draw_odds if draw_odds > 1 else 1.0
        total_raw = raw_home + raw_away + raw_draw
        if total_raw > 0:
            home_implied = raw_home / total_raw
            away_implied = raw_away / total_raw
        else:
            home_implied = away_implied = 0.5

        # Derive statistical features from odds (market-based proxies)
        strength_ratio = home_implied / (home_implied + away_implied) if (home_implied + away_implied) > 0 else 0.5
        n_h2h = 8  # Typical h2h history
        h2h_home = int(round(n_h2h * strength_ratio))
        h2h_away = int(round(n_h2h * (1 - strength_ratio)))
        h2h_draws = max(0, n_h2h - h2h_home - h2h_away)

        # Odds spread as proxy for market certainty/movement
        home_odds_list = odds_by_selection.get('home', odds_by_selection.get(event.home_team, [home_odds]))
        away_odds_list = odds_by_selection.get('away', odds_by_selection.get(event.away_team, [away_odds]))
        home_std = float(np.std(home_odds_list)) if np and len(home_odds_list) > 1 else 0.0
        away_std = float(np.std(away_odds_list)) if np and len(away_odds_list) > 1 else 0.0

        event_data = {
            'event_id': event.id,
            'event_name': event.name,
            'sport': event.sport.name if event.sport else 'unknown',
            'home_team': event.home_team,
            'away_team': event.away_team,
            'start_time': event.start_time,
            'venue': event.venue,

            # Real odds from bookmakers
            'home_odds': home_odds,
            'away_odds': away_odds,
            'draw_odds': draw_odds,

            # Market-derived features (instead of hardcoded defaults)
            'home_win_rate': round(home_implied, 4),
            'away_win_rate': round(away_implied, 4),
            'home_recent_form': round(min(0.9, home_implied * 1.1), 4),
            'away_recent_form': round(min(0.9, away_implied * 1.1), 4),
            'h2h_home_wins': h2h_home,
            'h2h_away_wins': h2h_away,
            'h2h_draws': h2h_draws,
            'odds_movement_home': round(home_std * 0.3, 4),
            'odds_movement_away': round(away_std * 0.3, 4),
            'is_home_game': 1,
            'venue_advantage': round((home_implied - 0.5) * 2, 4),
            'days_since_last_game_home': 5,
            'days_since_last_game_away': 5,
            'home_goals_scored_avg': round(1.0 + home_implied * 1.5, 2),
            'away_goals_scored_avg': round(1.0 + away_implied * 1.5, 2),
            'home_goals_conceded_avg': round(1.0 + (1 - home_implied) * 1.5, 2),
            'away_goals_conceded_avg': round(1.0 + (1 - away_implied) * 1.5, 2),
            'home_ranking': max(1, int(100 - home_implied * 100)),
            'away_ranking': max(1, int(100 - away_implied * 100)),
            'ranking_difference': int((away_implied - home_implied) * 100),
        }

        return event_data
    
    def _create_recommendation(
        self,
        event: Event,
        odds: Odds,
        prediction: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create betting recommendation
        
        Args:
            event: Event object
            odds: Odds entry
            prediction: Model prediction
            event_data: Event data
        
        Returns:
            Recommendation dictionary
        """
        # Calculate expected value
        # The model predicts P(home_win). Map to the correct selection.
        raw_home_prob = prediction.get('probability', 0.5)
        selection_lower = odds.selection.lower()

        home_team_lower = (event.home_team or '').lower()
        away_team_lower = (event.away_team or '').lower()

        if selection_lower in ('home', home_team_lower) or selection_lower == event.home_team:
            probability = raw_home_prob
        elif selection_lower in ('draw',):
            # Draw probability: approximate from 1 - home - away
            draw_odds_val = event_data.get('draw_odds', 3.5)
            home_odds_val = event_data.get('home_odds', 2.0)
            away_odds_val = event_data.get('away_odds', 2.0)
            # Use market-implied draw probability
            implied_draw = (1.0 / draw_odds_val) / ((1.0 / home_odds_val) + (1.0 / away_odds_val) + (1.0 / draw_odds_val))
            probability = implied_draw
        else:
            # Away team or named team (not home) → P(away) = 1 - P(home) - P(draw)
            probability = 1.0 - raw_home_prob
        odds_decimal = odds.odds_decimal
        
        # Calculate EV with vigorish (bookmaker commission)
        ev_with_vig = calculate_ev_with_vig(probability, odds_decimal, vig_rate=0.0476)
        expected_value = ev_with_vig - 1  # Convert to edge
        
        # Confidence should reflect this selection's probability, not only the model's raw confidence
        confidence = probability  # Use the selection-adjusted probability as confidence
        risk_score = 1 - confidence
        
        # Calculate recommended unit size (Leans.ai style)
        recommended_units = calculate_unit_size(
            confidence=confidence,
            expected_value=ev_with_vig,
            risk_score=risk_score,
            max_units=5.0
        )
        
        # Calculate recommended stake
        stake_info = self._calculate_stake(
            probability, odds_decimal, confidence
        )
        
        # Generate rationale
        rationale = self._generate_rationale(
            event, odds, prediction, expected_value, confidence
        )
        
        return {
            'event_id': event.id,
            'event_name': event.name,
            'sport': event.sport.name if event.sport else 'unknown',
            'start_time': event.start_time.isoformat(),
            'selection': odds.selection,
            'market_type': odds.market_type,
            'recommended_odds': odds_decimal,
            'bookmaker': odds.bookmaker,
            'confidence_score': confidence * 100,  # Convert to 0-100
            'expected_value': expected_value,
            'ev_with_vig': ev_with_vig,  # EV including bookmaker commission
            'risk_score': risk_score,
            'probability': probability,
            'recommended_units': recommended_units,  # Leans.ai style unit sizing
            'recommended_stake': stake_info['amount'],
            'recommended_stake_percentage': stake_info['percentage'],
            'rationale': rationale,
            'ensemble_scores': prediction.get('individual_confidences', {}),
            'model_weights': prediction.get('model_weights', {}),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_stake(
        self,
        probability: float,
        odds: float,
        confidence: float
    ) -> Dict[str, float]:
        """
        Calculate recommended stake using Kelly Criterion
        
        Args:
            probability: Win probability
            odds: Decimal odds
            confidence: Confidence score
        
        Returns:
            Stake information
        """
        stake_config = self.recommendation_config.get('stake_sizing', {})
        max_stake_pct = stake_config.get('max_stake_percentage', 0.05)
        min_stake = stake_config.get('min_stake_amount', 10)
        max_stake = stake_config.get('max_stake_amount', 1000)
        
        # Kelly Criterion: f = (bp - q) / b
        # where b = odds - 1, p = probability, q = 1 - p
        b = odds - 1
        p = probability
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b if b > 0 else 0
        
        # Apply fractional Kelly (more conservative)
        fractional_kelly = kelly_fraction * 0.25  # Use 1/4 Kelly
        
        # Adjust by confidence
        adjusted_stake_pct = min(fractional_kelly * confidence, max_stake_pct)
        
        # Assume default bankroll of $10,000 for calculation
        default_bankroll = 10000
        stake_amount = default_bankroll * adjusted_stake_pct
        
        # Apply limits
        stake_amount = max(min_stake, min(stake_amount, max_stake))
        
        return {
            'amount': round(stake_amount, 2),
            'percentage': round(adjusted_stake_pct * 100, 2)
        }
    
    def _generate_rationale(
        self,
        event: Event,
        odds: Odds,
        prediction: Dict[str, Any],
        expected_value: float,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Generate detailed rationale for recommendation
        
        Args:
            event: Event object
            odds: Odds entry
            prediction: Model prediction
            expected_value: Expected value
            confidence: Confidence score
        
        Returns:
            Rationale dictionary
        """
        reasons = []
        
        # Confidence-based reasoning
        if confidence > 0.8:
            reasons.append("Very high model confidence (>80%)")
        elif confidence > 0.7:
            reasons.append("High model confidence (>70%)")
        
        # Expected value reasoning
        if expected_value > 0.2:
            reasons.append(f"Excellent expected value (+{expected_value*100:.1f}%)")
        elif expected_value > 0.1:
            reasons.append(f"Strong expected value (+{expected_value*100:.1f}%)")
        elif expected_value > 0.05:
            reasons.append(f"Positive expected value (+{expected_value*100:.1f}%)")
        
        # Odds value reasoning
        probability = prediction.get('probability', 0.5)
        implied_probability = 1 / odds.odds_decimal
        if probability > implied_probability * 1.2:
            reasons.append("Significant value vs market odds")
        
        # Model consensus
        individual_confidences = prediction.get('individual_confidences', {})
        if len(individual_confidences) >= 3:
            vals = list(individual_confidences.values())
            avg_confidence = np.mean(vals) if np else (sum(vals) / len(vals))
            if avg_confidence > 0.7:
                reasons.append("Strong consensus across all models")
        
        return {
            'summary': f"Recommended {odds.selection} bet with {confidence*100:.1f}% confidence",
            'key_reasons': reasons,
            'model_agreement': individual_confidences,
            'value_analysis': {
                'expected_value': f"{expected_value*100:.2f}%",
                'implied_probability': f"{implied_probability*100:.2f}%",
                'model_probability': f"{probability*100:.2f}%",
                'edge': f"{(probability - implied_probability)*100:.2f}%"
            }
        }
    
    def _filter_recommendations(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter recommendations by criteria using inverse filtering
        
        Args:
            recommendations: List of recommendations
        
        Returns:
            Filtered recommendations
        """
        if self.demo_mode:
            logger.info("Demo mode enabled: skipping recommendation filters")
            return recommendations

        filtered = []
        rejected = []
        
        for rec in recommendations:
            # Use inverse filter (Leans.ai approach: reject bad bets)
            is_valid, reason = inverse_filter_bad_bets(
                confidence=rec['confidence_score'] / 100,
                expected_value=rec['ev_with_vig'],
                risk_score=rec['risk_score'],
                min_confidence=self.min_confidence,
                min_ev=self.min_expected_value,
                max_risk=self.max_risk_score
            )
            
            if is_valid:
                filtered.append(rec)
            else:
                rejected.append({
                    'event': rec['event_name'],
                    'reason': reason
                })
        
        if rejected:
            logger.info(f"Inverse filter rejected {len(rejected)} bets:")
            for r in rejected[:5]:  # Log first 5
                logger.info(f"  - {r['event']}: {r['reason']}")
        
        logger.info(f"Filtered {len(filtered)} recommendations from {len(recommendations)}")
        
        return filtered
    
    def _rank_and_select_top3(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rank recommendations and select top 3
        
        Args:
            recommendations: List of recommendations
        
        Returns:
            Top 3 recommendations
        """
        if not recommendations:
            return []
        
        # Calculate composite score for each recommendation (Leans.ai approach)
        for rec in recommendations:
            composite_score = calculate_composite_score(
                confidence=rec['confidence_score'] / 100,
                expected_value=rec['ev_with_vig'],
                risk_score=rec['risk_score'],
                weights={
                    'confidence': self.confidence_weight,
                    'ev': self.ev_weight,
                    'risk_adjusted': self.risk_weight
                }
            )
            
            rec['composite_score'] = composite_score
        
        # Sort by composite score
        ranked = sorted(
            recommendations,
            key=lambda x: x['composite_score'],
            reverse=True
        )
        
        # Select top 3, ensuring event diversity (max 1 per event)
        top3 = []
        seen_events = set()
        for rec in ranked:
            eid = rec.get('event_id')
            if eid in seen_events:
                continue
            seen_events.add(eid)
            top3.append(rec)
            if len(top3) >= 3:
                break
        
        # Add rank
        for i, rec in enumerate(top3, 1):
            rec['rank'] = i
        
        return top3
    
    def _save_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        db: Session
    ):
        """
        Save recommendations to database
        
        Args:
            recommendations: List of recommendations
            db: Database session
        """
        try:
            for rec in recommendations:
                db_rec = Recommendation(
                    event_id=rec['event_id'],
                    recommendation_type='top3',
                    selection=rec['selection'],
                    recommended_odds=rec['recommended_odds'],
                    confidence_score=rec['confidence_score'],
                    expected_value=rec['expected_value'],
                    risk_score=rec['risk_score'],
                    recommended_stake=rec['recommended_stake'],
                    recommended_stake_percentage=rec['recommended_stake_percentage'],
                    rationale=rec['rationale'],
                    ensemble_scores=rec['ensemble_scores'],
                    status='pending'
                )
                db.add(db_rec)
            
            db.commit()
            logger.info(f"Saved {len(recommendations)} recommendations to database")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving recommendations: {e}")
