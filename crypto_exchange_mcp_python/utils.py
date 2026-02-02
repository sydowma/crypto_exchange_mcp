"""Utility functions for crypto exchange operations."""

from decimal import Decimal
from typing import Any

from exchanges.binance import BinanceExchange
from exchanges.bybit import BybitExchange
from exchanges.okx import OKXExchange


def compare_prices(symbol: str) -> dict[str, Any]:
    """Compare prices across all exchanges.

    Args:
        symbol: Base currency (e.g., BTC, ETH)

    Returns:
        Price comparison with best buy/sell prices
    """
    bybit = BybitExchange()
    binance = BinanceExchange()
    okx = OKXExchange()

    # Symbol format mapping
    bybit_symbol = f"{symbol}USDT"
    binance_symbol = f"{symbol}USDT"
    okx_symbol = f"{symbol}-USDT"

    prices = []

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


def get_arbitrage_opportunities(symbols: list[str] | None = None) -> list[dict[str, Any]]:
    """Find potential arbitrage opportunities across exchanges.

    Args:
        symbols: List of symbols to check (default: common cryptos)

    Returns:
        List of arbitrage opportunities
    """
    if symbols is None:
        symbols = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK", "MATIC", "DOT"]

    opportunities = []

    for symbol in symbols:
        comparison = compare_prices(symbol)
        if "error" in comparison:
            continue

        spread = comparison.get("spread_percent")
        if spread and spread > 0.1:  # Only show if spread > 0.1%
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


def format_price_comparison(comparison: dict[str, Any]) -> str:
    """Format price comparison for display.

    Args:
        comparison: Result from compare_prices()

    Returns:
        Formatted string
    """
    if "error" in comparison:
        return f"Error: {comparison['error']}"

    lines = [
        f"\n=== {comparison['symbol']} Price Comparison ===",
    ]

    for p in comparison["prices"]:
        lines.append(
            f"  {p['exchange'].upper():10} | "
            f"Last: ${p['last_price']:,.2f} | "
            f"Bid: ${p['bid']:,.2f} | "
            f"Ask: ${p['ask']:,.2f}"
        )

    lines.append(f"\n  Best Bid: {comparison['best_bid']['exchange'].upper()} @ ${comparison['best_bid']['price']:,.2f}")
    lines.append(f"  Best Ask: {comparison['best_ask']['exchange'].upper()} @ ${comparison['best_ask']['price']:,.2f}")

    if comparison["spread_percent"]:
        lines.append(f"  Spread: {comparison['spread_percent']:.4f}%")

    return "\n".join(lines)
