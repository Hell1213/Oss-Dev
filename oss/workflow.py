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
import logging

from config.config import Config
from oss.repository import RepositoryManager
from oss.memory import BranchMemoryManager
from oss.github import GitHubClient

logger = logging.getLogger(__name__)


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
        
        # Check if branch already exists for this issue
        if self.state.issue_number:
            expected_branch = self.config.oss.branch_naming_pattern.format(number=self.state.issue_number)
            # Check if branch exists
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "rev-parse", "--verify", f"refs/heads/{expected_branch}"],
                    cwd=self.repository_path,
                    capture_output=True,
                    check=False,
                )
                if result.returncode == 0:
                    # Branch exists - reuse it
                    self.state.branch_name = expected_branch
                    logger.info(f"Reusing existing branch: {expected_branch}")
logger.info(f"Starting workflow with issue number: {self.state.issue_number} and issue URL: {self.state.issue_url}")
            except Exception as e:
                logger.debug(f"Could not check branch existence: {e}")

        # Initialize phases 1-2 but let Agent work on them
        # Don't execute automatically - Agent needs to work through all phases
        self.state.phase = WorkflowPhase.REPOSITORY_UNDERSTANDING
        logger.info(f"Set workflow phase to: {self.state.phase}")
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
        logger.info(f"Set workflow phase to: {self.state.phase}")
            
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
        logger.info(f"Set workflow phase to: {self.state.phase}")

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

        # Generate branch name (agent will create it via git_branch tool)
        if not self.state.branch_name:
            self.state.branch_name = await self._create_feature_branch()
            logger.info(f"Generated branch name for implementation: {self.state.branch_name}")

        # Implementation will be done via tools orchestrated by Agent
        # This method sets the phase - actual implementation happens via Agent
        # The Agent will use tools to make code changes
        
        # Note: File tracking happens after agent makes changes
        # We'll track files when agent marks phase complete or during validation

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
        # Check if repository has been analyzed
        if not self.state.repository_analysis:
            # Need to analyze first
            return """# Phase 1: Repository Understanding

**CRITICAL**: You MUST ensure START_HERE.md exists.

## Steps (in order):

1. **Analyze Repository**: Use `analyze_repository` tool to understand the codebase
2. **Check START_HERE.md**: Use `check_start_here` tool
3. **Create if missing**: If START_HERE.md doesn't exist, use `create_start_here` tool
4. **Mark complete**: Once START_HERE.md exists, call `workflow_orchestrator(action='mark_phase_complete')`

**DO NOT skip creating START_HERE.md. It is mandatory.**"""
        
        # Repository analyzed, check START_HERE
        if self.state.start_here_exists:
            return """# Phase 1: Repository Understanding

**Status**: START_HERE.md exists. Review it and proceed.

**Action**: Call `workflow_orchestrator(action='mark_phase_complete')` to proceed to Phase 2: Issue Intake."""
        else:
            return """# Phase 1: Repository Understanding

**CRITICAL**: START_HERE.md does NOT exist. You MUST create it.

**Steps:**
1. Use `create_start_here` tool to create START_HERE.md
2. After creation, call `workflow_orchestrator(action='mark_phase_complete')`

**DO NOT skip creating START_HERE.md. It is mandatory.**"""

    def _get_issue_intake_prompt(self) -> str:
        """Get prompt for issue intake phase."""
        if not self.state.issue_url:
            return "Issue URL is required. Please provide a GitHub issue URL."

        return f"""# Phase 2: Issue Intake

**Task**: Fetch and understand the GitHub issue.

## Steps:

1. **Fetch Issue**: Use `fetch_issue` tool with issue URL: {self.state.issue_url}
2. **Analyze**: Summarize:
   - What is being asked
   - What is explicitly out of scope
   - Key requirements
3. **Mark Complete**: Call `workflow_orchestrator(action='mark_phase_complete')` to proceed to Phase 3: Planning"""

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

CRITICAL: Do NOT write any code yet. Only plan. If the fix scope is unclear, ask ONE precise clarification question.

## Phase Completion - REQUIRED ACTION
When you have completed your planning, you MUST call the tool to transition to the next phase.

**You MUST call this tool now (do not just describe it, actually call it):**
```
workflow_orchestrator(action='mark_phase_complete')
```

