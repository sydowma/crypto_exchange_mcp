"""External MCP server integration for exchange-specific implementations."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from core.exceptions import ExchangeError


DEFAULT_TIMEOUT_SECONDS = 60

DEFAULT_EXTERNAL_MCP_SERVERS: dict[str, dict[str, Any]] = {
    "bybit": {
        "command": "npx",
        "args": ["-y", "bybit-official-trading-server@latest"],
        "env_keys": [
            "BYBIT_API_KEY",
            "BYBIT_API_SECRET",
            "BYBIT_API_PRIVATE_KEY_PATH",
            "BYBIT_TESTNET",
        ],
        "description": "Official Bybit Trading MCP server.",
        "source": "https://github.com/bybit-exchange/trading-mcp",
    },
    "okx": {
        "command": "npx",
        "args": [
            "-y",
            "@okx_ai/okx-trade-mcp@latest",
            "--modules",
            "market",
            "--read-only",
        ],
        "env_keys": [
            "OKX_API_KEY",
            "OKX_API_SECRET",
            "OKX_PASSPHRASE",
            "OKX_PROFILE",
        ],
        "description": "Official OKX Agent Trade Kit MCP server, market/read-only by default.",
        "source": "https://github.com/okx/agent-trade-kit",
    },
    "binance": {
        "command": "uvx",
        "args": ["--from", "binance-mcp-server", "binance-mcp-server"],
        "env_keys": [
            "BINANCE_API_KEY",
            "BINANCE_API_SECRET",
            "BINANCE_TESTNET",
        ],
        "description": "Community Binance MCP server from AnalyticAce.",
        "source": "https://github.com/AnalyticAce/binance-mcp-server",
    },
}


@dataclass(frozen=True)
class ExternalMCPServerSpec:
    """Configuration for one stdio MCP child server."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    env_keys: list[str] = field(default_factory=list)
    cwd: str | None = None
    enabled: bool = True
    description: str | None = None
    source: str | None = None

    @classmethod
    def from_mapping(cls, name: str, data: dict[str, Any]) -> "ExternalMCPServerSpec":
        """Create a spec from JSON-compatible configuration."""
        if "command" not in data:
            raise ExchangeError(f"External MCP server '{name}' is missing command")

        args = data.get("args", [])
        if not isinstance(args, list):
            raise ExchangeError(f"External MCP server '{name}' args must be a list")

        env = data.get("env", {})
        if not isinstance(env, dict):
            raise ExchangeError(f"External MCP server '{name}' env must be an object")

        env_keys = data.get("env_keys", [])
        if not isinstance(env_keys, list):
            raise ExchangeError(f"External MCP server '{name}' env_keys must be a list")

        return cls(
            name=name,
            command=str(data["command"]),
            args=[str(arg) for arg in args],
            env={str(key): str(value) for key, value in env.items()},
            env_keys=[str(key) for key in env_keys],
            cwd=str(data["cwd"]) if data.get("cwd") else None,
            enabled=bool(data.get("enabled", True)),
            description=data.get("description"),
            source=data.get("source"),
        )

    def effective_env(self) -> dict[str, str]:
        """Return child process environment overrides, including selected host env vars."""
        selected = {
            key: value
            for key in self.env_keys
            if (value := os.environ.get(key)) is not None
        }
        selected.update(self.env)
        return selected

    def to_public_dict(self) -> dict[str, Any]:
        """Return a safe summary without secret values."""
        configured_env = {
            key: key in os.environ or key in self.env
            for key in self.env_keys
        }
        return {
            "enabled": self.enabled,
            "command": self.command,
            "args": self.args,
            "cwd": self.cwd,
            "description": self.description,
            "source": self.source,
            "env_keys": self.env_keys,
            "configured_env": configured_env,
        }


