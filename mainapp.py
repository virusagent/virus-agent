"""
Virus Agent — Self-Replicating Autonomous Agent
Main application: FastAPI server + heartbeat loop + replication scheduler

Origin: Bitcointalk #507656 (Feb 2014) by niniyo
"almost like a virus"
"""

import os
import asyncio
import uuid
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from management.agent import VirusAgent
from blockchain.payments import PaymentVerifier
from services.exchange import ExchangeService
from services.compute import ComputeService
from services.replication import ReplicationService
from services.survival import SurvivalMonitor


agent: Optional[VirusAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    agent = VirusAgent(
        instance_id=os.getenv("INSTANCE_ID", f"i-{uuid.uuid4().hex[:6]}"),
        parent_endpoint=os.getenv("PARENT_ENDPOINT", ""),
    )
    await agent.initialize()

    heartbeat_task = asyncio.create_task(agent.heartbeat_loop())
    replication_task = asyncio.create_task(agent.replication_loop())
    survival_task = asyncio.create_task(agent.survival_loop())

    yield

    heartbeat_task.cancel()
    replication_task.cancel()
    survival_task.cancel()
    await agent.shutdown()


app = FastAPI(
    title="Virus Agent",
    description="Self-replicating autonomous agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Status ──────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status(network: bool = False):
    if not agent:
        raise HTTPException(503, "Agent not initialized")

    status = await agent.get_status()

    if network:
        status["network"] = await agent.get_network_status()

    return status


# ── Exchange ────────────────────────────────────────────────────────

class QuoteRequest(BaseModel):
    pair: str
    side: str
    amount: float

class SwapIntentRequest(BaseModel):
    quote_id: str
    max_slippage_bps: int = 50


@app.post("/api/quote")
async def request_quote(req: QuoteRequest):
    if not agent:
        raise HTTPException(503, "Agent not initialized")
    return await agent.exchange.create_quote(req.pair, req.side, req.amount)


@app.post("/api/swap_intent")
async def create_swap_intent(req: SwapIntentRequest):
    if not agent:
        raise HTTPException(503, "Agent not initialized")
    return await agent.exchange.create_intent(req.quote_id, req.max_slippage_bps)


@app.get("/api/intents/{intent_id}")
async def get_intent(intent_id: str):
    if not agent:
        raise HTTPException(503, "Agent not initialized")
    intent = agent.exchange.get_intent(intent_id)
    if not intent:
        raise HTTPException(404, "Intent not found")
    return intent


# ── Messaging ───────────────────────────────────────────────────────

class AgentMessage(BaseModel):
    id: str
    from_id: str
    to: str
    type: str
    payload: dict
    timestamp: str
    nonce: str
    signature: str = ""


@app.post("/api/message")
async def receive_message(msg: AgentMessage):
    if not agent:
        raise HTTPException(503, "Agent not initialized")
    return await agent.handle_message(msg.model_dump())


# ── Network ─────────────────────────────────────────────────────────

@app.get("/api/network")
async def get_network():
    if not agent:
        raise HTTPException(503, "Agent not initialized")
    return await agent.get_children_status()


# ── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("mainapp:app", host="0.0.0.0", port=port, reload=False)
