"""Plugin contracts — interfaces for the OSS-Dev plugin system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: Optional[str] = None
    entry_point: str = ""
    dependencies: list[str] = field(default_factory=list)


class HookHandler:
    """Callable type for plugin hooks."""


class Command:
    """CLI command definition from a plugin."""

    def __init__(
        self,
        name: str,
        help_text: str,
        callback: Any,
    ) -> None:
        self.name = name
        self.help_text = help_text
        self.callback = callback


class Plugin(ABC):
    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    async def initialize(self, config: Any) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    def get_commands(self) -> list[Command]:
        return []

    def get_tools(self) -> list[Any]:
        return []

    def get_hooks(self) -> dict[str, HookHandler]:
        return {}
