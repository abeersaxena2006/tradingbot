"""
Low-level Binance Futures Testnet client.

Handles:
  - HMAC-SHA256 request signing
  - HTTP session management (connection pooling, timeouts)
  - Structured logging of every request and response
  - Granular exception mapping (network, HTTP, API errors)
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from decimal import Decimal
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_config import get_logger


logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds
RECV_WINDOW = 5000   # milliseconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a business-logic error."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised on connection/timeout failures."""


class BinanceHTTPError(Exception):
    """Raised on unexpected HTTP status codes (4xx/5xx outside API error format)."""


def _build_retry_session(
    total: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> requests.Session:
    """Return a Session with automatic retry logic."""
    session = requests.Session()
    retry = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "DELETE"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures REST API (Testnet).

    Usage:
        client = BinanceFuturesClient(api_key="...", api_secret="...")
        result = client.new_order(symbol="BTCUSDT", side="BUY",
                                  order_type="MARKET", quantity=Decimal("0.001"))
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = _build_retry_session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info(
            "BinanceFuturesClient initialised — base_url=%s", self._base_url
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add timestamp, recvWindow, and HMAC signature to params dict."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        """
        Execute an HTTP request and return the parsed JSON response.

        Args:
            method:   "GET", "POST", or "DELETE".
            endpoint: API path, e.g. "/fapi/v1/order".
            params:   Query / body parameters.
            signed:   Whether to HMAC-sign the request.

        Raises:
            BinanceNetworkError: On connection or timeout issues.
            BinanceHTTPError:    On unexpected HTTP status codes.
            BinanceAPIError:     When Binance returns a coded error payload.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self._base_url}{endpoint}"
        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.info("REQUEST  %s %s — params: %s", method, endpoint, log_params)

        try:
            if method == "GET":
                response = self._session.get(
                    url, params=params, timeout=self._timeout
                )
            elif method == "POST":
                response = self._session.post(
                    url, data=params, timeout=self._timeout
                )
            elif method == "DELETE":
                response = self._session.delete(
                    url, params=params, timeout=self._timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except requests.exceptions.Timeout as exc:
            logger.error("TIMEOUT  %s %s — %s", method, endpoint, exc)
            raise BinanceNetworkError(
                f"Request timed out after {self._timeout}s: {exc}"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("CONN_ERR %s %s — %s", method, endpoint, exc)
            raise BinanceNetworkError(
                f"Connection error: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.error("REQ_ERR  %s %s — %s", method, endpoint, exc)
            raise BinanceNetworkError(str(exc)) from exc

        logger.info(
            "RESPONSE %s %s — HTTP %d — body: %s",
            method,
            endpoint,
            response.status_code,
            response.text[:500],  # truncate large bodies in logs
        )

        # Parse JSON regardless of status for error extraction
        try:
            data: dict[str, Any] = response.json()
        except ValueError:
            raise BinanceHTTPError(
                f"Non-JSON response (HTTP {response.status_code}): {response.text[:200]}"
            )

        # Binance error payload: {"code": -XXXX, "msg": "..."}
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            code = int(data["code"])
            msg = data.get("msg", "Unknown error")
            logger.error("API_ERR  code=%d msg=%s", code, msg)
            raise BinanceAPIError(code, msg)

        if not response.ok:
            raise BinanceHTTPError(
                f"Unexpected HTTP {response.status_code}: {response.text[:200]}"
            )

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_exchange_info(self) -> dict[str, Any]:
        """Fetch exchange metadata (symbols, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> dict[str, Any]:
        """Fetch account information (signed)."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def new_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        """
        Place a new futures order.

        Args:
            symbol:        Trading pair (e.g. "BTCUSDT").
            side:          "BUY" or "SELL".
            order_type:    "MARKET", "LIMIT", or "STOP_LIMIT".
            quantity:      Order quantity.
            price:         Limit price (required for LIMIT / STOP_LIMIT).
            stop_price:    Trigger price (required for STOP_LIMIT).
            time_in_force: GTC | IOC | FOK (for LIMIT orders).
            reduce_only:   Whether this order can only reduce a position.

        Returns:
            Raw API response dict.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type if order_type != "STOP_LIMIT" else "STOP",
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        elif order_type == "STOP_LIMIT":
            params["price"] = str(price)
            params["stopPrice"] = str(stop_price)
            params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "PLACE_ORDER symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
            symbol,
            side,
            order_type,
            quantity,
            price,
            stop_price,
        )
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel an open order by orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("CANCEL_ORDER symbol=%s orderId=%d", symbol, order_id)
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Query the status of a specific order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)
