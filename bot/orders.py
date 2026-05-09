"""
High-level order placement logic.

This module sits between the CLI and the raw API client.
It handles:
  - Building validated order requests
  - Calling the client
  - Formatting and returning clean result dicts for the CLI to display
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from .client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from .logging_config import get_logger


logger = get_logger("orders")


def _fmt(value: Any, default: str = "N/A") -> str:
    """Return a human-readable string, falling back to default."""
    if value is None or value == "":
        return default
    return str(value)


def format_order_response(response: dict[str, Any]) -> dict[str, str]:
    """
    Extract the most relevant fields from a raw Binance order response.

    Returns a flat dict suitable for CLI display.
    """
    return {
        "orderId":     _fmt(response.get("orderId")),
        "symbol":      _fmt(response.get("symbol")),
        "side":        _fmt(response.get("side")),
        "type":        _fmt(response.get("type")),
        "status":      _fmt(response.get("status")),
        "origQty":     _fmt(response.get("origQty")),
        "executedQty": _fmt(response.get("executedQty")),
        "avgPrice":    _fmt(response.get("avgPrice")),
        "price":       _fmt(response.get("price")),
        "stopPrice":   _fmt(response.get("stopPrice")),
        "timeInForce": _fmt(response.get("timeInForce")),
        "updateTime":  _fmt(response.get("updateTime")),
    }


class OrderManager:
    """
    Wraps BinanceFuturesClient to provide high-level order operations.

    Each place_* method validates prerequisites, calls the client,
    logs the outcome, and returns a structured result dict:

        {
            "success": bool,
            "order":   dict | None,   # formatted response on success
            "error":   str  | None,   # error message on failure
            "raw":     dict | None,   # full raw API response on success
        }
    """

    def __init__(self, client: BinanceFuturesClient) -> None:
        self._client = client

    def _wrap_call(self, fn, *args, **kwargs) -> dict[str, Any]:
        """Execute a client call and normalise the result."""
        try:
            raw = fn(*args, **kwargs)
            logger.info("Order placed successfully: %s", raw)
            return {
                "success": True,
                "order": format_order_response(raw),
                "error": None,
                "raw": raw,
            }
        except BinanceAPIError as exc:
            logger.error("API error placing order: %s", exc)
            return {"success": False, "order": None, "error": str(exc), "raw": None}
        except BinanceNetworkError as exc:
            logger.error("Network error placing order: %s", exc)
            return {"success": False, "order": None, "error": str(exc), "raw": None}
        except Exception as exc:
            logger.exception("Unexpected error placing order: %s", exc)
            return {
                "success": False,
                "order": None,
                "error": f"Unexpected error: {exc}",
                "raw": None,
            }

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        """Place a MARKET order."""
        logger.info(
            "Placing MARKET order: %s %s qty=%s", side, symbol, quantity
        )
        return self._wrap_call(
            self._client.new_order,
            symbol=symbol,
            side=side,
            order_type="MARKET",
            quantity=quantity,
            reduce_only=reduce_only,
        )

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        """Place a LIMIT order."""
        logger.info(
            "Placing LIMIT order: %s %s qty=%s price=%s tif=%s",
            side, symbol, quantity, price, time_in_force,
        )
        return self._wrap_call(
            self._client.new_order,
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        stop_price: Decimal,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        """Place a STOP_LIMIT (Stop) order."""
        logger.info(
            "Placing STOP_LIMIT order: %s %s qty=%s price=%s stopPrice=%s",
            side, symbol, quantity, price, stop_price,
        )
        return self._wrap_call(
            self._client.new_order,
            symbol=symbol,
            side=side,
            order_type="STOP_LIMIT",
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )
