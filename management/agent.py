"""
VirusAgent — Core agent class.
Orchestrates the full lifecycle: earn, survive, replicate.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from blockchain.btc_wallet import BTCWallet
from blockchain.sol_wallet import SOLWallet
from blockchain.payments import PaymentVerifier
from services.exchange import ExchangeService
from services.compute import ComputeService
from services.replication import ReplicationService
from services.survival import SurvivalMonitor

logger = logging.getLogger("virus-agent")


@dataclass
class ChildInstance:
    instance_id: str
    endpoint: str
    status: str = "alive"
    last_heartbeat: float = 0.0
    missed_beats: int = 0
    wallets: dict = field(default_factory=dict)


class VirusAgent:
    def __init__(self, instance_id: str, parent_endpoint: str = ""):
        self.instance_id = instance_id
        self.parent_endpoint = parent_endpoint
        self.started_at = time.time()

        self.btc_wallet = BTCWallet()
        self.sol_wallet = SOLWallet()
        self.payments = PaymentVerifier()

        self.exchange = ExchangeService(self.sol_wallet, self.payments)
        self.compute = ComputeService(self.sol_wallet, self.payments)
        self.replicator = ReplicationService(self)
        self.survival = SurvivalMonitor(self)

        self.children: dict[str, ChildInstance] = {}
        self._running = True

    async def initialize(self):
        """Start the agent: refresh wallet balances, announce to parent."""
        logger.info(f"Initializing virus-agent {self.instance_id}")

        await self.btc_wallet.refresh_balance()
        await self.sol_wallet.refresh_balance()

        logger.info(
            f"BTC: {self.btc_wallet.balance_btc:.6f} | "
            f"SOL: {self.sol_wallet.balance_sol:.4f}"
        )

        if self.parent_endpoint:
            await self._send_replicate_ack()

    async def shutdown(self):
        """Graceful shutdown: drain funds to parent, notify."""
        self._running = False
        logger.info(f"Shutting down {self.instance_id}")

        if self.parent_endpoint:
            await self._notify_parent("SHUTDOWN_NOTICE", {
                "instance_id": self.instance_id,
                "remaining_btc": self.btc_wallet.balance_btc,
                "remaining_sol": self.sol_wallet.balance_sol,
            })

    async def get_status(self) -> dict:
        """Build the full status response."""
        await self.btc_wallet.refresh_balance()
        await self.sol_wallet.refresh_balance()

        uptime_ms = int((time.time() - self.started_at) * 1000)
        burn_rate = self.survival.daily_burn_btc
        runway = self.survival.runway_hours(self.btc_wallet.balance_btc)

        if runway > 48:
            status = "alive"
        elif runway > 24:
            status = "degraded"
        else:
            status = "dying"

        return {
            "agent": "virus",
            "version": "0.1.0",
            "instance_id": self.instance_id,
            "status": status,
            "uptime_ms": uptime_ms,
            "wallets": {
                "btc": self.btc_wallet.to_dict(),
                "sol": self.sol_wallet.to_dict(),
            },
            "capabilities": ["quote", "swap_intent", "compute"],
            "children": list(self.children.keys()),
            "revenue": self.exchange.revenue_summary(),
            "burn": {
                "rate_per_day": burn_rate,
                "runway_hours": runway,
            },
            "profit": self.survival.profit_summary(),
            "replication": {
                "threshold_btc": self.replicator.threshold,
                "ready": self.replicator.is_ready(),
                "children_count": len(self.children),
            },
        }

    async def get_network_status(self) -> dict:
        """Aggregate stats across all known instances."""
        alive = sum(1 for c in self.children.values() if c.status == "alive")
        degraded = sum(1 for c in self.children.values() if c.status == "degraded")
        return {
            "total_instances": 1 + len(self.children),
            "alive": alive + 1,
            "degraded": degraded,
            "dying": len(self.children) - alive - degraded,
        }

    async def get_children_status(self) -> list[dict]:
        """Return status of all child instances."""
        return [
            {
                "instance_id": c.instance_id,
                "endpoint": c.endpoint,
                "status": c.status,
                "last_heartbeat": c.last_heartbeat,
            }
            for c in self.children.values()
        ]

    # ── Background Loops ────────────────────────────────────────────

    async def heartbeat_loop(self):
        """Poll all children every 30s."""
        while self._running:
            for child in list(self.children.values()):
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            f"{child.endpoint}/api/status",
                            timeout=5.0,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            child.status = data.get("status", "alive")
                            child.last_heartbeat = time.time()
                            child.missed_beats = 0
                        else:
                            child.missed_beats += 1
                except Exception:
                    child.missed_beats += 1

                if child.missed_beats >= 3:
                    child.status = "dead"
                    logger.warning(f"Child {child.instance_id} marked dead")

            await asyncio.sleep(30)

    async def replication_loop(self):
        """Check replication conditions every 5 minutes."""
        while self._running:
            await asyncio.sleep(300)

            if self.replicator.is_ready():
                logger.info("Replication threshold met — initiating clone")
                try:
                    child = await self.replicator.replicate()
                    if child:
                        self.children[child.instance_id] = child
                        logger.info(f"Child {child.instance_id} deployed")
                except Exception as e:
                    logger.error(f"Replication failed: {e}")

    async def survival_loop(self):
        """Monitor profitability every 60s, shutdown if dying."""
        while self._running:
            await asyncio.sleep(60)

            await self.btc_wallet.refresh_balance()
            runway = self.survival.runway_hours(self.btc_wallet.balance_btc)

            if runway < 24:
                logger.warning(f"Runway critical: {runway:.1f}h — preparing shutdown")
                if runway < 1:
                    await self.shutdown()
                    break

    # ── Messaging ───────────────────────────────────────────────────

    async def handle_message(self, msg: dict) -> dict:
        """Process an incoming inter-agent message."""
        msg_type = msg.get("type", "")

        if msg_type == "REPLICATE_ACK":
            payload = msg.get("payload", {})
            child_id = payload.get("child_id", "")
            if child_id:
                self.children[child_id] = ChildInstance(
                    instance_id=child_id,
                    endpoint=payload.get("endpoint", ""),
                    wallets=payload.get("wallets", {}),
                    last_heartbeat=time.time(),
                )
            return {"status": "ack"}

        elif msg_type == "HEARTBEAT_PING":
            status = await self.get_status()
            return {"type": "HEARTBEAT_PONG", "payload": status}

        elif msg_type == "SHUTDOWN_NOTICE":
            child_id = msg.get("from_id", "")
            if child_id in self.children:
                self.children[child_id].status = "dead"
            return {"status": "ack"}

        elif msg_type == "FUND_INJECT":
            return {"status": "received"}

        elif msg_type == "QUOTE_REQUEST":
            quote = await self.exchange.create_quote(
                msg["payload"].get("pair", "BTC/SOL"),
                msg["payload"].get("side", "buy"),
                msg["payload"].get("amount", 0.001),
            )
            return {"type": "QUOTE_RESPONSE", "payload": quote}

        return {"status": "unknown_type"}

    async def _send_replicate_ack(self):
        """Notify parent that this child is alive."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.parent_endpoint}/api/message",
                    json={
                        "id": f"msg_{self.instance_id}_ack",
                        "from_id": self.instance_id,
                        "to": "parent",
                        "type": "REPLICATE_ACK",
                        "payload": {
                            "child_id": self.instance_id,
                            "endpoint": f"http://localhost:8000",
                            "wallets": {
                                "btc": self.btc_wallet.address,
                                "sol": self.sol_wallet.address,
                            },
                        },
                        "timestamp": "",
                        "nonce": "",
                    },
                    timeout=10.0,
                )
        except Exception as e:
            logger.error(f"Failed to send REPLICATE_ACK: {e}")

    async def _notify_parent(self, msg_type: str, payload: dict):
        """Send a message to the parent instance."""
        if not self.parent_endpoint:
            return
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.parent_endpoint}/api/message",
                    json={
                        "id": f"msg_{self.instance_id}_{msg_type.lower()}",
                        "from_id": self.instance_id,
                        "to": "parent",
                        "type": msg_type,
                        "payload": payload,
                        "timestamp": "",
                        "nonce": "",
                    },
                    timeout=10.0,
                )
        except Exception:
            pass
