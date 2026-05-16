"""Base error types for OSS-Dev."""

from typing import Any, Optional


class OssDevError(Exception):
    """Base exception for all OSS-Dev errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        base = self.message
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base = f"{base} ({detail_str})"
        if self.cause:
            base = f"{base} [caused by: {self.cause}]"
        return base


class ConfigError(OssDevError):
    """Configuration-related errors."""


class WorkflowError(OssDevError):
    """Workflow state machine errors."""


class ProviderError(OssDevError):
    """Provider integration errors."""


class ApprovalError(OssDevError):
    """Approval policy errors."""


class PluginError(OssDevError):
    """Plugin loading and execution errors."""


class StateError(OssDevError):
    """State persistence errors."""
