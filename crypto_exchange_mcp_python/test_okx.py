import pytest
from okx import get_last_price

def test_get_last_price():
    assert get_last_price("BTC-USDT") > 0
