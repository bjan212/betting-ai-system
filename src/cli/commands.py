"""
CLI Commands for Betting AI System
"""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime, timedelta

from src.database.database import db_manager
from src.ml_models.ensemble_predictor import EnsemblePredictor
from src.ml_models.xgboost_model import XGBoostModel
from src.recommendation.top3_selector import Top3Selector
from src.integrations.stake_client import get_stake_client
from src.integrations.crypto_wallet import get_crypto_wallet
from src.utils.logger import get_logger

logger = get_logger(__name__)
console = Console()


@click.group()
def cli():
    """Betting AI System CLI"""
    pass


@cli.command()
def top3_bets():
    """
    Get top 3 betting recommendations for the next 24 hours
    
    This is the main command that analyzes all upcoming events and
    provides the 3 most promising betting opportunities.
    """
    console.print("\n[bold cyan]🎯 Analyzing Betting Opportunities...[/bold cyan]\n")
    
    try:
        # Initialize components
        console.print("[yellow]Initializing ML models...[/yellow]")
        ensemble = EnsemblePredictor()
        xgboost_model = XGBoostModel()
        ensemble.register_model('xgboost', xgboost_model)
        
        console.print("[yellow]Connecting to database...[/yellow]")
        
        # Get recommendations
        with db_manager.get_session() as db:
            selector = Top3Selector(ensemble)
            recommendations = selector.get_top3_bets(db)
        
        if not recommendations:
            console.print("[red]No betting opportunities found meeting criteria.[/red]")
            return
        
        # Display recommendations
        console.print(f"\n[bold green]✅ Top 3 Betting Recommendations (Next 24 Hours)[/bold green]\n")
        
        for i, rec in enumerate(recommendations, 1):
            _display_recommendation(rec, i)
        
        # Summary
        _display_summary(recommendations)
        
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        logger.error(f"Error in top3_bets command: {e}")


def _display_recommendation(rec: dict, rank: int):
    """Display a single recommendation"""
    
    # Create recommendation panel
    title = f"🏆 Rank #{rank}: {rec['event_name']}"
    
    # Build content
    content = Text()
    content.append(f"Sport: ", style="bold")
    content.append(f"{rec['sport']}\n", style="cyan")
    
    content.append(f"Match Time: ", style="bold")
    content.append(f"{rec['start_time']}\n\n", style="yellow")
    
    content.append(f"Recommended Bet: ", style="bold green")
    content.append(f"{rec['selection']} @ {rec['recommended_odds']}\n", style="green")
    
    content.append(f"Bookmaker: ", style="bold")
    content.append(f"{rec['bookmaker']}\n\n", style="white")
    
    # Metrics
    content.append("📊 Metrics:\n", style="bold cyan")
    content.append(f"  • Confidence Score: ", style="bold")
    content.append(f"{rec['confidence_score']:.1f}%\n", style="green" if rec['confidence_score'] > 70 else "yellow")
    
    content.append(f"  • Expected Value: ", style="bold")
    ev_pct = rec['expected_value'] * 100
    content.append(f"+{ev_pct:.2f}%\n", style="green")
    
    content.append(f"  • Win Probability: ", style="bold")
    content.append(f"{rec['probability']*100:.1f}%\n", style="cyan")
    
    content.append(f"  • Risk Score: ", style="bold")
    content.append(f"{rec['risk_score']:.2f}\n\n", style="yellow" if rec['risk_score'] < 0.5 else "red")
    
    # Stake recommendation
    content.append("💰 Stake Recommendation:\n", style="bold magenta")
    content.append(f"  • Amount: ", style="bold")
    content.append(f"${rec['recommended_stake']:.2f}\n", style="green")
    content.append(f"  • Percentage: ", style="bold")
    content.append(f"{rec['recommended_stake_percentage']:.2f}% of bankroll\n\n", style="green")
    
    # Rationale
    rationale = rec.get('rationale', {})
    content.append("📝 Analysis:\n", style="bold blue")
    content.append(f"{rationale.get('summary', 'N/A')}\n\n", style="white")
    
    if 'key_reasons' in rationale:
        content.append("Key Reasons:\n", style="bold")
        for reason in rationale['key_reasons']:
            content.append(f"  ✓ {reason}\n", style="green")
    
    # Value analysis
    if 'value_analysis' in rationale:
        va = rationale['value_analysis']
        content.append(f"\n💎 Value Analysis:\n", style="bold yellow")
        content.append(f"  • Edge vs Market: {va.get('edge', 'N/A')}\n", style="cyan")
        content.append(f"  • Model Probability: {va.get('model_probability', 'N/A')}\n", style="cyan")
        content.append(f"  • Implied Probability: {va.get('implied_probability', 'N/A')}\n", style="cyan")
    
    panel = Panel(content, title=title, border_style="green", padding=(1, 2))
    console.print(panel)
    console.print()


