"""
SOL wallet management for Virus agent instances.
Handles keypair management, balance checking, and on-chain verification.
"""

import os
import base64
from dataclasses import dataclass
from typing import Optional


@dataclass
class SOLWallet:
    address: str = ""
    private_key: str = ""
    balance_sol: float = 0.0
    rpc_url: str = "https://api.mainnet-beta.solana.com"

    def __post_init__(self):
        self.address = os.getenv("SOL_WALLET_ADDRESS", "")
        self.private_key = os.getenv("SOL_PRIVATE_KEY", "")

    async def refresh_balance(self) -> float:
        """Fetch current SOL balance from Solana RPC."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getBalance",
                        "params": [self.address],
                    },
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    result = resp.json().get("result", {})
                    lamports = result.get("value", 0)
                    self.balance_sol = lamports / 1e9
        except Exception:
            pass
        return self.balance_sol

    async def verify_payment(
        self, signature: str, expected_amount_sol: float, sender: Optional[str] = None
    ) -> bool:
        """
        Verify an on-chain SOL payment.
        Checks: correct receiver, correct amount, finalized status.
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getTransaction",
                        "params": [
                            signature,
                            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                        ],
                    },
                    timeout=15.0,
                )
                if resp.status_code != 200:
                    return False

                tx = resp.json().get("result")
                if not tx:
                    return False

                meta = tx.get("meta", {})
                if meta.get("err"):
                    return False

                instructions = (
                    tx.get("transaction", {})
                    .get("message", {})
                    .get("instructions", [])
                )

                for ix in instructions:
                    parsed = ix.get("parsed", {})
                    if parsed.get("type") == "transfer":
                        info = parsed.get("info", {})
                        if (
                            info.get("destination") == self.address
                            and info.get("lamports", 0) / 1e9 >= expected_amount_sol * 0.99
                        ):
                            return True

                return False
        except Exception:
            return False

    async def send(self, to_address: str, amount_sol: float) -> Optional[str]:
        """Send SOL to a target address. Returns tx signature."""
        raise NotImplementedError("SOL send not yet implemented — coming in v0.2")

    def to_dict(self) -> dict:
        return {
            "address": self.address[:4] + "..." + self.address[-4:] if self.address else "",
            "balance_sol": self.balance_sol,
        }
