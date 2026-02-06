"""
Tests for OSS-specific prompts.
"""

import pytest

from prompts.oss import (
    get_oss_identity_prompt,
    get_scope_discipline_prompt,
    get_repository_understanding_prompt,
    get_issue_intake_prompt,
    get_planning_prompt,
    get_implementation_prompt,
    get_verification_prompt,
    get_validation_prompt,
    get_commit_and_pr_prompt,
)
from prompts.oss_review import (
    get_code_review_self_check_prompt,
    get_maintainer_feedback_prompt,
    get_rebase_prompt,
    get_scope_violation_check_prompt,
)


def test_oss_identity_prompt():
    """Test OSS identity prompt."""
    prompt = get_oss_identity_prompt()
    assert "OSS Contributor Identity" in prompt
    assert "maintainer" in prompt.lower()
    assert "scope discipline" in prompt.lower()


def test_scope_discipline_prompt():
    """Test scope discipline prompt."""
    prompt = get_scope_discipline_prompt()
    assert "Scope Discipline" in prompt
    assert "DO:" in prompt
    assert "DO NOT:" in prompt
    assert "maintainer" in prompt.lower()


def test_repository_understanding_prompt():
    """Test repository understanding prompt."""
    prompt = get_repository_understanding_prompt({})
    assert "Phase 1" in prompt
    assert "Repository Understanding" in prompt
    assert "START_HERE.md" in prompt


def test_issue_intake_prompt():
    """Test issue intake prompt."""
    context = {"issue_url": "https://github.com/test/repo/issues/123"}
    prompt = get_issue_intake_prompt(context)
    assert "Phase 2" in prompt
    assert "Issue Intake" in prompt
    assert "123" in prompt


def test_planning_prompt():
    """Test planning prompt."""
    context = {
        "issue_data": {
            "title": "Fix bug",
            "body": "This is a bug description",
        },
        "repository_analysis": {
            "architecture_summary": "Python web application",
            "key_folders": {"src": "Source code", "tests": "Tests"},
        },
    }
    prompt = get_planning_prompt(context)
    assert "Phase 3" in prompt
    assert "Planning" in prompt
    assert "NO CODE YET" in prompt
    assert "Fix bug" in prompt


def test_implementation_prompt():
    """Test implementation prompt."""
    context = {
        "issue_title": "Fix bug",
        "branch_name": "feature/fix-bug",
        "plan": "Step 1: Fix the bug",
    }
    prompt = get_implementation_prompt(context)
    assert "Phase 4" in prompt
    assert "Implementation" in prompt
    assert "STRICTLY within issue scope" in prompt


def test_verification_prompt():
    """Test verification prompt."""
    context = {
        "test_strategy": {
            "unit": "pytest tests/",
            "integration": "pytest tests/integration/",
        }
    }
    prompt = get_verification_prompt(context)
    assert "Phase 5" in prompt
    assert "Verification" in prompt
    assert "pytest" in prompt


def test_validation_prompt():
    """Test validation prompt."""
    context = {
        "issue_title": "Fix bug",
        "issue_body": "This is a bug that needs fixing",
    }
    prompt = get_validation_prompt(context)
    assert "Phase 6" in prompt
    assert "Validation" in prompt
    assert "git_status" in prompt
    assert "git_diff" in prompt


def test_commit_and_pr_prompt():
    """Test commit and PR prompt."""
    context = {
        "issue_number": 123,
        "issue_title": "Fix bug",
    }
    prompt = get_commit_and_pr_prompt(context)
    assert "Phase 7" in prompt
    assert "Commit & PR" in prompt
    assert "123" in prompt
    assert "conventional commit" in prompt.lower() or "type(scope)" in prompt


def test_code_review_self_check_prompt():
    """Test code review self-check prompt."""
    prompt = get_code_review_self_check_prompt(
        "Changed file1.py and file2.py",
        "Fix the bug"
    )
    assert "Code Review Self-Check" in prompt
    assert "Scope Alignment" in prompt
    assert "Code Quality" in prompt
    assert "file1.py" in prompt


def test_maintainer_feedback_prompt():
    """Test maintainer feedback prompt."""
    prompt = get_maintainer_feedback_prompt(
        "Please add tests for this fix",
        "https://github.com/test/repo/pull/123"
    )
    assert "Maintainer Feedback" in prompt
    assert "123" in prompt
    assert "tests" in prompt.lower()


def test_rebase_prompt():
    """Test rebase prompt."""
    prompt = get_rebase_prompt("main")
    assert "Rebase" in prompt
    assert "main" in prompt
    assert "conflicts" in prompt.lower()


def test_scope_violation_check_prompt():
    """Test scope violation check prompt."""
    prompt = get_scope_violation_check_prompt(
        "Changed file1.py, file2.py, and formatted file3.py",
        "Fix bug in file1.py"
    )
    assert "Scope Violation Check" in prompt
    assert "Unrelated Files" in prompt
    assert "Formatting Changes" in prompt
