from typing import Any


class AgentError(Exception):
    """Custom exception for errors that happen inside the agent.

    Attributes:
        message: The error message.
        details: Extra info about what went wrong.
        cause: The exception that caused this, if any.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Sets up the error with a message and optional extra context.

        Args:
            message: A short description of what went wrong.
            details: Optional dict with more info about the error.
            cause: The original exception that led to this one, if any.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        """Builds a readable string from the error info.

        Returns:
            The error message, with details and cause included if present.
        """
        base = self.message
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base = f"{base} ({detail_str})"
        if self.cause:
            base = f"{base} [caused by: {self.cause}]"
        return base

    def to_dict(self) -> dict[str, Any]:
        """Turns the error into a plain dictionary.

        Returns:
            A dict with the error type, message, details, and cause.
        """
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


class ConfigError(AgentError):
    """Raised when something goes wrong with the configuration.

    Attributes:
        config_key: The config key that caused the issue.
        config_file: The config file where the problem was found.
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Sets up the config error with relevant file/key info.

        Args:
            message: Description of the config problem.
            config_key: The key in the config that caused the error.
            config_file: Path to the config file with the issue.
            **kwargs: Any extra args passed up to AgentError.
        """
        details = kwargs.pop("details", {}) or {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, details=details, **kwargs)
        self.config_key = config_key
        self.config_file = config_file
