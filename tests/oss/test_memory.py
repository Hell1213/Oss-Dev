"""
Tests for Branch Memory Manager.
"""

import pytest
from pathlib import Path

from oss.memory import BranchMemoryManager, BranchMemoryData


def test_branch_memory_manager_initialization(temp_dir):
    """Test branch memory manager initialization."""
    manager = BranchMemoryManager(temp_dir)
    
    assert manager.repository_path == Path(temp_dir).resolve()
    assert manager.memory_dir.exists()


def test_branch_memory_save_and_load(temp_dir):
    """Test saving and loading branch memory."""
    manager = BranchMemoryManager(temp_dir)
    
    memory = BranchMemoryData(
        branch_name="test-branch",
        issue_url="https://github.com/owner/repo/issues/123",
        issue_number=123,
    )
    
    manager.save_branch(memory)
    
    loaded = manager.load_branch("test-branch")
    assert loaded is not None
    assert loaded["branch_name"] == "test-branch"
    assert loaded["issue_number"] == 123
