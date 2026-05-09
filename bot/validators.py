"""
Input validation for trading bot CLI arguments.
All validators raise ValueError with a descriptive message on failure.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}


def validate_symbol(symbol: str) -> str:
    """
    Ensure symbol is a non-empty uppercase string (e.g. BTCUSDT).

    Binance symbols are alphanumeric and uppercase; we normalise and do a
    basic sanity check without hard-coding every available pair.
    """
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol must not be empty.")
    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Expected alphanumeric only (e.g. BTCUSDT)."
        )
    if len(symbol) < 3 or len(symbol) > 20:
        raise ValueError(
            f"Symbol '{symbol}' length ({len(symbol)}) is outside the "
            "expected range 3–20 characters."
        )
    return symbol


def validate_side(side: str) -> str:
    """Ensure side is BUY or SELL (case-insensitive)."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Ensure order type is one of the supported types."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """
    Parse and validate order quantity.

    Must be a positive number. Returned as Decimal for precision.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero (got {qty}).")
    return qty


def validate_price(price: str | float | None) -> Optional[Decimal]:
    """
    Parse and validate order price.

    Must be a positive number when provided. Returns None if price is None
    (acceptable for MARKET orders).
    """
    if price is None:
        return None
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero (got {p}).")
    return p


def validate_stop_price(stop_price: str | float | None) -> Optional[Decimal]:
    """Parse and validate stop price for STOP_LIMIT orders."""
    if stop_price is None:
        return None
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero (got {sp}).")
    return sp


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """
    Run all field-level validators and return a clean params dict.

    Also enforces cross-field rules:
      - LIMIT orders require a price.
      - STOP_LIMIT orders require both price and stop_price.
      - MARKET orders must not have a price.

    Returns:
        Dict with keys: symbol, side, order_type, quantity, price, stop_price.
        Numeric values are Decimal instances.
    """
    cleaned = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price),
        "stop_price": validate_stop_price(stop_price),
    }

    ot = cleaned["order_type"]

    if ot == "MARKET":
        if cleaned["price"] is not None:
            raise ValueError("Price must not be provided for MARKET orders.")

    elif ot == "LIMIT":
        if cleaned["price"] is None:
            raise ValueError("Price is required for LIMIT orders.")

    elif ot == "STOP_LIMIT":
        if cleaned["price"] is None:
            raise ValueError("Price (limit price) is required for STOP_LIMIT orders.")
        if cleaned["stop_price"] is None:
            raise ValueError("Stop price is required for STOP_LIMIT orders.")

    return cleaned
