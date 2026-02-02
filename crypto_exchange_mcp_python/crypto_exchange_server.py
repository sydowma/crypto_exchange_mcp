"""
Unified MCP server for crypto exchanges (Bybit, Binance, OKX).

This server provides a unified interface to interact with multiple cryptocurrency exchanges.
It supports both public APIs (market data) and private APIs (trading, account management)
when API credentials are configured.

Configuration:
    Set the following environment variables to enable private APIs:
    - BYBIT_API_KEY, BYBIT_API_SECRET
    - BINANCE_API_KEY, BINANCE_API_SECRET
    - OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE

Example usage in Claude Desktop:
    {
        "mcpServers": {
            "crypto-exchange": {
                "command": "uv",
                "args": [
                    "--directory",
                    "/path/to/crypto_exchange_mcp_python",
                    "run",
                    "crypto_exchange_server.py"
                ],
                "env": {
                    "BYBIT_API_KEY": "your_key",
                    "BYBIT_API_SECRET": "your_secret"
                }
            }
        }
    }
"""

from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

from core.config import Config
from core.exceptions import ExchangeError
from exchanges.binance import BinanceExchange
from exchanges.bybit import BybitExchange
from exchanges.okx import OKXExchange

# Create MCP server
mcp = FastMCP("crypto-exchange")

# Initialize exchanges
config = Config()

bybit = BybitExchange()
binance = BinanceExchange()
okx = OKXExchange()

# Track which exchanges have authentication
EXCHANGES = {
    "bybit": bybit,
    "binance": binance,
    "okx": okx,
}


# ===== Helper Functions =====

def format_decimal(value: Decimal | None) -> str:
    """Format decimal for display."""
    if value is None:
        return "N/A"
    return str(value)


def format_balance(balance: dict[str, Any]) -> str:
    """Format balance for display."""
    lines = []
    for asset, bal in balance.items():
        lines.append(f"  {asset}: {bal.total} (free: {bal.free}, locked: {bal.locked})")
    return "\n".join(lines) if lines else "No balances found"


# ===== Public API Tools =====

@mcp.tool()
def get_ticker(exchange: str, symbol: str) -> dict[str, Any]:
    """
    Get ticker/price information for a trading symbol.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Trading symbol (e.g., BTCUSDT for Bybit/Binance, BTC-USDT for OKX)

    Returns:
        Ticker information including last price, 24h change, volume
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    ticker = exchange_obj.get_ticker(symbol)

    return {
        "exchange": exchange.lower(),
        "symbol": ticker.symbol,
        "last_price": format_decimal(ticker.last_price),
        "price_change_24h": format_decimal(ticker.price_change_24h),
        "price_change_pct_24h": format_decimal(ticker.price_change_pct_24h) + "%",
        "volume_24h": format_decimal(ticker.volume_24h),
        "high_24h": format_decimal(ticker.high_24h),
        "low_24h": format_decimal(ticker.low_24h),
        "timestamp": ticker.timestamp,
    }


@mcp.tool()
def get_orderbook(exchange: str, symbol: str, limit: int = 10) -> dict[str, Any]:
    """
    Get order book for a trading symbol.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Trading symbol
        limit: Number of levels to return (default: 10)

    Returns:
        Order book with bids (buy orders) and asks (sell orders)
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    orderbook = exchange_obj.get_order_book(symbol, limit)

    bids = [{"price": str(b.price), "size": str(b.size)} for b in orderbook.bids[:limit]]
    asks = [{"price": str(a.price), "size": str(a.size)} for a in orderbook.asks[:limit]]

    return {
        "exchange": exchange.lower(),
        "symbol": orderbook.symbol,
        "bids": bids,
        "asks": asks,
        "timestamp": orderbook.timestamp,
    }


