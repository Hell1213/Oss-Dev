"""Core contracts and interfaces for OSS-Dev."""

from oss_dev.core.contracts.provider import (
    GitHubProvider,
    GitProvider,
    LLMProvider,
    ProviderRegistry,
)
from oss_dev.core.contracts.workflow import (
    WorkflowEngine,
    WorkflowState,
    WorkflowPhase,
    PhaseValidator,
)
from oss_dev.core.contracts.plugin import (
    Plugin,
    PluginManifest,
)

__all__ = [
    "GitHubProvider",
    "GitProvider",
    "LLMProvider",
    "ProviderRegistry",
    "WorkflowEngine",
    "WorkflowState",
    "WorkflowPhase",
    "PhaseValidator",
    "Plugin",
    "PluginManifest",
]
