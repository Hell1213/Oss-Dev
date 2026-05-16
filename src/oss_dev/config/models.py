"""Pydantic config models for OSS-Dev."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from oss_dev.core.approvals.manager import ApprovalPolicy


class ModelConfig(BaseModel):
    name: str = "gemini-2.0-flash-exp"
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    context_window: int = 1_000_000
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    provider: str = "gemini"


class OSSConfig(BaseModel):
    enabled: bool = True
    default_base_branch: str = "main"
    auto_create_start_here: bool = True
    branch_naming_pattern: str = "fix/issue-{number}"
    require_tests_before_pr: bool = True


class GitHubConfig(BaseModel):
    token: Optional[str] = Field(default=None)
    preferred_method: str = "cli"


class PluginConfig(BaseModel):
    enabled: bool = True
    directories: list[str] = Field(default_factory=list)


class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)
    approval: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    oss: OSSConfig = Field(default_factory=OSSConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    debug: bool = False

    @property
    def api_key(self) -> Optional[str]:
        if self.model.api_key:
            return self.model.api_key
        if self.model.provider == "gemini":
            return os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY")
        return os.environ.get("API_KEY")

    @property
    def github_token(self) -> Optional[str]:
        if self.github.token:
            return self.github.token
        return os.environ.get("GITHUB_TOKEN")
