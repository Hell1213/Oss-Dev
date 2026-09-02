"""Compact phase prompts — replaces the 1085-line prompt generation
in the legacy oss/workflow.py god module.

Each phase prompt is kept under 15 lines to minimize token consumption.
The validation gates in the state machine are the real enforcement —
the prompt just guides the agent, it doesn't need to repeat every rule.
"""

from __future__ import annotations

from typing import Any


def get_phase_prompt(phase: str, context: dict[str, Any] | None = None) -> str:
    ctx = context or {}
    prompts = {
        "repository_understanding": _repo_analysis_prompt(ctx),
        "repo_analysis": _repo_analysis_prompt(ctx),
        "issue_intake": _issue_intake_prompt(ctx),
        "issue_analysis": _issue_intake_prompt(ctx),
        "planning": _planning_prompt(ctx),
        "implementation": _implementation_prompt(ctx),
        "verification": _verification_prompt(ctx),
        "validation": _validation_prompt(ctx),
        "commit_and_pr": _commit_pr_prompt(ctx),
        "commit_pr": _commit_pr_prompt(ctx),
    }
    return prompts.get(phase, f"Continue with the current workflow phase: {phase}")


def _repo_analysis_prompt(ctx: dict) -> str:
    return """# Phase: Repository Understanding
Analyze the repo structure. Use `analyze_repository` tool.
Check for START_HERE.md — create it with `create_start_here` if missing.
When done, call `workflow_orchestrator(action='mark_phase_complete')`."""


def _issue_intake_prompt(ctx: dict) -> str:
    url = ctx.get("issue_url", "the provided URL")
    return f"""# Phase: Issue Intake
Fetch issue {url} using `fetch_issue` tool.
Summarize: what's asked, what's out of scope, key requirements.
When done, call `workflow_orchestrator(action='mark_phase_complete')`."""


def _planning_prompt(ctx: dict) -> str:
    title = ctx.get("issue_title", "the issue")
    return f"""# Phase: Planning (NO CODE YET)
Plan the fix for: {title}.
Use `grep` and `read_file` to locate relevant code. Identify files to modify.
Do NOT write code, create branches, or make commits.
When your plan is ready, call `workflow_orchestrator(action='mark_phase_complete')`."""


def _implementation_prompt(ctx: dict) -> str:
    issue_num = ctx.get("issue_number", "unknown")
    return f"""# Phase: Implementation
1. Create branch `fix/issue-{issue_num}` using `git_branch(action='create')`.
2. Make minimal, scoped code changes using `edit` or `write_file`.
3. Verify with `git_status` and `git_diff`.
The workflow validates: branch created + files modified before allowing transition.
When done, call `workflow_orchestrator(action='mark_phase_complete')`."""


def _verification_prompt(ctx: dict) -> str:
    return """# Phase: Verification
Run the project's test suite using `shell`. Identify test commands from
START_HERE.md or CONTRIBUTING.md if unknown.
Fix regressions (max 3 iterations). Document pre-existing failures.
When tests pass, call `workflow_orchestrator(action='mark_phase_complete')`."""


def _validation_prompt(ctx: dict) -> str:
    return """# Phase: Validation
Validate changes against the original issue:
1. `git_diff` — review all changes
2. `fetch_issue` — re-read requirements
3. Check each file: is it necessary for the issue? Remove scope violations.
When validated, call `workflow_orchestrator(action='mark_phase_complete')`."""


def _commit_pr_prompt(ctx: dict) -> str:
    issue_num = ctx.get("issue_number", "N/A")
    branch = ctx.get("branch_name", "current branch")
    return f"""# Phase: Commit & PR
1. `git_commit` with message: `fix(scope): description` (conventional format)
2. Ask user confirmation with `user_confirm` BEFORE pushing
3. `git_push` to remote
4. `create_pr` with body referencing `Fixes #{issue_num}`
Branch: {branch}
After PR is created, call `workflow_orchestrator(action='mark_phase_complete')`."""
