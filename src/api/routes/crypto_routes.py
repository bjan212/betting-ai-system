"""
Cryptocurrency API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

try:
    from src.integrations.crypto_wallet import get_crypto_wallet
except ImportError:
    get_crypto_wallet = None
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models
class BalanceRequest(BaseModel):
    """Balance request model"""
    token_symbol: str = "USDT"


class BalanceResponse(BaseModel):
    """Balance response model"""
    token: str
    balance: float
    address: str
    timestamp: int


class TransactionRequest(BaseModel):
    """Transaction request model"""
    to_address: str
    amount: float
    token_symbol: str = "USDT"
    private_key: str


class TransactionResponse(BaseModel):
    """Transaction response model"""
    success: bool
    transaction_hash: Optional[str]
    from_address: Optional[str]
    to_address: Optional[str]
    amount: Optional[float]
    token: Optional[str]
    gas_used: Optional[int]
    block_number: Optional[int]
    error: Optional[str]


class TransactionStatusRequest(BaseModel):
    """Transaction status request model"""
    transaction_hash: str


class GasEstimateRequest(BaseModel):
    """Gas estimate request model"""
    to_address: str
    amount: float
    token_symbol: str = "USDT"


@router.post("/balance", response_model=BalanceResponse)
async def get_balance(request: BalanceRequest):
    """
    Get wallet balance for specified token
    
    Args:
        request: Balance request with token symbol
    
    Returns:
        Balance information
    """
    try:
        logger.info(f"API request: get balance for {request.token_symbol}")
        
        wallet = get_crypto_wallet()
        balance_info = wallet.get_balance(request.token_symbol)
        
        if 'error' in balance_info:
            raise HTTPException(status_code=400, detail=balance_info['error'])
        
        return balance_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", response_model=TransactionResponse)
async def send_transaction(request: TransactionRequest):
    """
    Send cryptocurrency transaction
    
    Args:
        request: Transaction request with details
    
    Returns:
        Transaction result
    
    Note:
        This endpoint requires a private key. In production, implement
        proper key management and security measures.
    """
    try:
        logger.info(f"API request: send {request.amount} {request.token_symbol} to {request.to_address}")
        
        wallet = get_crypto_wallet()
        result = wallet.send_transaction(
            to_address=request.to_address,
            amount=request.amount,
            token_symbol=request.token_symbol,
            private_key=request.private_key
        )
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Transaction failed')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transaction/status")
async def get_transaction_status(request: TransactionStatusRequest):
    """
    Get transaction status
    
    Args:
        request: Transaction status request with hash
    
    Returns:
        Transaction status information
    """
    try:
        logger.info(f"API request: get transaction status for {request.transaction_hash}")
        
        wallet = get_crypto_wallet()
        status = wallet.get_transaction_status(request.transaction_hash)
        
        if 'error' in status:
            raise HTTPException(status_code=400, detail=status['error'])
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gas/estimate")
async def estimate_gas(request: GasEstimateRequest):
    """
    Estimate gas for transaction
    
    Args:
        request: Gas estimate request
    
    Returns:
        Gas estimation
    """
    try:
        logger.info(f"API request: estimate gas for {request.amount} {request.token_symbol}")
        
        wallet = get_crypto_wallet()
        estimate = wallet.estimate_gas(
            to_address=request.to_address,
            amount=request.amount,
            token_symbol=request.token_symbol
        )
        
        if 'error' in estimate:
            raise HTTPException(status_code=400, detail=estimate['error'])
        
        return estimate
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating gas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallet/info")
async def get_wallet_info():
    """
    Get wallet information
    
    Returns:
        Wallet address and supported tokens
    """
    try:
        wallet = get_crypto_wallet()
        
        return {
            "address": wallet.wallet_address,
            "network": "Binance Smart Chain",
            "supported_tokens": list(wallet.supported_tokens.keys()),
            "rpc_url": wallet.rpc_url
        }
        
    except Exception as e:
        logger.error(f"Error getting wallet info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens")
async def get_supported_tokens():
    """
    Get list of supported tokens
    
    Returns:
        List of supported cryptocurrency tokens
    """
    try:
        wallet = get_crypto_wallet()
        
        tokens = []
        for symbol, info in wallet.supported_tokens.items():
            tokens.append({
                "symbol": symbol,
                "contract": info.get('contract'),
                "network": "BSC"
            })
        
        return {"tokens": tokens}
        
    except Exception as e:
        logger.error(f"Error getting supported tokens: {e}")
        raise HTTPException(status_code=500, detail=str(e))