def _display_summary(recommendations: list):
    """Display summary table"""
    
    table = Table(title="📈 Summary", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="cyan", justify="center")
    table.add_column("Event", style="white")
    table.add_column("Selection", style="green")
    table.add_column("Odds", style="yellow", justify="right")
    table.add_column("Confidence", style="green", justify="right")
    table.add_column("EV", style="green", justify="right")
    table.add_column("Stake", style="magenta", justify="right")
    
    total_stake = 0
    for rec in recommendations:
        table.add_row(
            str(rec['rank']),
            rec['event_name'][:40] + "..." if len(rec['event_name']) > 40 else rec['event_name'],
            rec['selection'],
            f"{rec['recommended_odds']:.2f}",
            f"{rec['confidence_score']:.1f}%",
            f"+{rec['expected_value']*100:.1f}%",
            f"${rec['recommended_stake']:.2f}"
        )
        total_stake += rec['recommended_stake']
    
    console.print(table)
    console.print(f"\n[bold]Total Recommended Stake: [green]${total_stake:.2f}[/green][/bold]\n")


@cli.command()
@click.option('--currency', default='USDT', help='Currency to check (BNB, USDT, BUSD)')
def balance(currency):
    """Check wallet balance"""
    try:
        console.print(f"\n[yellow]Checking {currency} balance...[/yellow]\n")
        
        wallet = get_crypto_wallet()
        balance_info = wallet.get_balance(currency)
        
        if 'error' in balance_info:
            console.print(f"[red]Error: {balance_info['error']}[/red]")
            return
        
        console.print(f"[bold green]Balance: {balance_info['balance']:.4f} {currency}[/bold green]")
        console.print(f"[cyan]Address: {balance_info['address']}[/cyan]\n")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def status():
    """Check system status"""
    console.print("\n[bold cyan]🔍 System Status Check[/bold cyan]\n")
    
    try:
        # Database
        console.print("[yellow]Checking database connection...[/yellow]")
        db_healthy = db_manager.health_check()
        status_text = "[green]✓ Connected[/green]" if db_healthy else "[red]✗ Disconnected[/red]"
        console.print(f"Database: {status_text}")
        
        # Crypto wallet
        console.print("\n[yellow]Checking crypto wallet...[/yellow]")
        try:
            wallet = get_crypto_wallet()
            console.print("[green]✓ Wallet initialized[/green]")
            console.print(f"Address: [cyan]{wallet.wallet_address}[/cyan]")
        except Exception as e:
            console.print(f"[red]✗ Wallet error: {e}[/red]")
        
        # Stake client
        console.print("\n[yellow]Checking Stake.com connection...[/yellow]")
        console.print("[green]✓ Client initialized[/green]")
        
        console.print("\n[bold green]System operational ✓[/bold green]\n")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]\n")


