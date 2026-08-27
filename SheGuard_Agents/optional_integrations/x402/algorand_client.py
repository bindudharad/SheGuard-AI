"""
Algorand payment client for x402 real-mode integration.

This module implements the REAL Algorand payment flow for x402.
It does NOT simulate payments - it uses the actual Algorand SDK.

Requires: algosdk installed and valid credentials in environment.
"""
import os
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class PaymentResult:
    status: PaymentStatus
    payment_id: Optional[str] = None
    tx_id: Optional[str] = None
    amount: float = 0.0
    currency: str = "ALGO"
    network: str = "testnet"
    error: Optional[str] = None


class AlgorandPaymentClient:
    """
    Real Algorand payment client for x402 integration.
    
    Supports:
    - Testnet and Mainnet
    - ALGO and ASA payments
    - Transaction verification
    
    Credentials from environment:
    - ALGORAND_NETWORK (testnet/mainnet)
    - ALGORAND_ALGOD_TOKEN
    - ALGORAND_ALGOD_SERVER
    - ALGORAND_INDEXER_TOKEN (optional)
    - ALGORAND_INDEXER_SERVER (optional)
    - ALGORAND_MNEMONIC (sender account mnemonic - DO NOT COMMIT)
    """
    
    def __init__(
        self,
        network: Optional[str] = None,
        algod_token: Optional[str] = None,
        algod_server: Optional[str] = None,
        mnemonic: Optional[str] = None,
    ):
        self.network = network or os.environ.get("ALGORAND_NETWORK", "testnet")
        self.algod_token = algod_token or os.environ.get("ALGORAND_ALGOD_TOKEN", "")
        self.algod_server = algod_server or os.environ.get(
            "ALGORAND_ALGOD_SERVER",
            "https://testnet-algorand.api.purestake.io/ps2" if self.network == "testnet" 
            else "https://mainnet-algorand.api.purestake.io/ps2"
        )
        self.mnemonic = mnemonic or os.environ.get("ALGORAND_MNEMONIC", "")
        
        self._algod_client = None
        self._available = self._init_client()
    
    def _init_client(self) -> bool:
        """Initialize Algorand client. Returns False if unavailable."""
        if not self.algod_token or not self.mnemonic:
            logger.warning("[Algorand] Missing credentials - client unavailable")
            return False
        
        try:
            from algosdk.v2client import algod
            from algosdk import mnemonic as algo_mnemonic
            
            self._algod_client = algod.AlgodClient(self.algod_token, self.algod_server)
            # Verify mnemonic
            self._private_key = algo_mnemonic.to_private_key(self.mnemonic)
            self._address = algo_mnemonic.address_from_private_key(self._private_key)
            logger.info(f"[Algorand] Client initialized for {self.network}")
            return True
        except ImportError:
            logger.error("[Algorand] algosdk not installed")
            return False
        except Exception as e:
            logger.error(f"[Algorand] Init failed: {e}")
            return False
    
    @property
    def available(self) -> bool:
        return self._available
    
    async def submit_payment(
        self,
        amount: float,
        currency: str = "ALGO",
        network: str = "testnet",
        pay_to: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        """
        Submit a real Algorand payment.
        
        Returns PaymentResult dict with status, tx_id, etc.
        """
        if not self._available:
            return PaymentResult(
                status=PaymentStatus.FAILED,
                error="Algorand client not available (missing credentials)"
            ).__dict__
        
        try:
            from algosdk.transaction import PaymentTxn, AssetTransferTxn
            from algosdk import transaction
            from algosdk.encoding import decode_address
            
            # Validate recipient
            if not pay_to:
                raise ValueError("Missing payment recipient address")
            
            params = self._algod_client.suggested_params()
            
            if currency.upper() == "ALGO":
                # ALGO payment
                amount_micro = int(amount * 1_000_000)  # ALGO -> microALGO
                txn = PaymentTxn(
                    sender=self._address,
                    sp=params,
                    receiver=pay_to,
                    amt=amount_micro,
                    note=note.encode() if note else None,
                )
            else:
                # ASA payment - need asset ID mapping
                asset_id = self._get_asset_id(currency)
                txn = AssetTransferTxn(
                    sender=self._address,
                    sp=params,
                    receiver=pay_to,
                    amt=int(amount * 1000),  # Assume 3 decimals for ASA
                    index=asset_id,
                    note=note.encode() if note else None,
                )
            
            # Sign
            signed_txn = txn.sign(self._private_key)
            
            # Submit
            import asyncio
            loop = asyncio.get_event_loop()
            tx_id = await loop.run_in_executor(
                None, 
                lambda: self._algod_client.send_transaction(signed_txn)
            )
            
            # Wait for confirmation
            confirmed = await self._wait_for_confirmation(tx_id, max_rounds=10)
            
            if confirmed:
                return PaymentResult(
                    status=PaymentStatus.CONFIRMED,
                    payment_id=f"pay-{tx_id[:16]}",
                    tx_id=tx_id,
                    amount=amount,
                    currency=currency,
                    network=network,
                ).__dict__
            else:
                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    tx_id=tx_id,
                    error="Transaction not confirmed in time",
                ).__dict__
                
        except Exception as e:
            logger.error(f"[Algorand] Payment failed: {e}")
            return PaymentResult(
                status=PaymentStatus.FAILED,
                error=str(e),
            ).__dict__
    
    async def verify_payment(self, tx_id: str) -> bool:
        """Verify a payment transaction on chain"""
        if not self._available:
            return False
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            tx_info = await loop.run_in_executor(
                None,
                lambda: self._algod_client.pending_transaction_info(tx_id)
            )
            return tx_info.get("confirmed-round", 0) > 0
        except Exception as e:
            logger.error(f"[Algorand] Verification failed: {e}")
            return False
    
    async def _wait_for_confirmation(self, tx_id: str, max_rounds: int = 10) -> bool:
        """Wait for transaction confirmation"""
        import asyncio
        from algosdk.logic import get_application_address
        
        loop = asyncio.get_event_loop()
        for _ in range(max_rounds):
            try:
                tx_info = await loop.run_in_executor(
                    None,
                    lambda: self._algod_client.pending_transaction_info(tx_id)
                )
                if tx_info.get("confirmed-round", 0) > 0:
                    return True
                elif tx_info.get("pool-error", ""):
                    return False
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)
        return False
    
    def _get_asset_id(self, currency: str) -> int:
        """Map currency symbol to Algorand asset ID"""
        asset_map = {
            "USDC": 10458941,  # Testnet USDC
            "USDT": 10458942,  # Testnet USDT (example)
        }
        return asset_map.get(currency.upper(), 0)


# Global instance
_algorand_client: Optional[AlgorandPaymentClient] = None


def get_algorand_client() -> Optional[AlgorandPaymentClient]:
    global _algorand_client
    if _algorand_client is None:
        _algorand_client = AlgorandPaymentClient()
    return _algorand_client
