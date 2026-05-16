"""Workflow contracts — state machine interfaces for the contribution workflow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class WorkflowPhase(str, Enum):
    IDLE = "idle"
    REPO_ANALYSIS = "repo_analysis"
    ISSUE_ANALYSIS = "issue_analysis"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    VALIDATION = "validation"
    COMMIT_PR = "commit_pr"
    COMPLETE = "complete"
    BLOCKED = "blocked"


PHASE_ORDER: list[WorkflowPhase] = [
    WorkflowPhase.IDLE,
    WorkflowPhase.REPO_ANALYSIS,
    WorkflowPhase.ISSUE_ANALYSIS,
    WorkflowPhase.PLANNING,
    WorkflowPhase.IMPLEMENTATION,
    WorkflowPhase.VERIFICATION,
    WorkflowPhase.VALIDATION,
    WorkflowPhase.COMMIT_PR,
    WorkflowPhase.COMPLETE,
]


@dataclass
class WorkflowState:
    workflow_id: str
    phase: WorkflowPhase = WorkflowPhase.IDLE
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    branch_name: Optional[str] = None
    repository_path: Optional[Path] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1


class PhaseValidator(ABC):
    @abstractmethod
    async def validate(self, state: WorkflowState) -> tuple[bool, str]:
        ...


class WorkflowEngine(ABC):
    @abstractmethod
    async def start(self, issue_url: str) -> WorkflowState:
        ...

    @abstractmethod
    async def transition(self, to_phase: WorkflowPhase) -> WorkflowState:
        ...

    @abstractmethod
    async def complete_phase(self) -> WorkflowState:
        ...

    @abstractmethod
    async def fail_phase(self, reason: str) -> WorkflowState:
        ...

    @abstractmethod
    async def get_state(self) -> WorkflowState:
        ...

    @abstractmethod
    async def save_state(self) -> None:
        ...

    @abstractmethod
    async def load_state(self, workflow_id: str) -> Optional[WorkflowState]:
        ...
