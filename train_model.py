#!/usr/bin/env python3
"""
Training pipeline for the XGBoost betting model.

Since we don't have historical match results, we use a market-implied approach:
1. Extract features from real bookmaker odds across events + bookmakers
2. Compute implied probabilities from odds (the "smart money" signal)
3. Generate outcomes weighted by implied probability
4. Train the model to learn the relationship between odds features and outcomes

This trains the model to predict outcomes *at least as well as the market*,
which is the baseline any profitable betting system must exceed.
"""
import os
import sys
import random
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.database import db_manager
from src.database.models import Event, Odds, Sport
from src.ml_models.xgboost_model import XGBoostModel
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Path for the trained model
MODEL_DIR = Path("data/models")
MODEL_PATH = MODEL_DIR / "xgboost_latest.pkl"


def compute_implied_prob(odds_decimal: float) -> float:
    """Convert decimal odds to implied probability."""
    if odds_decimal <= 1.0:
        return 1.0
    return 1.0 / odds_decimal


def remove_vig(probs: dict) -> dict:
    """Remove bookmaker overround (vig) to get fair probabilities."""
    total = sum(probs.values())
    if total == 0:
        return probs
    return {k: v / total for k, v in probs.items()}


def build_training_dataset() -> pd.DataFrame:
    """
    Build a training dataset from live odds data.

    For each event, we:
    1. Average odds across all bookmakers for each selection
    2. Compute fair implied probabilities (vig-removed)
    3. Derive odds-based features (spread, favorite strength, etc.)
    4. Generate multiple training samples with probabilistic outcomes

    Returns a DataFrame with 23 feature columns + 'outcome' target.
    """
    db_manager.create_tables()
    rows = []

    with db_manager.get_session() as db:
        events = db.query(Event).all()
        logger.info(f"Building training data from {len(events)} events")

        for event in events:
            current_odds = (
                db.query(Odds)
                .filter(Odds.event_id == event.id, Odds.is_current == True)
                .all()
            )
            if not current_odds:
                continue

            # Aggregate odds by selection across bookmakers
            odds_by_selection: dict[str, list[float]] = {}
            bookmaker_set = set()
            for o in current_odds:
                odds_by_selection.setdefault(o.selection, []).append(o.odds_decimal)
                bookmaker_set.add(o.bookmaker)

            # Compute average odds per selection
            avg_odds: dict[str, float] = {
                sel: np.mean(vals) for sel, vals in odds_by_selection.items()
            }

            home_odds = avg_odds.get("home", avg_odds.get(event.home_team, 2.0))
            away_odds = avg_odds.get("away", avg_odds.get(event.away_team, 2.0))
            draw_odds = avg_odds.get("Draw", avg_odds.get("draw", 3.5))

            # Fair implied probabilities (vig-removed)
            raw_probs = {
                "home": compute_implied_prob(home_odds),
                "away": compute_implied_prob(away_odds),
                "draw": compute_implied_prob(draw_odds),
            }
            fair_probs = remove_vig(raw_probs)

            # Odds spread / range features
            all_home = odds_by_selection.get("home", odds_by_selection.get(event.home_team, [home_odds]))
            all_away = odds_by_selection.get("away", odds_by_selection.get(event.away_team, [away_odds]))
            home_odds_std = float(np.std(all_home)) if len(all_home) > 1 else 0.0
            away_odds_std = float(np.std(all_away)) if len(all_away) > 1 else 0.0

            # Simulate odds movement (real systems would track this over time)
            home_movement = np.random.normal(0, home_odds_std * 0.3)
            away_movement = np.random.normal(0, away_odds_std * 0.3)

            # Derive features that approximate the 23 the model expects
            home_implied = fair_probs["home"]
            away_implied = fair_probs["away"]
            draw_implied = fair_probs["draw"]

            # Approximate win rates from implied probability + noise
            home_win_rate = np.clip(home_implied + np.random.normal(0, 0.05), 0.05, 0.95)
            away_win_rate = np.clip(away_implied + np.random.normal(0, 0.05), 0.05, 0.95)

            # Recent form: correlated with implied probability
            home_form = np.clip(home_implied + np.random.normal(0, 0.08), 0.1, 0.9)
            away_form = np.clip(away_implied + np.random.normal(0, 0.08), 0.1, 0.9)

            # H2H stats derived from relative strength
            strength_ratio = home_implied / (home_implied + away_implied) if (home_implied + away_implied) > 0 else 0.5
            n_h2h = np.random.randint(3, 12)
            h2h_home = int(round(n_h2h * strength_ratio))
            h2h_away = int(round(n_h2h * (1 - strength_ratio)))
            h2h_draws = max(0, n_h2h - h2h_home - h2h_away)

            # Venue advantage from home implied prob vs 50%
            venue_advantage = (home_implied - 0.5) * 2  # Scale: -1 to +1

            # Approximate performance stats from implied strength
            home_goals_scored = 1.0 + home_implied * 1.5 + np.random.normal(0, 0.2)
            away_goals_scored = 1.0 + away_implied * 1.5 + np.random.normal(0, 0.2)
            home_goals_conceded = 1.0 + (1 - home_implied) * 1.5 + np.random.normal(0, 0.2)
            away_goals_conceded = 1.0 + (1 - away_implied) * 1.5 + np.random.normal(0, 0.2)

            # Rankings correlated with strength
            home_ranking = int(np.clip(100 - home_implied * 100 + np.random.normal(0, 10), 1, 100))
            away_ranking = int(np.clip(100 - away_implied * 100 + np.random.normal(0, 10), 1, 100))

            # Generate MULTIPLE training samples per event 
            # (different simulated outcomes, adds diversity)
            n_samples = max(5, len(bookmaker_set))  # More bookmakers = more data

            for _ in range(n_samples):
                # Simulate outcome based on fair implied probabilities
                rng = np.random.random()
                if rng < fair_probs["home"]:
                    outcome = 1  # Home win (positive class)
                elif rng < fair_probs["home"] + fair_probs["draw"]:
                    outcome = 0  # Draw
                else:
                    outcome = 0  # Away win

                # Add per-sample noise to features (data augmentation)
                noise = lambda scale=0.02: np.random.normal(0, scale)

                row = {
                    "home_win_rate": np.clip(home_win_rate + noise(0.03), 0.05, 0.95),
                    "away_win_rate": np.clip(away_win_rate + noise(0.03), 0.05, 0.95),
                    "home_recent_form": np.clip(home_form + noise(0.04), 0.1, 0.9),
                    "away_recent_form": np.clip(away_form + noise(0.04), 0.1, 0.9),
                    "h2h_home_wins": h2h_home,
                    "h2h_away_wins": h2h_away,
                    "h2h_draws": h2h_draws,
                    "home_odds": home_odds + noise(0.05),
                    "away_odds": away_odds + noise(0.05),
                    "draw_odds": draw_odds + noise(0.05),
                    "odds_movement_home": home_movement + noise(0.01),
                    "odds_movement_away": away_movement + noise(0.01),
                    "is_home_game": 1,
                    "venue_advantage": np.clip(venue_advantage + noise(0.05), -1, 1),
                    "days_since_last_game_home": np.random.randint(3, 10),
                    "days_since_last_game_away": np.random.randint(3, 10),
                    "home_goals_scored_avg": max(0.3, home_goals_scored + noise(0.1)),
                    "away_goals_scored_avg": max(0.3, away_goals_scored + noise(0.1)),
                    "home_goals_conceded_avg": max(0.3, home_goals_conceded + noise(0.1)),
                    "away_goals_conceded_avg": max(0.3, away_goals_conceded + noise(0.1)),
                    "home_ranking": max(1, home_ranking + int(noise(3))),
                    "away_ranking": max(1, away_ranking + int(noise(3))),
                    "ranking_difference": home_ranking - away_ranking + int(noise(3)),
                    "outcome": outcome,
                }
                rows.append(row)

    df = pd.DataFrame(rows)
    logger.info(f"Built training dataset: {len(df)} samples, {len(df.columns) - 1} features")
    logger.info(f"Outcome distribution: {dict(df['outcome'].value_counts())}")
    return df


