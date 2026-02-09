from __future__ import annotations
from enum import Enum
import os
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, model_validator


class ModelConfig(BaseModel):
    # Default to Gemini 2.0 Flash Experimental for hackathon
    # This is the primary and intended model for OSS Dev Agent
    name: str = "gemini-2.0-flash-exp"
    temperature: float = Field(default=1, ge=0.0, le=2.0)
    context_window: int = 1_000_000  # Gemini 2.0 supports up to 1M tokens
    api_key: str | None = Field(
        default=None,
        description="Gemini API key (can also be set via GEMINI_API_KEY or API_KEY env var)",
    )
    base_url: str | None = Field(
        default=None,
        description="Base URL for LLM API. For Gemini (primary), set to OpenAI-compatible endpoint. Leave None for default (fallback/dev only).",
    )
    # Provider selection: 'gemini' (default) or 'openai' (fallback/dev only)
    provider: str = Field(
        default="gemini",
        description="LLM provider: 'gemini' (primary) or 'openai' (fallback/dev only)",
    )


class ShellEnvironmentPolicy(BaseModel):
    ignore_default_excludes: bool = False
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*KEY*", "*TOKEN*", "*SECRET*"]
    )
    set_vars: dict[str, str] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    enabled: bool = True
    startup_timeout_sec: float = 10

    # stdio transport
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None

    # http/sse transport
    url: str | None = None

    @model_validator(mode="after")
    def validate_transport(self) -> MCPServerConfig:
        has_command = self.command is not None
        has_url = self.url is not None

        if not has_command and not has_url:
            raise ValueError(
                "MCP Server must have either 'command' (stdio) or 'url' (http/sse)"
            )

        if has_command and has_url:
            raise ValueError(
                "MCP Server cannot have both 'command' (stdio) and 'url' (http/sse)"
            )

        return self


class ApprovalPolicy(str, Enum):
    ON_REQUEST = "on-request"
    ON_FAILURE = "on-failure"
    AUTO = "auto"
    AUTO_EDIT = "auto-edut"
    NEVER = "never"
    YOLO = "yolo"


class HookTrigger(str, Enum):
    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"


class HookConfig(BaseModel):
    name: str
    trigger: HookTrigger
    command: str | None = None  # python3 tests.py
    script: str | None = None  # *.sh
    timeout_sec: float = 30
    enabled: bool = True

    @model_validator(mode="after")
    def validate_hook(self) -> HookConfig:
        if not self.command and not self.script:
            raise ValueError("Hook must either have 'command' or 'script'")
        return self


class OSSConfig(BaseModel):
    """OSS Dev Agent specific configuration"""

    enabled: bool = Field(
        default=True,
        description="Enable OSS Dev Agent features",
    )
    github_token: str | None = Field(
        default=None,
        description="GitHub token for API access (optional if using GitHub CLI)",
    )
    default_base_branch: str = Field(
        default="main",
        description="Default base branch for PRs (main or master)",
    )
    auto_create_start_here: bool = Field(
        default=True,
        description="Automatically create START_HERE.md if missing",
    )
    branch_naming_pattern: str = Field(
        default="fix/issue-{number}",
        description="Pattern for branch naming (use {number} for issue number)",
    )
    require_tests_before_pr: bool = Field(
        default=True,
        description="Require tests to pass before creating PR",
    )


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)
    shell_environment: ShellEnvironmentPolicy = Field(
        default_factory=ShellEnvironmentPolicy
    )
    hooks_enabled: bool = False
    hooks: list[HookConfig] = Field(default_factory=list)
    approval: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    max_turns: int = 100
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    allowed_tools: list[str] | None = Field(
        None,
        description="If set, only these tools will be available to the agent",
    )

    developer_instructions: str | None = None
    user_instructions: str | None = None

    # OSS Dev Agent configuration
    oss: OSSConfig = Field(
        default_factory=OSSConfig,
        description="OSS Dev Agent configuration",
    )

    debug: bool = False

    @property
    def api_key(self) -> str | None:
        """Get API key from config file first, then environment variable."""
        # Try config file first
        if self.model.api_key:
            return self.model.api_key
        # For Gemini (default), check GEMINI_API_KEY first, then API_KEY
        if self.model.provider == "gemini":
            return os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY")
        # For OpenAI fallback, use API_KEY
        return os.environ.get("API_KEY")

    @property
    def base_url(self) -> str | None:
        """Get base URL from config file first, then environment variable."""
        # Try config file first
        if self.model.base_url:
            return self.model.base_url
        # Fall back to environment variable
        return os.environ.get("BASE_URL")

    @property
    def github_token(self) -> str | None:
        """Get GitHub token from config or environment."""
        if self.oss.github_token:
            return self.oss.github_token
        return os.environ.get("GITHUB_TOKEN")

    @property
    def model_name(self) -> str:
        return self.model.name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self.model.name = value

    @property
    def temperature(self) -> float:
        return self.model.temperature

    @model_name.setter
    def temperature(self, value: str) -> None:
        self.model.temperature = value

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.api_key:
            if self.model.provider == "gemini":
                errors.append(
                    "No Gemini API key found. Set GEMINI_API_KEY (or API_KEY) environment variable or add 'api_key' to [model] section in .ai-agent/config.toml"
                )
            else:
                errors.append(
                    "No API key found. Set API_KEY environment variable or add 'api_key' to [model] section in .ai-agent/config.toml"
                )

        if not self.cwd.exists():
            errors.append(f"Working directory does not exist: {self.cwd}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
