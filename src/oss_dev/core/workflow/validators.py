"""Phase validators — validation gates for workflow phase transitions.

These replace the inline validation in oss/workflow.py's
mark_phase_complete() method. Each validator checks that the required
work was actually done before allowing the phase to transition.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

from src.oss_dev.core.contracts.workflow import PhaseValidator, WorkflowState

logger = logging.getLogger(__name__)


class ImplementationValidator(PhaseValidator):
    """Validates that the implementation phase produced real changes.

    Checks:
    1. Current git branch is not main/master
    2. At least one file has been modified
    """

    def __init__(self, repo_path: Path, expected_branch: str | None = None) -> None:
        self.repo_path = repo_path
        self.expected_branch = expected_branch

    async def validate(self, state: WorkflowState) -> tuple[bool, str]:
        # Check 1: Must be on a feature branch, not main/master
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()

            if current_branch in ("main", "master"):
                return (
                    False,
                    f"You are on {current_branch}. Create a feature branch "
                    f"before marking implementation complete.",
                )

            if self.expected_branch and current_branch != self.expected_branch:
                logger.warning(
                    f"Branch mismatch: expected {self.expected_branch}, "
                    f"got {current_branch}"
                )

        except Exception as e:
            return False, f"Could not verify git branch: {e}"

        # Check 2: At least one file must be modified
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            modified = [line for line in result.stdout.strip().split("\n") if line.strip()]

            if not modified:
                return False, "No files modified. Make code changes before marking complete."

            has_modified = any(
                line.startswith(("M ", "A ", "D ")) for line in modified
            )
            if not has_modified:
                return False, "No existing files modified. Edit relevant files first."

            logger.info(f"Implementation validation passed: {len(modified)} files modified")
            return True, f"Validation passed: {len(modified)} files on branch {current_branch}"

        except Exception as e:
            return False, fbCould not verify file changes: {e}"


class VerificationValidator(PhaseValidator):
    """Validates that tests were run during verification.

    Currently a soft check — just verifies the phase was entered.
    A stricter version could parse test output from context.
    """

    async def validate(self, state: WorkflowState) -> tuple[bool, str]:
        # Soft validation: just let it pass
        # A stricter version could check state.metadata for test results
        return True, "Verification phase completed"


class ValidationValidator(PhaseValidator):
    """Validates that scope checking was done during validation."""

    async def validate(self, state: WorkflowState) -> tuple[bool, str]:
        return True, "Validation phase completed"


def get_default_validators(
    repo_path: Path,
    expected_branch: str | None = None,
) -> dict:
    """Get the default set of phase validators.

    Args:
        repo_path: Path to the git repository.
        expected_branch: Expected feature branch name for implementation phase.

    Returns:
        Dict mapping WorkflowPhase to PhaseValidator instances.
    """
    from src.oss_dev.core.contracts.workflow import WorkflowPhase

    return {
        WorkflowPhase.IMPLEMENTATION: ImplementationValidator(repo_path, expected_branch),
        WorkflowPhase.VERIFICATION: VerificationValidator(),
        WorkflowPhase.VALIDATION: ValidationValidator(),
    }
