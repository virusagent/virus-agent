"""
Exchange service: quote generation and swap intent handling.
Revenue source for the Virus agent.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


SUPPORTED_PAIRS = {"BTC/SOL", "SOL/BTC"}
FEE_BPS = 25
QUOTE_TTL_SECONDS = 300


@dataclass
class Quote:
    quote_id: str
    pair: str
    side: str
    amount: float
    price: float
    fee_bps: int
    created_at: float
    expires_at: float


@dataclass
class SwapIntent:
    intent_id: str
    quote_id: str
    max_slippage_bps: int
    status: str = "pending"
    created_at: float = 0.0
    filled_at: Optional[float] = None


class ExchangeService:
    def __init__(self, sol_wallet, payment_verifier):
        self.sol_wallet = sol_wallet
        self.payments = payment_verifier
        self._quotes: dict[str, Quote] = {}
        self._intents: dict[str, SwapIntent] = {}
        self._total_revenue_btc: float = 0.0
        self._revenue_24h_btc: float = 0.0
        self._trades_count: int = 0

    async def create_quote(self, pair: str, side: str, amount: float) -> dict:
        """Generate a price quote for the requested pair."""
        if pair not in SUPPORTED_PAIRS:
            return {"error": f"Unsupported pair: {pair}. Supported: {', '.join(SUPPORTED_PAIRS)}"}

        price = self._get_price(pair)
        now = time.time()
        quote_id = f"q_{uuid.uuid4().hex[:8]}"

        quote = Quote(
            quote_id=quote_id,
            pair=pair,
            side=side,
            amount=amount,
            price=price,
            fee_bps=FEE_BPS,
            created_at=now,
            expires_at=now + QUOTE_TTL_SECONDS,
        )
        self._quotes[quote_id] = quote

        return {
            "quote_id": quote_id,
            "pair": pair,
            "side": side,
            "amount": amount,
            "price": price,
            "fee_bps": FEE_BPS,
            "expires_at": quote.expires_at,
        }

    async def create_intent(self, quote_id: str, max_slippage_bps: int) -> dict:
        """Create a swap intent from a quote."""
        quote = self._quotes.get(quote_id)
        if not quote:
            return {"error": "Quote not found"}

        if time.time() > quote.expires_at:
            return {"error": "Quote expired"}

        intent_id = f"i_{uuid.uuid4().hex[:8]}"
        intent = SwapIntent(
            intent_id=intent_id,
            quote_id=quote_id,
            max_slippage_bps=max_slippage_bps,
            created_at=time.time(),
        )
        self._intents[intent_id] = intent

        # In production, this would wait for on-chain payment verification
        # then execute the swap. For now, mark as pending.
        return {
            "intent_id": intent_id,
            "status": "pending",
            "quote_id": quote_id,
            "pay_to": self.sol_wallet.address,
            "amount_due": quote.amount * quote.price * (1 + FEE_BPS / 10000),
        }

    def get_intent(self, intent_id: str) -> Optional[dict]:
        """Get the current state of a swap intent."""
        intent = self._intents.get(intent_id)
        if not intent:
            return None
        return {
            "intent_id": intent.intent_id,
            "status": intent.status,
            "quote_id": intent.quote_id,
            "created_at": intent.created_at,
            "filled_at": intent.filled_at,
        }

    def revenue_summary(self) -> dict:
        return {
            "total_btc": self._total_revenue_btc,
            "last_24h_btc": self._revenue_24h_btc,
            "trades": self._trades_count,
            "sources": {
                "exchange_fees": self._total_revenue_btc,
            },
        }

    def _get_price(self, pair: str) -> float:
        """
        Get current price for a pair.
        TODO: integrate with real price feed (CoinGecko, Jupiter, etc.)
        """
        mock_prices = {
            "BTC/SOL": 245.50,
            "SOL/BTC": 0.00407,
        }
        return mock_prices.get(pair, 0.0)
