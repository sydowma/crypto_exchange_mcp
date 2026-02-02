"""Bybit exchange client."""

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import requests

from core.base import (
    Balance,
    Kline,
    Order,
    OrderBook,
    OrderBookLevel,
    OrderResult,
    Position,
    Ticker,
    BaseExchange,
)
from core.config import Config
from core.exceptions import (
    AuthenticationError,
    ExchangeError,
    InvalidSymbolError,
    OrderError,
    RateLimitError,
)


class BybitExchange(BaseExchange):
    """Bybit exchange implementation.

    API docs: https://bybit-exchange.github.io/docs/v5/
    """

    # API endpoints
    API_BASE_URL = "https://api.bybit.com"  # Production
    API_TESTNET_URL = "https://api-testnet.bybit.com"  # Testnet

    # Categories
    CATEGORY_SPOT = "spot"
    CATEGORY_LINEAR = "linear"
    CATEGORY_INVERSE = "inverse"
    CATEGORY_OPTION = "option"

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        testnet: bool = False,
    ):
        """Initialize Bybit exchange.

        Args:
            api_key: API key for private endpoints
            api_secret: API secret for private endpoints
            testnet: Use testnet instead of production
        """
        super().__init__(api_key, api_secret)

        # If credentials not provided, try to load from config
        if not api_key and not api_secret:
            creds = Config().get_credentials("bybit")
            if creds:
                self.api_key = creds.api_key
                self.api_secret = creds.api_secret
                self._authenticated = True

        self.base_url = self.API_TESTNET_URL if testnet else self.API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-BAPI-API-KEY": self.api_key or "",
        })

    # ===== HTTP Methods =====

    def _generate_signature(self, timestamp: str, params: str, recv_window: str = "5000") -> str:
        """Generate signature for private API requests."""
        if not self.api_secret:
            raise AuthenticationError("API secret is required for private endpoints")

        sign_str = timestamp + self.api_key + recv_window + params
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        signed: bool = False,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to Bybit API.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request needs signature
            category: Category for the request (spot, linear, etc.)

        Returns:
            Response data

        Raises:
            ExchangeError: On API errors
        """
        url = f"{self.base_url}{endpoint}"

        # Build query string or body
        if params is None:
            params = {}

        # Add category if specified
        if category and category not in params:
            params["category"] = category

        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"

        if signed:
            self.require_auth()
            params_str = urlencode(sorted(params.items()))
            signature = self._generate_signature(timestamp, params_str, recv_window)
            headers = self.session.headers.copy()
            headers.update({
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window,
                "X-BAPI-SIGN": signature,
            })
        else:
            headers = self.session.headers.copy()
            if not self.api_key:
                headers.pop("X-BAPI-API-KEY", None)

        try:
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=params, headers=headers, timeout=10)
            elif method == "DELETE":
                response = self.session.delete(url, json=params, headers=headers, timeout=10)
            else:
                raise ExchangeError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if data.get("retCode") != 0:
                error_msg = data.get("retMsg", "Unknown error")
                error_code = data.get("retCode")

                # Handle specific errors
                if error_code in (10001, 10003, 10004, 10005):
                    raise AuthenticationError(error_msg, error_code, data)
                elif error_code in (10006, 10011, 10012, 10013):
                    raise RateLimitError(error_msg, error_code, data)
                elif error_code in (10014, 10015, 10016, 10017, 10018):
                    raise InvalidSymbolError(error_msg, error_code, data)
                else:
                    raise ExchangeError(error_msg, error_code, data)

            return data.get("result", {})

        except requests.RequestException as e:
            raise ExchangeError(f"Network error: {e}") from e

    def _get(self, endpoint: str, params: dict | None = None, **kwargs) -> dict:
        """Make GET request."""
        return self._request("GET", endpoint, params, **kwargs)

    def _post(self, endpoint: str, params: dict | None = None, **kwargs) -> dict:
        """Make POST request."""
        return self._request("POST", endpoint, params, **kwargs)

    def _delete(self, endpoint: str, params: dict | None = None, **kwargs) -> dict:
        """Make DELETE request."""
        return self._request("DELETE", endpoint, params, **kwargs)

    # ===== Public API =====

    def get_ticker(self, symbol: str, category: str = CATEGORY_SPOT) -> Ticker:
        """Get ticker for a symbol.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            category: Category (spot, linear, inverse, option)

        Returns:
            Ticker data
        """
        result = self._get("/v5/market/tickers", {"category": category, "symbol": symbol})

        if not result.get("list"):
            raise InvalidSymbolError(f"Symbol not found: {symbol}")

        data = result["list"][0]

        return Ticker(
            symbol=data.get("symbol", symbol),
            last_price=Decimal(data.get("lastPrice", "0")),
            price_change_24h=Decimal(data.get("price24hPcnt", "0")),
            price_change_pct_24h=Decimal(data.get("price24hPcnt", "0")) * 100,
            volume_24h=Decimal(data.get("volume24h", "0")),
            high_24h=Decimal(data.get("highPrice24h", "0")),
            low_24h=Decimal(data.get("lowPrice24h", "0")),
            timestamp=int(data.get("time", 0)),
        )

    def get_order_book(
        self, symbol: str, limit: int = 20, category: str = CATEGORY_SPOT
    ) -> OrderBook:
        """Get order book for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of levels to return (max 500)
            category: Category (spot, linear, inverse, option)

        Returns:
            Order book data
        """
        result = self._get("/v5/market/orderbook", {
            "category": category,
            "symbol": symbol,
            "limit": min(limit, 500),
        })

        bids = [
            OrderBookLevel(price=Decimal(b[0]), size=Decimal(b[1]))
            for b in result.get("b", [])[:limit]
        ]
        asks = [
            OrderBookLevel(price=Decimal(a[0]), size=Decimal(a[1]))
            for a in result.get("a", [])[:limit]
        ]

        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=int(result.get("ts", 0)),
        )

    def _normalize_interval(self, interval: str) -> str:
        """Normalize interval string for Bybit API.

        Bybit interval format: 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M
        """
        # Map common formats to Bybit format
        interval_map = {
            "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
            "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
            "1d": "D", "3d": "3D", "1w": "W", "1M": "M",
        }
        return interval_map.get(interval, interval)

    def get_klines(
        self,
        symbol: str,
        interval: str = "60",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
        category: str = CATEGORY_SPOT,
    ) -> list[Kline]:
        """Get klines/candlesticks for a symbol.

        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, etc.)
            limit: Number of klines to return (max 1000)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
            category: Category (spot, linear, inverse, option)

        Returns:
            List of kline data
        """
        bybit_interval = self._normalize_interval(interval)
        params = {
            "category": category,
            "symbol": symbol,
            "interval": bybit_interval,
            "limit": min(limit, 1000),
        }

        if start_time:
            params["start"] = start_time
        if end_time:
            params["end"] = end_time

        result = self._get("/v5/market/kline", params)

        klines = []
        for item in result.get("list", []):
            # Bybit returns: [startTime, open, high, low, close, volume, quoteVolume]
            # Data is in reverse chronological order
            klines.append(Kline(
                symbol=symbol,
                open_time=int(item[0]),
                open=Decimal(item[1]),
                high=Decimal(item[2]),
                low=Decimal(item[3]),
                close=Decimal(item[4]),
                volume=Decimal(item[5]),
                close_time=None,  # Bybit doesn't provide close time in klines
                quote_volume=Decimal(item[6]) if len(item) > 6 else None,
            ))

        # Reverse to get chronological order
        return list(reversed(klines))

    def get_symbols(self, spot: bool = True, futures: bool = False) -> list[str]:
        """Get list of trading symbols.

        Args:
            spot: Include spot trading pairs
            futures: Include futures trading pairs

        Returns:
            List of trading symbols
        """
        symbols = []

        if spot:
            result = self._get("/v5/market/tickers", {"category": self.CATEGORY_SPOT})
            symbols.extend([item["symbol"] for item in result.get("list", [])])

        if futures:
            result = self._get("/v5/market/tickers", {"category": self.CATEGORY_LINEAR})
            symbols.extend([item["symbol"] for item in result.get("list", [])])

        return symbols

    def get_funding_rate(self, symbol: str) -> dict[str, Any]:
        """Get funding rate for a symbol.

        Args:
            symbol: Trading symbol (linear contract)

        Returns:
            Funding rate data
        """
        result = self._get("/v5/market/tickers", {
            "category": self.CATEGORY_LINEAR,
            "symbol": symbol,
        })

        if not result.get("list"):
            raise InvalidSymbolError(f"Symbol not found: {symbol}")

        data = result["list"][0]

        return {
            "symbol": symbol,
            "funding_rate": Decimal(data.get("fundingRate", "0")),
            "funding_rate_pct": Decimal(data.get("fundingRate", "0")) * 100,
            "next_funding_time": int(data.get("nextFundingTime", 0)),
            "predicted_funding_rate": Decimal(data.get("predictedFundingRate", "0")),
            "timestamp": int(data.get("time", 0)),
        }

    def get_open_interest(
        self,
        symbol: str,
        interval: str = "1d",
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> dict[str, Any]:
        """Get open interest for a symbol.

        Args:
            symbol: Trading symbol (linear contract)
            interval: Interval (1d, 1h)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            Open interest data
        """
        params = {
            "category": self.CATEGORY_LINEAR,
            "symbol": symbol,
            "intervalTime": interval,
            "limit": 1,
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        result = self._get("/v5/market/open-interest", params)

        if not result.get("list"):
            return {"symbol": symbol, "open_interest": Decimal("0"), "timestamp": 0}

        data = result["list"][0]

        return {
            "symbol": symbol,
            "open_interest": Decimal(data.get("openInterest", "0")),
            "timestamp": int(data.get("timestamp", 0)),
        }

    # ===== Private API =====

    def get_wallet_balance(self, account_type: str = "UNIFIED") -> dict[str, Any]:
        """Get wallet balance.

        Args:
            account_type: Account type (UNIFIED, CONTRACT, SPOT, etc.)

        Returns:
            Wallet balance data
        """
        result = self._post("/v5/account/wallet-balance", {
            "accountType": account_type,
        }, signed=True)

        if not result.get("list"):
            return {"balances": []}

        account = result["list"][0]
        balances = []

        for item in account.get("coin", []):
            balances.append({
                "asset": item.get("coin", ""),
                "free": Decimal(item.get("walletBalance", "0")),
                "locked": Decimal(item.get("locked", "0")),
                "total": Decimal(item.get("walletBalance", "0")),
            })

        return {
            "account_type": account_type,
            "balances": balances,
            "total_equity": Decimal(account.get("totalEquity", "0")),
        }

    def get_balance(self) -> dict[str, Balance]:
        """Get account balances.

        Returns:
            Dictionary of asset to Balance
        """
        result = self.get_wallet_balance()
        balances = {}

        for item in result.get("balances", []):
            asset = item["asset"]
            if item["total"] > 0:  # Only include non-zero balances
                balances[asset] = Balance(
                    asset=asset,
                    free=item["free"],
                    locked=item["locked"],
                    total=item["total"],
                )

        return balances

    def get_positions(self, category: str = CATEGORY_LINEAR) -> list[Position]:
        """Get current positions.

        Args:
            category: Category (linear, inverse, option)

        Returns:
            List of positions
        """
        result = self._get("/v5/position/list", {
            "category": category,
        }, signed=True)

        positions = []
        for item in result.get("list", []):
            size = Decimal(item.get("size", "0"))
            if size == 0:
                continue  # Skip closed positions

            side = "long" if item.get("side") == "Buy" else "short"

            positions.append(Position(
                symbol=item.get("symbol", ""),
                side=side,
                size=size,
                entry_price=Decimal(item.get("avgPrice", "0")),
                mark_price=Decimal(item.get("markPrice", "0")),
                unrealized_pnl=Decimal(item.get("unrealisedPnl", "0")),
                leverage=int(item.get("leverage", "1").replace("x", "")),
            ))

        return positions

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        category: str = CATEGORY_SPOT,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        **kwargs,
    ) -> OrderResult:
        """Place an order.

        Args:
            symbol: Trading symbol
            side: Order side (buy or sell)
            order_type: Order type (market, limit)
            quantity: Order quantity
            price: Limit price (required for limit orders)
            category: Category (spot, linear, inverse, option)
            time_in_force: Time in force (GTC, IOC, FOK, PostOnly)
            reduce_only: Reduce position size only (for futures)
            **kwargs: Additional parameters

        Returns:
            Order result
        """
        side = side.upper()
        order_type = order_type.upper()

        if order_type == "LIMIT" and price is None:
            raise OrderError("Price is required for limit orders")

        params = {
            "category": category,
            "symbol": symbol,
            "side": side.capitalize(),
            "orderType": order_type.capitalize(),
            "qty": str(quantity),
        }

        if price is not None:
            params["price"] = str(price)

        if order_type.upper() == "LIMIT":
            params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = True

        # Add additional parameters
        params.update(kwargs)

        result = self._post("/v5/order/create", params, signed=True)

        if not result.get("list"):
            raise OrderError("Failed to place order")

        order_data = result["list"][0]

        return OrderResult(
            order_id=order_data.get("orderId", ""),
            symbol=symbol,
            side=side.lower(),
            order_type=order_type.lower(),
            quantity=quantity,
            price=price,
            status=order_data.get("orderStatus"),
            client_order_id=order_data.get("orderLinkId"),
        )

    def cancel_order(
        self,
        symbol: str,
        order_id: str,
        category: str = CATEGORY_SPOT,
    ) -> bool:
        """Cancel an order.

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel
            category: Category (spot, linear, inverse, option)

        Returns:
            True if successful
        """
        result = self._post("/v5/order/cancel", {
            "category": category,
            "symbol": symbol,
            "orderId": order_id,
        }, signed=True)

        return result.get("retCode") == 0

    def cancel_all_orders(
        self,
        symbol: str,
        category: str = CATEGORY_SPOT,
    ) -> int:
        """Cancel all orders for a symbol.

        Args:
            symbol: Trading symbol
            category: Category (spot, linear, inverse, option)

        Returns:
            Number of orders canceled
        """
        result = self._post("/v5/order/cancel-all", {
            "category": category,
            "symbol": symbol,
        }, signed=True)

        # Try to get the count from the response
        # Note: Bybit doesn't always return the count
        return 0 if result.get("retCode") != 0 else 1

    def get_open_orders(
        self,
        symbol: str | None = None,
        category: str = CATEGORY_SPOT,
    ) -> list[Order]:
        """Get open orders.

        Args:
            symbol: Trading symbol (None for all symbols)
            category: Category (spot, linear, inverse, option)

        Returns:
            List of open orders
        """
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol

        result = self._get("/v5/order/realtime", params, signed=True)

        orders = []
        for item in result.get("list", []):
            side = item.get("side", "").lower()
            order_type = item.get("orderType", "").lower()

            orders.append(Order(
                order_id=item.get("orderId", ""),
                symbol=item.get("symbol", ""),
                side=side,
                order_type=order_type,
                quantity=Decimal(item.get("qty", "0")),
                price=Decimal(item.get("price", "0")) if item.get("price") else None,
                filled_quantity=Decimal(item.get("cummExecQty", "0")),
                status=item.get("orderStatus", "").lower(),
                timestamp=int(item.get("createdTime", 0)),
            ))

        return orders

    def get_order_history(
        self,
        symbol: str | None = None,
        category: str = CATEGORY_SPOT,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Order]:
        """Get order history.

        Args:
            symbol: Trading symbol (None for all symbols)
            category: Category (spot, linear, inverse, option)
            limit: Number of orders to return (max 200)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of historical orders
        """
        params = {
            "category": category,
            "limit": min(limit, 200),
        }

        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        result = self._get("/v5/order/history", params, signed=True)

        orders = []
        for item in result.get("list", []):
            side = item.get("side", "").lower()
            order_type = item.get("orderType", "").lower()

            orders.append(Order(
                order_id=item.get("orderId", ""),
                symbol=item.get("symbol", ""),
                side=side,
                order_type=order_type,
                quantity=Decimal(item.get("qty", "0")),
                price=Decimal(item.get("price", "0")) if item.get("price") else None,
                filled_quantity=Decimal(item.get("cummExecQty", "0")),
                status=item.get("orderStatus", "").lower(),
                timestamp=int(item.get("createdTime", 0)),
            ))

        return orders
