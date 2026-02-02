"""Binance MCP server - individual exchange server."""

from mcp.server.fastmcp import FastMCP
from decimal import Decimal

from exchanges.binance import BinanceExchange
from core.config import Config

mcp = FastMCP("binance")

config = Config()
binance = BinanceExchange()


@mcp.tool()
def get_last_price(symbol: str) -> float:
    """
    Get the Binance last price of a symbol

    Args:
        symbol: The symbol to get the last price of (e.g. BTCUSDT)
    Returns:
        The last price of the symbol
    """
    ticker = binance.get_ticker(symbol)
    return float(ticker.last_price)


@mcp.tool()
def get_price_change(symbol: str) -> str:
    """
    Get the Binance price change of a symbol (24h percentage)

    Args:
        symbol: The symbol to get the price change of (e.g. BTCUSDT)
    Returns:
        The price change percentage
    """
    ticker = binance.get_ticker(symbol)
    return f"{ticker.price_change_pct_24h}%"


@mcp.tool()
def get_order_book_spot(symbol: str, limit: int = 20) -> dict:
    """
    Get the Binance order book of a symbol for spot trading

    Args:
        symbol: Trading symbol (e.g. BTCUSDT)
        limit: Number of levels to return
    """
    orderbook = binance.get_order_book(symbol, limit)
    return {
        "bids": [[str(b.price), str(b.size)] for b in orderbook.bids[:limit]],
        "asks": [[str(a.price), str(a.size)] for a in orderbook.asks[:limit]],
    }


@mcp.tool()
def get_klines(symbol: str, interval: str = "1h", limit: int = 100) -> list:
    """
    Get Binance klines/candlesticks for a symbol

    Args:
        symbol: Trading symbol (e.g. BTCUSDT)
        interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
        limit: Number of klines to return
    """
    klines = binance.get_klines(symbol, interval, limit)
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
    Get the Binance funding rate of a perpetual futures symbol

    Args:
        symbol: The perpetual futures symbol (e.g. BTCUSDT)
    """
    result = binance.get_funding_rate(symbol)
    return f"{result['funding_rate_pct']}%"


@mcp.tool()
def get_symbols(spot: bool = True, futures: bool = False) -> list[str]:
    """
    Get list of available trading symbols on Binance

    Args:
        spot: Include spot trading pairs
        futures: Include futures trading pairs
    """
    return binance.get_symbols(spot=spot, futures=futures)


if __name__ == "__main__":
    mcp.run(transport="stdio")