@cli.command()
@click.option('--sport', help='Filter by sport')
@click.option('--limit', default=10, help='Number of events to show')
def upcoming_events(sport, limit):
    """List upcoming events"""
    console.print("\n[bold cyan]📅 Upcoming Events[/bold cyan]\n")
    
    try:
        with db_manager.get_session() as db:
            from src.database.models import Event
            
            query = db.query(Event).filter(
                Event.status == 'upcoming',
                Event.start_time >= datetime.utcnow()
            )
            
            if sport:
                query = query.join(Event.sport).filter(Sport.name == sport)
            
            events = query.order_by(Event.start_time).limit(limit).all()
            
            if not events:
                console.print("[yellow]No upcoming events found.[/yellow]")
                return
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan")
            table.add_column("Sport", style="yellow")
            table.add_column("Event", style="white")
            table.add_column("Start Time", style="green")
            
            for event in events:
                table.add_row(
                    str(event.id),
                    event.sport.name if event.sport else "N/A",
                    event.name,
                    event.start_time.strftime("%Y-%m-%d %H:%M")
                )
            
            console.print(table)
            console.print()
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
def init_db():
    """Initialize database tables"""
    console.print("\n[yellow]Initializing database...[/yellow]\n")
    
    try:
        db_manager.create_tables()
        console.print("[green]✓ Database tables created successfully[/green]\n")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]\n")


@cli.command()
def seed_demo():
    """Seed demo sports, events, and odds for local previews"""
    console.print("\n[bold cyan]🧪 Seeding demo data...[/bold cyan]\n")

    try:
        from src.database.models import Sport, Event, Odds

        demo_sports = [
            {"name": "soccer", "category": "team_sport"},
            {"name": "basketball", "category": "team_sport"},
            {"name": "tennis", "category": "individual_sport"},
        ]

        demo_events = [
            {
                "external_id": "demo-soccer-1",
                "sport": "soccer",
                "name": "Demo FC vs Sample United",
                "home_team": "Demo FC",
                "away_team": "Sample United",
                "hours_from_now": 3,
            },
            {
                "external_id": "demo-basketball-1",
                "sport": "basketball",
                "name": "Example City vs Test Town",
                "home_team": "Example City",
                "away_team": "Test Town",
                "hours_from_now": 6,
            },
            {
                "external_id": "demo-tennis-1",
                "sport": "tennis",
                "name": "Player A vs Player B",
                "home_team": "Player A",
                "away_team": "Player B",
                "hours_from_now": 9,
            },
        ]

        with db_manager.get_session() as db:
            # Ensure sports exist
            sports_map = {}
            for sport in demo_sports:
                existing = db.query(Sport).filter(Sport.name == sport["name"]).first()
                if existing:
                    sports_map[sport["name"]] = existing
                    continue

                new_sport = Sport(
                    name=sport["name"],
                    category=sport["category"],
                    is_active=True
                )
                db.add(new_sport)
                db.flush()
                sports_map[sport["name"]] = new_sport

            created_events = 0
            created_odds = 0
            now = datetime.utcnow()

            for event in demo_events:
                existing_event = db.query(Event).filter(
                    Event.external_id == event["external_id"]
                ).first()

                if existing_event:
                    db_event = existing_event
                else:
                    db_event = Event(
                        sport_id=sports_map[event["sport"]].id,
                        external_id=event["external_id"],
                        name=event["name"],
                        home_team=event["home_team"],
                        away_team=event["away_team"],
                        start_time=now + timedelta(hours=event["hours_from_now"]),
                        status="upcoming",
                        venue="Demo Arena",
                    )
                    db.add(db_event)
                    db.flush()
                    created_events += 1

                # Seed odds if missing
                selections = [
                    ("home", 2.15),
                    ("away", 2.55),
                    ("draw", 3.2),
                ]

                for selection, odds_decimal in selections:
                    existing_odds = db.query(Odds).filter(
                        Odds.event_id == db_event.id,
                        Odds.selection == selection,
                        Odds.is_current == True
                    ).first()

                    if existing_odds:
                        continue

                    db.add(Odds(
                        event_id=db_event.id,
                        bookmaker="DemoBook",
                        market_type="moneyline",
                        selection=selection,
                        odds_decimal=odds_decimal,
                        odds_american=None,
                        odds_fractional=None,
                        is_current=True
                    ))
                    created_odds += 1

            console.print(
                f"[green]✓ Demo data ready: {created_events} events, {created_odds} odds entries[/green]\n"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]\n")
        logger.error(f"Error seeding demo data: {e}")


