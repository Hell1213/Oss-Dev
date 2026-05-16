"""State persistence for workflow state machine.

Stores and loads workflow state from the .oss-dev directory.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from oss_dev.core.contracts.workflow import WorkflowPhase, WorkflowState
from oss_dev.core.errors import StateError


def _state_to_dict(state: WorkflowState) -> dict[str, Any]:
    return {
        "workflow_id": state.workflow_id,
        "phase": state.phase.value,
        "issue_url": state.issue_url,
        "issue_number": state.issue_number,
        "branch_name": state.branch_name,
        "repository_path": str(state.repository_path) if state.repository_path else None,
        "metadata": state.metadata,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "version": state.version,
    }


def _state_from_dict(data: dict[str, Any]) -> WorkflowState:
    return WorkflowState(
        workflow_id=data["workflow_id"],
        phase=WorkflowPhase(data["phase"]),
        issue_url=data.get("issue_url"),
        issue_number=data.get("issue_number"),
        branch_name=data.get("branch_name"),
        repository_path=Path(data["repository_path"]) if data.get("repository_path") else None,
        metadata=data.get("metadata", {}),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        version=data.get("version", 1),
    )


class FileStateRepository:
    """Persists workflow state to the .oss-dev directory."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path / ".oss-dev" / "workflows"
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _state_path(self, workflow_id: str) -> Path:
        return self._base_path / f"{workflow_id}.json"

    def save(self, state: WorkflowState) -> None:
        path = self._state_path(state.workflow_id)
        data = _state_to_dict(state)
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            raise StateError(f"Failed to save state: {e}") from e

    def load(self, workflow_id: str) -> Optional[WorkflowState]:
        path = self._state_path(workflow_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return _state_from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise StateError(f"Failed to load state: {e}") from e

    def delete(self, workflow_id: str) -> bool:
        path = self._state_path(workflow_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_workflows(self) -> list[str]:
        return [p.stem for p in self._base_path.glob("*.json")]

    def workflow_exists(self, workflow_id: str) -> bool:
        return self._state_path(workflow_id).exists()
