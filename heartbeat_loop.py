"""
Standalone heartbeat monitor.
Polls all known child instances and logs their status.
Can be run independently of the main agent.
"""

import asyncio
import time
import json
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("heartbeat")

POLL_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
MAX_MISSED = 3


async def poll_instance(endpoint: str) -> dict:
    """Poll a single instance for its status."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{endpoint}/api/status", timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"status": "unreachable"}


async def main():
    seed_file = os.getenv("SEED_FILE", "seeds.json")

    if os.path.exists(seed_file):
        with open(seed_file) as f:
            instances = json.load(f)
    else:
        instances = []

    missed: dict[str, int] = {}

    logger.info(f"Heartbeat monitor started — polling {len(instances)} instances every {POLL_INTERVAL}s")

    while True:
        for inst in instances:
            endpoint = inst.get("endpoint", "")
            inst_id = inst.get("instance_id", endpoint)

            status = await poll_instance(endpoint)
            state = status.get("status", "unreachable")

            if state == "unreachable":
                missed[inst_id] = missed.get(inst_id, 0) + 1
                if missed[inst_id] >= MAX_MISSED:
                    logger.warning(f"  {inst_id}: DEAD (missed {missed[inst_id]} beats)")
                else:
                    logger.info(f"  {inst_id}: MISSED ({missed[inst_id]}/{MAX_MISSED})")
            else:
                missed[inst_id] = 0
                runway = status.get("burn", {}).get("runway_hours", "?")
                margin = status.get("profit", {}).get("margin_pct", "?")
                logger.info(f"  {inst_id}: {state.upper()} | runway: {runway}h | margin: {margin}%")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