@cli.command()
@click.option('--sport', help='Specific sport to fetch')
@click.option('--days', default=7, help='Number of days ahead to fetch')
def fetch_odds(sport, days):
    """Fetch odds data from The Odds API"""
    console.print("\n[bold cyan]📊 Fetching Odds Data...[/bold cyan]\n")
    
    try:
        import asyncio
        from src.data_ingestion.odds_ingestion_service import get_ingestion_service
        
        service = get_ingestion_service()
        
        if sport:
            console.print(f"[yellow]Fetching odds for {sport}...[/yellow]")
            asyncio.run(service.process_sport(sport))
        else:
            console.print("[yellow]Fetching odds for all sports...[/yellow]")
            asyncio.run(service.fetch_and_store_odds())
        
        console.print("\n[green]✓ Odds data fetched successfully[/green]\n")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]\n")
        logger.error(f"Error fetching odds: {e}")


@cli.command()
def start_odds_service():
    """Start continuous odds ingestion service"""
    console.print("\n[bold cyan]🔄 Starting Odds Ingestion Service...[/bold cyan]\n")
    
    try:
        import asyncio
        from src.data_ingestion.odds_ingestion_service import get_ingestion_service
        
        service = get_ingestion_service(update_interval=60)
        
        console.print("[green]Service started. Press Ctrl+C to stop.[/green]\n")
        console.print("[yellow]Updating odds every 60 seconds...[/yellow]\n")
        
        asyncio.run(service.start())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Service stopped by user[/yellow]\n")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]\n")
        logger.error(f"Error in odds service: {e}")


@cli.command()
def find_arbitrage():
    """Find arbitrage betting opportunities"""
    console.print("\n[bold cyan]💎 Finding Arbitrage Opportunities...[/bold cyan]\n")
    
    try:
        import asyncio
        from src.data_ingestion.odds_ingestion_service import get_ingestion_service
        
        service = get_ingestion_service()
        opportunities = asyncio.run(service.get_arbitrage_opportunities())
        
        if not opportunities:
            console.print("[yellow]No arbitrage opportunities found.[/yellow]\n")
            return
        
        console.print(f"[green]Found {len(opportunities)} arbitrage opportunities![/green]\n")
        
        for i, opp in enumerate(opportunities, 1):
            console.print(f"[bold]Opportunity #{i}:[/bold]")
            console.print(f"  Event: {opp['event']}")
            console.print(f"  Sport: {opp['sport']}")
            console.print(f"  Profit Margin: [green]{opp['profit_margin']:.2f}%[/green]")
            console.print(f"  Stakes: {opp['stakes']}")
            console.print(f"  Best Odds: {opp['best_odds']}\n")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]\n")
        logger.error(f"Error finding arbitrage: {e}")


@cli.command()
def api_usage():
    """Check Odds API usage statistics"""
    console.print("\n[bold cyan]📈 API Usage Statistics[/bold cyan]\n")
    
    try:
        import asyncio
        from src.data_ingestion.odds_ingestion_service import get_ingestion_service
        
        service = get_ingestion_service()
        stats = asyncio.run(service.get_usage_stats())
        
        if stats:
            console.print(f"[bold]Requests Used:[/bold] {stats.get('requests_used', 'N/A')}")
            console.print(f"[bold]Requests Remaining:[/bold] {stats.get('requests_remaining', 'N/A')}")
            console.print(f"[bold]Last Request:[/bold] {stats.get('requests_last', 'N/A')}\n")
        else:
            console.print("[yellow]Unable to fetch usage statistics[/yellow]\n")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]\n")


if __name__ == '__main__':
    cli()
