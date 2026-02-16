"""
Polymarket Sports Market Discovery

Fetches active sports-related prediction markets from Polymarket's Gamma API
and makes them available for browsing/betting alongside sportsbook recommendations.
"""
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from src.utils.logger import get_logger

logger = get_logger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"

# Keywords to identify sports events/markets
SPORTS_KEYWORDS = [
    'nba', 'nfl', 'nhl', 'mlb', 'mls', 'ufc', 'mma',
    'premier league', 'epl', 'la liga', 'serie a', 'bundesliga',
    'ligue 1', 'champions league', 'world cup', 'stanley cup',
    'super bowl', 'march madness', 'ncaa', 'college football',
    'basketball', 'soccer', 'football', 'hockey', 'baseball',
    'tennis', 'golf', 'boxing', 'f1', 'formula 1',
    'mvp', 'rookie of the year', 'cy young', 'heisman',
    'win the 202', 'conference finals', 'playoff',
]

# Cache
_cached_markets: List[Dict[str, Any]] = []
_cache_time: Optional[datetime] = None
CACHE_TTL = timedelta(minutes=10)


def _is_sports_market(market: Dict[str, Any]) -> bool:
    """Check if a market is sports-related."""
    question = (market.get('question', '') or '').lower()
    slug = (market.get('slug', '') or '').lower()
    text = question + ' ' + slug
    return any(kw in text for kw in SPORTS_KEYWORDS)


def _is_sports_event(event: Dict[str, Any]) -> bool:
    """Check if a Gamma event is sports-related."""
    title = (event.get('title', '') or '').lower()
    slug = (event.get('slug', '') or '').lower()
    text = title + ' ' + slug
    tags = event.get('tags', []) or []
    if isinstance(tags, list):
        for t in tags:
            label = t.get('label', '') if isinstance(t, dict) else str(t)
            text += ' ' + label.lower()
    return any(kw in text for kw in SPORTS_KEYWORDS)


def fetch_polymarket_sports_markets(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch active sports prediction markets from Polymarket.

    Returns a simplified list of markets with:
    - question, event_title, token_ids, outcomes, prices, url, accepting_orders
    """
    global _cached_markets, _cache_time

    if not force_refresh and _cache_time and datetime.utcnow() - _cache_time < CACHE_TTL:
        return _cached_markets

    try:
        # Fetch events (which contain markets)
        resp = requests.get(f'{GAMMA_API}/events', params={
            'active': 'true',
            'closed': 'false',
            'limit': 200,
        }, timeout=15)
        resp.raise_for_status()
        events = resp.json()

        results = []
        for ev in events:
            if not _is_sports_event(ev):
                continue

            event_title = ev.get('title', '')
            event_slug = ev.get('slug', '')
            event_id = ev.get('id')

            for mkt in (ev.get('markets', []) or []):
                if not mkt.get('acceptingOrders', False):
                    continue

                question = mkt.get('question', '')
                outcomes_raw = mkt.get('outcomes', '[]')
                prices_raw = mkt.get('outcomePrices', '[]')

                # Parse outcomes and prices
                import json
                try:
                    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                except (json.JSONDecodeError, TypeError):
                    outcomes = []
                try:
                    prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
                except (json.JSONDecodeError, TypeError):
                    prices = []

                clob_tokens_raw = mkt.get('clobTokenIds', '[]') or '[]'
                try:
                    clob_tokens = json.loads(clob_tokens_raw) if isinstance(clob_tokens_raw, str) else clob_tokens_raw
                except (json.JSONDecodeError, TypeError):
                    clob_tokens = []

                # Build token-outcome-price mapping
                token_map = []
                for i, outcome in enumerate(outcomes):
                    token_map.append({
                        'outcome': outcome,
                        'price': float(prices[i]) if i < len(prices) else None,
                        'token_id': clob_tokens[i] if i < len(clob_tokens) else None,
                    })

                slug = mkt.get('slug', '')
                url = f"https://polymarket.com/event/{event_slug}/{slug}" if slug else f"https://polymarket.com/event/{event_slug}"

                results.append({
                    'question': question,
                    'event_title': event_title,
                    'event_id': event_id,
                    'market_id': mkt.get('id'),
                    'condition_id': mkt.get('conditionId', ''),
                    'slug': slug,
                    'url': url,
                    'end_date': mkt.get('endDate'),
                    'accepting_orders': True,
                    'tokens': token_map,
                    'image': mkt.get('image', ''),
                })

        # Sort by number of tokens (more interesting markets first), then by event title
        results.sort(key=lambda x: (-len(x.get('tokens', [])), x.get('event_title', '')))

        _cached_markets = results
        _cache_time = datetime.utcnow()
        logger.info(f"Fetched {len(results)} active Polymarket sports markets from {len(events)} events")
        return results

    except Exception as e:
        logger.error(f"Error fetching Polymarket sports markets: {e}")
        return _cached_markets  # Return stale cache on error


def search_polymarket_markets(query: str) -> List[Dict[str, Any]]:
    """Search cached Polymarket sports markets by keyword."""
    markets = fetch_polymarket_sports_markets()
    q = query.lower()
    return [
        m for m in markets
        if q in m.get('question', '').lower()
        or q in m.get('event_title', '').lower()
    ]