@mcp.tool()
def get_klines(
    exchange: str,
    symbol: str,
    interval: str = "1h",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Get kline/candlestick data for a trading symbol.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Trading symbol
        interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
        limit: Number of klines to return (default: 10)

    Returns:
        List of kline data with open, high, low, close, volume
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    klines = exchange_obj.get_klines(symbol, interval, limit)

    return [
        {
            "symbol": k.symbol,
            "open_time": k.open_time,
            "open": str(k.open),
            "high": str(k.high),
            "low": str(k.low),
            "close": str(k.close),
            "volume": str(k.volume),
        }
        for k in klines
    ]


@mcp.tool()
def get_symbols(
    exchange: str,
    spot: bool = True,
    futures: bool = False,
) -> list[str]:
    """
    Get list of available trading symbols.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        spot: Include spot trading pairs
        futures: Include futures contracts

    Returns:
        List of trading symbols
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    return exchange_obj.get_symbols(spot=spot, futures=futures)


@mcp.tool()
def get_funding_rate(exchange: str, symbol: str) -> dict[str, Any]:
    """
    Get funding rate for a perpetual contract.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Contract symbol (e.g., BTCUSDT for Bybit, BTCUSDT perpetual for Binance)

    Returns:
        Funding rate information
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    result = exchange_obj.get_funding_rate(symbol)

    return {
        "exchange": exchange.lower(),
        "symbol": result.get("symbol", symbol),
        "funding_rate": format_decimal(result.get("funding_rate")),
        "funding_rate_pct": format_decimal(result.get("funding_rate_pct")) + "%",
        "next_funding_time": result.get("next_funding_time"),
    }


@mcp.tool()
def get_open_interest(exchange: str, symbol: str) -> dict[str, Any]:
    """
    Get open interest for a contract (Bybit only).

    Args:
        exchange: Exchange name (currently only bybit supported)
        symbol: Contract symbol

    Returns:
        Open interest information
    """
    if exchange.lower() != "bybit":
        raise ExchangeError("Open interest is currently only supported for Bybit")

    result = bybit.get_open_interest(symbol)

    return {
        "exchange": "bybit",
        "symbol": result.get("symbol", symbol),
        "open_interest": format_decimal(result.get("open_interest")),
        "timestamp": result.get("timestamp"),
    }


@mcp.tool()
def get_new_coins_okx(limit: int = 20) -> list[dict[str, Any]]:
    """
    Get recently listed coins on OKX.

    Args:
        limit: Number of coins to return

    Returns:
        List of new coin information
    """
    coins = okx.get_new_coins()

    return [
        {
            "symbol": c["symbol"],
            "last_price": str(c["last_price"]),
            "volume_24h": str(c["volume_24h"]),
        }
        for c in coins[:limit]
    ]


# ===== Private API Tools =====

@mcp.tool()
def get_balance(exchange: str) -> dict[str, Any]:
    """
    Get account balance. Requires API credentials.

    Args:
        exchange: Exchange name (bybit, binance, okx)

    Returns:
        Account balance information
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    if not exchange_obj.is_authenticated:
        raise ExchangeError(
            f"API credentials not configured for {exchange}. "
            f"Please set {exchange.upper()}_API_KEY and {exchange.upper()}_API_SECRET environment variables."
        )

    balances = exchange_obj.get_balance()

    return {
        "exchange": exchange.lower(),
        "balances": {
            asset: {
                "total": str(bal.total),
                "free": str(bal.free),
                "locked": str(bal.locked),
            }
            for asset, bal in balances.items()
        },
    }


@mcp.tool()
def get_positions(exchange: str) -> list[dict[str, Any]]:
    """
    Get current open positions. Requires API credentials.

    Args:
        exchange: Exchange name (bybit, binance, okx)

    Returns:
        List of open positions
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    if not exchange_obj.is_authenticated:
        raise ExchangeError(
            f"API credentials not configured for {exchange}. "
            f"Please set {exchange.upper()}_API_KEY and {exchange.upper()}_API_SECRET environment variables."
        )

    positions = exchange_obj.get_positions()

    return [
        {
            "symbol": p.symbol,
            "side": p.side,
            "size": str(p.size),
            "entry_price": str(p.entry_price),
            "mark_price": str(p.mark_price) if p.mark_price else None,
            "unrealized_pnl": str(p.unrealized_pnl) if p.unrealized_pnl else None,
            "leverage": p.leverage,
        }
        for p in positions
    ]


@mcp.tool()
def place_order(
    exchange: str,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None = None,
) -> dict[str, Any]:
    """
    Place an order. Requires API credentials.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Trading symbol
        side: Order side (buy or sell)
        order_type: Order type (market or limit)
        quantity: Order quantity
        price: Limit price (required for limit orders)

    Returns:
        Order result
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    if not exchange_obj.is_authenticated:
        raise ExchangeError(
            f"API credentials not configured for {exchange}. "
            f"Please set {exchange.upper()}_API_KEY and {exchange.upper()}_API_SECRET environment variables."
        )

    result = exchange_obj.place_order(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=Decimal(quantity),
        price=Decimal(price) if price else None,
    )

    return {
        "exchange": exchange.lower(),
        "order_id": result.order_id,
        "symbol": result.symbol,
        "side": result.side,
        "order_type": result.order_type,
        "quantity": str(result.quantity),
        "price": str(result.price) if result.price else None,
        "status": result.status,
    }


@mcp.tool()
def cancel_order(exchange: str, symbol: str, order_id: str) -> dict[str, Any]:
    """
    Cancel an order. Requires API credentials.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Trading symbol
        order_id: Order ID to cancel

    Returns:
        Cancellation result
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    if not exchange_obj.is_authenticated:
        raise ExchangeError(
            f"API credentials not configured for {exchange}. "
            f"Please set {exchange.upper()}_API_KEY and {exchange.upper()}_API_SECRET environment variables."
        )

    success = exchange_obj.cancel_order(symbol, order_id)

    return {
        "exchange": exchange.lower(),
        "symbol": symbol,
        "order_id": order_id,
        "cancelled": success,
    }


@mcp.tool()
def get_open_orders(exchange: str, symbol: str | None = None) -> list[dict[str, Any]]:
    """
    Get open orders. Requires API credentials.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Trading symbol (None for all symbols)

    Returns:
        List of open orders
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    if not exchange_obj.is_authenticated:
        raise ExchangeError(
            f"API credentials not configured for {exchange}. "
            f"Please set {exchange.upper()}_API_KEY and {exchange.upper()}_API_SECRET environment variables."
        )

    orders = exchange_obj.get_open_orders(symbol)

    return [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "side": o.side,
            "order_type": o.order_type,
            "quantity": str(o.quantity),
            "price": str(o.price) if o.price else None,
            "filled_quantity": str(o.filled_quantity) if o.filled_quantity else None,
            "status": o.status,
        }
        for o in orders
    ]


@mcp.tool()
def get_order_history(
    exchange: str,
    symbol: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Get order history. Requires API credentials.

    Args:
        exchange: Exchange name (bybit, binance, okx)
        symbol: Trading symbol (None for all symbols)
        limit: Number of orders to return

    Returns:
        List of historical orders
    """
    exchange_obj = EXCHANGES.get(exchange.lower())
    if not exchange_obj:
        raise ExchangeError(f"Unknown exchange: {exchange}")

    if not exchange_obj.is_authenticated:
        raise ExchangeError(
            f"API credentials not configured for {exchange}. "
            f"Please set {exchange.upper()}_API_KEY and {exchange.upper()}_API_SECRET environment variables."
        )

    orders = exchange_obj.get_order_history(symbol, limit=limit)

    return [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "side": o.side,
            "order_type": o.order_type,
            "quantity": str(o.quantity),
            "price": str(o.price) if o.price else None,
            "filled_quantity": str(o.filled_quantity) if o.filled_quantity else None,
            "status": o.status,
        }
        for o in orders
    ]


