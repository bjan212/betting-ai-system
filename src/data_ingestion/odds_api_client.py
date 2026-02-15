"""
The Odds API Client - Real-time sports odds data
API Documentation: https://the-odds-api.com/liveapi/guides/v4/
"""
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

from src.utils.logger import get_logger
from src.utils.config_loader import get_config

logger = get_logger(__name__)
config = get_config()


class OddsAPIClient:
    """
    Client for The Odds API - provides real-time sports odds
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Odds API client
        
        Args:
            api_key: The Odds API key
        """
        self.api_key = api_key or config.get('sports.data_sources.odds.api_key')
        self.base_url = "https://api.the-odds-api.com/v4"
        self.timeout = 30
        
        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={'User-Agent': 'BettingAI/1.0'}
        )
        
        # Sport mappings
        self.sport_keys = {
            'soccer': 'soccer_epl',  # English Premier League
            'football': 'americanfootball_nfl',
            'basketball': 'basketball_nba',
            'baseball': 'baseball_mlb',
            'ice_hockey': 'icehockey_nhl',
            'mma': 'mma_mixed_martial_arts',
            'tennis': 'tennis_atp',
            'cricket': 'cricket_test_match'
        }
        
        # Supported regions
        self.regions = ['us', 'uk', 'eu', 'au']
        
        # Supported markets
        self.markets = ['h2h', 'spreads', 'totals']  # head-to-head, spreads, over/under
        
        # Bookmakers to track
        self.bookmakers = [
            'draftkings',
            'fanduel',
            'betmgm',
            'pointsbetus',
            'bovada',
            'mybookieag',
            'betus',
            'betonlineag'
        ]
        
        logger.info("Odds API client initialized")
    
    async def get_sports(self) -> List[Dict[str, Any]]:
        """
        Get list of available sports
        
        Returns:
            List of sports with details
        """
        try:
            response = await self.client.get(
                '/sports',
                params={'apiKey': self.api_key}
            )
            response.raise_for_status()
            
            sports = response.json()
            logger.info(f"Retrieved {len(sports)} sports from Odds API")
            
            return sports
            
        except Exception as e:
            logger.error(f"Error fetching sports: {e}")
            return []
    
    async def get_odds(
        self,
        sport: str,
        regions: List[str] = None,
        markets: List[str] = None,
        bookmakers: List[str] = None,
        event_ids: List[str] = None,
        commence_time_from: datetime = None,
        commence_time_to: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Get odds for a sport
        
        Args:
            sport: Sport key (e.g., 'soccer_epl', 'basketball_nba')
            regions: Regions to get odds from
            markets: Markets to include (h2h, spreads, totals)
            bookmakers: Specific bookmakers to include
            event_ids: Filter by specific event IDs
            commence_time_from: Filter events starting from this time
            commence_time_to: Filter events starting before this time
        
        Returns:
            List of events with odds
        """
        try:
            # Map sport name to API key
            sport_key = self.sport_keys.get(sport.lower(), sport)
            
            # Build parameters
            params = {
                'apiKey': self.api_key,
                'regions': ','.join(regions or self.regions),
                'markets': ','.join(markets or self.markets),
                'oddsFormat': 'decimal',
                'dateFormat': 'iso'
            }
            
            if bookmakers:
                params['bookmakers'] = ','.join(bookmakers)
            
            if event_ids:
                params['eventIds'] = ','.join(event_ids)
            
            if commence_time_from:
                params['commenceTimeFrom'] = commence_time_from.strftime('%Y-%m-%dT%H:%M:%SZ')

            if commence_time_to:
                params['commenceTimeTo'] = commence_time_to.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            response = await self.client.get(
                f'/sports/{sport_key}/odds',
                params=params
            )
            response.raise_for_status()
            
            events = response.json()
            
            # Log remaining requests
            remaining = response.headers.get('x-requests-remaining')
            used = response.headers.get('x-requests-used')
            logger.info(f"Retrieved {len(events)} events. API requests: {used} used, {remaining} remaining")
            
            return events
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching odds: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            return []
    
    async def get_event_odds(
        self,
        sport: str,
        event_id: str,
        regions: List[str] = None,
        markets: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get odds for a specific event
        
        Args:
            sport: Sport key
            event_id: Event ID
            regions: Regions to get odds from
            markets: Markets to include
        
        Returns:
            Event with odds data
        """
        try:
            sport_key = self.sport_keys.get(sport.lower(), sport)
            
            params = {
                'apiKey': self.api_key,
                'regions': ','.join(regions or self.regions),
                'markets': ','.join(markets or self.markets),
                'oddsFormat': 'decimal',
                'dateFormat': 'iso'
            }
            
            response = await self.client.get(
                f'/sports/{sport_key}/events/{event_id}/odds',
                params=params
            )
            response.raise_for_status()
            
            event = response.json()
            logger.debug(f"Retrieved odds for event {event_id}")
            
            return event
            
        except Exception as e:
            logger.error(f"Error fetching event odds: {e}")
            return {}
    
    async def get_historical_odds(
        self,
        sport: str,
        date: datetime,
        regions: List[str] = None,
        markets: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical odds for a specific date
        
        Args:
            sport: Sport key
            date: Date to get historical odds for
            regions: Regions to get odds from
            markets: Markets to include
        
        Returns:
            List of events with historical odds
        """
        try:
            sport_key = self.sport_keys.get(sport.lower(), sport)
            
            params = {
                'apiKey': self.api_key,
                'regions': ','.join(regions or self.regions),
                'markets': ','.join(markets or self.markets),
                'oddsFormat': 'decimal',
                'dateFormat': 'iso',
                'date': date.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            
            response = await self.client.get(
                f'/sports/{sport_key}/odds-history',
                params=params
            )
            response.raise_for_status()
            
            events = response.json()
            logger.info(f"Retrieved {len(events)} historical events for {date.date()}")
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching historical odds: {e}")
            return []
    
    async def get_usage_quota(self) -> Dict[str, Any]:
        """
        Get API usage quota information
        
        Returns:
            Usage quota details
        """
        try:
            # Make a minimal request to check quota
            response = await self.client.get(
                '/sports',
                params={'apiKey': self.api_key}
            )
            response.raise_for_status()
            
            return {
                'requests_remaining': response.headers.get('x-requests-remaining'),
                'requests_used': response.headers.get('x-requests-used'),
                'requests_last': response.headers.get('x-requests-last')
            }
            
        except Exception as e:
            logger.error(f"Error fetching usage quota: {e}")
            return {}
    
    def parse_odds_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse odds data into standardized format
        
        Args:
            event: Raw event data from API
        
        Returns:
            Parsed event data
        """
        parsed = {
            'external_id': event.get('id'),
            'sport': event.get('sport_key'),
            'sport_title': event.get('sport_title'),
            'commence_time': event.get('commence_time'),
            'home_team': event.get('home_team'),
            'away_team': event.get('away_team'),
            'bookmakers': []
        }
        
        # Parse bookmaker odds
        for bookmaker in event.get('bookmakers', []):
            bookmaker_data = {
                'name': bookmaker.get('key'),
                'title': bookmaker.get('title'),
                'last_update': bookmaker.get('last_update'),
                'markets': []
            }
            
            for market in bookmaker.get('markets', []):
                market_data = {
                    'key': market.get('key'),
                    'outcomes': []
                }
                
                for outcome in market.get('outcomes', []):
                    outcome_data = {
                        'name': outcome.get('name'),
                        'price': outcome.get('price'),  # Decimal odds
                        'point': outcome.get('point')  # For spreads/totals
                    }
                    market_data['outcomes'].append(outcome_data)
                
                bookmaker_data['markets'].append(market_data)
            
            parsed['bookmakers'].append(bookmaker_data)
        
        return parsed
    
    def get_best_odds(self, event: Dict[str, Any], market: str = 'h2h') -> Dict[str, Any]:
        """
        Get best odds across all bookmakers for an event
        
        Args:
            event: Parsed event data
            market: Market type (h2h, spreads, totals)
        
        Returns:
            Best odds for each outcome
        """
        best_odds = {}
        
        for bookmaker in event.get('bookmakers', []):
            for mkt in bookmaker.get('markets', []):
                if mkt['key'] == market:
                    for outcome in mkt['outcomes']:
                        name = outcome['name']
                        price = outcome['price']
                        
                        if name not in best_odds or price > best_odds[name]['price']:
                            best_odds[name] = {
                                'price': price,
                                'bookmaker': bookmaker['name'],
                                'bookmaker_title': bookmaker['title']
                            }
        
        return best_odds
    
    def calculate_arbitrage(self, best_odds: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate if arbitrage opportunity exists
        
        Args:
            best_odds: Best odds for each outcome
        
        Returns:
            Arbitrage analysis
        """
        if len(best_odds) < 2:
            return {'has_arbitrage': False}
        
        # Calculate implied probabilities
        implied_probs = {}
        for outcome, data in best_odds.items():
            implied_probs[outcome] = 1 / data['price']
        
        total_implied_prob = sum(implied_probs.values())
        
        # Arbitrage exists if total implied probability < 1
        has_arbitrage = total_implied_prob < 1.0
        
        if has_arbitrage:
            profit_margin = (1 / total_implied_prob - 1) * 100
            
            # Calculate optimal stakes (assuming $100 total)
            stakes = {}
            for outcome, prob in implied_probs.items():
                stakes[outcome] = (prob / total_implied_prob) * 100
            
            return {
                'has_arbitrage': True,
                'profit_margin': profit_margin,
                'total_implied_probability': total_implied_prob,
                'stakes': stakes,
                'best_odds': best_odds
            }
        
        return {
            'has_arbitrage': False,
            'total_implied_probability': total_implied_prob
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("Odds API client closed")


# Singleton instance
_odds_client: Optional[OddsAPIClient] = None


def get_odds_client() -> OddsAPIClient:
    """
    Get Odds API client singleton
    
    Returns:
        Odds API client instance
    """
    global _odds_client
    if _odds_client is None:
        _odds_client = OddsAPIClient()
    return _odds_client
