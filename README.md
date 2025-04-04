# Description

MCP server implementation for the cryptocurrency exchange. This package provides a simple interface to interact with Bybit/OKX/Binance public API endpoints.

## Features

- Real-time price data retrieval
- Order book access for both spot and linear markets
- Funding rate monitoring
- Open interest tracking
- Price change percentage calculations


## bybit example with Claude desktop

1. git clone repo
```shell
git clone https://github.com/sydowma/crypto_exchange_mcp.git
```
2. update settings
`~/Library/Application\ Support/Claude/claude_desktop_config.json`

`{your_path}` means git repo fold path

```json
{
  "mcpServers": {
    "Bybit": {
      "command": "uv",
      "args": [
        "--directory",
        "{your_path}/crypto_exchange_mcp/crypto_exchange_mcp_python",
        "run",
        "bybit.py"
      ]
    }
  }
}
```

3. open/restart your Claude desktop app

