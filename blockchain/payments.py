"""
Unified payment verification with replay protection.
Uses Supabase to store processed transaction signatures.
"""

import os
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class PaymentVerifier:
    supabase_url: str = ""
    supabase_key: str = ""
    _processed: set = field(default_factory=set)

    def __post_init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_KEY", "")

    async def is_signature_used(self, signature: str) -> bool:
        """Check if a transaction signature has already been processed."""
        if signature in self._processed:
            return True

        if not self.supabase_url:
            return False

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.supabase_url}/rest/v1/processed_signatures",
                    params={"signature": f"eq.{signature}", "select": "id"},
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                    },
                    timeout=5.0,
                )
                if resp.status_code == 200:
                    return len(resp.json()) > 0
        except Exception:
            pass
        return False

    async def mark_signature_used(self, signature: str) -> None:
        """Record a transaction signature as processed."""
        self._processed.add(signature)

        if not self.supabase_url:
            return

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.supabase_url}/rest/v1/processed_signatures",
                    json={"signature": signature},
                    headers={
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=5.0,
                )
        except Exception:
            pass

    async def verify_and_record(
        self, signature: str, sol_wallet, expected_amount: float
    ) -> bool:
        """Full verification: check replay, verify on-chain, record."""
        if await self.is_signature_used(signature):
            return False

        verified = await sol_wallet.verify_payment(signature, expected_amount)
        if not verified:
            return False

        await self.mark_signature_used(signature)
        return True
