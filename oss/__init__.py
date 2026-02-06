"""
OSS Dev Agent Module

This module provides Open Source Contributor Agent functionality,
transforming the AI Coding Agent into a first-class OSS contributor.
"""

__version__ = "0.1.0"

from oss.workflow import OSSWorkflow
from oss.repository import RepositoryManager
from oss.memory import BranchMemoryManager
from oss.github import GitHubClient

__all__ = [
    "OSSWorkflow",
    "RepositoryManager",
    "BranchMemoryManager",
    "GitHubClient",
]
