"""
Stake.com API Client for betting operations
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import hmac
import time

from src.utils.logger import get_logger, betting_logger
from src.utils.config_loader import get_config

logger = get_logger(__name__)
config = get_config()


class StakeClient:
    """
    Client for interacting with Stake.com API
    """
    
    def __init__(self):
        """Initialize Stake client"""
        stake_config = config.get_betting_platform_config('stake')
        
        self.base_url = stake_config.get('base_url', 'https://api.stake.com').rstrip('/')
        self.api_key = stake_config.get('api_key')
        self.api_secret = stake_config.get('api_secret')
        self.timeout = stake_config.get('timeout', 30)
        self.max_retries = stake_config.get('max_retries', 3)
        self.default_currency = stake_config.get('default_currency', 'USDT')
        
        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._get_headers()
        )
        
        logger.info("Stake client initialized")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication
        
        Returns:
            Headers dictionary
        """
        return {
            'Content-Type': 'application/json',
            'x-access-token': self.api_key or '',
            'X-API-Key': self.api_key or '',
            'User-Agent': 'BettingAI/1.0'
        }

    async def update_credentials(
        self,
        api_key: str,
        api_secret: str,
        base_url: Optional[str] = None,
        default_currency: Optional[str] = None
    ) -> None:
        """
        Update Stake API credentials at runtime

        Args:
            api_key: Stake API key
            api_secret: Stake API secret
            base_url: Optional base URL override
            default_currency: Optional default currency override
        """
        self.api_key = api_key
        self.api_secret = api_secret
        if base_url:
            self.base_url = base_url.rstrip('/')
        if default_currency:
            self.default_currency = default_currency

        await self.client.aclose()
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._get_headers()
        )
        logger.info("Stake client credentials updated")
    
    def _generate_signature(self, payload: str, timestamp: int) -> str:
        """
        Generate HMAC signature for request
        
        Args:
            payload: Request payload
            timestamp: Unix timestamp
        
        Returns:
            HMAC signature
        """
        if not self.api_secret:
            return ''
        
        message = f"{timestamp}{payload}"
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def get_sports(self) -> List[Dict[str, Any]]:
        """
        Get available sports
        
        Returns:
            List of sports
        """
        try:
            response = await self.client.get('/sports')
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Retrieved {len(data.get('sports', []))} sports")
            
            return data.get('sports', [])
            
        except Exception as e:
            logger.error(f"Error fetching sports: {e}")
            return []
    
    async def get_events(
        self,
        sport: str,
        start_time_from: Optional[datetime] = None,
        start_time_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get events for a sport
        
        Args:
            sport: Sport name
            start_time_from: Start time filter (from)
            start_time_to: Start time filter (to)
        
        Returns:
            List of events
        """
        try:
            params = {'sport': sport}
            
            if start_time_from:
                params['start_time_from'] = start_time_from.isoformat()
            if start_time_to:
                params['start_time_to'] = start_time_to.isoformat()
            
            response = await self.client.get('/events', params=params)
            response.raise_for_status()
            
            data = response.json()
            events = data.get('events', [])
            
            logger.info(f"Retrieved {len(events)} events for {sport}")
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []
    
    async def get_odds(self, event_id: str) -> Dict[str, Any]:
        """
        Get odds for an event
        
        Args:
            event_id: Event ID
        
        Returns:
            Odds data
        """
        try:
            response = await self.client.get(f'/events/{event_id}/odds')
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Retrieved odds for event {event_id}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching odds for event {event_id}: {e}")
            return {}
    
    async def place_bet(
        self,
        event_id: str,
        selection: str,
        stake: float,
        odds: float,
        currency: str = None
    ) -> Dict[str, Any]:
        """
        Place a bet
        
        Args:
            event_id: Event ID
            selection: Bet selection
            stake: Stake amount
            odds: Odds value
            currency: Currency (default: USDT)
        
        Returns:
            Bet placement result
        """
        try:
            currency = currency or self.default_currency
            
            payload = {
                'event_id': event_id,
                'selection': selection,
                'stake': stake,
                'odds': odds,
                'currency': currency,
                'timestamp': int(time.time())
            }
            
            response = await self.client.post('/bets', json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            betting_logger.log_bet_placement({
                'event_id': event_id,
                'selection': selection,
                'stake': stake,
                'odds': odds,
                'currency': currency,
                'bet_id': result.get('bet_id'),
                'status': result.get('status')
            })
            
            logger.info(f"Bet placed successfully: {result.get('bet_id')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error placing bet: {e}")
            betting_logger.log_error('bet_placement_error', str(e), {
                'event_id': event_id,
                'selection': selection,
                'stake': stake
            })
            return {'error': str(e), 'success': False}
    
    async def get_bet_status(self, bet_id: str) -> Dict[str, Any]:
        """
        Get bet status
        
        Args:
            bet_id: Bet ID
        
        Returns:
            Bet status
        """
        try:
            response = await self.client.get(f'/bets/{bet_id}')
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching bet status: {e}")
            return {}
    
    async def get_balance(self, currency: str = None) -> Dict[str, Any]:
        """
        Get account balance
        
        Args:
            currency: Currency (default: all)
        
        Returns:
            Balance information
        """
        try:
            params = {}
            if currency:
                params['currency'] = currency
            
            response = await self.client.get('/account/balance', params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {}

    async def check_connection(self) -> Dict[str, Any]:
        """
        Check Stake token validity using a lightweight endpoint

        Returns:
            Response payload if successful
        """
        try:
            payload = {
                'limit': 1,
                'offset': 0,
                'type': 'available'
            }

            response = await self.client.post('/challenge/list', json=payload)
            status_code = response.status_code
            text = response.text

            if status_code >= 400:
                logger.error("Stake connection failed: %s %s", status_code, text)
                return {
                    'error': 'stake_http_error',
                    'status_code': status_code,
                    'detail': text
                }

            return response.json()
        except Exception as e:
            logger.error(f"Error checking Stake connection: {e}")
            return {
                'error': 'stake_connection_error',
                'detail': str(e)
            }
    
    async def get_betting_history(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get betting history
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of records
        
        Returns:
            List of historical bets
        """
        try:
            params = {'limit': limit}
            
            if start_date:
                params['start_date'] = start_date.isoformat()
            if end_date:
                params['end_date'] = end_date.isoformat()
            
            response = await self.client.get('/bets/history', params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get('bets', [])
            
        except Exception as e:
            logger.error(f"Error fetching betting history: {e}")
            return []
    
    async def cancel_bet(self, bet_id: str) -> Dict[str, Any]:
        """
        Cancel a pending bet
        
        Args:
            bet_id: Bet ID
        
        Returns:
            Cancellation result
        """
        try:
            response = await self.client.delete(f'/bets/{bet_id}')
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Bet cancelled: {bet_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error cancelling bet: {e}")
            return {'error': str(e), 'success': False}
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("Stake client closed")


# Singleton instance
_stake_client: Optional[StakeClient] = None


def get_stake_client() -> StakeClient:
    """
    Get Stake client singleton
    
    Returns:
        Stake client instance
    """
    global _stake_client
    if _stake_client is None:
        _stake_client = StakeClient()
    return _stake_client
