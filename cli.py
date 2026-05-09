#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Trading Bot.

Usage examples
--------------
# Market BUY
python cli.py --api-key KEY --api-secret SECRET \
    --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py --api-key KEY --api-secret SECRET \
    --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3200

# Stop-Limit BUY (bonus order type)
python cli.py --api-key KEY --api-secret SECRET \
    --symbol BTCUSDT --side BUY --type STOP_LIMIT \
    --quantity 0.001 --price 65000 --stop-price 64500

# Use env vars instead of flags (recommended)
export BINANCE_API_KEY=your_key
export BINANCE_API_SECRET=your_secret
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap

from bot import (
    BinanceFuturesClient,
    OrderManager,
    setup_logging,
    validate_order_params,
    BinanceAPIError,
    BinanceNetworkError,
)


# ──────────────────────────────────────────────
# ANSI colours (gracefully degrade on Windows)
# ──────────────────────────────────────────────
_ANSI = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _ANSI else text


def green(t):   return _c("32", t)
def red(t):     return _c("31", t)
def yellow(t):  return _c("33", t)
def cyan(t):    return _c("36", t)
def bold(t):    return _c("1",  t)
def dim(t):     return _c("2",  t)


# ──────────────────────────────────────────────
# Display helpers
# ──────────────────────────────────────────────

_SEP = "─" * 52


def print_header() -> None:
    print()
    print(bold(cyan("  ╔══════════════════════════════════════════════╗")))
    print(bold(cyan("  ║   Binance Futures Testnet — Trading Bot      ║")))
    print(bold(cyan("  ╚══════════════════════════════════════════════╝")))
    print()


def print_request_summary(params: dict) -> None:
    print(bold("  Order Request"))
    print(f"  {dim(_SEP)}")
    rows = [
        ("Symbol",      params["symbol"]),
        ("Side",        params["side"]),
        ("Type",        params["order_type"]),
        ("Quantity",    str(params["quantity"])),
        ("Price",       str(params["price"]) if params["price"] else "—"),
        ("Stop Price",  str(params["stop_price"]) if params["stop_price"] else "—"),
    ]
    for label, value in rows:
        print(f"  {dim(label + ':'): <18}{value}")
    print(f"  {dim(_SEP)}")
    print()


def print_order_result(result: dict) -> None:
    if not result["success"]:
        print(red(f"  ✗  Order FAILED"))
        print(f"  {dim('Error:')} {result['error']}")
        print()
        return

    order = result["order"]
    status = order["status"]
    status_colour = green if status == "FILLED" else yellow

    print(bold(green("  ✓  Order placed successfully")))
    print(f"  {dim(_SEP)}")

    rows = [
        ("Order ID",      order["orderId"]),
        ("Symbol",        order["symbol"]),
        ("Side",          order["side"]),
        ("Type",          order["type"]),
        ("Status",        status_colour(status)),
        ("Orig Qty",      order["origQty"]),
        ("Executed Qty",  order["executedQty"]),
        ("Avg Price",     order["avgPrice"]),
        ("Limit Price",   order["price"]),
        ("Stop Price",    order["stopPrice"]),
        ("Time-in-Force", order["timeInForce"]),
        ("Update Time",   order["updateTime"]),
    ]
    for label, value in rows:
        print(f"  {dim(label + ':'): <18}{value}")
    print(f"  {dim(_SEP)}")
    print()


def print_raw_json(raw: dict) -> None:
    print(dim("  ── Raw API Response ──────────────────────────────"))
    print(dim(textwrap.indent(json.dumps(raw, indent=2), "  ")))
    print()


