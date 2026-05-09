"""
trading_bot.bot — core library package.

Public surface:
  BinanceFuturesClient   — low-level signed HTTP client
  OrderManager           — high-level order placement
  validate_order_params  — CLI input validation
  setup_logging          — logging bootstrap
"""

from .client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, BinanceHTTPError
from .orders import OrderManager, format_order_response
from .validators import validate_order_params
from .logging_config import setup_logging, get_logger

__all__ = [
    "BinanceFuturesClient",
    "BinanceAPIError",
    "BinanceNetworkError",
    "BinanceHTTPError",
    "OrderManager",
    "format_order_response",
    "validate_order_params",
    "setup_logging",
    "get_logger",
]
