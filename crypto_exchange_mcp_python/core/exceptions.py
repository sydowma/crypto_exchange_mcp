"""Exceptions for crypto exchange MCP."""


class ExchangeError(Exception):
    """Base exception for exchange errors."""

    def __init__(self, message: str, code: int | None = None, raw_response: dict | None = None):
        self.message = message
        self.code = code
        self.raw_response = raw_response
        super().__init__(self.message)


class AuthenticationError(ExchangeError):
    """Raised when authentication fails."""

    pass


class RateLimitError(ExchangeError):
    """Raised when rate limit is exceeded."""

    pass


class InvalidSymbolError(ExchangeError):
    """Raised when symbol is invalid."""

    pass


class InsufficientBalanceError(ExchangeError):
    """Raised when balance is insufficient."""

    pass


class OrderError(ExchangeError):
    """Raised when order operation fails."""

    pass


class NetworkError(ExchangeError):
    """Raised when network error occurs."""

    pass