# ──────────────────────────────────────────────
# Argument parsing
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place orders on Binance Futures Testnet (USDT-M).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Environment variables (alternatives to flags):
              BINANCE_API_KEY       Your testnet API key
              BINANCE_API_SECRET    Your testnet API secret

            Examples:
              # Market buy
              python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

              # Limit sell
              python cli.py --symbol ETHUSDT --side SELL --type LIMIT \\
                            --quantity 0.01 --price 3200

              # Stop-Limit buy
              python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT \\
                            --quantity 0.001 --price 65000 --stop-price 64500
            """
        ),
    )

    # ── Credentials ──
    creds = parser.add_argument_group("credentials")
    creds.add_argument(
        "--api-key",
        default=os.environ.get("BINANCE_API_KEY", ""),
        metavar="KEY",
        help="Binance API key (or set BINANCE_API_KEY env var).",
    )
    creds.add_argument(
        "--api-secret",
        default=os.environ.get("BINANCE_API_SECRET", ""),
        metavar="SECRET",
        help="Binance API secret (or set BINANCE_API_SECRET env var).",
    )

    # ── Order params ──
    order = parser.add_argument_group("order parameters")
    order.add_argument(
        "--symbol", required=True, metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT.",
    )
    order.add_argument(
        "--side", required=True, choices=["BUY", "SELL"], metavar="SIDE",
        help="Order side: BUY or SELL.",
    )
    order.add_argument(
        "--type", required=True, dest="order_type",
        choices=["MARKET", "LIMIT", "STOP_LIMIT"], metavar="TYPE",
        help="Order type: MARKET, LIMIT, or STOP_LIMIT.",
    )
    order.add_argument(
        "--quantity", required=True, metavar="QTY",
        help="Order quantity (e.g. 0.001).",
    )
    order.add_argument(
        "--price", default=None, metavar="PRICE",
        help="Limit price (required for LIMIT / STOP_LIMIT).",
    )
    order.add_argument(
        "--stop-price", default=None, dest="stop_price", metavar="STOP_PRICE",
        help="Stop/trigger price (required for STOP_LIMIT).",
    )
    order.add_argument(
        "--tif", default="GTC", dest="time_in_force",
        choices=["GTC", "IOC", "FOK"], metavar="TIF",
        help="Time-in-force for LIMIT orders: GTC (default), IOC, FOK.",
    )
    order.add_argument(
        "--reduce-only", action="store_true",
        help="Mark order as reduce-only.",
    )

    # ── Misc ──
    misc = parser.add_argument_group("misc")
    misc.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity for the log file (default: INFO).",
    )
    misc.add_argument(
        "--raw", action="store_true",
        help="Print the full raw API response JSON.",
    )
    misc.add_argument(
        "--dry-run", action="store_true",
        help="Validate inputs and show the request summary without sending.",
    )

    return parser


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main() -> int:  # returns exit code
    parser = build_parser()
    args = parser.parse_args()

    # Bootstrap logging first
    setup_logging(log_level=args.log_level)

    print_header()

    # ── Validate credentials ──
    if not args.api_key or not args.api_secret:
        print(red("  ✗  API key / secret missing."))
        print(
            "     Pass --api-key / --api-secret or set "
            "BINANCE_API_KEY / BINANCE_API_SECRET."
        )
        print()
        return 1

    # ── Validate order parameters ──
    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(red(f"  ✗  Validation error: {exc}"))
        print()
        return 1

    print_request_summary(params)

    if args.dry_run:
        print(yellow("  ⚠  Dry-run mode — no order submitted."))
        print()
        return 0

    # ── Place order ──
    try:
        client = BinanceFuturesClient(
            api_key=args.api_key,
            api_secret=args.api_secret,
        )
    except ValueError as exc:
        print(red(f"  ✗  Client initialisation error: {exc}"))
        print()
        return 1

    manager = OrderManager(client)

    ot = params["order_type"]
    if ot == "MARKET":
        result = manager.place_market_order(
            symbol=params["symbol"],
            side=params["side"],
            quantity=params["quantity"],
            reduce_only=args.reduce_only,
        )
    elif ot == "LIMIT":
        result = manager.place_limit_order(
            symbol=params["symbol"],
            side=params["side"],
            quantity=params["quantity"],
            price=params["price"],
            time_in_force=args.time_in_force,
            reduce_only=args.reduce_only,
        )
    elif ot == "STOP_LIMIT":
        result = manager.place_stop_limit_order(
            symbol=params["symbol"],
            side=params["side"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
            time_in_force=args.time_in_force,
            reduce_only=args.reduce_only,
        )
    else:
        print(red(f"  ✗  Unhandled order type: {ot}"))
        return 1

    print_order_result(result)

    if args.raw and result["raw"]:
        print_raw_json(result["raw"])

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
