"""
Polymarket API Client for crypto-based betting operations
Built on Polygon blockchain (Chain ID 137) using USDC
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, MarketOrderArgs, OrderType, OpenOrderParams, BookParams
    from py_clob_client.order_builder.constants import BUY, SELL
    HAS_CLOB = True
except ImportError:
    HAS_CLOB = False
    ClobClient = None

from src.utils.logger import get_logger, betting_logger
from src.utils.config_loader import get_config

logger = get_logger(__name__)
config = get_config()


class PolymarketClient:
    """
    Client for interacting with Polymarket CLOB (Central Limit Order Book) API
    Non-custodial, crypto-native betting on Polygon blockchain
    """
    
    def __init__(self):
        """Initialize Polymarket client"""
        polymarket_config = config.get_betting_platform_config('polymarket', {
            'host': 'https://clob.polymarket.com',
            'chain_id': 137,  # Polygon mainnet
            'signature_type': 0,  # 0 for EOA (private key), 1 for Magic/email, 2 for proxy
            'default_currency': 'USDC'
        })
        
        self.host = polymarket_config.get('host', 'https://clob.polymarket.com')
        self.chain_id = polymarket_config.get('chain_id', 137)
        self.private_key = polymarket_config.get('private_key')
        self.funder_address = polymarket_config.get('funder_address')
        self.signature_type = polymarket_config.get('signature_type', 0)
        self.default_currency = polymarket_config.get('default_currency', 'USDC')
        
        # Initialize Polymarket CLOB client
        self.client = None
        self._initialize_client()
        
        logger.info(f"Polymarket client initialized (chain_id={self.chain_id})")
    
    def _initialize_client(self):
        """Initialize or reinitialize the CLOB client"""
        try:
            if self.private_key:
                # Authenticated client
                self.client = ClobClient(
                    self.host,
                    key=self.private_key,
                    chain_id=self.chain_id,
                    signature_type=self.signature_type,
                    funder=self.funder_address
                )
                # Generate API credentials
                self.client.set_api_creds(self.client.create_or_derive_api_creds())
                logger.info("Polymarket client authenticated with private key")
            else:
                # Read-only client (no authentication)
                self.client = ClobClient(self.host)
                logger.info("Polymarket client initialized in read-only mode")
        except Exception as e:
            logger.error(f"Error initializing Polymarket client: {e}")
            # Fall back to read-only
            self.client = ClobClient(self.host)
    
    async def update_credentials(
        self,
        private_key: str,
        funder_address: Optional[str] = None,
        signature_type: Optional[int] = None
    ) -> None:
        """
        Update Polymarket credentials at runtime
        
        Args:
            private_key: Polygon wallet private key (0x prefixed hex)
            funder_address: Optional funder address (for proxy wallets)
            signature_type: 0 for EOA, 1 for Magic/email, 2 for proxy
        """
        self.private_key = private_key
        if funder_address:
            self.funder_address = funder_address
        if signature_type is not None:
            self.signature_type = signature_type
        
        # Reinitialize client with new credentials
        self._initialize_client()
        logger.info("Polymarket client credentials updated")
    
    async def check_connection(self) -> Dict[str, Any]:
        """
        Check if connection to Polymarket is working
        
        Returns:
            Dictionary with connection status
        """
        try:
            # Test with a simple read-only call
            ok = self.client.get_ok()
            server_time = self.client.get_server_time()
            
            if ok and server_time:
                logger.info("Polymarket connection successful")
                return {
                    "connected": True, 
                    "server_time": server_time,
                    "authenticated": self.private_key is not None
                }
            else:
                return {
                    "error": "Failed to connect to Polymarket",
                    "connected": False
                }
        except Exception as e:
            error_msg = f"Error checking Polymarket connection: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "connected": False
            }
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get wallet balance (requires authentication)
        
        Returns:
            Balance information
        """
        try:
            if not self.private_key:
                return {
                    "error": "Authentication required. Please provide private key.",
                    "balance": 0
                }
            
            # Polymarket uses USDC on Polygon
            # Balance is stored on-chain, can query via wallet address
            # For now, we'll check if client is authenticated
            connection = await self.check_connection()
            
            if connection.get("connected") and connection.get("authenticated"):
                return {
                    "balance": "Connected - check wallet directly",
                    "currency": self.default_currency,
                    "chain": "Polygon",
                    "chain_id": self.chain_id,
                    "connected": True
                }
            else:
                return {
                    "error": "Not authenticated",
                    "balance": 0,
                    "connected": False
                }
        except Exception as e:
            error_msg = f"Error getting balance: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "balance": 0
            }
    
    async def get_markets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get available markets (prediction markets)
        
        Args:
            limit: Maximum number of markets to return
            
        Returns:
            List of markets
        """
        try:
            markets = self.client.get_simplified_markets()
            return markets.get('data', [])[:limit]
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    async def get_odds(self, token_id: str) -> Dict[str, Any]:
        """
        Get current odds for a specific market
        
        Args:
            token_id: Polymarket token ID for the outcome
            
        Returns:
            Odds information
        """
        try:
            # Get midpoint price
            mid = self.client.get_midpoint(token_id)
            
            # Get buy and sell prices
            buy_price = self.client.get_price(token_id, side="BUY")
            sell_price = self.client.get_price(token_id, side="SELL")
            
            # Get order book
            book = self.client.get_order_book(token_id)
            
            return {
                "token_id": token_id,
                "midpoint": mid,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "market": book.market if book else None,
                "spread": buy_price - sell_price if buy_price and sell_price else None
            }
        except Exception as e:
            logger.error(f"Error fetching odds for token {token_id}: {e}")
            return {}
    
    async def place_bet(
        self,
        token_id: str,
        side: str,  # 'BUY' or 'SELL'
        amount: float = None,  # Dollar amount for market order
        price: float = None,  # Price for limit order
        size: float = None  # Share size for limit order
    ) -> Dict[str, Any]:
        """
        Place a bet on Polymarket
        
        Args:
            token_id: Polymarket token ID
            side: 'BUY' or 'SELL' 
            amount: Dollar amount for market order
            price: Price for limit order (0.00 to 1.00)
            size: Number of shares for limit order
            
        Returns:
            Order response
        """
        try:
            if not self.private_key:
                return {
                    "success": False,
                    "error": "Authentication required. Please provide private key."
                }
            
            side_const = BUY if side.upper() == 'BUY' else SELL
            
            # Market order (buy by dollar amount)
            if amount and not price:
                order = MarketOrderArgs(
                    token_id=token_id,
                    amount=amount,
                    side=side_const,
                    order_type=OrderType.FOK  # Fill or Kill
                )
                signed = self.client.create_market_order(order)
                resp = self.client.post_order(signed, OrderType.FOK)
                
                betting_logger.info(
                    f"Polymarket market order placed: {side} ${amount} on token {token_id}",
                    extra={
                        "token_id": token_id,
                        "side": side,
                        "amount": amount,
                        "order_type": "market"
                    }
                )
                
                return {
                    "success": True,
                    "order_id": resp.get('orderID'),
                    "response": resp
                }
            
            # Limit order (buy shares at specific price)
            elif price and size:
                order = OrderArgs(
                    token_id=token_id,
                    price=price,
                    size=size,
                    side=side_const
                )
                signed = self.client.create_order(order)
                resp = self.client.post_order(signed, OrderType.GTC)  # Good Till Cancel
                
                betting_logger.info(
                    f"Polymarket limit order placed: {side} {size} shares @ ${price} on token {token_id}",
                    extra={
                        "token_id": token_id,
                        "side": side,
                        "price": price,
                        "size": size,
                        "order_type": "limit"
                    }
                )
                
                return {
                    "success": True,
                    "order_id": resp.get('orderID'),
                    "response": resp
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid order parameters. Provide either 'amount' for market order or 'price' and 'size' for limit order."
                }
                
        except Exception as e:
            error_msg = f"Error placing bet: {str(e)}"
            logger.error(error_msg)
            betting_logger.error(error_msg, extra={"token_id": token_id, "side": side})
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get open orders
        
        Returns:
            List of open orders
        """
        try:
            if not self.private_key:
                return []
            
            orders = self.client.get_orders(OpenOrderParams())
            return orders or []
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        try:
            if not self.private_key:
                return {"success": False, "error": "Authentication required"}
            
            self.client.cancel(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return {"success": True, "order_id": order_id}
        except Exception as e:
            error_msg = f"Error cancelling order: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_trades(self) -> List[Dict[str, Any]]:
        """
        Get trade history
        
        Returns:
            List of trades
        """
        try:
            if not self.private_key:
                return []
            
            trades = self.client.get_trades()
            return trades or []
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []


# Global client instance
_polymarket_client = None


def get_polymarket_client() -> PolymarketClient:
    """Get or create global Polymarket client instance"""
    global _polymarket_client
    if _polymarket_client is None:
        _polymarket_client = PolymarketClient()
    return _polymarket_client