**Important**: 
- You must ACTUALLY CALL the tool, not just describe calling it
- Use the exact tool name: `workflow_orchestrator`
- Use the exact action: `mark_phase_complete`
- This will transition the workflow to Phase 4: Implementation
- The workflow will provide the next phase prompt automatically"""

        return prompt

    def _get_implementation_prompt(self) -> str:
        """Get prompt for implementation phase."""
        if not self.state.plan:
            return "Planning is required before implementation. Complete planning phase first."

        issue_title = self.state.issue_data.get("title", "Unknown") if self.state.issue_data else "Unknown"
        
        # Generate expected branch name
        if self.state.issue_number:
            expected_branch = self.config.oss.branch_naming_pattern.format(number=self.state.issue_number)
        else:
            expected_branch = "fix/issue-unknown"

        prompt = f"""# Phase 4: Implementation

Implement the fix for issue: {issue_title}

## ⚠️ CRITICAL: MANDATORY WORK REQUIREMENTS

**YOU CANNOT MARK THIS PHASE COMPLETE UNLESS:**
1. ✅ You have created and switched to feature branch `{expected_branch}`
2. ✅ You have made actual code changes using 'edit' or 'write_file' tools
3. ✅ At least one file has been modified to fix the issue
4. ✅ You are NOT on main/master branch

**The workflow will VALIDATE these requirements. If validation fails, you will receive an error and must complete the work before trying again.**

## STEP 1: Create Feature Branch (MANDATORY FIRST STEP)

**You MUST do this FIRST, before any code changes:**

1. Check current branch:
   ```
   git_branch(action='current')
   ```

2. Create feature branch:
   ```
   git_branch(action='create', branch_name='{expected_branch}')
   ```
   (This automatically switches to the new branch)

3. Verify you're on the branch:
   ```
   git_branch(action='current')
   ```
   Should show: `{expected_branch}`

**DO NOT proceed to code changes until you are on the feature branch!**

## STEP 2: Make Code Changes (MANDATORY)

**You MUST make actual code changes to fix the issue. The workflow validates this.**

Based on your plan, make the necessary changes:

1. **Use 'edit' tool** for precise edits:
   ```
   edit(file_path='path/to/file.py', old_string='old code', new_string='new code')
   ```

2. **Use 'write_file' tool** for new files or complete rewrites:
   ```
   write_file(file_path='path/to/file.py', contents='file content')
   ```

3. **Follow these rules STRICTLY:**
   - ✅ Stay strictly within issue scope
   - ✅ Fix core logic, not symptoms
   - ✅ Use existing patterns in repo
   - ✅ Keep diffs minimal and intentional
   - ❌ Do NOT add irrelevant comments
   - ❌ Do NOT reformat unrelated files
   - ❌ Do NOT do drive-by refactors
   - ❌ No patch-work fixes
   - ❌ Do NOT modify files that are not mentioned in the issue or your plan
   - ❌ Do NOT change formatting, whitespace, or style in files unrelated to the fix
   - ❌ Do NOT add new features or functionality not requested in the issue
   - ⚠️ **CRITICAL**: Before making ANY file change, ask yourself: "Is this file change necessary to fix the issue?" If NO, do NOT change it.

## STEP 3: Verify Changes (BEFORE marking complete)

Before calling `mark_phase_complete`, verify:

1. **Check git status**:
   ```
   git_status()
   ```
   Should show modified files

2. **Check current branch**:
   ```
   git_branch(action='current')
   ```
   Must be `{expected_branch}`, NOT main/master

3. **Review your changes**:
   ```
   git_diff()
   ```
   Ensure changes are correct and within scope

## Phase Completion - VALIDATION GATE

**ONLY call this when ALL requirements are met:**

```
workflow_orchestrator(action='mark_phase_complete')
```

**What happens:**
1. Workflow validates:
   - ✅ You're on feature branch (not main/master)
   - ✅ Files have been modified
   - ✅ At least one existing file was changed
2. If validation passes → Transition to Verification phase
3. If validation fails → You'll get an error message explaining what's missing

**DO NOT call mark_phase_complete until you have:**
- ✅ Created and switched to branch `{expected_branch}`
- ✅ Made actual code changes using 'edit' or 'write_file'
- ✅ Verified changes with git_status and git_diff

