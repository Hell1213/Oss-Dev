"""Async approval manager for safe mutation operations.

Replaces the legacy synchronous callback pattern with a proper async protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from oss_dev.core.errors import ApprovalError


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CONFIRMATION = "needs_confirmation"


class ApprovalPolicy(str, Enum):
    ON_REQUEST = "on-request"
    ON_FAILURE = "on-failure"
    AUTO = "auto"
    AUTO_EDIT = "auto-edit"
    NEVER = "never"
    YOLO = "yolo"


@dataclass
class ApprovalContext:
    tool_name: str
    params: dict[str, Any]
    is_mutating: bool
    affected_paths: list[Path] = field(default_factory=list)
    command: Optional[str] = None
    is_dangerous: bool = False


class ConfirmationCallback:
    """Async protocol for user confirmation."""

    async def confirm(self, context: ApprovalContext) -> bool:
        raise NotImplementedError


class ApprovalManager:
    """Manages approval decisions with async confirmation support."""

    def __init__(
        self,
        policy: ApprovalPolicy = ApprovalPolicy.ON_REQUEST,
        cwd: Optional[Path] = None,
        confirmation_callback: Optional[ConfirmationCallback] = None,
    ) -> None:
        self._policy = policy
        self._cwd = cwd or Path.cwd()
        self._confirmation_callback = confirmation_callback

    async def check_approval(self, context: ApprovalContext) -> ApprovalDecision:
        if not context.is_mutating:
            return ApprovalDecision.APPROVED

        if self._policy == ApprovalPolicy.YOLO:
            return ApprovalDecision.APPROVED

        if context.is_dangerous:
            return ApprovalDecision.NEEDS_CONFIRMATION

        if self._policy == ApprovalPolicy.NEVER:
            return ApprovalDecision.REJECTED

        if self._policy in (ApprovalPolicy.AUTO, ApprovalPolicy.ON_FAILURE):
            return ApprovalDecision.APPROVED

        if self._policy == ApprovalPolicy.AUTO_EDIT:
            if context.command and self._is_safe_command(context.command):
                return ApprovalDecision.APPROVED
            return ApprovalDecision.NEEDS_CONFIRMATION

        for path in context.affected_paths:
            if not path.is_relative_to(self._cwd):
                return ApprovalDecision.NEEDS_CONFIRMATION

        return ApprovalDecision.APPROVED

    async def request_confirmation(self, context: ApprovalContext) -> bool:
        if self._confirmation_callback is None:
            raise ApprovalError(
                "Confirmation required but no callback registered",
                details={"tool": context.tool_name},
            )
        return await self._confirmation_callback.confirm(context)

    def _is_safe_command(self, command: str) -> bool:
        safe_patterns = [
            "ls", "pwd", "echo", "cat", "head", "tail",
            "git status", "git log", "git diff", "git branch",
            "pytest", "ruff", "mypy", "coverage",
            "pip list", "pip show",
            "date", "whoami", "id", "uname",
            "ps", "which",
        ]
        cmd_lower = command.strip().lower()
        return any(cmd_lower.startswith(p) for p in safe_patterns)
