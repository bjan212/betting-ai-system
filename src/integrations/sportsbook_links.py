"""
Sportsbook Deep Link Generator

Maps bookmaker names from The Odds API to their actual websites
and generates direct links for bet placement.
"""
from typing import Dict, Optional
from urllib.parse import quote
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Mapping: Odds API bookmaker key → (display name, base URL, event search URL pattern)
SPORTSBOOK_MAP: Dict[str, Dict[str, str]] = {
    # US Major Books
    "draftkings": {
        "name": "DraftKings",
        "url": "https://sportsbook.draftkings.com",
        "search": "https://sportsbook.draftkings.com/search?q={query}",
        "color": "#61B510",
    },
    "fanduel": {
        "name": "FanDuel",
        "url": "https://sportsbook.fanduel.com",
        "search": "https://sportsbook.fanduel.com/search?q={query}",
        "color": "#1493FF",
    },
    "betmgm": {
        "name": "BetMGM",
        "url": "https://sports.betmgm.com",
        "search": "https://sports.betmgm.com/en/sports?query={query}",
        "color": "#C7A44B",
    },
    "betrivers": {
        "name": "BetRivers",
        "url": "https://www.betrivers.com",
        "search": "https://www.betrivers.com/search?q={query}",
        "color": "#003DA5",
    },
    "bovada": {
        "name": "Bovada",
        "url": "https://www.bovada.lv",
        "search": "https://www.bovada.lv/sports",
        "color": "#E51A38",
    },
    "betonlineag": {
        "name": "BetOnline",
        "url": "https://www.betonline.ag",
        "search": "https://www.betonline.ag/sportsbook",
        "color": "#8B0000",
    },
    "williamhill_us": {
        "name": "Caesars Sportsbook",
        "url": "https://www.caesars.com/sportsbook-and-casino",
        "search": "https://www.caesars.com/sportsbook-and-casino/search?query={query}",
        "color": "#006847",
    },
    "pointsbetus": {
        "name": "PointsBet",
        "url": "https://www.pointsbet.com",
        "search": "https://www.pointsbet.com/search?q={query}",
        "color": "#ED1C24",
    },
    "unibet_us": {
        "name": "Unibet",
        "url": "https://www.unibet.com",
        "search": "https://www.unibet.com/betting/sports",
        "color": "#147B45",
    },
    "betus": {
        "name": "BetUS",
        "url": "https://www.betus.com.pa",
        "search": "https://www.betus.com.pa/sportsbook/",
        "color": "#002B5C",
    },
    "lowvig": {
        "name": "LowVig",
        "url": "https://www.lowvig.ag",
        "search": "https://www.lowvig.ag/sportsbook",
        "color": "#333333",
    },
    "mybookieag": {
        "name": "MyBookie",
        "url": "https://www.mybookie.ag",
        "search": "https://www.mybookie.ag/sportsbook/",
        "color": "#1F1F1F",
    },
    "superbook": {
        "name": "SuperBook",
        "url": "https://co.superbook.com",
        "search": "https://co.superbook.com/sports",
        "color": "#C41230",
    },
    "twinspires": {
        "name": "TwinSpires",
        "url": "https://www.twinspires.com",
        "search": "https://www.twinspires.com/sportsbook",
        "color": "#009CDE",
    },
    "wynnbet": {
        "name": "WynnBET",
        "url": "https://www.wynnbet.com",
        "search": "https://www.wynnbet.com/sports",
        "color": "#8B6914",
    },
    "pinnacle": {
        "name": "Pinnacle",
        "url": "https://www.pinnacle.com",
        "search": "https://www.pinnacle.com/en/search/{query}",
        "color": "#0C3B5E",
    },
    "betfair": {
        "name": "Betfair",
        "url": "https://www.betfair.com",
        "search": "https://www.betfair.com/sport/search?query={query}",
        "color": "#FFB80C",
    },
    "bet365": {
        "name": "Bet365",
        "url": "https://www.bet365.com",
        "search": "https://www.bet365.com/#/IP/",
        "color": "#027B5B",
    },
}


def get_sportsbook_info(bookmaker_key: str) -> Optional[Dict[str, str]]:
    """Get sportsbook info by bookmaker key from The Odds API."""
    return SPORTSBOOK_MAP.get(bookmaker_key.lower())


def generate_bet_link(
    bookmaker: str,
    home_team: str = "",
    away_team: str = "",
    sport: str = "",
    event_name: str = "",
) -> Dict[str, str]:
    """
    Generate a deep link for placing a bet at a given sportsbook.

    Returns dict with: url, search_url, bookmaker_name, color
    """
    info = get_sportsbook_info(bookmaker)
    if not info:
        # Fallback: generic Google search
        query = quote(f"{event_name or f'{home_team} vs {away_team}'} {sport} odds")
        return {
            "bookmaker_name": bookmaker.replace("_", " ").title(),
            "url": f"https://www.google.com/search?q={query}",
            "search_url": f"https://www.google.com/search?q={query}",
            "color": "#666666",
        }

    # Build search query from the team names
    if home_team and away_team:
        query_text = f"{home_team} vs {away_team}"
    elif event_name:
        query_text = event_name
    else:
        query_text = sport

    search_url = info["search"].format(query=quote(query_text))

    return {
        "bookmaker_name": info["name"],
        "url": info["url"],
        "search_url": search_url,
        "color": info["color"],
    }


def generate_all_book_links(
    event_name: str,
    home_team: str,
    away_team: str,
    sport: str,
    bookmakers: list[str] | None = None,
) -> list[Dict[str, str]]:
    """Generate links for all sportsbooks that have odds for an event."""
    if bookmakers is None:
        bookmakers = list(SPORTSBOOK_MAP.keys())[:5]  # Top 5 by default

    links = []
    seen = set()
    for bk in bookmakers:
        bk_lower = bk.lower()
        if bk_lower in seen:
            continue
        seen.add(bk_lower)
        link = generate_bet_link(bk_lower, home_team, away_team, sport, event_name)
        link["bookmaker_key"] = bk_lower
        links.append(link)
    return links
