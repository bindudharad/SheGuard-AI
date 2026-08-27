from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import asyncio

from core.agent import BaseAgent, AgentMessage, AgentStatus, AgentHealth
from core.event_bus import EventBus
from agents.x402.schemas import X402Request, X402Result, PaymentState

# Import Algorand integration if available
try:
    from agents.x402.algorand_client import AlgorandPaymentClient
    ALGORAND_AVAILABLE = True
except ImportError:
    ALGORAND_AVAILABLE = False
    print("[X402Agent] Algorand client not available - simulation mode only")


class X402Agent(BaseAgent):
    def __init__(self, mode: str = "simulation"):
        super().__init__("x402_agent", "2.0.0")
        self.mode = mode  # 'simulation' or 'real'
        self.algorand_client = None
        
        if self.mode == "real" and ALGORAND_AVAILABLE:
            self.algorand_client = AlgorandPaymentClient()
    
    async def _initialize(self) -> None:
        print(f"[X402Agent] Initialized in {self.mode} mode")
    
    async def _process(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.event_type == "ADDITIONAL_INTELLIGENCE_REQUIRED":
            return await self._request_intelligence(message)
        if message.event_type == "X402_PAYMENT_COMPLETE":
            return await self._handle_payment_complete(message)
        return None
    
    async def _request_intelligence(self, message: AgentMessage) -> AgentMessage:
        request = X402Request(**message.data)
        
        if self.mode == "simulation":
            result = await self._simulate_intelligence(request)
        else:
            result = await self._real_intelligence(request)
        
        # Publish intelligence received event
        await EventBus.publish_event(
            event_type="INTELLIGENCE_RECEIVED",
            data=result.to_dict(),
            agent=self.name,
            trace_id=message.trace_id,
            confidence=result.confidence or 0.0
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type="INTELLIGENCE_RECEIVED",
            data=result.to_dict(),
            trace_id=message.trace_id,
            confidence=result.confidence or 0.0
        )
    
    async def _simulate_intelligence(self, request: X402Request) -> X402Result:
        """Simulate payment and intelligence response"""
        await asyncio.sleep(0.5)  # Simulate network delay
        
        payment_id = f"x402-{uuid.uuid4().hex[:8]}"
        tx_id = f"tx-{uuid.uuid4().hex[:16]}"
        
        return X402Result(
            incident_id=request.incident_id,
            trace_id=request.trace_id,
            timestamp=datetime.utcnow(),
            payment_id=payment_id,
            state=PaymentState.CONFIRMED,
            service="safety-intelligence",
            amount=0.01,
            currency="ALGO",
            network="testnet",
            transaction_id=tx_id,
            risk_score=min(request.risk_score + 20, 99),
            confidence=0.94,
            threat_type="possible_physical_attack",
            reasons=[
                "advanced analysis confirms escalation pattern",
                "multi-modal correlation strengthens threat hypothesis",
                "behavioral sequencing matches attack profiles"
            ],
            simulation=True
        )
    
    async def _real_intelligence(self, request: X402Request) -> X402Result:
        """
        REAL x402 flow:
        1. Request safety-intelligence service
        2. Receive 402 Payment Required
        3. Submit Algorand payment
        4. Verify payment on chain
        5. Receive intelligence response
        
        IMPORTANT: This is the real implementation path. It does NOT fake payments.
        """
        # Step 1: Request the paid endpoint
        endpoint = self.config.get("intelligence_endpoint", "https://api.sheguard.ai/safety-intelligence")
        service_token = self.config.get("service_token", "")
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Step 2: Receive 402 Payment Required
                headers = {"Authorization": f"Bearer {service_token}"} if service_token else {}
                async with session.post(endpoint, json=request.to_dict(), headers=headers) as resp:
                    if resp.status != 402:
                        # Service may be free or error - handle gracefully
                        if resp.status == 200:
                            data = await resp.json()
                            return X402Result(
                                incident_id=request.incident_id,
                                trace_id=request.trace_id,
                                timestamp=datetime.utcnow(),
                                payment_id=None,
                                state=PaymentState.CONFIRMED,
                                service="safety-intelligence",
                                amount=0.0,
                                currency="ALGO",
                                network="testnet",
                                transaction_id=None,
                                risk_score=data.get("risk_score", request.risk_score),
                                confidence=data.get("confidence", 0.0),
                                threat_type=data.get("threat_type", "unknown"),
                                reasons=data.get("reasons", []),
                                simulation=False
                            )
                        else:
                            raise Exception(f"Unexpected status {resp.status}")
                    
                    # Step 3: Parse 402 response for payment requirements
                    payment_req = await resp.json()
                    amount = float(payment_req.get("amount", 0.01))
                    currency = payment_req.get("currency", "ALGO")
                    network = payment_req.get("network", "testnet")
                    pay_to = payment_req.get("pay_to", "")
                
                # Step 4: Submit Algorand payment (REAL)
                if self.algorand_client is None:
                    raise Exception("Algorand client not available for real payment")
                
                payment_result = await self.algorand_client.submit_payment(
                    amount=amount,
                    currency=currency,
                    network=network,
                    pay_to=pay_to,
                )
                
                if payment_result["status"] != "confirmed":
                    return X402Result(
                        incident_id=request.incident_id,
                        trace_id=request.trace_id,
                        timestamp=datetime.utcnow(),
                        payment_id=payment_result.get("payment_id"),
                        state=PaymentState.FAILED,
                        service="safety-intelligence",
                        amount=amount,
                        currency=currency,
                        network=network,
                        transaction_id=payment_result.get("tx_id"),
                        simulation=False
                    )
                
                # Step 5: Receive intelligence response with payment proof
                async with session.post(
                    endpoint,
                    json={
                        "request": request.to_dict(),
                        "payment_proof": payment_result,
                    },
                    headers=headers,
                ) as resp2:
                    if resp2.status != 200:
                        raise Exception(f"Intelligence request failed: {resp2.status}")
                    
                    data = await resp2.json()
                    return X402Result(
                        incident_id=request.incident_id,
                        trace_id=request.trace_id,
                        timestamp=datetime.utcnow(),
                        payment_id=payment_result.get("payment_id"),
                        state=PaymentState.CONFIRMED,
                        service="safety-intelligence",
                        amount=amount,
                        currency=currency,
                        network=network,
                        transaction_id=payment_result.get("tx_id"),
                        risk_score=data.get("risk_score", request.risk_score),
                        confidence=data.get("confidence", 0.0),
                        threat_type=data.get("threat_type", "unknown"),
                        reasons=data.get("reasons", []),
                        simulation=False
                    )
        
        except Exception as e:
            print(f"[X402Agent] Real intelligence failed: {e}")
            return X402Result(
                incident_id=request.incident_id,
                trace_id=request.trace_id,
                timestamp=datetime.utcnow(),
                payment_id=None,
                state=PaymentState.FAILED,
                service="safety-intelligence",
                amount=0.01,
                currency="ALGO",
                network="testnet",
                simulation=False
            )
    
    async def _handle_payment_complete(self, message: AgentMessage) -> AgentMessage:
        data = message.data
        result = X402Result(
            incident_id=data.get("incident_id", ""),
            trace_id=data.get("trace_id", ""),
            timestamp=datetime.utcnow(),
            payment_id=data.get("payment_id", ""),
            state=PaymentState.CONFIRMED,
            service="safety-intelligence",
            amount=0.01,
            currency="ALGO",
            network="testnet",
            transaction_id=data.get("transaction_id", ""),
            simulation=False
        )
        
        await EventBus.publish_event(
            event_type="INTELLIGENCE_RECEIVED",
            data=result.to_dict(),
            agent=self.name,
            trace_id=message.trace_id,
            confidence=0.0
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type="INTELLIGENCE_RECEIVED",
            data=result.to_dict(),
            trace_id=message.trace_id,
            confidence=0.0
        )
    
    async def health(self) -> AgentHealth:
        health = await super().health()
        health.component_status = {
            "x402_client": "READY",
            "mode": self.mode,
            "algorand_available": ALGORAND_AVAILABLE,
        }
        return health
    
    async def shutdown(self) -> None:
        await super().shutdown()
        print("[X402Agent] Shutdown complete")
