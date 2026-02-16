"""
Odds Ingestion Service - Continuously fetches and stores odds data
"""
import asyncio
import os
import httpx
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.data_ingestion.odds_api_client import get_odds_client
from src.database.database import db_manager
from src.database.models import Sport, Event, Odds
from src.utils.logger import get_logger, betting_logger

logger = get_logger(__name__)


class OddsIngestionService:
    """
    Service for continuous odds data ingestion
    """
    
    def __init__(self, update_interval: int = 60):
        """
        Initialize odds ingestion service
        
        Args:
            update_interval: Update interval in seconds (default: 60)
        """
        self.odds_client = get_odds_client()
        self.update_interval = update_interval
        self.is_running = False
        
        # Sports to track
        self.tracked_sports = [
            'soccer',
            'football',
            'basketball',
            'baseball',
            'ice_hockey',
            'mma',
            'tennis'
        ]

        # Priority league keys — fetched first to maximize value from limited
        # API credits.  Leagues not on this list are still fetched if credits
        # remain. Order matters: most popular first.
        self.priority_leagues = [
            'basketball_nba',
            'americanfootball_nfl',
            'soccer_epl',
            'soccer_usa_mls',
            'basketball_ncaab',
            'icehockey_nhl',
            'baseball_mlb',
            'mma_mixed_martial_arts',
            'soccer_spain_la_liga',
            'soccer_germany_bundesliga',
            'soccer_italy_serie_a',
            'soccer_france_ligue_one',
            'americanfootball_ncaaf',
            'tennis_atp_french_open',
            'tennis_atp_us_open',
            'tennis_atp_wimbledon',
            'tennis_atp_australian_open',
        ]

        # Maximum number of league API calls per fetch cycle (saves credits)
        self.max_leagues_per_fetch = int(os.getenv('MAX_LEAGUES_PER_FETCH', '10'))
        
        logger.info(f"Odds ingestion service initialized (interval: {update_interval}s)")
    
    async def start(self):
        """Start the odds ingestion service"""
        self.is_running = True
        logger.info("Starting odds ingestion service")
        
        try:
            while self.is_running:
                await self.fetch_and_store_odds()
                await asyncio.sleep(self.update_interval)
        except Exception as e:
            logger.error(f"Error in odds ingestion service: {e}")
            self.is_running = False
    
    def stop(self):
        """Stop the odds ingestion service"""
        self.is_running = False
        logger.info("Stopping odds ingestion service")
    
    async def fetch_and_store_odds(self):
        """Fetch odds for active leagues, prioritising popular ones and respecting credit limits."""
        logger.info("Fetching live odds data...")

        available_sports = await self.odds_client.get_sports()
        active_keys_set = {
            s['key'] for s in available_sports
            if s.get('active') and not s.get('has_outrights')
        }

        # Build reverse map: API key → canonical sport name
        group_map = self.odds_client.sport_group_map
        key_to_sport: dict[str, str] = {}
        for s in available_sports:
            if not s.get('active') or s.get('has_outrights'):
                continue
            key = s['key']
            prefix = key.split('_')[0]
            canonical = group_map.get(prefix)
            if canonical and canonical in self.tracked_sports:
                key_to_sport[key] = canonical

        # Order: priority leagues first (maintaining order), then the rest
        ordered_keys: list[str] = []
        seen = set()
        for pk in self.priority_leagues:
            if pk in key_to_sport and pk not in seen:
                ordered_keys.append(pk)
                seen.add(pk)
        for k in sorted(key_to_sport.keys()):
            if k not in seen:
                ordered_keys.append(k)
                seen.add(k)

        # Cap the number of API calls
        fetch_limit = self.max_leagues_per_fetch
        ordered_keys = ordered_keys[:fetch_limit]

        logger.info(f"Will fetch odds for {len(ordered_keys)} leagues (limit {fetch_limit}): {ordered_keys}")

        total_events = 0
        for league_key in ordered_keys:
            sport_name = key_to_sport[league_key]
            try:
                count = await self.process_sport_key(sport_name, league_key)
                total_events += count
            except Exception as e:
                if 'OUT_OF_USAGE_CREDITS' in str(e):
                    logger.warning("API credits exhausted — stopping fetch loop early")
                    break
                logger.error(f"Error processing {league_key}: {e}")

        logger.info(f"Live odds fetch complete — {total_events} events across {len(ordered_keys)} leagues")
    
    async def process_sport(self, sport: str):
        """Legacy: process a single mapped sport key."""
        sport_key = self.odds_client.sport_keys.get(sport.lower(), sport)
        await self.process_sport_key(sport, sport_key)

    async def process_sport_key(self, sport_name: str, league_key: str) -> int:
        """
        Fetch and store odds for one league key.

        Args:
            sport_name: Canonical sport name (e.g. 'soccer')
            league_key: Odds API sport key (e.g. 'soccer_epl')

        Returns:
            Number of events processed
        """
        try:
            commence_time_from = datetime.utcnow()
            commence_time_to = commence_time_from + timedelta(days=7)

            events = await self.odds_client.get_odds(
                sport=league_key,   # pass the full API key directly
                commence_time_from=commence_time_from,
                commence_time_to=commence_time_to
            )

            if not events:
                logger.debug(f"No events found for {league_key}")
                return 0

            logger.info(f"Processing {len(events)} events for {league_key}")

            with db_manager.get_session() as db:
                for event_data in events:
                    self.store_event_and_odds(db, event_data, sport_name)

            return len(events)

        except httpx.HTTPStatusError:
            raise  # Propagate 401 etc. so the fetch loop can stop early
        except Exception as e:
            logger.error(f"Error processing {league_key}: {e}")
            return 0
    
    def store_event_and_odds(
        self,
        db: Session,
        event_data: Dict[str, Any],
        sport_name: str
    ):
        """
        Store event and odds in database
        
        Args:
            db: Database session
            event_data: Event data from API
            sport_name: Sport name
        """
        try:
            # Parse event data
            parsed = self.odds_client.parse_odds_data(event_data)
            
            # Get or create sport
            sport = db.query(Sport).filter(Sport.name == sport_name).first()
            if not sport:
                sport = Sport(
                    name=sport_name,
                    category='team_sport',
                    is_active=True
                )
                db.add(sport)
                db.flush()
            
            # Get or create event
            event = db.query(Event).filter(
                Event.external_id == parsed['external_id']
            ).first()
            
            if not event:
                event = Event(
                    sport_id=sport.id,
                    external_id=parsed['external_id'],
                    name=f"{parsed['home_team']} vs {parsed['away_team']}",
                    home_team=parsed['home_team'],
                    away_team=parsed['away_team'],
                    start_time=datetime.fromisoformat(parsed['commence_time'].replace('Z', '+00:00')),
                    status='upcoming',
                    extra_metadata={
                        'sport_title': parsed['sport_title']
                    }
                )
                db.add(event)
                db.flush()
                logger.info(f"Created new event: {event.name}")
            else:
                # Update event details
                event.start_time = datetime.fromisoformat(parsed['commence_time'].replace('Z', '+00:00'))
                event.updated_at = datetime.utcnow()
            
            # Mark existing odds as not current
            db.query(Odds).filter(
                Odds.event_id == event.id,
                Odds.is_current == True
            ).update({'is_current': False})
            
            # Store odds from each bookmaker
            odds_count = 0
            for bookmaker in parsed['bookmakers']:
                for market in bookmaker['markets']:
                    for outcome in market['outcomes']:
                        odds_entry = Odds(
                            event_id=event.id,
                            bookmaker=bookmaker['name'],
                            market_type=market['key'],
                            selection=outcome['name'],
                            odds_decimal=outcome['price'],
                            odds_american=self.decimal_to_american(outcome['price']),
                            timestamp=datetime.utcnow(),
                            is_current=True
                        )
                        db.add(odds_entry)
                        odds_count += 1
            
            db.commit()
            logger.debug(f"Stored {odds_count} odds entries for event {event.id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing event and odds: {e}")
    
    def decimal_to_american(self, decimal_odds: float) -> float:
        """
        Convert decimal odds to American odds
        
        Args:
            decimal_odds: Decimal odds
        
        Returns:
            American odds
        """
        if decimal_odds >= 2.0:
            return (decimal_odds - 1) * 100
        else:
            return -100 / (decimal_odds - 1)
    
    async def fetch_specific_event(self, sport: str, event_id: str) -> Dict[str, Any]:
        """
        Fetch odds for a specific event
        
        Args:
            sport: Sport name
            event_id: Event ID
        
        Returns:
            Event data with odds
        """
        try:
            event_data = await self.odds_client.get_event_odds(sport, event_id)
            
            if event_data:
                with db_manager.get_session() as db:
                    self.store_event_and_odds(db, event_data, sport)
            
            return event_data
            
        except Exception as e:
            logger.error(f"Error fetching specific event: {e}")
            return {}
    
    async def get_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities across all events
        
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        try:
            for sport in self.tracked_sports:
                events = await self.odds_client.get_odds(sport=sport)
                
                for event_data in events:
                    parsed = self.odds_client.parse_odds_data(event_data)
                    best_odds = self.odds_client.get_best_odds(parsed, market='h2h')
                    arbitrage = self.odds_client.calculate_arbitrage(best_odds)
                    
                    if arbitrage.get('has_arbitrage'):
                        opportunities.append({
                            'event': f"{parsed['home_team']} vs {parsed['away_team']}",
                            'sport': parsed['sport_title'],
                            'commence_time': parsed['commence_time'],
                            'profit_margin': arbitrage['profit_margin'],
                            'stakes': arbitrage['stakes'],
                            'best_odds': arbitrage['best_odds']
                        })
                        
                        betting_logger.logger.info(
                            f"Arbitrage opportunity found: {parsed['home_team']} vs {parsed['away_team']} "
                            f"({arbitrage['profit_margin']:.2f}% profit)"
                        )
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error finding arbitrage opportunities: {e}")
            return []
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics
        
        Returns:
            Usage statistics
        """
        return await self.odds_client.get_usage_quota()


# Global service instance
_ingestion_service: OddsIngestionService = None


def get_ingestion_service(update_interval: int = 60) -> OddsIngestionService:
    """
    Get odds ingestion service singleton
    
    Args:
        update_interval: Update interval in seconds
    
    Returns:
        Odds ingestion service instance
    """
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = OddsIngestionService(update_interval)
    return _ingestion_service
