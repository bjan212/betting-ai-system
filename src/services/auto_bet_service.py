"""
Auto-Bet & Ledger Service

Runs non-stop in the background:
  1. Periodically fetches top-3 recommendations and records them in the ledger
  2. Checks completed events via Odds API /scores to grade past bets (won/lost)
  3. Keeps a running P&L tally

Ledger uses the existing Recommendation table (status: pending → won/lost/void).
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from src.database.database import db_manager
from src.database.models import Event, Odds, Recommendation, Sport
from src.data_ingestion.odds_api_client import get_odds_client
from src.data_ingestion.odds_ingestion_service import OddsIngestionService
from src.ml_models.ensemble_predictor import EnsemblePredictor
from src.ml_models.xgboost_model import XGBoostModel
from src.recommendation.top3_selector import Top3Selector
from src.integrations.sportsbook_links import generate_bet_link
from src.utils.logger import get_logger, betting_logger

logger = get_logger(__name__)

TRAINED_MODEL_PATH = "data/models/xgboost_latest.pkl"

# ──────────────────────────── config ────────────────────────────
BET_INTERVAL_SECONDS = int(os.getenv("AUTO_BET_INTERVAL", "300"))      # 5 min
GRADE_INTERVAL_SECONDS = int(os.getenv("AUTO_GRADE_INTERVAL", "600"))  # 10 min
ODDS_REFRESH_INTERVAL = int(os.getenv("ODDS_REFRESH_INTERVAL", "900")) # 15 min

# Priority leagues to check scores for (1 credit each)
SCORE_LEAGUES = [
    "basketball_nba",
    "soccer_epl",
    "icehockey_nhl",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_france_ligue_one",
    "soccer_usa_mls",
    "basketball_ncaab",
    "americanfootball_nfl",
    "baseball_mlb",
    "mma_mixed_martial_arts",
]

MAX_SCORE_LEAGUES_PER_CYCLE = int(os.getenv("MAX_SCORE_LEAGUES", "4"))


# ──────────────────── Ensemble singleton ────────────────────────
_ensemble: Optional[EnsemblePredictor] = None


def _get_ensemble() -> EnsemblePredictor:
    global _ensemble
    if _ensemble is None:
        _ensemble = EnsemblePredictor()
        xgb = XGBoostModel()
        if os.path.exists(TRAINED_MODEL_PATH):
            try:
                xgb.load_model(TRAINED_MODEL_PATH)
                logger.info(f"Auto-bet: loaded trained model from {TRAINED_MODEL_PATH}")
            except Exception as e:
                logger.warning(f"Auto-bet: model load failed: {e}")
        _ensemble.register_model("xgboost", xgb)
    return _ensemble


# ════════════════════════════════════════════════════════════════
#  1.  AUTO-BET: Record new recommendations into the ledger
# ════════════════════════════════════════════════════════════════

def _recommendation_already_recorded(db: Session, event_id: int, selection: str) -> bool:
    """Check if we already have a ledger entry for this event+selection today."""
    cutoff = datetime.utcnow() - timedelta(hours=12)
    return (
        db.query(Recommendation)
        .filter(
            Recommendation.event_id == event_id,
            Recommendation.selection == selection,
            Recommendation.created_at >= cutoff,
        )
        .first()
        is not None
    )


def record_top3_bets(db: Session) -> List[Dict[str, Any]]:
    """
    Run the top-3 selector and save each recommendation into the
    Recommendation table as a ledger entry (status='pending').

    Returns the list of newly recorded recommendations.
    """
    ensemble = _get_ensemble()
    selector = Top3Selector(ensemble)
    recs = selector.get_top3_bets(db)

    recorded = []
    for rec in recs:
        event_id = rec.get("event_id")
        selection = rec.get("selection", "")

        if _recommendation_already_recorded(db, event_id, selection):
            logger.debug(f"Skipping duplicate: event {event_id} / {selection}")
            continue

        # Build bet_link for the ledger
        bet_link = generate_bet_link(
            bookmaker=rec.get("bookmaker", ""),
            home_team=rec.get("event_name", "").split(" vs ")[0] if " vs " in rec.get("event_name", "") else "",
            away_team=rec.get("event_name", "").split(" vs ")[-1] if " vs " in rec.get("event_name", "") else "",
            sport=rec.get("sport", ""),
            event_name=rec.get("event_name", ""),
        )

        entry = Recommendation(
            event_id=event_id,
            recommendation_type="top3",
            selection=selection,
            recommended_odds=rec.get("recommended_odds"),
            confidence_score=rec.get("confidence_score"),
            expected_value=rec.get("expected_value"),
            risk_score=rec.get("risk_score"),
            recommended_stake=rec.get("recommended_stake"),
            recommended_stake_percentage=rec.get("recommended_stake_percentage"),
            rationale=rec.get("rationale"),
            ensemble_scores=rec.get("ensemble_scores"),
            status="pending",
        )
        db.add(entry)
        rec["bet_link"] = bet_link
        rec["ledger_status"] = "pending"
        recorded.append(rec)

    if recorded:
        db.commit()
        logger.info(f"Auto-bet: recorded {len(recorded)} new bets in ledger")
        for r in recorded:
            betting_logger.info(
                f"BET PLACED | {r.get('event_name')} | {r.get('selection')} | "
                f"P={r.get('probability',0):.0%} | ${r.get('recommended_stake',0)} | "
                f"Book={r.get('bookmaker')}"
            )
    else:
        logger.debug("Auto-bet: no new bets to record")

    return recorded


# ════════════════════════════════════════════════════════════════
#  2.  RESULT GRADING: Check completed events & grade bets
# ════════════════════════════════════════════════════════════════

async def grade_pending_bets() -> Dict[str, Any]:
    """
    For every pending bet in the ledger:
      1. Check if the event has completed (via Odds API /scores)
      2. Determine if our selection won
      3. Update Recommendation status → won/lost/void
      4. Calculate actual_return (stake × odds for win, 0 for loss)

    Returns summary dict.
    """
    odds_client = get_odds_client()
    graded = {"won": 0, "lost": 0, "void": 0, "still_pending": 0, "errors": 0}

    # Fetch scores for priority leagues (costs 1 credit each)
    completed_events: Dict[str, Dict] = {}
    leagues_checked = 0
    for league_key in SCORE_LEAGUES:
        if leagues_checked >= MAX_SCORE_LEAGUES_PER_CYCLE:
            break
        try:
            scores = await odds_client.get_scores(league_key, days_from=3)
            for ev in scores:
                if ev.get("completed"):
                    completed_events[ev["id"]] = ev
            leagues_checked += 1
        except Exception as e:
            logger.error(f"Error fetching scores for {league_key}: {e}")

    if not completed_events:
        logger.debug("Grade: no completed events found from scores API")

    # Now grade pending recommendations
    with db_manager.get_session() as db:
        pending = (
            db.query(Recommendation)
            .filter(Recommendation.status == "pending")
            .all()
        )

        for rec in pending:
            event = db.query(Event).filter(Event.id == rec.event_id).first()
            if not event:
                continue

            # Check if event has passed its start time + a buffer
            if event.start_time and event.start_time > datetime.utcnow():
                graded["still_pending"] += 1
                continue

            ext_id = event.external_id
            score_data = completed_events.get(ext_id)

            if not score_data:
                # Event may have started but not finished yet, or not in checked leagues
                # If it's older than 48h past start time, mark void
                if event.start_time and (datetime.utcnow() - event.start_time) > timedelta(hours=48):
                    rec.status = "void"
                    rec.actual_outcome = "expired - no result found"
                    rec.actual_return = 0.0
                    rec.updated_at = datetime.utcnow()
                    event.status = "finished"
                    graded["void"] += 1
                else:
                    graded["still_pending"] += 1
                continue

            # We have scores — determine winner
            try:
                winner = _determine_winner(score_data)
                event.status = "finished"

                if winner is None:
                    rec.status = "void"
                    rec.actual_outcome = "no winner determined"
                    rec.actual_return = 0.0
                    graded["void"] += 1
                elif _selection_matches_winner(rec.selection, winner, event):
                    rec.status = "won"
                    rec.actual_outcome = winner
                    rec.actual_return = round(
                        (rec.recommended_stake or 0) * (rec.recommended_odds or 1), 2
                    )
                    graded["won"] += 1
                    betting_logger.info(
                        f"BET WON | {event.name} | {rec.selection} | "
                        f"Return=${rec.actual_return}"
                    )
                else:
                    rec.status = "lost"
                    rec.actual_outcome = winner
                    rec.actual_return = 0.0
                    graded["lost"] += 1
                    betting_logger.info(
                        f"BET LOST | {event.name} | {rec.selection} | Winner={winner}"
                    )

                rec.updated_at = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error grading rec {rec.id}: {e}")
                graded["errors"] += 1

        db.commit()

    logger.info(
        f"Grade complete: {graded['won']}W {graded['lost']}L {graded['void']}V "
        f"{graded['still_pending']} pending | {leagues_checked} leagues checked"
    )
    return graded


def _determine_winner(score_data: Dict) -> Optional[str]:
    """
    Determine the winning team from Odds API score data.

    The /scores response has:
      'scores': [{'name': 'Team A', 'score': '3'}, {'name': 'Team B', 'score': '1'}]
      'completed': True
    """
    scores = score_data.get("scores")
    if not scores or len(scores) < 2:
        return None

    try:
        a_name = scores[0]["name"]
        b_name = scores[1]["name"]
        a_score = int(scores[0]["score"])
        b_score = int(scores[1]["score"])
    except (KeyError, ValueError, TypeError):
        return None

    if a_score > b_score:
        return a_name
    elif b_score > a_score:
        return b_name
    else:
        return "Draw"


def _selection_matches_winner(
    selection: str, winner: str, event: Event
) -> bool:
    """Check if a recommendation's selection matches the actual winner."""
    sel = selection.lower().strip()
    win = winner.lower().strip()

    # Direct name match
    if sel == win:
        return True

    # Home/Away keyword match
    if sel in ("home", (event.home_team or "").lower()):
        return win == (event.home_team or "").lower()
    if sel in ("away", (event.away_team or "").lower()):
        return win == (event.away_team or "").lower()
    if sel == "draw" and win == "draw":
        return True

    # Partial match (team name might be abbreviated)
    if win in sel or sel in win:
        return True

    return False


