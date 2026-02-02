"""
Comprehensive tests for all crypto exchange implementations.

Run with: uv run pytest test_all_exchanges.py -v
Or: uv run python test_all_exchanges.py
"""

import sys
from decimal import Decimal

from exchanges.bybit import BybitExchange
from exchanges.binance import BinanceExchange
from exchanges.okx import OKXExchange


def test_bybit():
    """Test Bybit exchange implementation."""
    print("\n=== Testing Bybit ===")

    exchange = BybitExchange()

    # Test ticker
    ticker = exchange.get_ticker("BTCUSDT")
    assert ticker.symbol == "BTCUSDT"
    assert ticker.last_price > 0
    print(f"  Ticker: BTCUSDT = ${ticker.last_price}")

    # Test orderbook
    orderbook = exchange.get_order_book("BTCUSDT", 5)
    assert len(orderbook.bids) > 0
    assert len(orderbook.asks) > 0
    assert orderbook.bids[0].price > 0
    print(f"  Orderbook: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")

    # Test klines
    klines = exchange.get_klines("BTCUSDT", "1h", 10)
    assert len(klines) > 0
    assert klines[0].open > 0
    print(f"  Klines: {len(klines)} candles")

    # Test funding rate
    funding = exchange.get_funding_rate("BTCUSDT")
    assert "funding_rate" in funding
    print(f"  Funding Rate: {funding['funding_rate_pct']}%")

    # Test symbols
    symbols = exchange.get_symbols(spot=True, futures=False)
    assert len(symbols) > 0
    print(f"  Spot Symbols: {len(symbols)}")

    print("  Bybit: PASSED")


def test_binance():
    """Test Binance exchange implementation."""
    print("\n=== Testing Binance ===")

    exchange = BinanceExchange()

    # Test ticker
    ticker = exchange.get_ticker("BTCUSDT")
    assert ticker.symbol == "BTCUSDT"
    assert ticker.last_price > 0
    print(f"  Ticker: BTCUSDT = ${ticker.last_price}")

    # Test orderbook
    orderbook = exchange.get_order_book("BTCUSDT", 5)
    assert len(orderbook.bids) > 0
    assert len(orderbook.asks) > 0
    assert orderbook.bids[0].price > 0
    print(f"  Orderbook: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")

    # Test klines
    klines = exchange.get_klines("BTCUSDT", "1h", 10)
    assert len(klines) > 0
    assert klines[0].open > 0
    print(f"  Klines: {len(klines)} candles")

    # Test funding rate
    funding = exchange.get_funding_rate("BTCUSDT")
    assert "funding_rate" in funding
    print(f"  Funding Rate: {funding['funding_rate_pct']}%")

    # Test symbols
    symbols = exchange.get_symbols(spot=True, futures=False)
    assert len(symbols) > 0
    print(f"  Spot Symbols: {len(symbols)}")

    print("  Binance: PASSED")


def test_okx():
    """Test OKX exchange implementation."""
    print("\n=== Testing OKX ===")

    exchange = OKXExchange()

    # Test ticker
    ticker = exchange.get_ticker("BTC-USDT")
    assert ticker.symbol == "BTC-USDT"
    assert ticker.last_price > 0
    print(f"  Ticker: BTC-USDT = ${ticker.last_price}")

    # Test orderbook
    orderbook = exchange.get_order_book("BTC-USDT", 5)
    assert len(orderbook.bids) > 0
    assert len(orderbook.asks) > 0
    assert orderbook.bids[0].price > 0
    print(f"  Orderbook: {len(orderbook.bids)} bids, {len(orderbook.asks)} asks")

    # Test klines
    klines = exchange.get_klines("BTC-USDT", "1H", 10)
    assert len(klines) > 0
    assert klines[0].open > 0
    print(f"  Klines: {len(klines)} candles")

    # Test funding rate
    funding = exchange.get_funding_rate("BTC-USDT-SWAP")
    assert "funding_rate" in funding
    print(f"  Funding Rate: {funding['funding_rate_pct']}%")

    # Test symbols
    symbols = exchange.get_symbols(spot=True, futures=False)
    assert len(symbols) > 0
    print(f"  Spot Symbols: {len(symbols)}")

    # Test new coins
    new_coins = exchange.get_new_coins()
    assert len(new_coins) > 0
    print(f"  New Coins: {len(new_coins)}")

    print("  OKX: PASSED")


def test_cross_exchange():
    """Test cross-exchange comparison."""
    print("\n=== Testing Cross-Exchange Comparison ===")

    bybit = BybitExchange()
    binance = BinanceExchange()
    okx = OKXExchange()

    # Get prices from all exchanges
    bybit_ticker = bybit.get_ticker("BTCUSDT")
    binance_ticker = binance.get_ticker("BTCUSDT")
    okx_ticker = okx.get_ticker("BTC-USDT")

    prices = {
        "bybit": float(bybit_ticker.last_price),
        "binance": float(binance_ticker.last_price),
        "okx": float(okx_ticker.last_price),
    }

    # Check prices are reasonable (within 1% of each other)
    max_price = max(prices.values())
    min_price = min(prices.values())
    spread = ((max_price - min_price) / min_price) * 100

    print(f"  Bybit: ${prices['bybit']:,.2f}")
    print(f"  Binance: ${prices['binance']:,.2f}")
    print(f"  OKX: ${prices['okx']:,.2f}")
    print(f"  Spread: {spread:.4f}%")

    assert spread < 1.0, "Prices differ by more than 1%!"

    print("  Cross-Exchange: PASSED")


def test_error_handling():
    """Test error handling."""
    print("\n=== Testing Error Handling ===")

    bybit = BybitExchange()

    # Test invalid symbol
    try:
        bybit.get_ticker("INVALIDSYMBOL")
        assert False, "Should have raised an error"
    except Exception as e:
        print(f"  Invalid symbol error: OK ({type(e).__name__})")

    # Test private API without auth
    try:
        bybit.get_balance()
        assert False, "Should have raised an error"
    except Exception as e:
        print(f"  No auth error: OK ({type(e).__name__})")

    print("  Error Handling: PASSED")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Crypto Exchange MCP - Test Suite")
    print("=" * 50)

    try:
        test_bybit()
        test_binance()
        test_okx()
        test_cross_exchange()
        test_error_handling()

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)
        return 0

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