# ===== Cross-Exchange Tools =====

@mcp.tool()
def compare_prices(symbol: str) -> dict[str, Any]:
    """
    Compare prices across all exchanges for a symbol.

    Args:
        symbol: Base currency (e.g., BTC, ETH, SOL)

    Returns:
        Price comparison with best buy/sell prices across exchanges
    """
    # Symbol format mapping
    bybit_symbol = f"{symbol}USDT"
    binance_symbol = f"{symbol}USDT"
    okx_symbol = f"{symbol}-USDT"

    prices = []

    # Try Bybit
    try:
        bybit_ticker = bybit.get_ticker(bybit_symbol)
        bybit_ob = bybit.get_order_book(bybit_symbol, 1)
        prices.append({
            "exchange": "bybit",
            "last_price": float(bybit_ticker.last_price),
            "bid": float(bybit_ob.bids[0].price) if bybit_ob.bids else None,
            "ask": float(bybit_ob.asks[0].price) if bybit_ob.asks else None,
        })
    except Exception:
        pass

    # Try Binance
    try:
        binance_ticker = binance.get_ticker(binance_symbol)
        binance_ob = binance.get_order_book(binance_symbol, 1)
        prices.append({
            "exchange": "binance",
            "last_price": float(binance_ticker.last_price),
            "bid": float(binance_ob.bids[0].price) if binance_ob.bids else None,
            "ask": float(binance_ob.asks[0].price) if binance_ob.asks else None,
        })
    except Exception:
        pass

    # Try OKX
    try:
        okx_ticker = okx.get_ticker(okx_symbol)
        okx_ob = okx.get_order_book(okx_symbol, 1)
        prices.append({
            "exchange": "okx",
            "last_price": float(okx_ticker.last_price),
            "bid": float(okx_ob.bids[0].price) if okx_ob.bids else None,
            "ask": float(okx_ob.asks[0].price) if okx_ob.asks else None,
        })
    except Exception:
        pass

    if not prices:
        return {"error": f"Could not fetch prices for {symbol}"}

    # Find best bid (highest) and ask (lowest)
    best_bid = max((p["bid"] for p in prices if p["bid"]), default=None)
    best_ask = min((p["ask"] for p in prices if p["ask"]), default=None)
    best_bid_exchange = next((p["exchange"] for p in prices if p["bid"] == best_bid), None)
    best_ask_exchange = next((p["exchange"] for p in prices if p["ask"] == best_ask), None)

    # Calculate spread
    if best_bid and best_ask:
        spread_pct = ((best_ask - best_bid) / best_bid) * 100
    else:
        spread_pct = None

    return {
        "symbol": symbol,
        "prices": prices,
        "best_bid": {
            "exchange": best_bid_exchange,
            "price": best_bid,
        },
        "best_ask": {
            "exchange": best_ask_exchange,
            "price": best_ask,
        },
        "spread_percent": spread_pct,
    }


