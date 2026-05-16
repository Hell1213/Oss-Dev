"""Deterministic workflow state machine.

Manages phase transitions with strict validation and no hidden side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from oss_dev.core.contracts.workflow import (
    PHASE_ORDER,
    WorkflowEngine,
    WorkflowPhase,
    WorkflowState,
    PhaseValidator,
)
from oss_dev.core.errors import WorkflowError


@dataclass
class TransitionRule:
    from_phase: WorkflowPhase
    to_phase: WorkflowPhase
    trigger: str
    guard: Optional[str] = None


TRANSITION_RULES: list[TransitionRule] = [
    TransitionRule(WorkflowPhase.IDLE, WorkflowPhase.REPO_ANALYSIS, "start"),
    TransitionRule(WorkflowPhase.REPO_ANALYSIS, WorkflowPhase.ISSUE_ANALYSIS, "complete"),
    TransitionRule(WorkflowPhase.ISSUE_ANALYSIS, WorkflowPhase.PLANNING, "complete"),
    TransitionRule(WorkflowPhase.PLANNING, WorkflowPhase.IMPLEMENTATION, "complete"),
    TransitionRule(WorkflowPhase.IMPLEMENTATION, WorkflowPhase.VERIFICATION, "complete"),
    TransitionRule(WorkflowPhase.VERIFICATION, WorkflowPhase.VALIDATION, "complete"),
    TransitionRule(WorkflowPhase.VERIFICATION, WorkflowPhase.IMPLEMENTATION, "retry"),
    TransitionRule(WorkflowPhase.VALIDATION, WorkflowPhase.COMMIT_PR, "complete"),
    TransitionRule(WorkflowPhase.COMMIT_PR, WorkflowPhase.COMPLETE, "complete"),
]


def _is_valid_transition(current: WorkflowPhase, target: WorkflowPhase) -> bool:
    current_idx = PHASE_ORDER.index(current) if current in PHASE_ORDER else -1
    target_idx = PHASE_ORDER.index(target) if target in PHASE_ORDER else -1
    if current_idx >= 0 and target_idx >= 0:
        return target_idx == current_idx + 1
    return False


class SimpleStateMachine(WorkflowEngine):
    """Deterministic workflow state machine with validation."""

    def __init__(
        self,
        state: Optional[WorkflowState] = None,
        validators: Optional[dict[WorkflowPhase, PhaseValidator]] = None,
    ) -> None:
        self._state = state or WorkflowState(workflow_id="")
        self._validators = validators or {}

    async def start(self, issue_url: str) -> WorkflowState:
        if self._state.phase != WorkflowPhase.IDLE:
            raise WorkflowError(
                f"Cannot start workflow from phase {self._state.phase.value}"
            )
        self._state.issue_url = issue_url
        self._state.phase = WorkflowPhase.REPO_ANALYSIS
        self._state.updated_at = datetime.now()
        return self._state

    async def transition(self, to_phase: WorkflowPhase) -> WorkflowState:
        if not _is_valid_transition(self._state.phase, to_phase):
            raise WorkflowError(
                f"Invalid transition: {self._state.phase.value} -> {to_phase.value}",
                details={
                    "current": self._state.phase.value,
                    "target": to_phase.value,
                },
            )
        validator = self._validators.get(self._state.phase)
        if validator:
            is_valid, message = await validator.validate(self._state)
            if not is_valid:
                raise WorkflowError(
                    f"Phase validation failed: {message}",
                    details={"phase": self._state.phase.value, "reason": message},
                )
        self._state.phase = to_phase
        self._state.updated_at = datetime.now()
        self._state.version += 1
        return self._state

    async def complete_phase(self) -> WorkflowState:
        current_idx = PHASE_ORDER.index(self._state.phase)
        if current_idx >= len(PHASE_ORDER) - 1:
            raise WorkflowError("Already at final phase")
        return await self.transition(PHASE_ORDER[current_idx + 1])

    async def fail_phase(self, reason: str) -> WorkflowState:
        if self._state.phase == WorkflowPhase.VERIFICATION:
            return await self.transition(WorkflowPhase.IMPLEMENTATION)
        self._state.metadata["failure_reason"] = reason
        self._state.phase = WorkflowPhase.BLOCKED
        self._state.updated_at = datetime.now()
        return self._state

    async def get_state(self) -> WorkflowState:
        return self._state

    async def save_state(self) -> None:
        pass

    async def load_state(self, workflow_id: str) -> Optional[WorkflowState]:
        return None