# ════════════════════════════════════════════════════════════════
#  3.  LEDGER QUERIES
# ════════════════════════════════════════════════════════════════

def get_ledger(
    db: Session,
    limit: int = 100,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the bet ledger with P&L information."""
    q = db.query(Recommendation).order_by(Recommendation.created_at.desc())
    if status_filter:
        q = q.filter(Recommendation.status == status_filter)
    entries = q.limit(limit).all()

    results = []
    for e in entries:
        event = db.query(Event).filter(Event.id == e.event_id).first()
        results.append({
            "id": e.id,
            "event_id": e.event_id,
            "event_name": event.name if event else "Unknown",
            "sport": event.sport.name if event and event.sport else "unknown",
            "start_time": event.start_time.isoformat() if event and event.start_time else None,
            "selection": e.selection,
            "recommended_odds": e.recommended_odds,
            "confidence_score": e.confidence_score,
            "expected_value": e.expected_value,
            "recommended_stake": e.recommended_stake,
            "status": e.status or "pending",
            "actual_outcome": e.actual_outcome,
            "actual_return": e.actual_return,
            "profit": round(
                (e.actual_return or 0) - (e.recommended_stake or 0), 2
            ) if e.status in ("won", "lost") else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        })
    return results


def get_ledger_summary(db: Session) -> Dict[str, Any]:
    """Aggregate P&L stats from the ledger."""
    all_recs = db.query(Recommendation).all()

    total = len(all_recs)
    won = [r for r in all_recs if r.status == "won"]
    lost = [r for r in all_recs if r.status == "lost"]
    pending = [r for r in all_recs if r.status == "pending"]
    void = [r for r in all_recs if r.status == "void"]

    total_staked = sum(r.recommended_stake or 0 for r in all_recs if r.status in ("won", "lost"))
    total_returned = sum(r.actual_return or 0 for r in all_recs if r.status in ("won", "lost"))
    net_profit = round(total_returned - total_staked, 2)
    roi = round((net_profit / total_staked) * 100, 2) if total_staked > 0 else 0.0

    return {
        "total_bets": total,
        "won": len(won),
        "lost": len(lost),
        "pending": len(pending),
        "void": len(void),
        "win_rate": round(len(won) / (len(won) + len(lost)) * 100, 2) if (len(won) + len(lost)) > 0 else 0.0,
        "total_staked": round(total_staked, 2),
        "total_returned": round(total_returned, 2),
        "net_profit": net_profit,
        "roi": roi,
        "current_streak": _get_streak(all_recs),
    }


def _get_streak(recs: list) -> Dict[str, Any]:
    """Calculate current win/loss streak from most recent graded bets."""
    graded = sorted(
        [r for r in recs if r.status in ("won", "lost")],
        key=lambda r: r.updated_at or r.created_at,
        reverse=True,
    )
    if not graded:
        return {"type": "none", "count": 0}

    streak_type = graded[0].status
    count = 0
    for r in graded:
        if r.status == streak_type:
            count += 1
        else:
            break
    return {"type": streak_type, "count": count}


# ════════════════════════════════════════════════════════════════
#  4.  MAIN LOOP — runs as a background asyncio task
# ════════════════════════════════════════════════════════════════

_running = False


async def auto_bet_loop():
    """
    Main background loop:
      - Every BET_INTERVAL: refresh odds → pick top3 → record in ledger
      - Every GRADE_INTERVAL: fetch scores → grade pending bets
    """
    global _running
    _running = True

    odds_service = OddsIngestionService()
    last_bet_time = datetime.min
    last_grade_time = datetime.min
    last_odds_time = datetime.min

    logger.info(
        f"Auto-bet loop started | bet every {BET_INTERVAL_SECONDS}s | "
        f"grade every {GRADE_INTERVAL_SECONDS}s | odds refresh every {ODDS_REFRESH_INTERVAL}s"
    )

    while _running:
        now = datetime.utcnow()

        # ── Refresh odds ──
        if (now - last_odds_time).total_seconds() >= ODDS_REFRESH_INTERVAL:
            try:
                logger.info("Auto-bet: refreshing odds...")
                await odds_service.fetch_and_store_odds()
                last_odds_time = now
            except Exception as e:
                logger.error(f"Auto-bet: odds refresh failed: {e}")

        # ── Record new bets ──
        if (now - last_bet_time).total_seconds() >= BET_INTERVAL_SECONDS:
            try:
                with db_manager.get_session() as db:
                    recorded = record_top3_bets(db)
                last_bet_time = now
            except Exception as e:
                logger.error(f"Auto-bet: bet recording failed: {e}")

        # ── Grade completed bets ──
        if (now - last_grade_time).total_seconds() >= GRADE_INTERVAL_SECONDS:
            try:
                result = await grade_pending_bets()
                last_grade_time = now
            except Exception as e:
                logger.error(f"Auto-bet: grading failed: {e}")

        await asyncio.sleep(30)  # check every 30s


def stop_auto_bet():
    """Stop the auto-bet loop."""
    global _running
    _running = False
    logger.info("Auto-bet loop stopped")
