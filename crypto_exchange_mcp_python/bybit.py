"""Bybit MCP server - individual exchange server."""

from mcp.server.fastmcp import FastMCP
from decimal import Decimal

from exchanges.bybit import BybitExchange
from core.config import Config

mcp = FastMCP("bybit")

config = Config()
bybit = BybitExchange()


@mcp.tool()
def get_last_price(symbol: str, category: str = "spot") -> float:
    """
    Get the Bybit last price of a symbol

    Args:
        symbol: The symbol to get the last price of (e.g. BTCUSDT)
        category: The category (spot, linear, inverse, option)
    Returns:
        The last price of the symbol
    """
    ticker = bybit.get_ticker(symbol, category)
    return float(ticker.last_price)


@mcp.tool()
def get_last_price_by_currency(ccy: str, category: str = "spot") -> float:
    """
    Get the Bybit last price of a currency

    Args:
        ccy: The currency to get the last price of (e.g. BTC)
        category: The category (spot, linear)
    Returns:
        The last price of the currency
    """
    symbol = f"{ccy}USDT"
    ticker = bybit.get_ticker(symbol, category)
    return float(ticker.last_price)


@mcp.tool()
def get_price_change(symbol: str, category: str = "spot") -> str:
    """
    Get the Bybit price change of a symbol (24h percentage)

    Args:
        symbol: The symbol to get the price change of (e.g. BTCUSDT)
        category: The category (spot, linear, inverse, option)
    Returns:
        The price change percentage
    """
    ticker = bybit.get_ticker(symbol, category)
    return f"{ticker.price_change_pct_24h}%"


@mcp.tool()
def get_order_book_spot(symbol: str, limit: int = 20) -> dict:
    """
    Get the Bybit order book of a symbol for spot trading

    Args:
        symbol: Trading symbol (e.g. BTCUSDT)
        limit: Number of levels to return
    """
    orderbook = bybit.get_order_book(symbol, limit, category="spot")
    return {
        "bids": [[str(b.price), str(b.size)] for b in orderbook.bids[:limit]],
        "asks": [[str(a.price), str(a.size)] for a in orderbook.asks[:limit]],
    }


@mcp.tool()
def get_order_book_linear(symbol: str, limit: int = 20) -> dict:
    """
    Get the Bybit order book of a symbol for contract trading

    Args:
        symbol: Trading symbol (e.g. BTCUSDT)
        limit: Number of levels to return
    """
    orderbook = bybit.get_order_book(symbol, limit, category="linear")
    return {
        "bids": [[str(b.price), str(b.size)] for b in orderbook.bids[:limit]],
        "asks": [[str(a.price), str(a.size)] for a in orderbook.asks[:limit]],
    }


@mcp.tool()
def get_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
    category: str = "spot",
) -> list:
    """
    Get Bybit klines/candlesticks for a symbol

    Args:
        symbol: Trading symbol (e.g. BTCUSDT)
        interval: Kline interval (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M)
        limit: Number of klines to return
        category: Category (spot, linear, inverse, option)
    """
    klines = bybit.get_klines(symbol, interval, limit, category=category)
    return [
        {
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
def get_funding_rate(symbol: str) -> str:
    """
    Get the Bybit funding rate of a perpetual futures symbol

    Args:
        symbol: The perpetual futures symbol (e.g. BTCUSDT)
    """
    result = bybit.get_funding_rate(symbol)
    return f"{result['funding_rate_pct']}%"


@mcp.tool()
def get_open_interest(
    symbol: str,
    interval: str = "1d",
    start_time: str = None,
    end_time: str = None,
) -> float:
    """
    Get the Bybit open interest of a symbol for contract trading

    Args:
        symbol: The symbol to get the open interest of (e.g. BTCUSDT)
        interval: The interval (1d, 1h)
        start_time: The start timestamp (ms)
        end_time: The end timestamp (ms)
    Returns:
        The open interest value in USD
    """
    result = bybit.get_open_interest(symbol, interval, start_time, end_time)
    ticker = bybit.get_ticker(symbol, "linear")
    return float(result["open_interest"]) * float(ticker.last_price)


@mcp.tool()
def get_symbols(spot: bool = True, futures: bool = False) -> list[str]:
    """
    Get list of available trading symbols on Bybit

    Args:
        spot: Include spot trading pairs
        futures: Include futures trading pairs
    """
    return bybit.get_symbols(spot=spot, futures=futures)


if __name__ == "__main__":
    mcp.run(transport="stdio")