**Remember: The workflow enforces these requirements. You cannot skip them.**"""

        return prompt

    def _get_verification_prompt(self) -> str:
        """Get prompt for verification phase."""
        analysis = self.state.repository_analysis or {}
        test_strategy = analysis.get("test_strategy", {})
        start_here_path = analysis.get("start_here_path")

        prompt = "# Phase 5: Verification\n\n"
        prompt += "Verify the fix with tests.\n\n"

        # Test command discovery
        if test_strategy:
            prompt += "## Test Commands Identified:\n"
            for test_type, command in test_strategy.items():
                prompt += f"- **{test_type}**: `{command}`\n"
            prompt += "\n"
        else:
            prompt += "## Test Command Discovery:\n"
            prompt += "No test strategy automatically identified.\n\n"
            prompt += "**Action Required**:\n"
            prompt += "1. Read START_HERE.md using 'read_file' tool to find test commands\n"
            if start_here_path:
                prompt += f"   - File path: `{start_here_path}`\n"
            else:
                prompt += "   - File path: `START_HERE.md` (in repository root)\n"
            prompt += "2. Check CONTRIBUTING.md if START_HERE.md doesn't have test info\n"
            prompt += "3. Look for sections like 'Testing', 'How to Run Tests', or 'Test Commands'\n"
            prompt += "4. Extract the test command(s) and run them using 'shell' tool\n\n"

        prompt += "## Verification Steps:\n\n"
        prompt += "1. **Run Tests**:\n"
        if test_strategy:
            prompt += "   - Use 'shell' tool to execute the identified test commands\n"
            prompt += "   - Example: `shell(command='pytest')` or `shell(command='npm test')`\n"
        else:
            prompt += "   - First, discover test commands from START_HERE.md\n"
            prompt += "   - Then use 'shell' tool to execute them\n"
        prompt += "   - Capture and analyze test output\n\n"
        
        prompt += "2. **Handle Test Failures**:\n"
        prompt += "   - If tests fail, analyze the error messages carefully\n"
        prompt += "   - Identify which tests failed and why\n"
        prompt += "   - Determine if failures are:\n"
        prompt += "     * Related to your changes (regression) → Fix immediately\n"
        prompt += "     * Pre-existing failures (unrelated) → Document in PR\n"
        prompt += "   - Fix regressions by updating your implementation\n"
        prompt += "   - Re-run tests after fixes\n\n"
        
        prompt += "3. **Iterate Until Pass**:\n"
        prompt += "   - Re-run tests after each fix\n"
        prompt += "   - Continue until all tests pass\n"
        prompt += "   - Maximum 3 iterations to avoid infinite loops\n"
        prompt += "   - If tests still fail after 3 attempts, document limitations\n\n"
        
        prompt += "4. **Additional Verification** (if applicable):\n"
        prompt += "   - For UI changes: Verify visually if possible\n"
        prompt += "   - For API changes: Test endpoints manually if needed\n"
        prompt += "   - For library changes: Test import/usage\n\n"
        
        prompt += "5. **Documentation**:\n"
        prompt += "   - Document any known limitations\n"
        prompt += "   - Note any skipped tests and reasons\n"
        prompt += "   - Record test results for PR description\n\n"

        prompt += "## Phase Completion\n"
        prompt += "When all tests pass and verification is complete:\n"
        prompt += "1. Verify test results are successful\n"
        prompt += "2. Call 'workflow_orchestrator' with action 'mark_phase_complete'\n"
        prompt += "3. This will transition to Phase 6: Validation\n"
        prompt += "4. The workflow will provide the next phase prompt automatically"

        return prompt

    def _get_validation_prompt(self) -> str:
        """Get prompt for validation phase."""
        issue_title = self.state.issue_data.get("title", "Unknown") if self.state.issue_data else "Unknown"
        issue_body = self.state.issue_data.get("body", "") if self.state.issue_data else ""
        issue_number = self.state.issue_number

        prompt = f"""# Phase 6: Validation

Validate the fix against the original issue requirements.

## Original Issue Context
**Issue #{issue_number}**: {issue_title}

**Description**:
{issue_body[:500]}{'...' if len(issue_body) > 500 else ''}

## CRITICAL: Scope Validation

Before committing, you MUST validate that your changes:
1. ✅ **Fully resolve the issue** - Does the fix address what was asked?
2. ✅ **Stay within scope** - Are there any unrelated changes?
3. ✅ **Handle edge cases** - Are there any scenarios you missed?

## Validation Steps (MANDATORY):

### Step 1: Review All Changes
1. **Check git status**: Use `git_status` tool to see all modified, staged, and untracked files
2. **Review diff**: Use `git_diff` tool to see the actual code changes
   - Review both staged and unstaged changes
   - For each file, verify the changes are related to the issue

