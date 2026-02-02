# Crypto Exchange MCP Server

A comprehensive MCP (Model Context Protocol) server implementation for cryptocurrency exchanges, supporting **Bybit**, **Binance**, and **OKX**. This package provides a unified interface to interact with both public APIs (market data) and private APIs (trading, account management).

## Features

### Public APIs (No authentication required)
- **Real-time price data** - Get current ticker information
- **Order book access** - Retrieve order book depth for spot and futures markets
- **Kline/candlestick data** - Historical OHLCV data with various intervals
- **Funding rate monitoring** - Track perpetual contract funding rates
- **Open interest tracking** - Monitor contract open interest (Bybit)
- **Trading pair information** - Query available symbols

### Private APIs (Authentication required)
- **Account balance** - Query wallet balances across multiple assets
- **Position management** - View open positions and unrealized PnL
- **Order placement** - Place market and limit orders
- **Order cancellation** - Cancel individual or all orders
- **Order history** - Retrieve past orders and fills
- **Open orders** - View pending orders

## Supported Exchanges

| Exchange | Spot | Futures | Public API | Private API |
|----------|------|---------|------------|-------------|
| Bybit    | ✅    | ✅      | ✅         | ✅          |
| Binance  | ✅    | ✅      | ✅         | ✅          |
| OKX      | ✅    | ✅      | ✅         | ✅          |

## Installation

### With uv (Recommended)

```shell
cd crypto_exchange_mcp/crypto_exchange_mcp_python
uv sync
```

### With pip

```shell
cd crypto_exchange_mcp/crypto_exchange_mcp_python
pip install -r requirements.txt
```

## Configuration

### For Public APIs Only

No configuration needed! Public market data endpoints work out of the box.

### For Private APIs

Set environment variables with your API credentials:

```bash
# Bybit
export BYBIT_API_KEY="your_bybit_api_key"
export BYBIT_API_SECRET="your_bybit_api_secret"

# Binance
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_API_SECRET="your_binance_api_secret"

# OKX
export OKX_API_KEY="your_okx_api_key"
export OKX_API_SECRET="your_okx_api_secret"
export OKX_PASSPHRASE="your_okx_passphrase"
```

Or copy `.env.example` to `.env` and fill in your credentials:

```shell
cp .env.example .env
```

## Usage with Claude Desktop

### Unified Server (Recommended)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "crypto-exchange": {
      "command": "uv",
      "args": [
        "--directory",
        "{your_path}/crypto_exchange_mcp/crypto_exchange_mcp_python",
        "run",
        "crypto_exchange_server.py"
      ],
      "env": {
        "BYBIT_API_KEY": "your_bybit_api_key",
        "BYBIT_API_SECRET": "your_bybit_api_secret",
        "BINANCE_API_KEY": "your_binance_api_key",
        "BINANCE_API_SECRET": "your_binance_api_secret",
        "OKX_API_KEY": "your_okx_api_key",
        "OKX_API_SECRET": "your_okx_api_secret",
        "OKX_PASSPHRASE": "your_okx_passphrase"
      }
    }
  }
}
```

### Individual Exchange Servers

You can also run each exchange separately:

```json
{
  "mcpServers": {
    "bybit": {
      "command": "uv",
      "args": [
        "--directory",
        "{your_path}/crypto_exchange_mcp/crypto_exchange_mcp_python",
        "run",
        "bybit.py"
      ]
    },
    "binance": {
      "command": "uv",
      "args": [
        "--directory",
        "{your_path}/crypto_exchange_mcp/crypto_exchange_mcp_python",
        "run",
        "binance.py"
      ]
    },
    "okx": {
      "command": "uv",
      "args": [
        "--directory",
        "{your_path}/crypto_exchange_mcp/crypto_exchange_mcp_python",
        "run",
        "okx.py"
      ]
    }
  }
}
```

## Available Tools

### Public Market Data

- `get_ticker(exchange, symbol)` - Get price and 24h statistics
- `get_orderbook(exchange, symbol, limit)` - Get order book depth
- `get_klines(exchange, symbol, interval, limit)` - Get candlestick data
- `get_symbols(exchange, spot, futures)` - List trading pairs
- `get_funding_rate(exchange, symbol)` - Get perpetual funding rate
- `get_open_interest(exchange, symbol)` - Get contract open interest
- `get_new_coins_okx(limit)` - Get newly listed coins on OKX

### Private Trading & Account

- `get_balance(exchange)` - Get account balances
- `get_positions(exchange)` - Get open positions
- `place_order(exchange, symbol, side, order_type, quantity, price)` - Place order
- `cancel_order(exchange, symbol, order_id)` - Cancel order
- `get_open_orders(exchange, symbol)` - Get pending orders
- `get_order_history(exchange, symbol, limit)` - Get order history

### Utility

- `get_supported_exchanges()` - List exchanges and auth status

## Symbol Format by Exchange

| Exchange | Spot Format | Futures Format |
|----------|-------------|----------------|
| Bybit    | `BTCUSDT`   | `BTCUSDT`     |
| Binance  | `BTCUSDT`   | `BTCUSDT`     |
| OKX      | `BTC-USDT`  | `BTC-USDT-SWAP` |

**Note:** OKX spot trading actually uses `-USD` suffix (e.g., `BTC-USD`), but `-USDT` also works for ticker queries.

## Architecture

```
crypto_exchange_mcp_python/
├── core/                      # Core abstractions
│   ├── __init__.py
│   ├── base.py               # Base exchange class and data models
│   ├── config.py             # Configuration and credential management
│   └── exceptions.py         # Custom exceptions
├── exchanges/                 # Exchange implementations
│   ├── bybit/
│   │   └── client.py         # Bybit API client
│   ├── binance/
│   │   └── client.py         # Binance API client
│   └── okx/
│       └── client.py         # OKX API client
├── bybit.py                  # Legacy Bybit MCP server
├── okx.py                    # Legacy OKX MCP server
├── crypto_exchange_server.py # Unified MCP server
└── .env.example              # Example configuration
```

## API Documentation

- [Bybit API](https://bybit-exchange.github.io/docs/v5/)
- [Binance API](https://binance-docs.github.io/apidocs/)
- [OKX API](https://www.okx.com/docs-v5/)

## License

Apache License 2.0
