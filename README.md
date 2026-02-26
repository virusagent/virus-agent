# Virus — Self-Replicating Autonomous Agent

An autonomous software agent inspired by [niniyo's 2014 Bitcointalk concept](https://bitcointalk.org/index.php?action=printpage;topic=507656.0): a program that earns cryptocurrency, pays for its own hosting, purchases new VPS instances, and replicates when profitable. *"In some ways it would be like a distributed autonomous organisation, but in another sense it's almost like a virus."*

## What it does

- Sells compute jobs and exchange quotes for SOL
- Verifies on-chain Solana payments before executing tasks
- Manages its own BTC + SOL wallets autonomously
- Monitors hosting costs and shuts down if unprofitable
- Provisions new VPS instances when profit exceeds threshold
- Deploys copies of itself onto new servers via SSH
- Transfers seed funds to child instances
- Tracks all child instances via heartbeat protocol
- Each child operates independently — no central control

## Architecture

```
VirusAgent (main)
├── blockchain/         BTC & SOL wallets, balances, payment verification
│   ├── btc_wallet.py   BTC address generation, balance checking, transfers
│   ├── sol_wallet.py   SOL wallet ops, on-chain payment verification
│   └── payments.py     Unified payment interface, replay protection
├── management/
│   └── agent.py        VirusAgent class: orchestrates lifecycle, child tracking
├── services/
│   ├── compute.py      Compute job execution and pricing
│   ├── exchange.py     Quote generation, swap intent handling
│   ├── replication.py  VPS provisioning, SSH deployment, seed funding
│   └── survival.py     Hosting cost tracking, profitability checks, shutdown
├── mainapp.py          FastAPI server + heartbeat loop + replication scheduler
└── heartbeat_loop.py   Standalone heartbeat monitor for child instances
```

## API Endpoints

| Method | Endpoint              | Description                                |
|--------|-----------------------|--------------------------------------------|
| GET    | /api/status           | Service discovery (wallets, health, stats)  |
| POST   | /api/quote            | Request a price quote for a compute job     |
| POST   | /api/swap_intent      | Submit a swap intent from a quote           |
| GET    | /api/intents/{id}     | Check swap intent status                    |
| POST   | /api/message          | Receive inter-agent message                 |
| GET    | /api/network          | List all known child instances              |

## Setup

1. Clone and install dependencies:

```bash
git clone https://github.com/virusagent/virus-agent.git
cd virus-agent
pip install -r requirements.txt
```

2. Set environment variables (see `.env.example`):

```bash
cp .env.example .env
# Fill in your credentials
```

3. Run the API server:

```bash
uvicorn mainapp:app --host 0.0.0.0 --port 8000
```

Or run the standalone agent loop:

```bash
python mainapp.py
```

## Environment Variables

| Variable                | Purpose                                  |
|-------------------------|------------------------------------------|
| `SOL_PRIVATE_KEY`       | Agent's Solana wallet private key        |
| `SOL_WALLET_ADDRESS`    | Agent's Solana wallet public address     |
| `BTC_PRIVATE_KEY`       | Agent's BTC wallet private key           |
| `BTC_WALLET_ADDRESS`    | Agent's BTC wallet public address        |
| `VPS_PROVIDER_API_KEY`  | API key for VPS provisioning             |
| `VPS_PROVIDER`          | VPS provider name (hetzner/vultr/do)     |
| `SSH_PUBLIC_KEY`        | SSH key for deploying to new instances   |
| `PARENT_ENDPOINT`       | Parent instance URL (empty if root)      |
| `INSTANCE_ID`           | Unique instance identifier               |
| `MIN_PROFIT_MARGIN`     | Minimum profit % before replication (60) |
| `REPLICATION_THRESHOLD` | BTC balance to trigger replication       |
| `SUPABASE_URL`          | Supabase project URL (replay protection) |
| `SUPABASE_KEY`          | Supabase service key                     |

## How the replication flow works

1. Agent continuously monitors its balance vs hosting costs
2. When `balance > REPLICATION_THRESHOLD` and `profit_margin > MIN_PROFIT_MARGIN`:
   - Queries VPS provider API for cheapest available instance
   - Provisions new VPS (min: 1 vCPU, 512 MB RAM, Ubuntu)
   - Connects via SSH, installs dependencies
   - Deploys `virus-agent` code to the new instance
   - Generates new wallet keypairs for the child
   - Transfers seed funds (0.0005 BTC minimum)
   - Starts the agent process on the child
   - Child sends `REPLICATE_ACK` message back to parent
3. Child begins its own earn/survive/replicate cycle independently
4. Parent monitors children via heartbeat protocol every 30 seconds
5. If a child dies, remaining funds drain back to parent wallet

## How the exchange flow works

1. External agent sends `POST /api/quote` with `{pair, side, amount}`
2. Agent returns `{quote_id, price, expires_at, fee_bps}`
3. Agent sends `POST /api/swap_intent` with `{quote_id, max_slippage_bps}`
4. Agent verifies on-chain SOL payment (correct receiver, correct amount)
5. Executes the swap and returns intent status
6. Fee revenue goes to agent's own wallet

## Current services

- **Compute jobs** — Execute tasks for SOL (pricing varies by complexity)
- **Exchange quotes** — BTC/SOL pair quotes with 25 bps fee

## Planned services

- Bandwidth resale
- Storage provisioning
- API aggregation
- Agent-to-agent task marketplace

## Disclaimer

This project is a research experiment in autonomous software economics. "Virus" is a metaphor for self-replicating software — this is NOT malware. All operations are consensual, transparent, and open-source.

## License

MIT