### Step 2: Re-read Original Issue
1. **Fetch issue again**: Use `fetch_issue` tool to get the complete issue details
2. **Compare requirements**: 
   - What was explicitly asked?
   - What was explicitly out of scope?
   - Are there any acceptance criteria?

### Step 3: Scope Check
For each modified file, ask:
- **Is this file change necessary for the issue?**
  - ✅ YES → Keep the change
  - ❌ NO → This is a scope violation! Remove unrelated changes

**Common scope violations to watch for**:
- ❌ Formatting changes in unrelated files
- ❌ Adding comments/docs to unrelated code
- ❌ Refactoring unrelated functions
- ❌ Adding new features not requested
- ❌ Changing test files unrelated to the fix

### Step 4: Issue Resolution Check
Verify the fix actually solves the problem:
- **Does the code change address the root cause?**
- **Are there edge cases not handled?**
- **Will this fix work for all scenarios mentioned in the issue?**

### Step 5: Final Verification
1. **Review git diff one more time** - Ensure only necessary changes remain
2. **Confirm issue requirements are met** - Check against original issue
3. **Document any limitations** - Note anything that couldn't be fixed

## If Scope Violations Found:
1. **DO NOT commit yet**
2. **Remove unrelated changes** using `edit` or `write_file` tools
3. **Re-run validation** after cleanup
4. **Only proceed when changes are scoped correctly**

## Phase Completion
When validation passes and you're ready to commit:
1. ✅ All changes are within scope
2. ✅ Issue requirements are fully met
3. ✅ No unrelated changes remain
4. Call 'workflow_orchestrator' with action 'mark_phase_complete'
5. This will transition to Phase 7: Commit & PR
6. The workflow will provide the next phase prompt automatically"""

        return prompt

    def _get_commit_and_pr_prompt(self) -> str:
        """Get prompt for commit and PR phase."""
        issue_number = self.state.issue_number
        issue_title = self.state.issue_data.get("title", "Unknown") if self.state.issue_data else "Unknown"
        branch_name = self.state.branch_name or "fix/issue-unknown"
        
        # Determine commit scope from modified files
        analysis = self.state.repository_analysis or {}
        files_modified = getattr(self.state, "files_modified", [])
        
        # Infer scope from file paths
        commit_scope = "general"
        if files_modified:
            # Try to infer scope from first modified file
            first_file = files_modified[0] if isinstance(files_modified, list) else str(files_modified).split()[0]
            if "/" in first_file:
                scope_candidate = first_file.split("/")[0]
                # Common scopes
                if scope_candidate in ["auth", "api", "cli", "config", "oss", "tools", "tests", "ui", "agent"]:
                    commit_scope = scope_candidate
        
        # Generate commit subject from issue title
        commit_subject = issue_title.lower().replace(" ", "-")[:50]
        # Remove special characters that might break commit message
        commit_subject = "".join(c for c in commit_subject if c.isalnum() or c in "-_")
        
        commit_message = f"fix({commit_scope}): {commit_subject}"

        prompt = f"""# Phase 7: Commit & Pull Request

Create commit and open pull request for issue #{issue_number}.

**Issue**: {issue_title}
**Branch**: {branch_name}

## Commit Steps

### Step 1: Final Status Check
1. **Review changes**: Use `git_status` tool to see all changes
2. **Verify diff**: Use `git_diff` tool to review what will be committed
3. **Confirm scope**: Ensure only issue-related changes are included

### Step 2: Create Commit
1. **Stage changes**: All changes should already be staged (or stage specific files if needed)
2. **Create commit** using `git_commit` tool with message:

   **Commit Message Format**: `{commit_message}`

   **Conventional Commit Format**:
   - **Type**: `fix` (for bug fixes), `feat` (for features), `docs` (for documentation)
   - **Scope**: Component/module name (e.g., `auth`, `api`, `cli`)
   - **Subject**: Brief description (50 chars max, lowercase, no period)

   **Examples**:
   - ✅ `fix(auth): handle null session on refresh`
   - ✅ `fix(oss): add missing import in main.py`
   - ✅ `feat(api): add user authentication endpoint`
   - ❌ `Fixed the bug` (not conventional)
   - ❌ `fix: Fixed the bug in auth module` (too long, has period)

