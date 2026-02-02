"""Binance exchange client."""

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


class BinanceExchange(BaseExchange):
    """Binance exchange implementation.

    API docs: https://binance-docs.github.io/apidocs/
    """

    # API endpoints
    API_BASE_URL = "https://api.binance.com"  # Spot
    API_FUTURES_URL = "https://fapi.binance.com"  # USD-M Futures
    API_TESTNET_URL = "https://testnet.binance.vision"  # Testnet
    API_FUTURES_TESTNET_URL = "https://testnet.binancefuture.com"  # Futures Testnet

    # Kline intervals
    INTERVALS = [
        "1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h",
        "1d", "3d", "1w", "1M",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        testnet: bool = False,
    ):
        """Initialize Binance exchange.

        Args:
            api_key: API key for private endpoints
            api_secret: API secret for private endpoints
            testnet: Use testnet instead of production
        """
        super().__init__(api_key, api_secret)

        # If credentials not provided, try to load from config
        if not api_key and not api_secret:
            creds = Config().get_credentials("binance")
            if creds:
                self.api_key = creds.api_key
                self.api_secret = creds.api_secret
                self._authenticated = True

        if testnet:
            self.spot_url = self.API_TESTNET_URL
            self.futures_url = self.API_FUTURES_TESTNET_URL
        else:
            self.spot_url = self.API_BASE_URL
            self.futures_url = self.API_FUTURES_URL

        self.session = requests.Session()

    # ===== HTTP Methods =====

    def _generate_signature(self, params: dict) -> str:
        """Generate signature for private API requests."""
        if not self.api_secret:
            raise AuthenticationError("API secret is required for private endpoints")

        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        signed: bool = False,
        futures: bool = False,
    ) -> dict[str, Any]:
        """Make HTTP request to Binance API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request needs signature
            futures: Use futures API endpoint

        Returns:
            Response data

        Raises:
            ExchangeError: On API errors
        """
        base_url = self.futures_url if futures else self.spot_url
        url = f"{base_url}{endpoint}"

        if params is None:
            params = {}

        headers = {}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        # Add timestamp for signed requests
        if signed:
            self.require_auth()
            params["timestamp"] = int(time.time() * 1000)

        # Build query string
        if signed:
            params["signature"] = self._generate_signature(params)

        if params:
            url = f"{url}?{urlencode(params)}"

        try:
            response = self.session.request(method, url, headers=headers, timeout=10)

            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if isinstance(data, dict) and data.get("-code") not in (None, 0):
                error_msg = data.get("-msg") or data.get("msg", "Unknown error")
                error_code = data.get("-code") or data.get("code")

                # Handle specific errors
                if error_code in (-1000, -1001, -1002, -1003, -1006, -1007, -1021):
                    raise ExchangeError(error_msg, error_code, data)
                elif error_code == -2014:
                    raise AuthenticationError(error_msg, error_code, data)
                elif error_code == -1021:
                    raise AuthenticationError("Timestamp for this request is outside of the recvWindow", error_code, data)
                elif error_code in (-1003, -1015, -1016, -1022, -1023):
                    raise RateLimitError(error_msg, error_code, data)
                elif error_code == -1121:
                    raise InvalidSymbolError(error_msg, error_code, data)
                else:
                    raise ExchangeError(error_msg, error_code, data)

            return data

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

    def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker for a symbol.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)

        Returns:
            Ticker data
        """
        result = self._get("/api/v3/ticker/24hr", {"symbol": symbol})

        return Ticker(
            symbol=result.get("symbol", symbol),
            last_price=Decimal(result.get("lastPrice", "0")),
            price_change_24h=Decimal(result.get("priceChange", "0")),
            price_change_pct_24h=Decimal(result.get("priceChangePercent", "0")),
            volume_24h=Decimal(result.get("volume", "0")),
            high_24h=Decimal(result.get("highPrice", "0")),
            low_24h=Decimal(result.get("lowPrice", "0")),
            timestamp=int(result.get("closeTime", 0)),
        )

    def get_order_book(
        self,
        symbol: str,
        limit: int = 20,
    ) -> OrderBook:
        """Get order book for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of levels to return (max 5000)

        Returns:
            Order book data
        """
        result = self._get("/api/v3/depth", {
            "symbol": symbol,
            "limit": min(limit, 5000),
        })

        bids = [
            OrderBookLevel(price=Decimal(b[0]), size=Decimal(b[1]))
            for b in result.get("bids", [])[:limit]
        ]
        asks = [
            OrderBookLevel(price=Decimal(a[0]), size=Decimal(a[1]))
            for a in result.get("asks", [])[:limit]
        ]

        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
        )

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Kline]:
        """Get klines/candlesticks for a symbol.

        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h,
                       12h, 1d, 3d, 1w, 1M)
            limit: Number of klines to return (max 1000)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of kline data
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        result = self._get("/api/v3/klines", params)

        klines = []
        for item in result:
            klines.append(Kline(
                symbol=symbol,
                open_time=int(item[0]),
                open=Decimal(item[1]),
                high=Decimal(item[2]),
                low=Decimal(item[3]),
                close=Decimal(item[4]),
                volume=Decimal(item[5]),
                close_time=int(item[6]),
                quote_volume=Decimal(item[7]),
            ))

        return klines

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
            result = self._get("/api/v3/exchangeInfo")
            symbols.extend([
                s["symbol"]
                for s in result.get("symbols", [])
                if s.get("status") == "TRADING"
            ])

        if futures:
            result = self._get("/fapi/v1/exchangeInfo", futures=True)
            symbols.extend([
                s["symbol"]
                for s in result.get("symbols", [])
                if s.get("status") == "TRADING"
            ])

        return symbols

    def get_funding_rate(self, symbol: str) -> dict[str, Any]:
        """Get funding rate for a symbol.

        Args:
            symbol: Trading symbol (perpetual futures)

        Returns:
            Funding rate data
        """
        result = self._get("/fapi/v1/premiumIndex", {"symbol": symbol}, futures=True)

        return {
            "symbol": symbol,
            "funding_rate": Decimal(result.get("lastFundingRate", "0")),
            "funding_rate_pct": Decimal(result.get("lastFundingRate", "0")) * 100,
            "next_funding_time": int(result.get("nextFundingTime", 0)),
            "mark_price": Decimal(result.get("markPrice", "0")),
            "index_price": Decimal(result.get("indexPrice", "0")),
            "timestamp": int(result.get("time", 0)),
        }

    # ===== Private API =====

    def get_account(self, futures: bool = False) -> dict[str, Any]:
        """Get account information.

        Args:
            futures: Get futures account info

        Returns:
            Account data
        """
        endpoint = "/fapi/v2/account" if futures else "/api/v3/account"
        result = self._get(endpoint, signed=True, futures=futures)

        if futures:
            balances = []
            for item in result.get("assets", []):
                balances.append({
                    "asset": item.get("asset", ""),
                    "free": Decimal(item.get("availableBalance", "0")),
                    "locked": Decimal(item.get("crossWalletBalance", "0")) - Decimal(item.get("availableBalance", "0")),
                    "total": Decimal(item.get("crossWalletBalance", "0")),
                })
            return {
                "total_wallet_balance": Decimal(result.get("totalWalletBalance", "0")),
                "balances": balances,
            }
        else:
            balances = []
            for item in result.get("balances", []):
                balances.append({
                    "asset": item.get("asset", ""),
                    "free": Decimal(item.get("free", "0")),
                    "locked": Decimal(item.get("locked", "0")),
                    "total": Decimal(item.get("free", "0")) + Decimal(item.get("locked", "0")),
                })
            return {"balances": balances}

    def get_balance(self) -> dict[str, Balance]:
        """Get account balances.

        Returns:
            Dictionary of asset to Balance
        """
        result = self.get_account(futures=False)
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

    def get_positions(self) -> list[Position]:
        """Get current positions.

        Returns:
            List of positions
        """
        result = self._get("/fapi/v2/positionRisk", signed=True, futures=True)

        positions = []
        for item in result:
            amount = Decimal(item.get("positionAmt", "0"))
            if amount == 0:
                continue  # Skip closed positions

            side = "long" if amount > 0 else "short"

            positions.append(Position(
                symbol=item.get("symbol", ""),
                side=side,
                size=abs(amount),
                entry_price=Decimal(item.get("entryPrice", "0")),
                mark_price=Decimal(item.get("markPrice", "0")),
                unrealized_pnl=Decimal(item.get("unRealizedProfit", "0")),
                leverage=int(float(item.get("leverage", "1"))),
            ))

        return positions

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        futures: bool = False,
        time_in_force: str = "GTC",
        **kwargs,
    ) -> OrderResult:
        """Place an order.

        Args:
            symbol: Trading symbol
            side: Order side (buy or sell)
            order_type: Order type (market, limit)
            quantity: Order quantity
            price: Limit price (required for limit orders)
            futures: Place futures order
            time_in_force: Time in force (GTC, IOC, FOK)
            **kwargs: Additional parameters

        Returns:
            Order result
        """
        side = side.upper()
        order_type = order_type.upper()

        if order_type == "LIMIT" and price is None:
            raise OrderError("Price is required for limit orders")

        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if price is not None:
            params["price"] = str(price)

        if order_type == "LIMIT":
            params["timeInForce"] = time_in_force

        # Add additional parameters
        params.update(kwargs)

        endpoint = "/fapi/v1/order" if futures else "/api/v3/order"
        result = self._post(endpoint, params, signed=True, futures=futures)

        return OrderResult(
            order_id=str(result.get("orderId", "")),
            symbol=symbol,
            side=side.lower(),
            order_type=order_type.lower(),
            quantity=quantity,
            price=price,
            status=result.get("status", "").lower(),
            client_order_id=result.get("clientOrderId"),
        )

    def cancel_order(
        self,
        symbol: str,
        order_id: str,
        futures: bool = False,
    ) -> bool:
        """Cancel an order.

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel
            futures: Cancel futures order

        Returns:
            True if successful
        """
        endpoint = "/fapi/v1/order" if futures else "/api/v3/order"
        result = self._delete(endpoint, {
            "symbol": symbol,
            "orderId": int(order_id),
        }, signed=True, futures=futures)

        return result.get("symbol") == symbol

    def cancel_all_orders(
        self,
        symbol: str,
        futures: bool = False,
    ) -> int:
        """Cancel all orders for a symbol.

        Args:
            symbol: Trading symbol
            futures: Cancel futures orders

        Returns:
            Number of orders canceled
        """
        endpoint = "/fapi/v1/allOpenOrders" if futures else "/api/v3/openOrders"
        result = self._delete(endpoint, {"symbol": symbol}, signed=True, futures=futures)

        # Binance doesn't return count, so we return 1 on success
        return 1 if result else 0

    def get_open_orders(
        self,
        symbol: str | None = None,
        futures: bool = False,
    ) -> list[Order]:
        """Get open orders.

        Args:
            symbol: Trading symbol (None for all symbols)
            futures: Get futures orders

        Returns:
            List of open orders
        """
        endpoint = "/fapi/v1/openOrders" if futures else "/api/v3/openOrders"
        params = {}
        if symbol:
            params["symbol"] = symbol

        result = self._get(endpoint, params, signed=True, futures=futures)

        orders = []
        for item in result:
            side = item.get("side", "").lower()
            order_type = item.get("type", "").lower()

            orders.append(Order(
                order_id=str(item.get("orderId", "")),
                symbol=item.get("symbol", ""),
                side=side,
                order_type=order_type,
                quantity=Decimal(item.get("origQty", "0")),
                price=Decimal(item.get("price", "0")) if item.get("price") else None,
                filled_quantity=Decimal(item.get("executedQty", "0")),
                status=item.get("status", "").lower(),
                timestamp=int(item.get("time", 0)),
            ))

        return orders

    def get_order_history(
        self,
        symbol: str | None = None,
        futures: bool = False,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Order]:
        """Get order history.

        Args:
            symbol: Trading symbol (None for all symbols)
            futures: Get futures orders
            limit: Number of orders to return (max 1000)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of historical orders
        """
        endpoint = "/fapi/v1/allOrders" if futures else "/api/v3/allOrders"
        params = {"limit": min(limit, 1000)}

        if symbol:
            params["symbol"] = symbol
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        result = self._get(endpoint, params, signed=True, futures=futures)

        orders = []
        for item in result:
            side = item.get("side", "").lower()
            order_type = item.get("type", "").lower()

            orders.append(Order(
                order_id=str(item.get("orderId", "")),
                symbol=item.get("symbol", ""),
                side=side,
                order_type=order_type,
                quantity=Decimal(item.get("origQty", "0")),
                price=Decimal(item.get("price", "0")) if item.get("price") else None,
                filled_quantity=Decimal(item.get("executedQty", "0")),
                status=item.get("status", "").lower(),
                timestamp=int(item.get("time", 0)),
            ))

        return orders

    # ===== Futures-specific methods =====

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol.

        Args:
            symbol: Trading symbol
            leverage: Leverage multiplier (1-125)

        Returns:
            True if successful
        """
        result = self._post("/fapi/v1/leverage", {
            "symbol": symbol,
            "leverage": leverage,
        }, signed=True, futures=True)

        return result.get("leverage") == leverage

    def set_margin_type(self, symbol: str, margin_type: str) -> bool:
        """Set margin type for a symbol.

        Args:
            symbol: Trading symbol
            margin_type: Margin type (CROSSED or ISOLATED)

        Returns:
            True if successful
        """
        margin_type = margin_type.upper()
        if margin_type not in ("CROSSED", "ISOLATED"):
            raise OrderError("Margin type must be CROSSED or ISOLATED")

        result = self._post("/fapi/v1/marginType", {
            "symbol": symbol,
            "marginType": margin_type,
        }, signed=True, futures=True)

        return result.get("msg") == "success"