def train_model(df: pd.DataFrame) -> XGBoostModel:
    """Train the XGBoost model on the prepared dataset."""
    model = XGBoostModel()

    # Override params to reduce overfitting (config.yaml may have aggressive defaults)
    model.params.update({
        'max_depth': 4,
        'learning_rate': 0.05,
        'n_estimators': 300,
        'subsample': 0.7,
        'colsample_bytree': 0.7,
        'min_child_weight': 5,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
    })

    logger.info("Starting model training...")
    metrics = model.train(df, target_column="outcome")

    logger.info(f"Training complete!")
    logger.info(f"  Train accuracy: {metrics['train_accuracy']:.4f}")
    logger.info(f"  Val accuracy:   {metrics['val_accuracy']:.4f}")
    logger.info(f"  Samples:        {metrics['n_samples']}")
    logger.info(f"  Features:       {metrics['n_features']}")

    # Feature importance
    importance = model.get_feature_importance()
    if importance:
        sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        logger.info("Top 10 features:")
        for name, score in sorted_imp[:10]:
            logger.info(f"  {name:30s} {score:.4f}")

    return model


def save_trained_model(model: XGBoostModel):
    """Save the trained model to the standard path."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))
    logger.info(f"Model saved to {MODEL_PATH}")


def main():
    print("=" * 60)
    print("  XGBoost Betting Model Training Pipeline")
    print("=" * 60)
    print()

    # Step 1: Build training data
    print("[1/3] Building training dataset from live odds...")
    df = build_training_dataset()
    print(f"      Dataset: {len(df)} samples, {len(df.columns) - 1} features")
    print(f"      Outcome split: {dict(df['outcome'].value_counts())}")
    print()

    # Step 2: Train model
    print("[2/3] Training XGBoost model...")
    model = train_model(df)
    print()

    # Step 3: Save model
    print("[3/3] Saving trained model...")
    save_trained_model(model)
    print(f"      Saved to: {MODEL_PATH}")
    print()

    # Quick test prediction
    print("=" * 60)
    print("  Testing prediction on sample event...")
    print("=" * 60)
    test_event = {
        "home_odds": 1.5, "away_odds": 3.8, "draw_odds": 4.2,
        "home_win_rate": 0.65, "away_win_rate": 0.35,
        "home_recent_form": 0.7, "away_recent_form": 0.4,
        "h2h_home_wins": 5, "h2h_away_wins": 2, "h2h_draws": 1,
        "odds_movement_home": -0.05, "odds_movement_away": 0.03,
        "is_home_game": 1, "venue_advantage": 0.3,
        "days_since_last_game_home": 5, "days_since_last_game_away": 7,
        "home_goals_scored_avg": 2.1, "away_goals_scored_avg": 1.2,
        "home_goals_conceded_avg": 0.9, "away_goals_conceded_avg": 1.6,
        "home_ranking": 15, "away_ranking": 45,
        "ranking_difference": -30,
    }
    pred = model.predict(test_event)
    print(f"  Prediction: {'Home Win' if pred['prediction'] == 1 else 'Away/Draw'}")
    print(f"  Confidence: {pred['confidence']:.1%}")
    print(f"  Home win probability: {pred['probability']:.1%}")
    print()
    print("Done! Model is ready for live predictions.")


if __name__ == "__main__":
    main()
