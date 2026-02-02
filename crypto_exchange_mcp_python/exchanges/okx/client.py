"""OKX exchange client."""

import base64
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


class OKXExchange(BaseExchange):
    """OKX exchange implementation.

    API docs: https://www.okx.com/docs-v5/
    """

    # API endpoints
    API_BASE_URL = "https://www.okx.com"  # Production
    API_TESTNET_URL = "https://www.okx.com"  # Demo trading

    # Institution/Account type
    ACCOUNT_TYPE_UNIFIED = "18"  # Unified account
    ACCOUNT_TYPE_NORMAL = "1"  # Normal account

    # Instrument types
    INST_TYPE_SPOT = "SPOT"
    INST_TYPE_MARGINS = "MARGIN"
    INST_TYPE_SWAP = "SWAP"
    INST_TYPE_FUTURES = "FUTURES"
    INST_TYPE_OPTION = "OPTION"

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        passphrase: str | None = None,
        demo: bool = False,
        simulate: bool = False,
    ):
        """Initialize OKX exchange.

        Args:
            api_key: API key for private endpoints
            api_secret: API secret for private endpoints
            passphrase: API passphrase (required for OKX)
            demo: Use demo trading
            simulate: Use simulated trading
        """
        super().__init__(api_key, api_secret, passphrase)

        # If credentials not provided, try to load from config
        if not api_key and not api_secret:
            creds = Config().get_credentials("okx")
            if creds:
                self.api_key = creds.api_key
                self.api_secret = creds.api_secret
                self.passphrase = creds.passphrase
                self._authenticated = True

        self.base_url = self.API_TESTNET if demo else self.API_BASE_URL
        self.demo = demo
        self.simulate = simulate
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-PASSPHRASE": self.passphrase or "",
            })

        if simulate:
            self.session.headers["x-simulated-trading"] = "1"

    # ===== HTTP Methods =====

    def _generate_signature(
        self,
        timestamp: str,
        method: str,
        request_path: str,
        body: str = "",
    ) -> str:
        """Generate signature for private API requests."""
        if not self.api_secret:
            raise AuthenticationError("API secret is required for private endpoints")

        sign_str = timestamp + method + request_path + body
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return base64.b64encode(signature.encode("utf-8")).decode("utf-8")

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        """Make HTTP request to OKX API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request needs signature

        Returns:
            Response data

        Raises:
            ExchangeError: On API errors
        """
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}

        headers = self.session.headers.copy()

        # Build query string or body
        request_path = endpoint
        body = ""

        if method == "GET" and params:
            query_string = urlencode(sorted(params.items()))
            url = f"{url}?{query_string}"
            request_path = f"{request_path}?{query_string}"
        elif method in ("POST", "DELETE") and params:
            import json
            body = json.dumps(params)
            headers["Content-Type"] = "application/json"

        # Add signature for signed requests
        if signed:
            self.require_auth()
            timestamp = str(time.time())
            signature = self._generate_signature(timestamp, method, request_path, body)
            headers["OK-ACCESS-TIMESTAMP"] = timestamp
            headers["OK-ACCESS-SIGN"] = signature

        try:
            response = self.session.request(method, url, headers=headers, data=body if body else None, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if data.get("code") != "0":
                error_msg = data.get("msg", "Unknown error")
                error_code = data.get("code")

                # Handle specific errors
                if error_code in ("50001", "50002", "50003", "50004", "50005"):
                    raise AuthenticationError(error_msg, error_code, data)
                elif error_code in ("50011", "50012", "50013", "50014"):
                    raise RateLimitError(error_msg, error_code, data)
                elif error_code in ("51001", "51002", "51003", "51004"):
                    raise InvalidSymbolError(error_msg, error_code, data)
                else:
                    raise ExchangeError(error_msg, error_code, data)

            return data.get("data", {})

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

    def get_ticker(self, symbol: str, inst_type: str | None = None) -> Ticker:
        """Get ticker for a symbol.

        Args:
            symbol: Trading instrument ID (e.g., BTC-USDT, BTC-USDT-SWAP)
            inst_type: Instrument type (SPOT, MARGIN, SWAP, FUTURES, OPTION)

        Returns:
            Ticker data
        """
        params = {"instId": symbol}
        if inst_type:
            params["instType"] = inst_type

        result = self._get("/api/v5/market/ticker", params)

        if not result or len(result) == 0:
            raise InvalidSymbolError(f"Symbol not found: {symbol}")

        data = result[0]

        return Ticker(
            symbol=symbol,
            last_price=Decimal(data.get("last", "0")),
            price_change_24h=Decimal(data.get("sodUtc8", "0")),
            price_change_pct_24h=Decimal(data.get("open24h", "0")) if data.get("open24h") else None,
            volume_24h=Decimal(data.get("vol24h", "0")),
            high_24h=Decimal(data.get("high24h", "0")),
            low_24h=Decimal(data.get("low24h", "0")),
            timestamp=int(data.get("ts", 0)),
        )

    def get_order_book(
        self,
        symbol: str,
        limit: int = 20,
    ) -> OrderBook:
        """Get order book for a symbol.

        Args:
            symbol: Trading instrument ID
            limit: Number of levels to return (max 400)

        Returns:
            Order book data
        """
        result = self._get("/api/v5/market/books", {
            "instId": symbol,
            "sz": min(limit, 400),
        })

        if not result or len(result) == 0:
            raise InvalidSymbolError(f"Symbol not found: {symbol}")

        data = result[0]

        bids = [
            OrderBookLevel(price=Decimal(b[0]), size=Decimal(b[1]))
            for b in data.get("bids", [])[:limit]
        ]
        asks = [
            OrderBookLevel(price=Decimal(a[0]), size=Decimal(a[1]))
            for a in data.get("asks", [])[:limit]
        ]

        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=int(data.get("ts", 0)),
        )

    def get_klines(
        self,
        symbol: str,
        interval: str = "1H",
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Kline]:
        """Get klines/candlesticks for a symbol.

        Args:
            symbol: Trading instrument ID
            interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1H, 2H, 4H, 6H,
                       12H, 1D, 1W, 1M, etc.)
            limit: Number of klines to return (max 300)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of kline data
        """
        params = {
            "instId": symbol,
            "bar": interval,
            "limit": min(limit, 300),
        }

        if start_time:
            params["after"] = start_time
        if end_time:
            params["before"] = end_time

        result = self._get("/api/v5/market/candles", params)

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
                close_time=int(item[0]) + self._get_interval_ms(interval) - 1,
                quote_volume=Decimal(item[6]) if len(item) > 6 else None,
            ))

        # OKX returns data in reverse chronological order
        return list(reversed(klines))

    def _get_interval_ms(self, interval: str) -> int:
        """Get milliseconds for an interval string."""
        unit = interval[-1]
        value = int(interval[:-1])

        multipliers = {
            "m": 60 * 1000,
            "H": 60 * 60 * 1000,
            "D": 24 * 60 * 60 * 1000,
            "W": 7 * 24 * 60 * 60 * 1000,
            "M": 30 * 24 * 60 * 60 * 1000,
        }

        return value * multipliers.get(unit, 60 * 60 * 1000)

    def get_symbols(
        self,
        spot: bool = True,
        futures: bool = False,
        swap: bool = False,
    ) -> list[str]:
        """Get list of trading symbols.

        Args:
            spot: Include spot trading pairs
            futures: Include futures
            swap: Include perpetual swaps

        Returns:
            List of trading symbols
        """
        symbols = []

        inst_types = []
        if spot:
            inst_types.append(self.INST_TYPE_SPOT)
        if futures:
            inst_types.append(self.INST_TYPE_FUTURES)
        if swap:
            inst_types.append(self.INST_TYPE_SWAP)

        for inst_type in inst_types:
            result = self._get("/api/v5/public/instruments", {
                "instType": inst_type,
            })

            for item in result:
                if item.get("state") == "live":
                    symbols.append(item.get("instId", ""))

        return symbols

    def get_funding_rate(self, symbol: str) -> dict[str, Any]:
        """Get funding rate for a symbol.

        Args:
            symbol: Trading instrument ID (perpetual swap)

        Returns:
            Funding rate data
        """
        result = self._get("/api/v5/public/funding-rate", {
            "instId": symbol,
        })

        if not result or len(result) == 0:
            raise InvalidSymbolError(f"Symbol not found: {symbol}")

        data = result[0]

        return {
            "symbol": symbol,
            "funding_rate": Decimal(data.get("fundingRate", "0")),
            "funding_rate_pct": Decimal(data.get("fundingRate", "0")) * 100,
            "next_funding_time": int(data.get("fundingTime", 0)),
            "timestamp": int(data.get("updateTime", 0)),
        }

    def get_new_coins(self) -> list[dict[str, Any]]:
        """Get recently listed new coins.

        Returns:
            List of new coin information
        """
        # This endpoint gets the Tickers of all USD pairs (OKX uses USD, not USDT)
        result = self._get("/api/v5/market/tickers", {
            "instType": self.INST_TYPE_SPOT,
        })

        # Filter for USD pairs (state is not provided in tickers endpoint)
        usd_pairs = []
        for item in result:
            inst_id = item.get("instId", "")
            # Check if it has trading data (not suspended/delisted)
            last_price = item.get("last", "0")
            if inst_id.endswith("-USD") and last_price and last_price != "0":
                usd_pairs.append({
                    "symbol": inst_id,
                    "last_price": Decimal(last_price),
                    "volume_24h": Decimal(item.get("vol24h", "0")),
                    "timestamp": int(item.get("ts", 0)),
                })

        # Sort by volume (highest first)
        usd_pairs.sort(key=lambda x: x["volume_24h"], reverse=True)

        return usd_pairs

    # ===== Private API =====

    def get_balance(self, currency: str | None = None) -> dict[str, Balance]:
        """Get account balances.

        Args:
            currency: Filter by currency (None for all)

        Returns:
            Dictionary of asset to Balance
        """
        params = {}
        if currency:
            params["ccy"] = currency

        result = self._get("/api/v5/account/balance", params, signed=True)

        balances = {}
        for item in result:
            for detail in item.get("details", []):
                asset = detail.get("ccy", "")
                if not asset:
                    continue

                cash_bal = Decimal(detail.get("cashBal", "0"))
                if cash_bal == 0:
                    continue  # Skip zero balances

                balances[asset] = Balance(
                    asset=asset,
                    free=Decimal(detail.get("availBal", "0")),
                    locked=Decimal(detail.get("frozenBal", "0")),
                    total=cash_bal,
                )

        return balances

    def get_positions(
        self,
        inst_type: str | None = None,
        inst_id: str | None = None,
    ) -> list[Position]:
        """Get current positions.

        Args:
            inst_type: Instrument type (MARGIN, SWAP, FUTURES, OPTION)
            inst_id: Instrument ID

        Returns:
            List of positions
        """
        params = {}
        if inst_type:
            params["instType"] = inst_type
        if inst_id:
            params["instId"] = inst_id

        result = self._get("/api/v5/account/positions", params, signed=True)

        positions = []
        for item in result:
            size = Decimal(item.get("pos", "0"))
            if size == 0:
                continue  # Skip closed positions

            side = "long" if item.get("posSide") == "long" else "short"

            positions.append(Position(
                symbol=item.get("instId", ""),
                side=side,
                size=size,
                entry_price=Decimal(item.get("avgPx", "0")),
                mark_price=Decimal(item.get("markPx", "0")) if item.get("markPx") else None,
                unrealized_pnl=Decimal(item.get("upl", "0")) if item.get("upl") else None,
                leverage=int(float(item.get("lever", "1"))),
            ))

        return positions

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        td_mode: str = "cash",
        pos_side: str | None = None,
        **kwargs,
    ) -> OrderResult:
        """Place an order.

        Args:
            symbol: Trading instrument ID
            side: Order side (buy or sell)
            order_type: Order type (market, limit, post_only, etc.)
            quantity: Order quantity
            price: Limit price (required for limit orders)
            td_mode: Trade mode (cash, cross, isolated)
            pos_side: Position side (long, short, net)
            **kwargs: Additional parameters

        Returns:
            Order result
        """
        side = side.lower()
        order_type = order_type.lower()

        if order_type == "limit" and price is None:
            raise OrderError("Price is required for limit orders")

        params = {
            "instId": symbol,
            "tdMode": td_mode,
            "side": side,
            "ordType": order_type,
            "sz": str(quantity),
        }

        if price is not None:
            params["px"] = str(price)

        if pos_side:
            params["posSide"] = pos_side

        # Add additional parameters
        params.update(kwargs)

        result = self._post("/api/v5/trade/order", params, signed=True)

        if not result or len(result) == 0:
            raise OrderError("Failed to place order")

        order_data = result[0]

        if order_data.get("sCode") != "0":
            raise OrderError(order_data.get("sMsg", "Failed to place order"))

        return OrderResult(
            order_id=order_data.get("ordId", ""),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=order_data.get("sMsg"),
            client_order_id=order_data.get("clOrdId"),
        )

    def cancel_order(
        self,
        symbol: str,
        order_id: str,
    ) -> bool:
        """Cancel an order.

        Args:
            symbol: Trading instrument ID
            order_id: Order ID to cancel

        Returns:
            True if successful
        """
        result = self._post("/api/v5/trade/cancel-order", {
            "instId": symbol,
            "ordId": order_id,
        }, signed=True)

        if not result or len(result) == 0:
            return False

        return result[0].get("sCode") == "0"

    def cancel_all_orders(
        self,
        symbol: str,
        inst_type: str = "SPOT",
    ) -> int:
        """Cancel all orders for a symbol.

        Args:
            symbol: Trading instrument ID
            inst_type: Instrument type (SPOT, MARGIN, SWAP, FUTURES, OPTION)

        Returns:
            Number of orders canceled
        """
        result = self._post("/api/v5/trade/cancel-all-orders", {
            "instType": inst_type,
            "instId": symbol,
        }, signed=True)

        # OKX doesn't return count, return 1 on success
        return 1 if result else 0

    def get_open_orders(
        self,
        symbol: str | None = None,
        inst_type: str | None = None,
    ) -> list[Order]:
        """Get open orders.

        Args:
            symbol: Trading instrument ID (None for all symbols)
            inst_type: Instrument type (SPOT, MARGIN, SWAP, FUTURES, OPTION)

        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params["instId"] = symbol
        if inst_type:
            params["instType"] = inst_type

        result = self._get("/api/v5/trade/orders-pending", params, signed=True)

        orders = []
        for item in result:
            side = item.get("side", "").lower()
            order_type = item.get("ordType", "").lower()

            orders.append(Order(
                order_id=item.get("ordId", ""),
                symbol=item.get("instId", ""),
                side=side,
                order_type=order_type,
                quantity=Decimal(item.get("sz", "0")),
                price=Decimal(item.get("px", "0")) if item.get("px") else None,
                filled_quantity=Decimal(item.get("accFillSz", "0")),
                status=item.get("state", "").lower(),
                timestamp=int(item.get("cTime", 0)),
            ))

        return orders

    def get_order_history(
        self,
        symbol: str | None = None,
        inst_type: str | None = None,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Order]:
        """Get order history.

        Args:
            symbol: Trading instrument ID (None for all symbols)
            inst_type: Instrument type (SPOT, MARGIN, SWAP, FUTURES, OPTION)
            limit: Number of orders to return (max 100)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of historical orders
        """
        params = {"limit": min(limit, 100)}

        if symbol:
            params["instId"] = symbol
        if inst_type:
            params["instType"] = inst_type
        if start_time:
            params["after"] = start_time
        if end_time:
            params["before"] = end_time

        result = self._get("/api/v5/trade/orders-history", params, signed=True)

        orders = []
        for item in result:
            side = item.get("side", "").lower()
            order_type = item.get("ordType", "").lower()

            orders.append(Order(
                order_id=item.get("ordId", ""),
                symbol=item.get("instId", ""),
                side=side,
                order_type=order_type,
                quantity=Decimal(item.get("sz", "0")),
                price=Decimal(item.get("px", "0")) if item.get("px") else None,
                filled_quantity=Decimal(item.get("accFillSz", "0")),
                status=item.get("state", "").lower(),
                timestamp=int(item.get("cTime", 0)),
            ))

        return orders

    # ===== Account-specific methods =====

    def set_leverage(self, symbol: str, leverage: int, mgn_mode: str = "cross") -> bool:
        """Set leverage for a symbol.

        Args:
            symbol: Trading instrument ID
            leverage: Leverage multiplier
            mgn_mode: Margin mode (cross, isolated, cash)

        Returns:
            True if successful
        """
        result = self._post("/api/v5/account/set-leverage", {
            "instId": symbol,
            "lever": str(leverage),
            "mgnMode": mgn_mode,
        }, signed=True)

        return bool(result and len(result) > 0 and result[0].get("sCode") == "0")

    def get_account_config(self) -> dict[str, Any]:
        """Get account configuration.

        Returns:
            Account configuration
        """
        result = self._get("/api/v5/account/config", signed=True)

        if not result or len(result) == 0:
            return {}

        return {
            "account_level": result[0].get("acctLv", ""),
            "position_mode": result[0].get("posMode", ""),
            "auto_loan": result[0].get("autoLoan", "false") == "true",
        }
