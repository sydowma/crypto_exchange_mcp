# Crypto Exchange MCP Python

Unified Model Context Protocol entrypoint for crypto exchanges.

It exposes the existing built-in REST tools for Bybit, Binance, and OKX, and can
also launch ready-made exchange MCP servers behind one entrypoint:

- Bybit official MCP: `npx -y bybit-official-trading-server@latest`
- OKX official MCP: `npx -y @okx_ai/okx-trade-mcp@latest --modules market --read-only`
- Binance community MCP: `uvx --from binance-mcp-server binance-mcp-server`

## Install

```bash
uv tool install crypto-exchange-mcp-python
```

Or run from this checkout:

```bash
uv run crypto-exchange-mcp
```

## MCP Client Config

```json
{
  "mcpServers": {
    "crypto-exchange": {
      "command": "uvx",
      "args": ["crypto-exchange-mcp-python"]
    }
  }
}
```

For local development:

```json
{
  "mcpServers": {
    "crypto-exchange": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/crypto_exchange_mcp/crypto_exchange_mcp_python",
        "run",
        "crypto-exchange-mcp"
      ]
    }
  }
}
```

## Built-in Tools

The unified server keeps the built-in REST tools:

- `get_ticker(exchange, symbol)`
- `get_orderbook(exchange, symbol, limit)`
- `get_klines(exchange, symbol, interval, limit)`
- `get_symbols(exchange, spot, futures)`
- `get_funding_rate(exchange, symbol)`
- `get_balance(exchange)`
- `get_positions(exchange)`
- `place_order(exchange, symbol, side, order_type, quantity, price)`
- `cancel_order(exchange, symbol, order_id)`
- `compare_prices(symbol)`
- `get_arbitrage_opportunities(symbols, min_spread)`

## External MCP Aggregation

Three tools provide the single entrypoint for ready-made exchange MCP servers:

- `get_external_mcp_servers()` lists configured child MCP servers.
- `list_exchange_mcp_tools(exchange)` starts one child server and lists its tools.
- `call_exchange_mcp_tool(exchange, tool_name, arguments)` calls one child tool.

The default external server names are `bybit`, `okx`, and `binance`. Defaults can
be disabled with:

```bash
export CRYPTO_EXCHANGE_MCP_ENABLE_DEFAULTS=false
```

Custom child servers or command overrides can be supplied with
`CRYPTO_EXCHANGE_MCP_CONFIG`:

```json
{
  "servers": {
    "okx": {
      "command": "npx",
      "args": [
        "-y",
        "@okx_ai/okx-trade-mcp@latest",
        "--modules",
        "market,spot,account",
        "--read-only"
      ],
      "env_keys": ["OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSPHRASE"]
    }
  }
}
```

Or inline with `CRYPTO_EXCHANGE_MCP_CONFIG_JSON`.

## Credentials

Built-in REST tools use these environment variables:

```bash
export BYBIT_API_KEY="..."
export BYBIT_API_SECRET="..."
export BINANCE_API_KEY="..."
export BINANCE_API_SECRET="..."
export OKX_API_KEY="..."
export OKX_API_SECRET="..."
export OKX_PASSPHRASE="..."
```

External MCP child servers receive only the selected `env_keys` listed in their
configuration. Secret values are never returned by `get_external_mcp_servers()`.

## Development

```bash
uv sync
uv run pytest test_external_mcp.py -q
uv build
```