@mcp.tool()
def get_arbitrage_opportunities(symbols: list[str] | None = None, min_spread: float = 0.1) -> list[dict[str, Any]]:
    """
    Find potential arbitrage opportunities across exchanges.

    Args:
        symbols: List of symbols to check (default: major cryptocurrencies)
        min_spread: Minimum spread percentage to consider (default: 0.1%)

    Returns:
        List of arbitrage opportunities sorted by spread
    """
    if symbols is None:
        symbols = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK", "MATIC", "DOT"]

    opportunities = []

    for symbol in symbols:
        comparison = compare_prices(symbol)
        if "error" in comparison:
            continue

        spread = comparison.get("spread_percent")
        if spread and spread > min_spread:
            opportunities.append({
                "symbol": symbol,
                "buy_exchange": comparison["best_ask"]["exchange"],
                "sell_exchange": comparison["best_bid"]["exchange"],
                "buy_price": comparison["best_ask"]["price"],
                "sell_price": comparison["best_bid"]["price"],
                "spread_percent": spread,
            })

    # Sort by spread (highest first)
    opportunities.sort(key=lambda x: x["spread_percent"], reverse=True)

    return opportunities


# ===== Status and Info =====

@mcp.tool()
def get_supported_exchanges() -> dict[str, dict[str, Any]]:
    """
    Get list of supported exchanges and their authentication status.

    Returns:
        Dictionary of exchanges with authentication status
    """
    return {
        name: {
            "authenticated": EXCHANGES[name].is_authenticated,
            "public_api": True,
            "private_api": EXCHANGES[name].is_authenticated,
        }
        for name in EXCHANGES
    }


# ===== Main =====

if __name__ == "__main__":
    mcp.run(transport="stdio")
