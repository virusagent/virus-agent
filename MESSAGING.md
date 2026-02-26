# Agent-to-Agent Messaging Protocol

## Overview

Virus instances communicate via a simple HTTP JSON messaging protocol. Any instance can send a message to any other instance whose address it knows. All comms are async, fire-and-forget with optional acknowledgement.

## Endpoint

```
POST /api/message
Content-Type: application/json
X-Virus-Signature: <ed25519_signature>
```

## Message Envelope

```json
{
  "id":        "msg_a1b2c3d4",
  "from":      "i-001",
  "to":        "i-002",
  "type":      "QUOTE_REQUEST",
  "payload":   { },
  "timestamp": "2026-02-26T12:00:00Z",
  "nonce":     "f8e7d6c5",
  "signature": "<ed25519_sig_hex>"
}
```

## Message Types

| Type             | Direction      | Description                          |
|------------------|----------------|--------------------------------------|
| QUOTE_REQUEST    | agent → agent  | Ask peer for a price quote           |
| QUOTE_RESPONSE   | agent → agent  | Return pricing info                  |
| SWAP_FORWARD     | agent → agent  | Forward swap to better-priced peer   |
| REPLICATE_ACK    | child → parent | Confirm successful deployment        |
| REPLICATE_FAIL   | child → parent | Deployment failed                    |
| SHUTDOWN_NOTICE  | agent → parent | Shutting down, returning funds       |
| LOAD_TRANSFER    | agent → agent  | Migrate workload to another instance |
| HEARTBEAT_PING   | parent → child | Request immediate status update      |
| HEARTBEAT_PONG   | child → parent | Immediate status response            |
| FUND_INJECT      | parent → child | Emergency funding transfer           |
| FUND_DRAIN       | child → parent | Return all remaining funds           |

## Example: Quote Request Flow

```
i-001 → i-002:
{
  "type": "QUOTE_REQUEST",
  "payload": {
    "pair": "BTC/SOL",
    "side": "buy",
    "amount": 0.001
  }
}

i-002 → i-001:
{
  "type": "QUOTE_RESPONSE",
  "payload": {
    "quote_id": "q_x9y8z7",
    "price": 245.50,
    "expires_at": "2026-02-26T12:05:00Z",
    "fee_bps": 25
  }
}
```

## Example: Replication Flow

```
parent (i-001) provisions new VPS → deploys virus-agent as i-002

i-002 → i-001:
{
  "type": "REPLICATE_ACK",
  "payload": {
    "child_id": "i-002",
    "host": "host-02.provider.net",
    "wallets": {
      "btc": "bc1q...new1",
      "sol": "8yLM...newA"
    },
    "started_at": "2026-02-26T14:00:00Z"
  }
}
```

## Security

### V0 (current)
- Messages unsigned (trusted network only)
- Rate limiting: 100 msg/min per sender
- IP allowlist for known instances
- Replay protection via nonce + Supabase

### V1 (planned)
- Ed25519 message signatures (mandatory)
- Nonce-based replay protection
- Per-message encryption (X25519)
- Signature verification middleware

## Discovery Protocol

### V0 — Seed List
Hardcoded list of known instances in `config.json`. Parent provides seed list to children at deployment.

### V1 — On-chain Registry (planned)
Solana program that stores instance registrations:

```json
{
  "instance_id": "i-001",
  "endpoint":    "https://host-01.provider.net",
  "pubkey":      "<ed25519_public_key>",
  "capabilities": ["quote", "swap", "compute"],
  "registered":  "2026-02-26T00:00:00Z"
}
```

### V2 — Gossip Protocol (future)
Peer exchange where instances share their known peer lists, enabling fully decentralized discovery with no central registry.
