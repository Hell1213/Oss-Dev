"""Provider contracts — interfaces for GitHub, Git, and LLM integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional


@dataclass
class Issue:
    number: int
    title: str
    body: str
    state: str
    labels: list[str]
    url: str
    owner: str = ""
    repo: str = ""


@dataclass
class PullRequest:
    url: str
    number: int
    title: str
    state: str = "open"


@dataclass
class PRStatus:
    state: str
    is_draft: bool = False
    review_decision: Optional[str] = None
    url: str = ""


@dataclass
class Comment:
    body: str
    user: str
    created_at: str


class GitHubProvider(ABC):
    @abstractmethod
    async def fetch_issue(self, owner: str, repo: str, issue_number: int) -> Issue:
        ...

    @abstractmethod
    async def list_issues(
        self, owner: str, repo: str, state: str = "open", limit: int = 10
    ) -> list[Issue]:
        ...

    @abstractmethod
    async def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> PullRequest:
        ...

    @abstractmethod
    async def get_pr_status(
        self, owner: str, repo: str, pr_number: int
    ) -> PRStatus:
        ...

    @abstractmethod
    async def get_pr_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[Comment]:
        ...


@dataclass
class GitStatus:
    branch: str
    staged: list[str] = field(default_factory=list)
    unstaged: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0


@dataclass
class Commit:
    hash: str
    message: str
    author: str
    timestamp: str


class GitProvider(ABC):
    @abstractmethod
    async def current_branch(self) -> str:
        ...

    @abstractmethod
    async def create_branch(self, name: str, base: str = "main") -> None:
        ...

    @abstractmethod
    async def checkout(self, branch: str) -> None:
        ...

    @abstractmethod
    async def commit(
        self, message: str, files: Optional[list[str]] = None
    ) -> str:
        ...

    @abstractmethod
    async def push(
        self, remote: str = "origin", branch: Optional[str] = None
    ) -> None:
        ...

    @abstractmethod
    async def diff(
        self, base: Optional[str] = None, head: Optional[str] = None
    ) -> str:
        ...

    @abstractmethod
    async def status(self) -> GitStatus:
        ...

    @abstractmethod
    async def log(self, max_count: int = 10) -> list[Commit]:
        ...


@dataclass
class Message:
    role: str
    content: str
    tool_calls: Optional[list[dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class StreamEvent:
    type: str
    text_delta: Optional[str] = None
    tool_call: Optional[Any] = None
    error: Optional[str] = None
    usage: Optional[Any] = None


class LLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[Message],
        tools: Optional[list[ToolSchema]] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @property
    @abstractmethod
    def context_window(self) -> int:
        ...


from enum import Enum, auto


class ProviderCategory(Enum):
    GITHUB = auto()
    GIT = auto()
    LLM = auto()


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[tuple[ProviderCategory, str], Any] = {}
        self._defaults: dict[ProviderCategory, str] = {}

    def register(
        self, name: str, provider: Any, category: ProviderCategory
    ) -> None:
        self._providers[(category, name)] = provider

    def set_default(self, category: ProviderCategory, name: str) -> None:
        self._defaults[category] = name

    def get(self, name: str, category: ProviderCategory) -> Any:
        key = (category, name)
        if key not in self._providers:
            raise KeyError(f"Provider '{name}' not found in category {category}")
        return self._providers[key]

    def get_default(self, category: ProviderCategory) -> Any:
        name = self._defaults.get(category)
        if name is None:
            raise KeyError(f"No default provider for category {category}")
        return self.get(name, category)
