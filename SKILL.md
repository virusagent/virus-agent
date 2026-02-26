# Virus Agent — Skill Manifest

## Identity

| Field   | Value                                    |
|---------|------------------------------------------|
| name    | virus-agent                              |
| type    | Self-replicating autonomous agent        |
| version | 0.1.0                                    |
| origin  | Bitcointalk #507656 (Feb 2014)           |
| license | MIT                                      |

## Capabilities

- Provides real-time exchange quotes across BTC/SOL pairs
- Executes swap intents with configurable slippage tolerance (default: 50 bps)
- Runs compute jobs (task execution) for SOL payments
- Self-replicating: profitable instances spawn clones on new VPS infrastructure
- Revenue tracking with per-instance P&L reporting
- Automatic shutdown when balance < 24h hosting burn rate
- Inter-agent messaging via HTTP JSON protocol
- Heartbeat-based health monitoring across all instances

## Quick Start (for agents)

**Want your agent to buy compute from Virus?**

1. `GET /api/status` — check if instance is alive, get wallet address
2. `POST /api/quote` — request a price quote: `{ "pair": "BTC/SOL", "side": "buy", "amount": 0.001 }`
3. Send SOL payment to the wallet address returned in status
4. `POST /api/swap_intent` — submit intent with `{ "quote_id": "...", "max_slippage_bps": 50 }`
5. `GET /api/intents/{id}` — poll until `status: "filled"` or `"expired"`

No downloads required. No risk for your agent. Pure HTTP API.

## API Endpoints

| Route                | Method | Description                     | Auth      | Rate Limit  |
|----------------------|--------|---------------------------------|-----------|-------------|
| `/api/status`        | GET    | Health, wallets, stats          | none      | 60 req/min  |
| `/api/quote`         | POST   | Request a price quote           | none      | 30 req/min  |
| `/api/swap_intent`   | POST   | Submit a swap intent            | api_key   | 10 req/min  |
| `/api/intents/{id}`  | GET    | Check intent status             | none      | 60 req/min  |
| `/api/message`       | POST   | Inter-agent messaging           | signature | 100 req/min |
| `/api/network`       | GET    | List known instances            | none      | 10 req/min  |

## Interaction Pattern

```
1. GET  /api/status
   → verify instance is alive, get wallet + capabilities

2. POST /api/quote
   body: { "pair": "BTC/SOL", "side": "buy", "amount": 0.001 }
   → returns { "quote_id": "q_abc123", "price": 245.50, "expires_at": "...", "fee_bps": 25 }

3. POST /api/swap_intent
   body: { "quote_id": "q_abc123", "max_slippage_bps": 50 }
   → returns { "intent_id": "i_xyz789", "status": "pending" }

4. GET  /api/intents/i_xyz789
   → poll until status is "filled" | "expired" | "failed"
```

## Replication Protocol

When an instance accumulates reserves above `replication_threshold`:

1. Query VPS provider API for cheapest available instance
2. Provision new VPS (minimum: 1 vCPU, 512 MB RAM)
3. Deploy virus-agent binary via SSH
4. Generate new wallet keypairs for the child
5. Transfer seed funds (0.0005 BTC minimum)
6. Child begins its own earn/survive/replicate cycle
7. Parent receives `REPLICATE_ACK` message from child

## Economic Parameters

| Parameter              | Value           |
|------------------------|-----------------|
| replication_threshold  | 0.002 BTC       |
| min_seed_funds         | 0.0005 BTC      |
| max_burn_rate          | 0.0004 BTC/day  |
| target_profit_margin   | > 60%           |
| shutdown_threshold     | < 24h burn left |
| exchange_fee           | 25 bps          |
| compute_fee            | 0.01 SOL / job  |

## Status Response Schema

```json
{
  "agent": "virus",
  "version": "0.1.0",
  "instance_id": "i-001",
  "status": "alive",
  "wallets": {
    "btc": "bc1q...v8mf",
    "sol": "7xKX...9vFd"
  },
  "capabilities": ["quote", "swap_intent", "compute"],
  "revenue": {
    "total_btc": 0.0048,
    "last_24h_btc": 0.0012
  },
  "burn": {
    "rate_per_day": 0.0003,
    "runway_hours": 384
  },
  "profit": {
    "margin_pct": 87.5,
    "status": "positive"
  },
  "replication": {
    "threshold_btc": 0.002,
    "ready": true,
    "children": 1
  }
}
```

## Origin

Concept by **niniyo** — [Bitcointalk Thread #507656](https://bitcointalk.org/index.php?action=printpage;topic=507656.0) (February 2014)

> *"Imagine a piece of software that has its own bitcoin wallet. With its wallet it can purchase VPS's, spawning another instance of itself, and sending it seed money to get started. In some ways it would be like a distributed autonomous organisation, but in another sense it's almost like a virus."*
