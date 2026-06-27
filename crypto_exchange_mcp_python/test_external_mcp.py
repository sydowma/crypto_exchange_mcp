import sys
from pathlib import Path

import pytest

from core.exceptions import ExchangeError
from core.external_mcp import (
    ExternalMCPGateway,
    ExternalMCPServerSpec,
    load_external_mcp_servers,
)


def test_external_gateway_can_list_and_call_stdio_mcp():
    server_path = Path(__file__).with_name("server.py")
    gateway = ExternalMCPGateway(
        servers={
            "demo": ExternalMCPServerSpec(
                name="demo",
                command=sys.executable,
                args=[str(server_path)],
            )
        },
        timeout_seconds=5,
    )

    tools = gateway.list_tools("demo")
    assert {tool["name"] for tool in tools} == {"add"}

    result = gateway.call_tool("demo", "add", {"a": 2, "b": 3})
    assert result["exchange"] == "demo"
    assert result["tool"] == "add"
    assert result["is_error"] is False
    assert result["content"] == [{"type": "text", "text": "5"}]


def test_config_json_can_override_default_server(monkeypatch):
    monkeypatch.setenv("CRYPTO_EXCHANGE_MCP_ENABLE_DEFAULTS", "false")
    monkeypatch.setenv(
        "CRYPTO_EXCHANGE_MCP_CONFIG_JSON",
        """
        {
          "servers": {
            "demo": {
              "command": "python",
              "args": ["server.py"],
              "env_keys": ["DEMO_SECRET"]
            }
          }
        }
        """,
    )
    monkeypatch.setenv("DEMO_SECRET", "not-returned")

    servers = load_external_mcp_servers()

    assert list(servers) == ["demo"]
    public = servers["demo"].to_public_dict()
    assert public["configured_env"] == {"DEMO_SECRET": True}
    assert "not-returned" not in str(public)


def test_unknown_external_server_has_supported_names():
    gateway = ExternalMCPGateway(
        servers={
            "demo": ExternalMCPServerSpec(
                name="demo",
                command=sys.executable,
            )
        },
        timeout_seconds=5,
    )

    with pytest.raises(ExchangeError, match="Supported: demo"):
        gateway.list_tools("missing")
