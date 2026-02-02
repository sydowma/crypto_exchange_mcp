"""Base classes for exchange implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from .exceptions import ExchangeError


@dataclass
class Ticker:
    """Ticker data."""

    symbol: str
    last_price: Decimal
    price_change_24h: Decimal | None = None
    price_change_pct_24h: Decimal | None = None
    volume_24h: Decimal | None = None
    high_24h: Decimal | None = None
    low_24h: Decimal | None = None
    timestamp: int | None = None


@dataclass
class OrderBookLevel:
    """Order book level."""

    price: Decimal
    size: Decimal


@dataclass
class OrderBook:
    """Order book data."""

    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: int | None = None


@dataclass
class Kline:
    """Kline/candlestick data."""

    symbol: str
    open_time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time: int | None = None
    quote_volume: Decimal | None = None


@dataclass
class Balance:
    """Account balance."""

    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal | None = None

    def __post_init__(self):
        if self.total is None:
            self.total = self.free + self.locked


@dataclass
class Position:
    """Position data."""

    symbol: str
    side: str  # "long" or "short"
    size: Decimal
    entry_price: Decimal
    mark_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    leverage: int | None = None


@dataclass
class Order:
    """Order data."""

    order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit", etc.
    quantity: Decimal
    price: Decimal | None = None
    filled_quantity: Decimal | None = None
    status: str | None = None  # "open", "filled", "canceled", etc.
    timestamp: int | None = None


@dataclass
class OrderResult:
    """Result of placing an order."""

    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    status: str | None = None
    client_order_id: str | None = None


class BaseExchange(ABC):
    """Base class for exchange implementations."""

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, passphrase: str | None = None):
        """Initialize the exchange.

        Args:
            api_key: API key for private endpoints
            api_secret: API secret for private endpoints
            passphrase: API passphrase (required for some exchanges like OKX)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self._authenticated = bool(api_key and api_secret)

    @property
    def is_authenticated(self) -> bool:
        """Check if the exchange is authenticated."""
        return self._authenticated

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker for a symbol.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)

        Returns:
            Ticker data
        """

    @abstractmethod
    def get_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        """Get order book for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of levels to return

        Returns:
            Order book data
        """

    @abstractmethod
    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Kline]:
        """Get klines/candlesticks for a symbol.

        Args:
            symbol: Trading symbol
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            limit: Number of klines to return
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of kline data
        """

    def get_symbols(self, spot: bool = True, futures: bool = False) -> list[str]:
        """Get list of trading symbols.

        Args:
            spot: Include spot trading pairs
            futures: Include futures trading pairs

        Returns:
            List of trading symbols
        """
        raise NotImplementedError("get_symbols is not implemented")

    def get_funding_rate(self, symbol: str) -> dict[str, Any]:
        """Get funding rate for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Funding rate data
        """
        raise NotImplementedError("get_funding_rate is not implemented")

    # Private API methods (require authentication)

    def require_auth(self) -> None:
        """Raise error if not authenticated."""
        if not self.is_authenticated:
            raise ExchangeError("Authentication required for this operation")

    def get_balance(self) -> dict[str, Balance]:
        """Get account balances.

        Returns:
            Dictionary of asset to Balance
        """
        self.require_auth()
        raise NotImplementedError("get_balance is not implemented")

    def get_positions(self) -> list[Position]:
        """Get current positions.

        Returns:
            List of positions
        """
        self.require_auth()
        raise NotImplementedError("get_positions is not implemented")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        **kwargs,
    ) -> OrderResult:
        """Place an order.

        Args:
            symbol: Trading symbol
            side: Order side ("buy" or "sell")
            order_type: Order type ("market", "limit", etc.)
            quantity: Order quantity
            price: Limit price (required for limit orders)

        Returns:
            Order result
        """
        self.require_auth()
        raise NotImplementedError("place_order is not implemented")

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order.

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel

        Returns:
            True if successful
        """
        self.require_auth()
        raise NotImplementedError("cancel_order is not implemented")

    def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all orders for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Number of orders canceled
        """
        self.require_auth()
        raise NotImplementedError("cancel_all_orders is not implemented")

    def get_open_orders(self, symbol: str | None = None) -> list[Order]:
        """Get open orders.

        Args:
            symbol: Trading symbol (None for all symbols)

        Returns:
            List of open orders
        """
        self.require_auth()
        raise NotImplementedError("get_open_orders is not implemented")

    def get_order_history(
        self,
        symbol: str | None = None,
        limit: int = 100,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[Order]:
        """Get order history.

        Args:
            symbol: Trading symbol (None for all symbols)
            limit: Number of orders to return
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds

        Returns:
            List of historical orders
        """
        self.require_auth()
        raise NotImplementedError("get_order_history is not implemented")
