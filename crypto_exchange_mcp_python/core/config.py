"""Configuration management for crypto exchange MCP."""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ExchangeCredentials:
    """Exchange API credentials."""

    api_key: str
    api_secret: str
    passphrase: str | None = None  # Required for OKX

    def validate(self) -> bool:
        """Validate credentials."""
        if not self.api_key or not self.api_secret:
            return False
        return True


class Config:
    """Configuration manager for exchange credentials."""

    def __init__(self, load_env: bool = True):
        self._credentials: dict[str, ExchangeCredentials] = {}
        if load_env:
            self.load_from_env()

    def load_from_env(self):
        """Load credentials from environment variables.

        Environment variables:
        - BYBIT_API_KEY, BYBIT_API_SECRET
        - BINANCE_API_KEY, BINANCE_API_SECRET
        - OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE
        """
        # Bybit
        bybit_key = os.getenv("BYBIT_API_KEY")
        bybit_secret = os.getenv("BYBIT_API_SECRET")
        if bybit_key and bybit_secret:
            self._credentials["bybit"] = ExchangeCredentials(
                api_key=bybit_key,
                api_secret=bybit_secret,
            )

        # Binance
        binance_key = os.getenv("BINANCE_API_KEY")
        binance_secret = os.getenv("BINANCE_API_SECRET")
        if binance_key and binance_secret:
            self._credentials["binance"] = ExchangeCredentials(
                api_key=binance_key,
                api_secret=binance_secret,
            )

        # OKX
        okx_key = os.getenv("OKX_API_KEY")
        okx_secret = os.getenv("OKX_API_SECRET")
        okx_passphrase = os.getenv("OKX_PASSPHRASE")
        if okx_key and okx_secret:
            self._credentials["okx"] = ExchangeCredentials(
                api_key=okx_key,
                api_secret=okx_secret,
                passphrase=okx_passphrase,
            )

    def get_credentials(self, exchange: str) -> ExchangeCredentials | None:
        """Get credentials for an exchange."""
        return self._credentials.get(exchange.lower())

    def has_credentials(self, exchange: str) -> bool:
        """Check if credentials exist for an exchange."""
        creds = self.get_credentials(exchange)
        return creds is not None and creds.validate()

    def set_credentials(self, exchange: str, credentials: ExchangeCredentials):
        """Set credentials for an exchange."""
        self._credentials[exchange.lower()] = credentials


# Global config instance
config = Config()
