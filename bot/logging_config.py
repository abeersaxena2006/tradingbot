"""
Logging configuration for the Binance Futures trading bot.
Sets up structured logging to both file and console.
"""

import logging
import logging.handlers
import os
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

# Log format: timestamp | level | module | message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root logger for the trading bot.

    Sets up:
      - Rotating file handler (logs/trading_bot.log, max 5 MB, 3 backups)
      - Console handler (WARNING and above only, to keep CLI output clean)

    Args:
        log_level: Minimum log level for the file handler (default: INFO).

    Returns:
        Configured root logger.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger("trading_bot")
    root_logger.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # Avoid adding duplicate handlers on repeated calls
    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- File handler (rotating) ---
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # --- Console handler (WARNING+ so CLI stays readable) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    root_logger.info("Logging initialised — file: %s", LOG_FILE)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the trading_bot namespace."""
    return logging.getLogger(f"trading_bot.{name}")
