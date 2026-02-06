"""
Branch-Level Memory Management

Manages context and state storage per branch,
enabling workflow resumption and branch switching.
"""

import json
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oss.workflow import WorkflowState


@dataclass
class BranchMemoryData:
    """Branch memory data structure"""

    branch_name: str
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    created_at: str = None
    updated_at: str = None
    status: str = "in_progress"
    pr_url: Optional[str] = None
    context_summary: str = ""
    current_phase: str = "repository_understanding"
    completed_steps: list[str] = None
    work_summary: str = ""
    files_modified: list[str] = None
    last_activity: str = ""
    conversation_summary: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
        if self.completed_steps is None:
            self.completed_steps = []
        if self.files_modified is None:
            self.files_modified = []


class BranchMemoryManager:
    """
    Manages branch-level memory storage and retrieval.

    Stores workflow state, context summaries, and issue associations
    per branch to enable resumption and context switching.
    """

    def __init__(self, repository_path: Path):
        """
        Initialize branch memory manager.

        Args:
            repository_path: Path to the repository
        """
        self.repository_path = Path(repository_path).resolve()
        self.memory_dir = self.repository_path / ".oss-dev" / "branches"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def get_current_branch(self) -> Optional[str]:
        """
        Get current git branch name.

        Returns:
            Branch name or None if not in git repo
        """
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def load_current_branch(self) -> Optional[dict[str, Any]]:
        """
        Load memory for current branch.

        Returns:
            Branch memory dictionary or None
        """
        branch_name = self.get_current_branch()
        if not branch_name:
            return None

        return self.load_branch(branch_name)

    def load_branch(self, branch_name: str) -> Optional[dict[str, Any]]:
        """
        Load memory for a specific branch.

        Args:
            branch_name: Name of the branch

        Returns:
            Branch memory dictionary or None
        """
        memory_file = self._get_memory_file(branch_name)
        if not memory_file.exists():
            return None

        try:
            content = memory_file.read_text(encoding="utf-8")
            return json.loads(content)
        except (json.JSONDecodeError, IOError):
            return None

    def save_branch(self, memory: BranchMemoryData) -> None:
        """
        Save branch memory.

        Args:
            memory: Branch memory object
        """
        memory.updated_at = datetime.now().isoformat()
        memory_file = self._get_memory_file(memory.branch_name)

        data = asdict(memory)
        memory_file.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def store_issue_intent(
        self,
        issue_url: str,
        issue_number: Optional[int],
        issue_data: dict[str, Any],
    ) -> None:
        """
        Store issue intent in current branch memory.

        Args:
            issue_url: GitHub issue URL
            issue_number: Issue number
            issue_data: Issue data dictionary
        """
        branch_name = self.get_current_branch()
        if not branch_name:
            # Create a default branch name if not in git repo
            branch_name = f"issue-{issue_number}" if issue_number else "default"

        # Load or create memory
        memory_data = self.load_branch(branch_name)
        if memory_data:
            memory = BranchMemoryData(**memory_data)
        else:
            memory = BranchMemoryData(branch_name=branch_name)

        # Update with issue info
        memory.issue_url = issue_url
        memory.issue_number = issue_number
        memory.work_summary = f"Issue: {issue_data.get('title', 'Unknown')}"

        self.save_branch(memory)

    def save_workflow_state(self, state: "WorkflowState") -> None:
        """
        Save workflow state to branch memory.

        Args:
            state: Workflow state object
        """
        branch_name = state.branch_name or self.get_current_branch()
        if not branch_name:
            return

        # Load or create memory
        memory_data = self.load_branch(branch_name)
        if memory_data:
            memory = BranchMemoryData(**memory_data)
        else:
            memory = BranchMemoryData(branch_name=branch_name)

        # Update with workflow state
        memory.current_phase = state.phase.value
        memory.issue_url = state.issue_url
        memory.issue_number = state.issue_number
        memory.pr_url = state.pr_url
        memory.status = "in_progress" if state.phase.value != "complete" else "complete"
        
        # Update context summary
        memory.context_summary = self.summarize_context(branch_name)
        
        # Track completed phase
        phase_step = f"Completed phase: {state.phase.value}"
        if phase_step not in (memory.completed_steps or []):
            if memory.completed_steps is None:
                memory.completed_steps = []
            memory.completed_steps.append(phase_step)

        self.save_branch(memory)

    def list_branches(self) -> list[dict[str, Any]]:
        """
        List all branches with memory.

        Returns:
            List of branch memory dictionaries
        """
        branches = []
        for memory_file in self.memory_dir.glob("*.json"):
            try:
                content = memory_file.read_text(encoding="utf-8")
                data = json.loads(content)
                branches.append(data)
            except (json.JSONDecodeError, IOError):
                continue

        return branches

    def summarize_context(self, branch_name: str, max_length: int = 500) -> str:
        """
        Create a compact summary of work done on a branch.

        Args:
            branch_name: Branch name
            max_length: Maximum summary length

        Returns:
            Context summary string
        """
        memory_data = self.load_branch(branch_name)
        if not memory_data:
            return ""

        memory = BranchMemoryData(**memory_data)
        
        summary_parts = []
        
        if memory.issue_number:
            summary_parts.append(f"Issue #{memory.issue_number}")
        
        if memory.current_phase:
            summary_parts.append(f"Phase: {memory.current_phase}")
        
        if memory.work_summary:
            summary_parts.append(memory.work_summary)
        
        if memory.files_modified:
            file_count = len(memory.files_modified)
            summary_parts.append(f"Modified {file_count} file(s)")
            if file_count <= 5:
                summary_parts.append(f"Files: {', '.join(memory.files_modified)}")
        
        if memory.completed_steps:
            summary_parts.append(f"Completed: {', '.join(memory.completed_steps[-3:])}")
        
        summary = " | ".join(summary_parts)
        
        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."
        
        return summary

    def update_context_summary(self, branch_name: str, summary: str) -> None:
        """
        Update context summary for a branch.

        Args:
            branch_name: Branch name
            summary: New context summary
        """
        memory_data = self.load_branch(branch_name)
        if memory_data:
            memory = BranchMemoryData(**memory_data)
        else:
            memory = BranchMemoryData(branch_name=branch_name)
        
        memory.context_summary = summary
        self.save_branch(memory)

    def add_file_modified(self, branch_name: str, file_path: str) -> None:
        """
        Track a file modification for a branch.

        Args:
            branch_name: Branch name
            file_path: Path to modified file
        """
        memory_data = self.load_branch(branch_name)
        if memory_data:
            memory = BranchMemoryData(**memory_data)
        else:
            memory = BranchMemoryData(branch_name=branch_name)
        
        if file_path not in memory.files_modified:
            memory.files_modified.append(file_path)
        
        self.save_branch(memory)

    def add_completed_step(self, branch_name: str, step: str) -> None:
        """
        Add a completed step to branch memory.

        Args:
            branch_name: Branch name
            step: Step description
        """
        memory_data = self.load_branch(branch_name)
        if memory_data:
            memory = BranchMemoryData(**memory_data)
        else:
            memory = BranchMemoryData(branch_name=branch_name)
        
        if step not in memory.completed_steps:
            memory.completed_steps.append(step)
        
        self.save_branch(memory)

    def switch_branch(self, target_branch: str) -> Optional[dict[str, Any]]:
        """
        Switch to a different branch, saving current and loading target.

        Args:
            target_branch: Target branch name

        Returns:
            Target branch memory or None
        """
        # Save current branch context
        current_branch = self.get_current_branch()
        if current_branch:
            self._save_current_context(current_branch)
        
        # Load target branch memory
        return self.load_branch(target_branch)

    def _save_current_context(self, branch_name: str) -> None:
        """
        Save current branch context with summary.

        Args:
            branch_name: Current branch name
        """
        memory_data = self.load_branch(branch_name)
        if memory_data:
            memory = BranchMemoryData(**memory_data)
        else:
            memory = BranchMemoryData(branch_name=branch_name)
        
        # Update context summary
        memory.context_summary = self.summarize_context(branch_name)
        memory.last_activity = datetime.now().isoformat()
        
        self.save_branch(memory)

    def cleanup_old_memories(self, days_old: int = 30) -> int:
        """
        Clean up branch memories older than specified days.

        Args:
            days_old: Number of days to keep memories

        Returns:
            Number of memories cleaned up
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned = 0
        
        for memory_file in self.memory_dir.glob("*.json"):
            try:
                content = memory_file.read_text(encoding="utf-8")
                data = json.loads(content)
                
                updated_at_str = data.get("updated_at")
                if updated_at_str:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if updated_at < cutoff_date:
                        # Check if branch still exists
                        branch_name = data.get("branch_name", "")
                        if not self._branch_exists(branch_name):
                            memory_file.unlink()
                            cleaned += 1
            except (json.JSONDecodeError, IOError, ValueError):
                # Skip invalid files
                continue
        
        return cleaned

    def cleanup_merged_branches(self) -> int:
        """
        Clean up memories for branches that have been merged.

        Args:
            Returns:
                Number of memories cleaned up
        """
        cleaned = 0
        
        for memory_file in self.memory_dir.glob("*.json"):
            try:
                content = memory_file.read_text(encoding="utf-8")
                data = json.loads(content)
                
                branch_name = data.get("branch_name", "")
                pr_url = data.get("pr_url")
                
                # If PR exists and branch is merged, clean up
                if pr_url and not self._branch_exists(branch_name):
                    # Check if PR is merged (would need GitHub API)
                    # For now, just check if branch exists
                    memory_file.unlink()
                    cleaned += 1
            except (json.JSONDecodeError, IOError):
                continue
        
        return cleaned

    def _branch_exists(self, branch_name: str) -> bool:
        """
        Check if a git branch exists.

        Args:
            branch_name: Branch name

        Returns:
            True if branch exists
        """
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--list", branch_name],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_branch_summary(self, branch_name: str) -> dict[str, Any]:
        """
        Get a summary of branch work.

        Args:
            branch_name: Branch name

        Returns:
            Summary dictionary
        """
        memory_data = self.load_branch(branch_name)
        if not memory_data:
            return {
                "branch_name": branch_name,
                "exists": False,
            }
        
        memory = BranchMemoryData(**memory_data)
        
        return {
            "branch_name": memory.branch_name,
            "issue_number": memory.issue_number,
            "issue_url": memory.issue_url,
            "current_phase": memory.current_phase,
            "status": memory.status,
            "pr_url": memory.pr_url,
            "files_modified": len(memory.files_modified or []),
            "completed_steps": len(memory.completed_steps or []),
            "context_summary": memory.context_summary or self.summarize_context(branch_name),
            "last_updated": memory.updated_at,
            "exists": True,
        }

    def _get_memory_file(self, branch_name: str) -> Path:
        """
        Get memory file path for a branch.

        Args:
            branch_name: Branch name

        Returns:
            Path to memory file
        """
        # Sanitize branch name for filename
        safe_name = branch_name.replace("/", "_").replace("\\", "_")
        return self.memory_dir / f"branch-{safe_name}.json"


