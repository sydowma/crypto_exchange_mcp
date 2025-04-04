from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("okx")

API_BASE_URL = "https://okx.com"

@mcp.tool()
def get_last_price(symbol: str) -> float:
    """
    Get the okx exchange last price of a symbol

    Args:
        symbol: The symbol to get the last price of  (e.g. BTC-USDT)
    Returns:
        The last price of the symbol
    """
    url = f"{API_BASE_URL}/api/v5/market/ticker?instId={symbol}"
    response = requests.get(url)
    return float(response.json()["data"][0]["last"])


if __name__ == "__main__":
    mcp.run(transport='stdio')
    