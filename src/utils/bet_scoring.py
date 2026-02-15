"""
Advanced Bet Scoring and Unit Sizing
Inspired by Leans.ai's approach to selective, unit-based betting
"""
from typing import Dict, Any
import math


def calculate_unit_size(
    confidence: float,
    expected_value: float,
    risk_score: float,
    max_units: float = 5.0
) -> float:
    """
    Calculate recommended bet units based on confidence and edge
    
    Leans.ai approach: Variable unit sizing based on strength of prediction
    - 1 unit = standard bet
    - 2-3 units = strong confidence
    - 4-5 units = very strong confidence
    
    Args:
        confidence: Model confidence (0.0-1.0)
        expected_value: Expected value (typically 1.0-2.0, where 1.1 = 10% edge)
        risk_score: Risk assessment (0.0-1.0, lower is better)
        max_units: Maximum unit size
        
    Returns:
        Recommended unit size (0.5-5.0)
    """
    # Base units on confidence
    if confidence < 0.70:
        return 0.0  # Don't bet if confidence too low
    
    # Calculate edge (how much better than breakeven)
    edge = expected_value - 1.0
    
    # Adjust for risk
    risk_penalty = risk_score * 0.5
    
    # Unit formula: higher confidence + higher edge + lower risk = more units
    base_units = (
        (confidence - 0.65) * 10 +  # 0.70 conf = 0.5 units, 0.80 = 1.5 units
        edge * 5 +  # 10% edge adds 0.5 units
        (1.0 - risk_score) * 2  # Lower risk adds units
    ) - risk_penalty
    
    # Clamp between 0.5 and max_units
    units = max(0.5, min(max_units, base_units))
    
    # Round to nearest 0.5
    return round(units * 2) / 2


def calculate_ev_with_vig(
    win_probability: float,
    decimal_odds: float,
    vig_rate: float = 0.0476  # Standard -110 juice (4.76%)
) -> float:
    """
    Calculate Expected Value including vigorish (bookmaker commission)
    
    Leans.ai includes vig in their calculations for honest metrics
    
    Args:
        win_probability: Predicted probability of winning (0.0-1.0)
        decimal_odds: Decimal odds (e.g., 2.0 for even money)
        vig_rate: Vigorish rate (default 0.0476 = -110 American odds)
        
    Returns:
        Expected value including vig (1.0 = breakeven)
    """
    # Adjusted payout after vigholds
    effective_payout = decimal_odds * (1 - vig_rate)
    
    # EV = (win_prob * payout) - (loss_prob * stake)
    ev = (win_probability * effective_payout) - (1 - win_probability)
    
    # Return as multiplier (1.0 = breakeven, 1.1 = 10% edge)
    return 1 + ev


def inverse_filter_bad_bets(
    confidence: float,
    expected_value: float,
    risk_score: float,
    min_confidence: float = 0.70,
    min_ev: float = 1.08,  # At least 8% edge after vig
    max_risk: float = 0.65
) -> tuple[bool, str]:
    """
    Inverse filtering: Reject bets that don't meet quality standards
    
    Leans.ai approach: Better to skip a bet than make a bad one
    
    Args:
        confidence: Model confidence (0.0-1.0)
        expected_value: Expected value
        risk_score: Risk assessment (0.0-1.0)
        min_confidence: Minimum confidence threshold
        min_ev: Minimum expected value
        max_risk: Maximum acceptable risk
        
    Returns:
        Tuple of (is_valid, rejection_reason)
    """
    # Check confidence
    if confidence < min_confidence:
        return (False, f"Low confidence: {confidence:.1%} < {min_confidence:.1%}")
    
    # Check expected value
    if expected_value < min_ev:
        edge = (expected_value - 1.0) * 100
        min_edge = (min_ev - 1.0) * 100
        return (False, f"Low edge: {edge:.1f}% < {min_edge:.1f}%")
    
    # Check risk
    if risk_score > max_risk:
        return (False, f"High risk: {risk_score:.1%} > {max_risk:.1%}")
    
    # Additional filters: Inverse bad patterns
    
    # If high confidence but low EV, model might be overconfident
    if confidence > 0.85 and expected_value < 1.10:
        return (False, "High confidence with low edge suggests overconfidence")
    
    # If low risk but low EV, might be a false sense of security
    if risk_score < 0.3 and expected_value < 1.12:
        return (False, "Low risk with marginal edge suggests false security")
    
    return (True, "Passes all filters")


def calculate_streak_adjustment(
    recent_results: list[bool],
    base_units: float,
    max_adjustment: float = 0.5
) -> float:
    """
    Adjust unit sizing based on recent performance streak
    
    Leans.ai observation: Systems can be "hot" or "cold" 
    
    Args:
        recent_results: List of recent bet outcomes (True=win, False=loss)
        base_units: Base unit size before adjustment
        max_adjustment: Maximum adjustment (default ±0.5 units)
        
    Returns:
        Adjusted unit size
    """
    if not recent_results or len(recent_results) < 3:
        return base_units
    
    # Look at last 10 bets
    recent = recent_results[-10:]
    win_rate = sum(recent) / len(recent)
    
    # Adjust based on recent performance
    if win_rate >= 0.70:
        # Hot streak: increase slightly
        adjustment = min(max_adjustment, 0.5)
    elif win_rate <= 0.40:
        # Cold streak: decrease slightly
        adjustment = -min(max_adjustment, 0.5)
    else:
        # Normal variance
        adjustment = 0.0
    
    return max(0.5, base_units + adjustment)


def calculate_composite_score(
    confidence: float,
    expected_value: float,
    risk_score: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Calculate composite score for ranking bets (Leans.ai style)
    
    Args:
        confidence: Model confidence (0.0-1.0)
        expected_value: Expected value
        risk_score: Risk assessment (0.0-1.0, lower is better)
        weights: Custom weights for each component
        
    Returns:
        Composite score (higher is better)
    """
    if weights is None:
        weights = {
            'confidence': 0.40,  # 40% weight
            'ev': 0.35,  # 35% weight
            'risk_adjusted': 0.25  # 25% weight
        }
    
    # Normalize components
    confidence_score = confidence
    ev_score = (expected_value - 1.0) * 5  # Scale 10% edge to 0.5 score
    risk_adjusted_score = (1.0 - risk_score) * expected_value  # Risk-adjusted return
    
    # Weighted composite
    composite = (
        weights['confidence'] * confidence_score +
        weights['ev'] * ev_score +
        weights['risk_adjusted'] * risk_adjusted_score
    )
    
    return composite


def kelly_criterion(
    win_probability: float,
    decimal_odds: float,
    fraction: float = 0.25
) -> float:
    """
    Kelly Criterion for optimal bet sizing
    
    Args:
        win_probability: Probability of winning (0.0-1.0)
        decimal_odds: Decimal odds
        fraction: Fraction of Kelly to use (0.25 = quarter Kelly, conservative)
        
    Returns:
        Recommended bet fraction of bankroll (0.0-1.0)
    """
    # Kelly formula: (bp - q) / b
    # where b = odds-1, p = win prob, q = 1-p
    
    b = decimal_odds - 1.0
    p = win_probability
    q = 1.0 - p
    
    # Full Kelly
    kelly = (b * p - q) / b
    
    # Apply fraction for safety (quarter Kelly is common)
    safe_kelly = max(0.0, min(0.20, kelly * fraction))
    
    return safe_kelly
