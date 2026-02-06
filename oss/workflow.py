"""
OSS Workflow Orchestrator

Manages the 7-phase OSS contribution workflow:
1. Repository Understanding
2. Issue Intake
3. Planning
4. Implementation
5. Verification
6. Validation
7. Commit & PR
"""

from enum import Enum
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from config.config import Config
from oss.repository import RepositoryManager
from oss.memory import BranchMemoryManager
from oss.github import GitHubClient


class WorkflowPhase(str, Enum):
    """OSS workflow phases"""

    REPOSITORY_UNDERSTANDING = "repository_understanding"
    ISSUE_INTAKE = "issue_intake"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    VALIDATION = "validation"
    COMMIT_AND_PR = "commit_and_pr"
    COMPLETE = "complete"


@dataclass
class WorkflowState:
    """Current state of the OSS workflow"""

    phase: WorkflowPhase = WorkflowPhase.REPOSITORY_UNDERSTANDING
    issue_url: Optional[str] = None
    issue_number: Optional[int] = None
    branch_name: Optional[str] = None
    repository_path: Optional[Path] = None
    start_here_exists: bool = False
    repository_analysis: Optional[dict[str, Any]] = None
    issue_data: Optional[dict[str, Any]] = None
    plan: Optional[str] = None
    changes_made: bool = False
    tests_passed: bool = False
    pr_url: Optional[str] = None
    context_summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class OSSWorkflow:
    """
    Orchestrates the complete OSS contribution workflow.

    This class manages the 7-phase workflow from repository understanding
    to PR creation, ensuring each phase completes before moving to the next.
    """

    def __init__(
        self,
        config: Config,
        repository_path: Optional[Path] = None,
    ):
        """
        Initialize OSS workflow.

        Args:
            config: Agent configuration
            repository_path: Path to the repository (defaults to config.cwd)
        """
        self.config = config
        self.repository_path = repository_path or config.cwd
        self.state = WorkflowState(repository_path=self.repository_path)

        # Initialize managers
        self.repo_manager = RepositoryManager(self.repository_path)
        self.github_client = GitHubClient(config)
        self.branch_memory = BranchMemoryManager(self.repository_path)

    async def start(self, issue_url: str) -> WorkflowState:
        """
        Start the OSS workflow for a given issue.

        Executes phases 1-2 immediately (repository understanding and issue intake),
        then transitions to planning phase for Agent to handle.

        Args:
            issue_url: GitHub issue URL

        Returns:
            Current workflow state
        """
        self.state.issue_url = issue_url
        self.state.updated_at = datetime.now()

        # Parse issue URL
        issue_data = self.github_client.parse_issue_url(issue_url)
        self.state.issue_number = issue_data.get("issue_number")

        # Execute phases 1-2 immediately (these use tools directly)
        await self._phase_repository_understanding()
        await self._phase_issue_intake()

        # Transition to planning phase - Agent will handle phases 3-7
        self.state.phase = WorkflowPhase.PLANNING
        self.state.updated_at = datetime.now()
        self.save_state()

        return self.state

    async def resume(self) -> WorkflowState:
        """
        Resume workflow from saved state.

        Returns:
            Current workflow state
        """
        # Load branch memory if exists
        memory = self.branch_memory.load_current_branch()
        if memory:
            # Restore state from memory
            phase_str = memory.get("current_phase", "repository_understanding")
            try:
                self.state.phase = WorkflowPhase(phase_str)
            except ValueError:
                self.state.phase = WorkflowPhase.REPOSITORY_UNDERSTANDING
            
            self.state.issue_url = memory.get("issue_url")
            self.state.issue_number = memory.get("issue_number")
            self.state.branch_name = memory.get("branch_name")
            self.state.pr_url = memory.get("pr_url")
            
            # Restore repository analysis if available
            if memory.get("repository_analysis"):
                self.state.repository_analysis = memory.get("repository_analysis")
            
            # Restore issue data if available
            if memory.get("issue_data"):
                self.state.issue_data = memory.get("issue_data")
            
            # Restore context summary
            context_summary = memory.get("context_summary", "")
            if context_summary:
                self.state.context_summary = context_summary

        return self.state

    async def _phase_repository_understanding(self) -> None:
        """Phase 1: Understand repository structure."""
        self.state.phase = WorkflowPhase.REPOSITORY_UNDERSTANDING

        # Check if repository already analyzed
        if await self.repo_manager.is_analyzed():
            # Load existing analysis
            analysis = await self.repo_manager.load_analysis()
            self.state.start_here_exists = analysis.get("start_here_exists", False)
        else:
            # Analyze repository
            analysis = await self.repo_manager.analyze()
            self.state.start_here_exists = analysis.get("start_here_exists", False)

        # Store analysis in state for later phases
        self.state.repository_analysis = analysis

        self.state.updated_at = datetime.now()
        self.save_state()

    async def _phase_issue_intake(self) -> None:
        """Phase 2: Fetch and understand the issue."""
        self.state.phase = WorkflowPhase.ISSUE_INTAKE

        if not self.state.issue_url:
            raise ValueError("Issue URL required for issue intake")

        # Fetch issue details
        issue_data = await self.github_client.fetch_issue(
            self.state.issue_url, self.state.issue_number
        )

        # Check if issue is closed
        if issue_data.get("state") == "closed":
            raise ValueError(
                f"Issue #{self.state.issue_number} is already closed. "
                "Cannot work on closed issues."
            )

        # Store issue data in state
        self.state.issue_data = issue_data

        # Store issue intent in branch memory
        self.branch_memory.store_issue_intent(
            issue_url=self.state.issue_url,
            issue_number=self.state.issue_number,
            issue_data=issue_data,
        )

        self.state.updated_at = datetime.now()
        self.save_state()

    async def _phase_planning(self) -> None:
        """Phase 3: Plan the fix (no code changes yet)."""
        self.state.phase = WorkflowPhase.PLANNING

        # Planning phase will be handled by LLM with guidance
        # The plan will be generated through Agent interaction
        # This method just sets the phase state
        # Actual planning happens via Agent with planning prompt

        self.state.updated_at = datetime.now()
        self.save_state()

    async def _phase_implementation(self) -> None:
        """Phase 4: Implement the fix."""
        self.state.phase = WorkflowPhase.IMPLEMENTATION

        # Create/checkout branch if needed
        if not self.state.branch_name:
            self.state.branch_name = await self._create_feature_branch()

        # Implementation will be done via tools orchestrated by Agent
        # This method sets the phase - actual implementation happens via Agent
        # The Agent will use tools to make code changes
        
        # Track files modified via git status
        await self._track_modified_files()

        self.state.updated_at = datetime.now()
        self.save_state()

    async def _track_modified_files(self) -> None:
        """Track files modified in current branch."""
        branch_name = self.state.branch_name or self.branch_memory.get_current_branch()
        if not branch_name:
            return

        try:
            import subprocess
            # Get modified files from git
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        # Parse git status line (format: " M file.py" or "MM file.py")
                        parts = line.split()
                        if len(parts) >= 2:
                            file_path = parts[-1]
                            # Only track actual modifications (not untracked files in some cases)
                            if parts[0] in ["M", "A", "MM", "AM"]:
                                self.branch_memory.add_file_modified(branch_name, file_path)
        except Exception:
            # Silently fail if git is not available
            pass

    async def _phase_verification(self) -> None:
        """Phase 5: Verify the fix with tests."""
        self.state.phase = WorkflowPhase.VERIFICATION

        # Verification will be done via tools orchestrated by Agent
        # Agent will run tests based on repository analysis
        # This method sets the phase - actual verification happens via Agent

        self.state.updated_at = datetime.now()
        self.save_state()

    async def _phase_validation(self) -> None:
        """Phase 6: Validate fix against issue requirements."""
        self.state.phase = WorkflowPhase.VALIDATION

        # Validation will be done via Agent comparing changes to issue
        # Agent will use git_diff and git_status to review changes
        # This method sets the phase - actual validation happens via Agent

        self.state.updated_at = datetime.now()
        self.save_state()

    async def _phase_commit_and_pr(self) -> None:
        """Phase 7: Commit changes and create PR."""
        self.state.phase = WorkflowPhase.COMMIT_AND_PR

        # Commit and PR creation will be done via tools orchestrated by Agent
        # Agent will use git_commit, git_push, and create_pr tools
        # This method sets the phase - actual commit/PR happens via Agent

        self.state.updated_at = datetime.now()
        self.save_state()

    async def _create_feature_branch(self) -> str:
        """
        Create a feature branch for the issue.

        Returns:
            Branch name
        """
        if not self.state.issue_number:
            raise ValueError("Issue number required to create branch")

        # Generate branch name using config pattern
        pattern = self.config.oss.branch_naming_pattern
        branch_name = pattern.format(number=self.state.issue_number)

        # Branch creation will be done via Git tools in implementation phase
        # This just generates the name
        return branch_name

    def get_phase_prompt(self) -> str:
        """
        Get the prompt for the current workflow phase.

        Returns:
            Phase-specific prompt to guide the Agent
        """
        if self.state.phase == WorkflowPhase.REPOSITORY_UNDERSTANDING:
            return self._get_repository_understanding_prompt()

        elif self.state.phase == WorkflowPhase.ISSUE_INTAKE:
            return self._get_issue_intake_prompt()

        elif self.state.phase == WorkflowPhase.PLANNING:
            return self._get_planning_prompt()

        elif self.state.phase == WorkflowPhase.IMPLEMENTATION:
            return self._get_implementation_prompt()

        elif self.state.phase == WorkflowPhase.VERIFICATION:
            return self._get_verification_prompt()

        elif self.state.phase == WorkflowPhase.VALIDATION:
            return self._get_validation_prompt()

        elif self.state.phase == WorkflowPhase.COMMIT_AND_PR:
            return self._get_commit_and_pr_prompt()

        return "Continue with the current workflow phase."

    def _get_repository_understanding_prompt(self) -> str:
        """Get prompt for repository understanding phase."""
        if self.state.start_here_exists:
            return (
                "Repository has been analyzed. START_HERE.md exists. "
                "Review the repository structure and proceed to issue intake."
            )
        else:
            return (
                "Analyze the repository structure. Use 'analyze_repository' tool to understand "
                "the codebase architecture, entry points, test strategy, and CI setup. "
                "Create START_HERE.md if it doesn't exist."
            )

    def _get_issue_intake_prompt(self) -> str:
        """Get prompt for issue intake phase."""
        if not self.state.issue_url:
            return "Issue URL is required. Please provide a GitHub issue URL."

        return (
            f"Fetch and analyze GitHub issue: {self.state.issue_url}\n"
            f"Use 'fetch_issue' tool to get issue details. "
            f"Summarize what is being asked and what is explicitly out of scope. "
            f"Store the issue intent for planning."
        )

    def _get_planning_prompt(self) -> str:
        """Get prompt for planning phase."""
        if not self.state.issue_data:
            return "Issue data is required for planning. Complete issue intake first."

        issue_title = self.state.issue_data.get("title", "Unknown")
        issue_body = self.state.issue_data.get("body", "")

        analysis = self.state.repository_analysis or {}
        key_folders = analysis.get("key_folders", {})
        entry_points = analysis.get("entry_points", [])

        prompt = f"""Plan the fix for issue: {issue_title}

Issue Description:
{issue_body[:500]}{'...' if len(issue_body) > 500 else ''}

Repository Context:
- Key folders: {', '.join(key_folders.keys()) if key_folders else 'None identified'}
- Entry points: {', '.join(entry_points) if entry_points else 'None identified'}

Planning Requirements:
1. Use 'grep' and 'read_file' tools to locate relevant code areas
2. Identify which files need to be modified
3. Identify which test files need updates
4. Form a step-by-step fix strategy
5. Explain why each area matters
6. Identify potential edge cases

CRITICAL: Do NOT write any code yet. Only plan. If the fix scope is unclear, ask ONE precise clarification question."""

        return prompt

    def _get_implementation_prompt(self) -> str:
        """Get prompt for implementation phase."""
        if not self.state.plan:
            return "Planning is required before implementation. Complete planning phase first."

        issue_title = self.state.issue_data.get("title", "Unknown") if self.state.issue_data else "Unknown"

        prompt = f"""Implement the fix for issue: {issue_title}

Current branch: {self.state.branch_name or 'Not created yet'}

Implementation Rules (STRICT):
- Stay strictly within issue scope
- Do NOT add irrelevant comments
- Do NOT reformat unrelated files
- Do NOT do drive-by refactors
- Fix core logic, not symptoms
- No patch-work fixes
- Use existing patterns in repo
- Keep diffs minimal and intentional

Steps:
1. Ensure you're on the correct branch (use 'git_branch' tool if needed)
2. Make minimal code changes required
3. Follow existing code patterns
4. Add necessary tests
5. Update documentation if needed

After making changes, proceed to verification phase."""

        return prompt

    def _get_verification_prompt(self) -> str:
        """Get prompt for verification phase."""
        analysis = self.state.repository_analysis or {}
        test_strategy = analysis.get("test_strategy", {})

        prompt = "Verify the fix with tests.\n\n"

        if test_strategy:
            prompt += "Test commands identified:\n"
            for test_type, command in test_strategy.items():
                prompt += f"- {test_type}: {command}\n"
            prompt += "\n"
        else:
            prompt += "No test strategy identified. Check START_HERE.md or CONTRIBUTING.md for test commands.\n\n"

        prompt += (
            "Verification Steps:\n"
            "1. Run the test suite using identified test commands\n"
            "2. If tests fail, fix regressions immediately\n"
            "3. Re-run tests until all pass\n"
            "4. For UI changes, verify visually if possible\n"
            "5. Document any known limitations\n\n"
            "After verification passes, proceed to validation phase."
        )

        return prompt

    def _get_validation_prompt(self) -> str:
        """Get prompt for validation phase."""
        issue_title = self.state.issue_data.get("title", "Unknown") if self.state.issue_data else "Unknown"
        issue_body = self.state.issue_data.get("body", "") if self.state.issue_data else ""

        prompt = f"""Validate the fix against the original issue requirements.

Original Issue:
Title: {issue_title}
Description: {issue_body[:300]}{'...' if len(issue_body) > 300 else ''}

Validation Steps:
1. Use 'git_status' to see all changes
2. Use 'git_diff' to review the diff
3. Re-read the original issue
4. Explicitly verify:
   - Does this fully resolve what was asked?
   - Did I avoid unrelated changes?
   - Are there any edge cases I missed?

If the fix doesn't match the issue scope, adjust before committing.
After validation passes, proceed to commit and PR phase."""

        return prompt

    def _get_commit_and_pr_prompt(self) -> str:
        """Get prompt for commit and PR phase."""
        issue_number = self.state.issue_number
        issue_title = self.state.issue_data.get("title", "Unknown") if self.state.issue_data else "Unknown"

        # Generate commit message
        commit_type = "fix"  # Could be enhanced to detect type from issue labels
        commit_scope = "auto"  # Could be enhanced to detect from changed files
        commit_subject = issue_title.lower().replace(" ", "-")[:50]

        prompt = f"""Create commit and open pull request.

Issue: #{issue_number} - {issue_title}

Commit Steps:
1. Use 'git_status' to see all changes
2. Stage all changes (or specific files)
3. Create commit with message: '{commit_type}({commit_scope}): {commit_subject}'
   Format: type(scope): brief description
   Example: fix(auth): handle null session on refresh
4. Push branch using 'git_push' tool

PR Steps:
1. Use 'create_pr' tool to open pull request
2. Reference issue in PR: Fixes #{issue_number}
3. Include:
   - What was fixed
   - How it was verified
   - Any known limitations

After PR is created, workflow is complete."""

        return prompt

    def mark_phase_complete(self, phase: WorkflowPhase) -> None:
        """Mark a phase as complete and transition to next phase."""
        phase_order = [
            WorkflowPhase.REPOSITORY_UNDERSTANDING,
            WorkflowPhase.ISSUE_INTAKE,
            WorkflowPhase.PLANNING,
            WorkflowPhase.IMPLEMENTATION,
            WorkflowPhase.VERIFICATION,
            WorkflowPhase.VALIDATION,
            WorkflowPhase.COMMIT_AND_PR,
            WorkflowPhase.COMPLETE,
        ]

        current_idx = phase_order.index(self.state.phase)
        if current_idx < len(phase_order) - 1:
            # Add completed step to memory
            branch_name = self.state.branch_name or self.branch_memory.get_current_branch()
            if branch_name:
                self.branch_memory.add_completed_step(branch_name, f"Completed phase: {phase.value}")
            
            self.state.phase = phase_order[current_idx + 1]
            self.state.updated_at = datetime.now()
            self.save_state()

    def get_current_phase_info(self) -> dict[str, Any]:
        """Get information about the current phase."""
        return {
            "phase": self.state.phase.value,
            "issue_number": self.state.issue_number,
            "branch_name": self.state.branch_name,
            "changes_made": self.state.changes_made,
            "tests_passed": self.state.tests_passed,
            "pr_url": self.state.pr_url,
        }

    def get_state(self) -> WorkflowState:
        """Get current workflow state."""
        return self.state

    def save_state(self) -> None:
        """Save current state to branch memory."""
        self.branch_memory.save_workflow_state(self.state)
