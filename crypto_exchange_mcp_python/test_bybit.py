import pytest
from bybit import (
    get_last_price,
    get_price_change,
    get_order_book_spot,
    get_order_book_linear,
    get_funding_rate,
    get_open_interest,
    get_last_price_by_currency
)

def test_get_last_price_symbol():
    result = get_last_price("BTCUSDT", "spot")
    assert isinstance(result, float)
    assert result > 0

def test_get_last_price_currency():
    result = get_last_price_by_currency("BTC", "spot")
    assert isinstance(result, float)
    assert result > 0

def test_get_price_change():
    result = get_price_change("BTCUSDT")
    assert result is not None
    assert isinstance(result, str)

def test_get_order_book_spot():
    result = get_order_book_spot("BTCUSDT")
    assert isinstance(result, dict)
    assert "asks" in result
    assert "bids" in result
    assert len(result["asks"]) > 0
    assert len(result["bids"]) > 0

def test_get_order_book_linear():
    result = get_order_book_linear("BTCUSDT")
    assert isinstance(result, dict)
    assert "asks" in result
    assert "bids" in result
    assert len(result["asks"]) > 0
    assert len(result["bids"]) > 0

def test_get_funding_rate():
    result = get_funding_rate("BTCUSDT")
    assert isinstance(result, str)
    assert "%" in result
    # Convert to float and check if it's a reasonable funding rate
    rate = float(result.strip("%"))
    assert -1 <= rate <= 1  # Funding rates are typically between -1% and 1%

def test_get_open_interest():
    result = get_open_interest("BTCUSDT")
    assert isinstance(result, float)
    assert result > 0

def test_get_open_interest_with_time_params():
    result = get_open_interest(
        "BTCUSDT",
        interval="1d",
        start_time="1717334400000",
        end_time="1717420800000"
    )
    assert isinstance(result, float)
    assert result > 0 