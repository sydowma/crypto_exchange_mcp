

from mcp.server.fastmcp import FastMCP
import requests

# Create an MCP server
mcp = FastMCP("bybit")

API_BASE_URL = "https://api.bybit.com"


@mcp.tool()
def get_last_price(symbol: str, category: str = "spot") -> float:
    """
    Get the bybit last price of a symbol

    Args:
        symbol: The symbol to get the last price of  (e.g. BTCUSDT)
        category: The category to get the last price of  (e.g. spot, linear)
    Returns:
        The last price of the symbol
    """
    url = f"{API_BASE_URL}/v5/market/tickers?category={category}&symbol={symbol}"
    response = requests.get(url)
    return float(response.json()["result"]["list"][0]["lastPrice"])

@mcp.tool()
def get_last_price(ccy: str, category: str = "spot") -> float:
    """
    Get the bybit last price of a currency

    Args:
        ccy: The currency to get the last price of  (e.g. BTC)
        category: The category to get the last price of  (e.g. spot, linear)
    Returns:
        The last price of the currency
    """
    url = f"{API_BASE_URL}/v5/market/tickers?category={category}&symbol={ccy}USDT"
    response = requests.get(url)
    return float(response.json()["result"]["list"][0]["lastPrice"])

@mcp.tool()
def get_price_change(symbol: str) -> float:
    """
    Get the bybit price change of a symbol
    """
    url = f"{API_BASE_URL}/v5/market/tickers?category=spot&symbol={symbol}"
    response = requests.get(url)
    return float(response.json()["result"]["list"][0]["priceChange"])

@mcp.tool()
def get_order_book_spot(symbol: str) -> dict:
    """
    Get the bybit order book of a symbol for spot trading
    """
    url = f"{API_BASE_URL}/v5/market/orderbook?category=spot&symbol={symbol}"
    response = requests.get(url)
    return response.json()["result"]["list"]

@mcp.tool()
def get_order_book_linear(symbol: str) -> dict:
    """
    Get the bybit order book of a symbol for contract trading
    """
    url = f"{API_BASE_URL}/v5/market/orderbook?category=linear&symbol={symbol}"
    response = requests.get(url)
    return response.json()["result"]["list"]

@mcp.tool()
def get_funding_rate(symbol: str) -> str:
    """
    Get the bybit funding rate of a symbol
    """
    url = f"{API_BASE_URL}/v5/market/tickers?category=linear&symbol={symbol}"
    response = requests.get(url)
    funding_rate = float(response.json()['result']['list'][0]['fundingRate'])
    return f"{funding_rate * 100}%"

@mcp.tool()
def get_open_interest(symbol: str, interval: str, start_time: str=None, end_time: str=None) -> float:
    """
    Get the bybit open interest of a symbol for contract trading

    Args:
        symbol: The symbol to get the open interest of  (e.g. BTCUSDT)
        interval: The interval to get the open interest of  (e.g. 5min, 15min, 30min,1h, 4h, 1d)
        start_time: The start time to get the open interest of  (e.g. 1717334400000) The start timestamp (ms)
        end_time: The end time to get the open interest of  (e.g. 1717334400000) The end timestamp (ms)
    Returns:
        The open interest of the symbol
    """
    url = f"{API_BASE_URL}/v5/market/open-interest?category=linear&symbol={symbol}&intervalTime={interval}&limit=1"
    if start_time:
        url += f"&startTime={start_time}"
    if end_time:
        url += f"&endTime={end_time}"
    response = requests.get(url)
    last_price = get_last_price(symbol, "linear")   
    return float(response.json()["result"]["list"][0]["openInterest"]) * last_price

if __name__ == "__main__":
    mcp.run(transport='stdio')
