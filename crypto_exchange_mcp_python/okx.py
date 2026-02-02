"""OKX MCP server - individual exchange server."""

from mcp.server.fastmcp import FastMCP
from decimal import Decimal

from exchanges.okx import OKXExchange
from core.config import Config

mcp = FastMCP("okx")

config = Config()
okx = OKXExchange()


@mcp.tool()
def get_last_price(symbol: str) -> float:
    """
    Get the OKX last price of a symbol

    Args:
        symbol: The symbol to get the last price of (e.g. BTC-USDT)
    Returns:
        The last price of the symbol
    """
    ticker = okx.get_ticker(symbol)
    return float(ticker.last_price)


@mcp.tool()
def get_price_change(symbol: str) -> str:
    """
    Get the OKX price change of a symbol (24h percentage)

    Args:
        symbol: The symbol to get the price change of (e.g. BTC-USDT)
    Returns:
        The price change percentage
    """
    ticker = okx.get_ticker(symbol)
    return f"{ticker.price_change_pct_24h}%"


@mcp.tool()
def get_order_book_spot(symbol: str, limit: int = 20) -> dict:
    """
    Get the OKX order book of a symbol for spot trading

    Args:
        symbol: Trading symbol (e.g. BTC-USDT)
        limit: Number of levels to return
    """
    orderbook = okx.get_order_book(symbol, limit)
    return {
        "bids": [[str(b.price), str(b.size)] for b in orderbook.bids[:limit]],
        "asks": [[str(a.price), str(a.size)] for a in orderbook.asks[:limit]],
    }


@mcp.tool()
def get_klines(symbol: str, interval: str = "1H", limit: int = 100) -> list:
    """
    Get OKX klines/candlesticks for a symbol

    Args:
        symbol: Trading symbol (e.g. BTC-USDT)
        interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 1W, 1M)
        limit: Number of klines to return
    """
    klines = okx.get_klines(symbol, interval, limit)
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
    Get the OKX funding rate of a perpetual swap symbol

    Args:
        symbol: The perpetual swap symbol (e.g. BTC-USDT-SWAP)
    """
    result = okx.get_funding_rate(symbol)
    return f"{result['funding_rate_pct']}%"


@mcp.tool()
def get_symbols(spot: bool = True, futures: bool = False, swap: bool = False) -> list[str]:
    """
    Get list of available trading symbols on OKX

    Args:
        spot: Include spot trading pairs
        futures: Include futures
        swap: Include perpetual swaps
    """
    return okx.get_symbols(spot=spot, futures=futures, swap=swap)


@mcp.tool()
def get_new_coins(limit: int = 50) -> list[dict]:
    """
    Get recently listed coins on OKX (USDT pairs)

    Args:
        limit: Number of coins to return
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
