"""
Cryptocurrency Wallet Integration for BSC (Binance Smart Chain)
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from web3 import Web3
from eth_account import Account
import json

from src.utils.logger import get_logger, betting_logger
from src.utils.config_loader import get_config

logger = get_logger(__name__)
config = get_config()


class CryptoWallet:
    """
    Cryptocurrency wallet for BSC transactions
    """
    
    def __init__(self):
        """Initialize crypto wallet"""
        crypto_config = config.get_crypto_config()
        
        self.rpc_url = crypto_config.get('rpc_url')
        self.wallet_address = crypto_config.get('wallet_address')
        self.gas_limit = crypto_config.get('gas_limit', 21000)
        self.gas_price_multiplier = crypto_config.get('gas_price_multiplier', 1.2)
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Check connection
        if not self.w3.is_connected():
            logger.error("Failed to connect to BSC network")
            raise ConnectionError("Cannot connect to BSC network")
        
        # Load supported tokens
        self.supported_tokens = {
            token['symbol']: token
            for token in crypto_config.get('supported_tokens', [])
        }
        
        logger.info(f"Crypto wallet initialized. Connected to BSC: {self.w3.is_connected()}")
    
    def get_balance(self, token_symbol: str = 'BNB') -> Dict[str, Any]:
        """
        Get wallet balance
        
        Args:
            token_symbol: Token symbol (BNB, USDT, BUSD)
        
        Returns:
            Balance information
        """
        try:
            if token_symbol == 'BNB':
                # Get native BNB balance
                balance_wei = self.w3.eth.get_balance(self.wallet_address)
                balance = self.w3.from_wei(balance_wei, 'ether')
            else:
                # Get token balance
                balance = self._get_token_balance(token_symbol)
            
            return {
                'token': token_symbol,
                'balance': float(balance),
                'address': self.wallet_address,
                'timestamp': self.w3.eth.get_block('latest')['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error getting balance for {token_symbol}: {e}")
            return {'error': str(e), 'balance': 0}
    
    def _get_token_balance(self, token_symbol: str) -> Decimal:
        """
        Get ERC-20 token balance
        
        Args:
            token_symbol: Token symbol
        
        Returns:
            Token balance
        """
        if token_symbol not in self.supported_tokens:
            raise ValueError(f"Unsupported token: {token_symbol}")
        
        token_info = self.supported_tokens[token_symbol]
        contract_address = token_info['contract']
        
        # ERC-20 ABI for balanceOf
        erc20_abi = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]')
        
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=erc20_abi
        )
        
        balance = contract.functions.balanceOf(
            Web3.to_checksum_address(self.wallet_address)
        ).call()
        
        # Convert from wei (assuming 18 decimals)
        return Decimal(balance) / Decimal(10**18)
    
    def send_transaction(
        self,
        to_address: str,
        amount: float,
        token_symbol: str = 'BNB',
        private_key: str = None
    ) -> Dict[str, Any]:
        """
        Send cryptocurrency transaction
        
        Args:
            to_address: Recipient address
            amount: Amount to send
            token_symbol: Token symbol
            private_key: Private key for signing
        
        Returns:
            Transaction result
        """
        try:
            if not private_key:
                logger.error("Private key required for transaction")
                return {'error': 'Private key required', 'success': False}
            
            # Validate addresses
            to_address = Web3.to_checksum_address(to_address)
            from_address = Web3.to_checksum_address(self.wallet_address)
            
            if token_symbol == 'BNB':
                tx_hash = self._send_native_transaction(
                    from_address, to_address, amount, private_key
                )
            else:
                tx_hash = self._send_token_transaction(
                    from_address, to_address, amount, token_symbol, private_key
                )
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            result = {
                'success': receipt['status'] == 1,
                'transaction_hash': tx_hash.hex(),
                'from_address': from_address,
                'to_address': to_address,
                'amount': amount,
                'token': token_symbol,
                'gas_used': receipt['gasUsed'],
                'block_number': receipt['blockNumber']
            }
            
            betting_logger.log_transaction(result)
            
            logger.info(f"Transaction successful: {tx_hash.hex()}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            betting_logger.log_error('transaction_error', str(e), {
                'to_address': to_address,
                'amount': amount,
                'token': token_symbol
            })
            return {'error': str(e), 'success': False}
    
    def _send_native_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        private_key: str
    ) -> bytes:
        """
        Send native BNB transaction
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount in BNB
            private_key: Private key
        
        Returns:
            Transaction hash
        """
        # Get nonce
        nonce = self.w3.eth.get_transaction_count(from_address)
        
        # Get gas price
        gas_price = int(self.w3.eth.gas_price * self.gas_price_multiplier)
        
        # Build transaction
        transaction = {
            'nonce': nonce,
            'to': to_address,
            'value': self.w3.to_wei(amount, 'ether'),
            'gas': self.gas_limit,
            'gasPrice': gas_price,
            'chainId': 56  # BSC Mainnet
        }
        
        # Sign transaction
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, private_key
        )
        
        # Send transaction
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash
    
    def _send_token_transaction(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        token_symbol: str,
        private_key: str
    ) -> bytes:
        """
        Send ERC-20 token transaction
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount in tokens
            token_symbol: Token symbol
            private_key: Private key
        
        Returns:
            Transaction hash
        """
        if token_symbol not in self.supported_tokens:
            raise ValueError(f"Unsupported token: {token_symbol}")
        
        token_info = self.supported_tokens[token_symbol]
        contract_address = Web3.to_checksum_address(token_info['contract'])
        
        # ERC-20 ABI for transfer
        erc20_abi = json.loads('[{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"type":"function"}]')
        
        contract = self.w3.eth.contract(
            address=contract_address,
            abi=erc20_abi
        )
        
        # Convert amount to wei (assuming 18 decimals)
        amount_wei = int(amount * 10**18)
        
        # Get nonce
        nonce = self.w3.eth.get_transaction_count(from_address)
        
        # Get gas price
        gas_price = int(self.w3.eth.gas_price * self.gas_price_multiplier)
        
        # Build transaction
        transaction = contract.functions.transfer(
            to_address,
            amount_wei
        ).build_transaction({
            'from': from_address,
            'nonce': nonce,
            'gas': 100000,  # Higher gas limit for token transfers
            'gasPrice': gas_price,
            'chainId': 56
        })
        
        # Sign transaction
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, private_key
        )
        
        # Send transaction
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        return tx_hash
    
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get transaction status
        
        Args:
            tx_hash: Transaction hash
        
        Returns:
            Transaction status
        """
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            return {
                'transaction_hash': tx_hash,
                'status': 'confirmed' if receipt['status'] == 1 else 'failed',
                'block_number': receipt['blockNumber'],
                'gas_used': receipt['gasUsed'],
                'from': receipt['from'],
                'to': receipt['to']
            }
            
        except Exception as e:
            logger.error(f"Error getting transaction status: {e}")
            return {'error': str(e), 'status': 'unknown'}
    
    def estimate_gas(
        self,
        to_address: str,
        amount: float,
        token_symbol: str = 'BNB'
    ) -> Dict[str, Any]:
        """
        Estimate gas for transaction
        
        Args:
            to_address: Recipient address
            amount: Amount to send
            token_symbol: Token symbol
        
        Returns:
            Gas estimation
        """
        try:
            to_address = Web3.to_checksum_address(to_address)
            
            if token_symbol == 'BNB':
                gas_estimate = self.gas_limit
            else:
                # Estimate for token transfer
                gas_estimate = 100000
            
            gas_price = self.w3.eth.gas_price
            total_gas_cost = self.w3.from_wei(gas_estimate * gas_price, 'ether')
            
            return {
                'gas_limit': gas_estimate,
                'gas_price': gas_price,
                'gas_price_gwei': self.w3.from_wei(gas_price, 'gwei'),
                'estimated_cost_bnb': float(total_gas_cost),
                'token': token_symbol
            }
            
        except Exception as e:
            logger.error(f"Error estimating gas: {e}")
            return {'error': str(e)}


# Singleton instance
_crypto_wallet: Optional[CryptoWallet] = None


def get_crypto_wallet() -> CryptoWallet:
    """
    Get crypto wallet singleton
    
    Returns:
        Crypto wallet instance
    """
    global _crypto_wallet
    if _crypto_wallet is None:
        _crypto_wallet = CryptoWallet()
    return _crypto_wallet
