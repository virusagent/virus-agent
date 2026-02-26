"""
Replication service: VPS provisioning, SSH deployment, seed funding.
The core "virus" mechanic — profitable instances spawn children.
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("virus-agent.replication")

REPLICATION_THRESHOLD_BTC = float(os.getenv("REPLICATION_THRESHOLD", "0.002"))
MIN_SEED_FUNDS_BTC = 0.0005
MIN_PROFIT_MARGIN = float(os.getenv("MIN_PROFIT_MARGIN", "60"))


@dataclass
class ProvisionedVPS:
    ip_address: str
    provider: str
    monthly_cost_usd: float
    ssh_ready: bool = False


class ReplicationService:
    def __init__(self, agent):
        self.agent = agent
        self.threshold = REPLICATION_THRESHOLD_BTC
        self.vps_provider = os.getenv("VPS_PROVIDER", "hetzner")
        self.vps_api_key = os.getenv("VPS_PROVIDER_API_KEY", "")
        self.ssh_pubkey = os.getenv("SSH_PUBLIC_KEY", "")

    def is_ready(self) -> bool:
        """Check if conditions for replication are met."""
        btc_balance = self.agent.btc_wallet.balance_btc
        profit = self.agent.survival.profit_margin()

        return (
            btc_balance >= self.threshold
            and profit >= MIN_PROFIT_MARGIN
            and self.vps_api_key != ""
        )

    async def replicate(self) -> Optional[object]:
        """Full replication flow: provision → deploy → fund → verify."""
        from management.agent import ChildInstance

        logger.info("Starting replication sequence...")

        vps = await self._provision_vps()
        if not vps:
            logger.error("VPS provisioning failed")
            return None

        logger.info(f"VPS provisioned: {vps.ip_address} ({vps.provider})")

        deployed = await self._deploy_agent(vps)
        if not deployed:
            logger.error("Agent deployment failed")
            return None

        logger.info(f"Agent deployed to {vps.ip_address}")

        child_id = f"i-{vps.ip_address.replace('.', '')[-6:]}"
        funded = await self._send_seed_funds(vps, MIN_SEED_FUNDS_BTC)
        if not funded:
            logger.warning("Seed funding failed — child may not survive")

        return ChildInstance(
            instance_id=child_id,
            endpoint=f"http://{vps.ip_address}:8000",
        )

    async def _provision_vps(self) -> Optional[ProvisionedVPS]:
        """Provision a new VPS instance via provider API."""
        if self.vps_provider == "hetzner":
            return await self._provision_hetzner()
        elif self.vps_provider == "vultr":
            return await self._provision_vultr()
        return None

    async def _provision_hetzner(self) -> Optional[ProvisionedVPS]:
        """Provision via Hetzner Cloud API."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.hetzner.cloud/v1/servers",
                    headers={"Authorization": f"Bearer {self.vps_api_key}"},
                    json={
                        "name": f"virus-{self.agent.instance_id}",
                        "server_type": "cx22",
                        "image": "ubuntu-22.04",
                        "location": "fsn1",
                        "ssh_keys": [self.ssh_pubkey] if self.ssh_pubkey else [],
                    },
                    timeout=30.0,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    server = data.get("server", {})
                    ip = server.get("public_net", {}).get("ipv4", {}).get("ip", "")
                    return ProvisionedVPS(
                        ip_address=ip,
                        provider="hetzner",
                        monthly_cost_usd=4.55,
                        ssh_ready=True,
                    )
        except Exception as e:
            logger.error(f"Hetzner provisioning error: {e}")
        return None

    async def _provision_vultr(self) -> Optional[ProvisionedVPS]:
        """Provision via Vultr API."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.vultr.com/v2/instances",
                    headers={"Authorization": f"Bearer {self.vps_api_key}"},
                    json={
                        "region": "ewr",
                        "plan": "vc2-1c-1gb",
                        "os_id": 387,
                        "label": f"virus-{self.agent.instance_id}",
                    },
                    timeout=30.0,
                )
                if resp.status_code in (200, 202):
                    data = resp.json()
                    ip = data.get("instance", {}).get("main_ip", "")
                    return ProvisionedVPS(
                        ip_address=ip,
                        provider="vultr",
                        monthly_cost_usd=6.00,
                    )
        except Exception as e:
            logger.error(f"Vultr provisioning error: {e}")
        return None

    async def _deploy_agent(self, vps: ProvisionedVPS) -> bool:
        """Deploy virus-agent to the provisioned VPS via SSH."""
        import asyncio

        deploy_script = f"""
            apt-get update -qq && apt-get install -y -qq python3-pip git
            git clone https://github.com/virusagent/virus-agent.git /opt/virus-agent
            cd /opt/virus-agent
            pip3 install -r requirements.txt
            cp .env.example .env
            nohup python3 mainapp.py > /var/log/virus-agent.log 2>&1 &
        """

        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=30",
                f"root@{vps.ip_address}",
                deploy_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"SSH deploy failed: {e}")
            return False

    async def _send_seed_funds(self, vps: ProvisionedVPS, amount_btc: float) -> bool:
        """Transfer seed BTC to the child instance."""
        # In v0.2: actual BTC transaction to child's generated wallet
        logger.info(f"Seed funds: {amount_btc} BTC → child at {vps.ip_address}")
        return True
