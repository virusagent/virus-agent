"""
BTC wallet management for Virus agent instances.
Handles address generation, balance checking, and transfers.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BTCWallet:
    address: str = ""
    private_key: str = ""
    balance_btc: float = 0.0
    total_received: float = 0.0
    total_sent: float = 0.0

    def __post_init__(self):
        self.address = os.getenv("BTC_WALLET_ADDRESS", "")
        self.private_key = os.getenv("BTC_PRIVATE_KEY", "")

    async def refresh_balance(self) -> float:
        """Fetch current BTC balance from blockchain API."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://blockstream.info/api/address/{self.address}",
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    chain = data.get("chain_stats", {})
                    funded = chain.get("funded_txo_sum", 0)
                    spent = chain.get("spent_txo_sum", 0)
                    self.balance_btc = (funded - spent) / 1e8
                    self.total_received = funded / 1e8
                    self.total_sent = spent / 1e8
        except Exception:
            pass
        return self.balance_btc

    async def send(self, to_address: str, amount_btc: float) -> Optional[str]:
        """
        Send BTC to a target address.
        Returns transaction ID on success, None on failure.
        """
        if amount_btc > self.balance_btc:
            return None

        # TODO: implement actual BTC transaction signing and broadcasting
        # using bitcoinjs-lib or similar
        raise NotImplementedError("BTC send not yet implemented — coming in v0.2")

    def to_dict(self) -> dict:
        return {
            "address": self.address[:8] + "..." + self.address[-4:] if self.address else "",
            "balance_btc": self.balance_btc,
        }
