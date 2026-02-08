"""
Tool for getting user confirmation before push/PR operations.
"""
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from config.config import Config
from tools.base import Tool, ToolInvocation, ToolResult, ToolKind

logger = logging.getLogger(__name__)


class UserConfirmParams(BaseModel):
    message: str
    default: bool = True


class UserConfirmTool(Tool):
    """Tool to get user confirmation for push/PR operations."""

    name = "user_confirm"
    description = "Ask user for yes/no confirmation. Use this before pushing changes or creating PRs."
    kind = ToolKind.READ

    def __init__(self, config: Config):
        super().__init__(config)
        self._pending_confirmation: dict[str, bool | None] = {}

    @property
    def schema(self) -> type[BaseModel]:
        return UserConfirmParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute user confirmation request."""
        params = UserConfirmParams(**invocation.params)
        
        # Store the confirmation request - the CLI will handle the actual prompt
        # For now, we'll use a simple approach: return a message that the CLI can intercept
        
        logger.info(f"User confirmation requested: {params.message}")
        
        # Return a special result that the CLI can intercept
        return ToolResult.success_result(
            f"CONFIRMATION_REQUIRED: {params.message}\n"
            f"Default: {'yes' if params.default else 'no'}\n"
            f"Please respond with 'yes' or 'no' in the CLI."
        )
