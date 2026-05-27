from typing import Any


class AgentError(Exception):
    """Base exception class for agent-related errors.

    Attributes:
        message: Human-readable error description.
        details: Additional error context as key-value pairs.
        cause: Original exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize AgentError.

        Args:
            message: Human-readable error description.
            details: Additional error context as key-value pairs.
            cause: Original exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        """Return string representation of the error.

        Returns:
            Formatted error string with details and cause.
        """
        base = self.message
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base = f"{base} ({detail_str})"
        if self.cause:
            base = f"{base} [caused by: {self.cause}]"
        return base

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary representation.

        Returns:
            Dictionary containing error type, message,
            details and cause.
        """
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


class ConfigError(AgentError):
    """Exception raised for configuration-related errors.

    Attributes:
        config_key: The configuration key that caused the error.
        config_file: The configuration file that caused the error.
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ConfigError.

        Args:
            message: Human-readable error description.
            config_key: Configuration key that caused the error.
            config_file: Configuration file that caused the error.
            **kwargs: Additional keyword arguments passed to AgentError.
        """
        details = kwargs.pop("details", {}) or {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, details=details, **kwargs)
        self.config_key = config_key
        self.config_file = config_file