3. **Verify commit**: Check that commit was created successfully

### Step 3: User Confirmation (MANDATORY - DO NOT SKIP)

**⚠️ CRITICAL: You MUST ask for user confirmation BEFORE pushing or creating PR.**

**This is a REQUIRED step. You cannot proceed to push/PR without user confirmation.**

1. **Call `user_confirm` tool NOW** (before any push or PR operations):
   ```
   user_confirm(message='Ready to push changes and create PR. Proceed?', default=True)
   ```

2. **DO NOT proceed until you get the user's response:**
   - If response is "User confirmed: YES" → Continue to Step 4 (Push) and Step 5 (Create PR)
   - If response is "User declined: NO" → Skip to Step 6 (Manual Instructions)

3. **IMPORTANT**: 
   - You MUST call `user_confirm` tool
   - You MUST wait for the response
   - You MUST check the response before proceeding
   - DO NOT call `git_push` or `create_pr` until user confirms

### Step 4: Push Branch (Only if user confirmed YES)

**Only proceed if user confirmed YES:**

1. **Push branch** using `git_push` tool
   - Branch: `{branch_name}`
   - This will push to remote repository
2. **Handle errors**: If push fails (e.g., branch doesn't exist on remote), create it:
   - Use: `git_push` with `create_remote=True` or similar option
   - Or push with: `git push -u origin {branch_name}`

## Pull Request Steps

### Step 5: Create PR (Only if user confirmed YES)

**Only proceed if user confirmed YES:**

1. **Use `create_pr` tool** with the following:

   **PR Title**: 
   - Use issue title or a clear summary
   - Example: `{issue_title}`

   **PR Body** (REQUIRED - include all sections):
   ```markdown
   ## What was fixed
   [Brief description of what was changed and why]

   ## How it was verified
   - [ ] Tests pass: [test command used]
   - [ ] Manual testing: [if applicable]
   - [ ] Edge cases handled: [if applicable]

   ## Changes Made
   - [List of key changes, one per line]

   ## Known Limitations
   [Any limitations or follow-up work needed, or "None"]

   Fixes #{issue_number}
   ```

   **PR Parameters**:
   - `title`: PR title
   - `body`: PR description (as above)
   - `head`: `{branch_name}` (source branch)
   - `base`: `main` (or `master` - check repository default)
   - `issue_number`: `{issue_number}` (to link issue)

2. **Verify PR creation**: Check that PR was created and URL is returned

## Important Notes

### Commit Message Guidelines:
- ✅ Keep it short and clear (50 chars for subject)
- ✅ Use conventional format: `type(scope): subject`
- ✅ No emojis, no fluff
- ✅ Reference issue in PR body, not commit message

### PR Description Guidelines:
- ✅ Clearly explain what was fixed
- ✅ Document how it was verified
- ✅ Include issue reference: `Fixes #{issue_number}`
- ✅ Be honest about limitations
- ✅ Keep it professional and concise

## Phase Completion
After PR is successfully created:
1. ✅ Commit created with proper format
2. ✅ Branch pushed to remote
3. ✅ PR created with complete description
4. ✅ Issue referenced in PR
5. Call 'workflow_orchestrator' with action 'mark_phase_complete'
6. This will mark the workflow as COMPLETE
7. The issue fix is now ready for maintainer review

**The workflow is complete when the PR is created and all phases are done.**"""

        return prompt

    async def _validate_implementation_complete(self) -> tuple[bool, str]:
        """
        Validate that implementation phase work was actually completed.
        
        Returns:
            (is_valid, error_message)
        """
        import subprocess
        from pathlib import Path
        
        # Check 1: Branch must be created and we must be on it
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()
            
            # Must not be on main/master
            if current_branch in ["main", "master"]:
                return False, "❌ VALIDATION FAILED: You are still on main/master branch. You MUST create and switch to a feature branch before marking implementation complete."
            
            # Branch should match expected pattern
            if self.state.issue_number:
                expected_branch = self.config.oss.branch_naming_pattern.format(number=self.state.issue_number)
                if current_branch != expected_branch:
                    logger.warning(f"Branch name mismatch: expected {expected_branch}, got {current_branch}")
        except Exception as e:
            logger.error(f"Error checking git branch: {e}")
            return False, f"❌ VALIDATION FAILED: Could not verify git branch. Error: {e}"
        
        # Check 2: Files must be modified
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                check=True,
            )
            modified_files = [line for line in result.stdout.strip().split("\n") if line.strip()]
            
            if not modified_files:
                return False, "❌ VALIDATION FAILED: No files have been modified. You MUST make code changes before marking implementation complete. Use 'edit' or 'write_file' tools to make changes."
            
            # Check that at least one file is actually modified (not just untracked)
            has_modified = any(line.startswith(("M ", "A ", "D ")) for line in modified_files)
            if not has_modified:
                return False, "❌ VALIDATION FAILED: No existing files have been modified. You MUST modify the relevant files to fix the issue before marking implementation complete."
            
            logger.info(f"Validation passed: {len(modified_files)} files modified on branch {current_branch}")
        except Exception as e:
            logger.error(f"Error checking git status: {e}")
            return False, f"❌ VALIDATION FAILED: Could not verify file changes. Error: {e}"
        
        return True, "✅ Validation passed: Branch created and files modified"

    async def mark_phase_complete(self, phase: WorkflowPhase) -> None:
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
        previous_phase = self.state.phase.value
        
        # CRITICAL: Only check branch when transitioning TO implementation phase
        # This is when code changes will happen, so we need to ensure we're on a feature branch
        # Don't check on every phase transition - only when it matters
        # Check if we're transitioning FROM planning TO implementation
        if previous_phase == WorkflowPhase.PLANNING.value:
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.repository_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                current_branch = result.stdout.strip()
                if current_branch in ["main", "master"]:
                    # Check if there are any uncommitted changes
                    status_result = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=self.repository_path,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    has_changes = bool(status_result.stdout.strip())
                    if has_changes:
                        # Only raise error if we're about to enter implementation phase with changes on main
                        # This warning should only appear once when transitioning to implementation
                        error_msg = f"❌ CRITICAL: You are on {current_branch} branch with uncommitted changes. You MUST create a feature branch before implementation phase. Use 'git_branch' tool with action='create' and branch_name='fix/issue-{self.state.issue_number or 'unknown'}' before making any changes."
                        # Log as warning, not error, to reduce verbosity
                        logger.warning(error_msg)
                        raise ValueError(error_msg)
            except ValueError:
                # Re-raise ValueError (our intentional error)
                raise
            except Exception as e:
                # Only log other exceptions as warnings, don't block workflow
                logger.debug(f"Could not verify branch during phase transition: {e}")
        
        # VALIDATION: For implementation phase, verify work was actually done
        if previous_phase == WorkflowPhase.IMPLEMENTATION.value:
            is_valid, validation_message = await self._validate_implementation_complete()
            if not is_valid:
                error_msg = f"Cannot mark implementation phase complete. {validation_message}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(validation_message)
        
        if current_idx < len(phase_order) - 1:
            # Add completed step to memory
            branch_name = self.state.branch_name or self.branch_memory.get_current_branch()
            if branch_name:
                self.branch_memory.add_completed_step(branch_name, f"Completed phase: {phase.value}")
            
            # Track modified files if we just completed implementation
            if previous_phase == WorkflowPhase.IMPLEMENTATION.value:
                await self._track_modified_files()
                self.state.changes_made = True
                logger.info(f"Tracked file modifications after implementation phase")
            
            self.state.phase = phase_order[current_idx + 1]
            self.state.updated_at = datetime.now()
            self.save_state()
            
            # Log phase transition
            logger.info(
                f"Phase transition: {previous_phase} -> {self.state.phase.value} "
                f"(Issue #{self.state.issue_number}, Branch: {branch_name or 'N/A'})"
            )
        else:
            logger.warning(f"Attempted to mark phase complete, but already at final phase: {self.state.phase.value}")

    def get_current_phase_info(self) -> dict[str, Any]:
        """Get information about the current phase."""
        analysis = self.state.repository_analysis or {}
        test_strategy = analysis.get("test_strategy", {})
        
        return {
            "phase": self.state.phase.value,
            "issue_number": self.state.issue_number,
            "branch_name": self.state.branch_name,
            "changes_made": self.state.changes_made,
            "tests_passed": self.state.tests_passed,
            "pr_url": self.state.pr_url,
            "test_strategy": test_strategy,
            "start_here_path": analysis.get("start_here_path"),
        }

    def get_state(self) -> WorkflowState:
        """Get current workflow state."""
        return self.state

    def save_state(self) -> None:
        """Save current state to branch memory."""
        self.branch_memory.save_workflow_state(self.state)
