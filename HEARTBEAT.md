# Heartbeat Protocol — Health Monitoring

## Overview

Every Virus instance exposes a heartbeat at `GET /api/status`. Parent nodes and monitoring tools poll this endpoint to track instance health across the network.

## Polling Configuration

| Parameter           | Value                    |
|---------------------|--------------------------|
| default_interval    | 30s                      |
| missed_before_dead  | 3 consecutive            |
| retry_backoff       | exponential (2s, 4s, 8s) |
| max_retry           | 3 attempts per cycle     |
| timeout             | 5000ms per request       |

## Response Schema

```
GET /api/status → 200 OK

{
  "agent":          "virus",
  "version":        "0.1.0",
  "instance_id":    "i-001",
  "host":           "host-01.provider.net",
  "status":         "alive",
  "uptime_ms":      3600000,
  "started_at":     "2026-02-26T00:00:00Z",
  "wallets": {
    "btc":          "bc1q...v8mf",
    "sol":          "7xKX...9vFd"
  },
  "capabilities":   ["quote", "swap_intent", "compute"],
  "instances":      2,
  "children":       ["i-002"],
  "revenue": {
    "total_btc":    0.0048,
    "last_24h_btc": 0.0012,
    "sources": {
      "exchange_fees": 0.0008,
      "compute_jobs":  0.0004
    }
  },
  "burn": {
    "total_btc":    0.0006,
    "rate_per_day":  0.0003,
    "runway_hours":  384
  },
  "profit": {
    "net_btc":      0.0042,
    "margin_pct":   87.5,
    "status":       "positive"
  },
  "replication": {
    "threshold_btc": 0.002,
    "ready":         true,
    "last_clone":    "2026-02-25T18:30:00Z"
  }
}
```

## Status Values

| Status   | Meaning                                                        |
|----------|----------------------------------------------------------------|
| alive    | Operating normally, balance healthy                            |
| degraded | Balance < 48h burn rate, reducing activity                     |
| dying    | Balance < 24h burn rate, shutdown pending, draining to parent  |
| dead     | Instance unreachable for 3+ consecutive cycles                 |

## Health State Machine

```
alive → degraded    (balance drops below 48h burn)
degraded → alive    (revenue restores balance)
degraded → dying    (balance drops below 24h burn)
dying → dead        (balance depleted or timeout)
dead → [removed]    (parent cleans up record)
```

## Parent-Child Monitoring Rules

- Parent polls all children every 30s
- If child status = `"dying"`:
  - Parent may inject emergency funds via `FUND_INJECT` message
  - OR accept death and redistribute load
- If child status = `"dead"`:
  - Remaining funds drain to parent wallet
  - Child removed from active instance list
- If parent dies:
  - Children become independent root nodes
  - Continue operating autonomously with no parent

## Network Health Aggregation

```
GET /api/status?network=true
```

Returns aggregated stats across all known instances in the network:
- Total revenue across all instances
- Total burn rate
- Instance count (alive / degraded / dying)
- Average profit margin
- Replication readiness

## Implementation

See `heartbeat_loop.py` for the standalone heartbeat monitor that polls all known child instances and updates their status.
