"""
OSS Tools Module

This module contains tools specific to OSS development workflows:
- Git operations
- GitHub API operations
- Repository analysis
"""

from config.config import Config
from tools.oss.git_status import GitStatusTool
from tools.oss.git_branch import GitBranchTool
from tools.oss.git_commit import GitCommitTool
from tools.oss.git_push import GitPushTool
from tools.oss.git_fetch import GitFetchTool
from tools.oss.git_diff import GitDiffTool
from tools.oss.git_rebase import GitRebaseTool
from tools.oss.git_merge import GitMergeTool
from tools.oss.fetch_issue import FetchIssueTool
from tools.oss.create_pr import CreatePRTool
from tools.oss.get_pr_status import GetPRStatusTool
from tools.oss.list_issues import ListIssuesTool
from tools.oss.check_pr_comments import CheckPRCommentsTool
from tools.oss.analyze_repository import AnalyzeRepositoryTool
from tools.oss.check_start_here import CheckStartHereTool
from tools.oss.create_start_here import CreateStartHereTool
from tools.oss.update_start_here import UpdateStartHereTool
from tools.oss.user_confirm import UserConfirmTool
from tools.oss.workflow_orchestrator import WorkflowOrchestratorTool
from tools.oss.branch_memory import BranchMemoryTool


def get_oss_tools(config: Config):
    """Get all OSS tools for registration."""
    tools = [
        # Git tools
        GitStatusTool(config),
        GitBranchTool(config),
        GitCommitTool(config),
        GitPushTool(config),
        GitFetchTool(config),
        GitDiffTool(config),
        GitRebaseTool(config),
        GitMergeTool(config),
    ]

    # GitHub tools (only if OSS is enabled)
    if config.oss.enabled:
        tools.extend([
            FetchIssueTool(config),
            CreatePRTool(config),
            GetPRStatusTool(config),
            ListIssuesTool(config),
            CheckPRCommentsTool(config),
            # Repository analysis tools
            AnalyzeRepositoryTool(config),
            CheckStartHereTool(config),
            CreateStartHereTool(config),
            UpdateStartHereTool(config),
            # Workflow orchestrator
            WorkflowOrchestratorTool(config),
            # Branch memory
            BranchMemoryTool(config),
            # User confirmation
            UserConfirmTool(config),
        ])

    return tools


__all__ = [
    "get_oss_tools",
    # Git tools
    "GitStatusTool",
    "GitBranchTool",
    "GitCommitTool",
    "GitPushTool",
    "GitFetchTool",
    "GitDiffTool",
    "GitRebaseTool",
    "GitMergeTool",
    # GitHub tools
    "FetchIssueTool",
    "CreatePRTool",
    "GetPRStatusTool",
    "ListIssuesTool",
    "CheckPRCommentsTool",
    # Repository analysis tools
    "AnalyzeRepositoryTool",
    "CheckStartHereTool",
    "CreateStartHereTool",
    "UpdateStartHereTool",
    # Workflow orchestrator
    "WorkflowOrchestratorTool",
    # Branch memory
    "BranchMemoryTool",
    # User confirmation
    "UserConfirmTool",
]