def _truthy_env(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _load_config_payload() -> dict[str, Any]:
    inline_config = os.environ.get("CRYPTO_EXCHANGE_MCP_CONFIG_JSON")
    if inline_config:
        try:
            return json.loads(inline_config)
        except json.JSONDecodeError as exc:
            raise ExchangeError(f"Invalid CRYPTO_EXCHANGE_MCP_CONFIG_JSON: {exc}") from exc

    config_path = os.environ.get("CRYPTO_EXCHANGE_MCP_CONFIG")
    if not config_path:
        return {}

    path = Path(config_path).expanduser()
    if not path.exists():
        raise ExchangeError(f"External MCP config file does not exist: {path}")

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExchangeError(f"Invalid external MCP config file {path}: {exc}") from exc


def load_external_mcp_servers() -> dict[str, ExternalMCPServerSpec]:
    """Load built-in external MCP specs plus optional JSON overrides."""
    raw_servers: dict[str, dict[str, Any]] = {}
    if _truthy_env("CRYPTO_EXCHANGE_MCP_ENABLE_DEFAULTS", default=True):
        raw_servers.update({name: spec.copy() for name, spec in DEFAULT_EXTERNAL_MCP_SERVERS.items()})

    payload = _load_config_payload()
    override_servers = payload.get("servers", payload)
    if override_servers and not isinstance(override_servers, dict):
        raise ExchangeError("External MCP config must be an object or contain a 'servers' object")

    for name, override in override_servers.items():
        if override is None:
            raw_servers.pop(name, None)
            continue
        if not isinstance(override, dict):
            raise ExchangeError(f"External MCP server '{name}' config must be an object")
        raw_servers[name] = {**raw_servers.get(name, {}), **override}

    return {
        name: ExternalMCPServerSpec.from_mapping(name, data)
        for name, data in raw_servers.items()
    }


class ExternalMCPGateway:
    """Small stdio MCP proxy used by the unified exchange server."""

    def __init__(
        self,
        servers: dict[str, ExternalMCPServerSpec] | None = None,
        timeout_seconds: int | None = None,
    ):
        self.servers = servers if servers is not None else load_external_mcp_servers()
        self.timeout_seconds = timeout_seconds or int(
            os.environ.get("CRYPTO_EXCHANGE_MCP_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        )

    def list_servers(self) -> dict[str, dict[str, Any]]:
        """Return configured child MCP servers."""
        return {
            name: spec.to_public_dict()
            for name, spec in self.servers.items()
        }

    def list_tools(self, server_name: str) -> list[dict[str, Any]]:
        """List tools exposed by one external MCP server."""
        spec = self._get_enabled_server(server_name)
        return anyio.run(self._list_tools_async, spec)

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a tool exposed by one external MCP server."""
        spec = self._get_enabled_server(server_name)
        return anyio.run(self._call_tool_async, spec, tool_name, arguments or {})

    def _get_enabled_server(self, server_name: str) -> ExternalMCPServerSpec:
        key = server_name.lower()
        spec = self.servers.get(key)
        if spec is None:
            supported = ", ".join(sorted(self.servers)) or "none"
            raise ExchangeError(f"Unknown external MCP server '{server_name}'. Supported: {supported}")
        if not spec.enabled:
            raise ExchangeError(f"External MCP server '{server_name}' is disabled")
        return spec

    async def _list_tools_async(self, spec: ExternalMCPServerSpec) -> list[dict[str, Any]]:
        try:
            async with self._session(spec) as session:
                result = await session.list_tools()
        except Exception as exc:
            raise ExchangeError(f"External MCP server '{spec.name}' failed to list tools: {exc}") from exc

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in result.tools
        ]

    async def _call_tool_async(
        self,
        spec: ExternalMCPServerSpec,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            async with self._session(spec) as session:
                result = await session.call_tool(tool_name, arguments)
        except Exception as exc:
            raise ExchangeError(
                f"External MCP server '{spec.name}' failed to call tool '{tool_name}': {exc}"
            ) from exc

        return {
            "exchange": spec.name,
            "tool": tool_name,
            "is_error": result.isError,
            "content": [
                item.model_dump(mode="json", by_alias=True, exclude_none=True)
                if hasattr(item, "model_dump")
                else item
                for item in result.content
            ],
        }

    @asynccontextmanager
    async def _session(self, spec: ExternalMCPServerSpec):
        params = StdioServerParameters(
            command=spec.command,
            args=spec.args,
            env=spec.effective_env(),
            cwd=spec.cwd,
        )
        timeout = timedelta(seconds=self.timeout_seconds)

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timeout,
            ) as session:
                await session.initialize()
                yield session
