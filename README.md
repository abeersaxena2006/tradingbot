# Binance Futures Testnet — Trading Bot

A clean, production-quality Python CLI application for placing orders on **Binance USDT-M Futures Testnet**.

---

## Features

| Feature | Details |
|---|---|
| Order types | MARKET, LIMIT, STOP_LIMIT (bonus) |
| Sides | BUY and SELL |
| Validation | Full input validation with descriptive error messages |
| Logging | Rotating file logs of every request, response, and error |
| Structure | Layered architecture: client → orders → CLI |
| Error handling | API errors, network failures, invalid inputs |
| Dry-run mode | Preview the request without sending |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Low-level HMAC-signed REST client
│   ├── orders.py            # High-level order placement logic
│   ├── validators.py        # Input validation (all fields)
│   └── logging_config.py   # Rotating file + console logging setup
├── cli.py                   # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Get Testnet Credentials

1. Visit [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Go to **API Key** → generate a key pair
4. Copy both the **API Key** and **Secret**

### 2. Install Dependencies

```bash
# Python 3.8+ required
pip install -r requirements.txt
```

### 3. Configure Credentials

**Option A — Environment variables (recommended)**
```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

**Option B — Pass directly as flags**
```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET ...
```

---

## How to Run

### Market Order

```bash
# Market BUY — 0.001 BTC
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001

# Market SELL — 0.01 ETH
python cli.py \
  --symbol ETHUSDT \
  --side SELL \
  --type MARKET \
  --quantity 0.01
```

### Limit Order

```bash
# Limit SELL — 0.001 BTC at $64,000
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 64000

# Limit BUY — IOC time-in-force
python cli.py \
  --symbol ETHUSDT \
  --side BUY \
  --type LIMIT \
  --quantity 0.05 \
  --price 2900 \
  --tif IOC
```

### Stop-Limit Order (Bonus)

```bash
# Stop-Limit BUY — triggers at $64,500, fills at $65,000
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type STOP_LIMIT \
  --quantity 0.001 \
  --price 65000 \
  --stop-price 64500
```

### Dry-Run (no order sent)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001 \
  --dry-run
```

### Print Raw API Response

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001 \
  --raw
```

### Verbose Logging (DEBUG)

```bash
python cli.py ... --log-level DEBUG
```

---

## CLI Reference

```
usage: trading_bot [-h] [--api-key KEY] [--api-secret SECRET]
                   --symbol SYMBOL --side SIDE --type TYPE
                   --quantity QTY [--price PRICE]
                   [--stop-price STOP_PRICE] [--tif TIF]
                   [--reduce-only] [--log-level {DEBUG,INFO,WARNING,ERROR}]
                   [--raw] [--dry-run]

Order parameters:
  --symbol SYMBOL         Trading pair, e.g. BTCUSDT
  --side SIDE             BUY or SELL
  --type TYPE             MARKET | LIMIT | STOP_LIMIT
  --quantity QTY          Order quantity (e.g. 0.001)
  --price PRICE           Limit price (required for LIMIT / STOP_LIMIT)
  --stop-price STOP_PRICE Stop/trigger price (required for STOP_LIMIT)
  --tif TIF               Time-in-force: GTC (default) | IOC | FOK

Misc:
  --reduce-only           Mark as reduce-only order
  --log-level             Log verbosity for file (default: INFO)
  --raw                   Print raw API response JSON
  --dry-run               Validate and preview without sending
```

---

## Sample Output

```
  ╔══════════════════════════════════════════════╗
  ║   Binance Futures Testnet — Trading Bot      ║
  ╚══════════════════════════════════════════════╝

  Order Request
  ────────────────────────────────────────────────────
  Symbol:           BTCUSDT
  Side:             BUY
  Type:             MARKET
  Quantity:         0.001
  Price:            —
  Stop Price:       —
  ────────────────────────────────────────────────────

  ✓  Order placed successfully
  ────────────────────────────────────────────────────
  Order ID:         4046228312
  Symbol:           BTCUSDT
  Side:             BUY
  Type:             MARKET
  Status:           FILLED
  Orig Qty:         0.001
  Executed Qty:     0.001
  Avg Price:        62345.10
  Limit Price:      0
  Stop Price:       0
  Time-in-Force:    GTC
  Update Time:      1746778443012
  ────────────────────────────────────────────────────
```

---

## Logging

Logs are written to `logs/trading_bot.log` (auto-created). The file rotates at 5 MB, keeping 3 backups.

**Log format:**
```
2025-05-09 10:14:02 | INFO     | trading_bot.client | REQUEST  POST /fapi/v1/order — params: {...}
2025-05-09 10:14:03 | INFO     | trading_bot.client | RESPONSE POST /fapi/v1/order — HTTP 200 — body: {...}
2025-05-09 10:14:03 | INFO     | trading_bot.orders | Order placed successfully: {...}
```

The console only shows `WARNING` and above to keep CLI output clean.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API credentials | Immediate exit with clear message |
| Invalid symbol / quantity / price | Validation error before any network call |
| Missing price for LIMIT order | Validation error |
| Binance API error (e.g. insufficient margin) | Error code + message printed; logged |
| Network timeout / connection failure | Descriptive error; retried up to 3× automatically |
| Non-JSON response | `BinanceHTTPError` raised and logged |

---

## Architecture

```
cli.py
  │  argparse + display
  ▼
bot/validators.py
  │  validate all fields; raise ValueError on failure
  ▼
bot/orders.py  (OrderManager)
  │  high-level place_market/limit/stop_limit_order()
  ▼
bot/client.py  (BinanceFuturesClient)
  │  HMAC signing, HTTP session, retry, error mapping
  ▼
Binance Futures Testnet REST API
```

---

## Assumptions

- Only **USDT-M** (linear) futures are targeted; the base URL is hard-coded to `https://testnet.binancefuture.com`.
- The bot does **not** maintain open positions or manage risk; it is a pure order-placement tool.
- Quantity precision must match the symbol's lot size rules on the testnet. If you receive a `-1111` filter error, adjust the quantity to the correct step size for your symbol.
- `STOP_LIMIT` maps to Binance's `STOP` order type (limit order triggered by a stop price), which is available on USDT-M Futures.

---

## Requirements

```
requests>=2.31.0
urllib3>=2.0.0
```

Python **3.8+** required (uses `from __future__ import annotations`).
"# tradingbot" 
"# tradingbot" 
