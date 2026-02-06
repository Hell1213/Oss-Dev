"""
Enhanced tests for branch memory system.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta

from oss.memory import BranchMemoryManager, BranchMemoryData


@pytest.mark.asyncio
async def test_context_summarization(temp_dir):
    """Test context summarization."""
    manager = BranchMemoryManager(temp_dir)
    
    # Create test memory
    memory = BranchMemoryData(
        branch_name="test-branch",
        issue_number=123,
        current_phase="implementation",
        work_summary="Fixed authentication bug",
        files_modified=["src/auth.py", "tests/test_auth.py"],
        completed_steps=["Phase 1", "Phase 2"],
    )
    manager.save_branch(memory)
    
    # Get summary
    summary = manager.summarize_context("test-branch")
    assert "Issue #123" in summary
    assert "implementation" in summary
    assert "Fixed authentication bug" in summary


@pytest.mark.asyncio
async def test_branch_switching(temp_dir):
    """Test branch switching."""
    manager = BranchMemoryManager(temp_dir)
    
    # Create memory for branch1
    memory1 = BranchMemoryData(
        branch_name="branch1",
        issue_number=1,
        current_phase="planning",
    )
    manager.save_branch(memory1)
    
    # Create memory for branch2
    memory2 = BranchMemoryData(
        branch_name="branch2",
        issue_number=2,
        current_phase="implementation",
    )
    manager.save_branch(memory2)
    
    # Switch to branch2
    target_memory = manager.switch_branch("branch2")
    assert target_memory is not None
    assert target_memory["issue_number"] == 2
    assert target_memory["current_phase"] == "implementation"


@pytest.mark.asyncio
async def test_file_tracking(temp_dir):
    """Test file modification tracking."""
    manager = BranchMemoryManager(temp_dir)
    
    branch_name = "test-branch"
    memory = BranchMemoryData(branch_name=branch_name)
    manager.save_branch(memory)
    
    # Add files
    manager.add_file_modified(branch_name, "src/file1.py")
    manager.add_file_modified(branch_name, "src/file2.py")
    
    # Verify
    memory_data = manager.load_branch(branch_name)
    assert "src/file1.py" in memory_data["files_modified"]
    assert "src/file2.py" in memory_data["files_modified"]


@pytest.mark.asyncio
async def test_completed_steps_tracking(temp_dir):
    """Test completed steps tracking."""
    manager = BranchMemoryManager(temp_dir)
    
    branch_name = "test-branch"
    memory = BranchMemoryData(branch_name=branch_name)
    manager.save_branch(memory)
    
    # Add steps
    manager.add_completed_step(branch_name, "Phase 1 complete")
    manager.add_completed_step(branch_name, "Phase 2 complete")
    
    # Verify
    memory_data = manager.load_branch(branch_name)
    assert "Phase 1 complete" in memory_data["completed_steps"]
    assert "Phase 2 complete" in memory_data["completed_steps"]


@pytest.mark.asyncio
async def test_memory_cleanup(temp_dir):
    """Test memory cleanup."""
    manager = BranchMemoryManager(temp_dir)
    
    # Create old memory
    old_memory = BranchMemoryData(
        branch_name="old-branch",
        issue_number=1,
    )
    old_memory.updated_at = (datetime.now() - timedelta(days=31)).isoformat()
    manager.save_branch(old_memory)
    
    # Create recent memory
    recent_memory = BranchMemoryData(
        branch_name="recent-branch",
        issue_number=2,
    )
    manager.save_branch(recent_memory)
    
    # Cleanup (30 days default)
    cleaned = manager.cleanup_old_memories(days=30)
    
    # Old memory should be cleaned if branch doesn't exist
    # Recent memory should remain
    recent_data = manager.load_branch("recent-branch")
    assert recent_data is not None


@pytest.mark.asyncio
async def test_branch_summary(temp_dir):
    """Test branch summary generation."""
    manager = BranchMemoryManager(temp_dir)
    
    memory = BranchMemoryData(
        branch_name="test-branch",
        issue_number=123,
        issue_url="https://github.com/test/repo/issues/123",
        current_phase="verification",
        status="in_progress",
        files_modified=["file1.py", "file2.py"],
        completed_steps=["step1", "step2"],
    )
    manager.save_branch(memory)
    
    summary = manager.get_branch_summary("test-branch")
    
    assert summary["branch_name"] == "test-branch"
    assert summary["issue_number"] == 123
    assert summary["current_phase"] == "verification"
    assert summary["files_modified"] == 2
    assert summary["completed_steps"] == 2
    assert summary["exists"] is True


@pytest.mark.asyncio
async def test_list_branches(temp_dir):
    """Test listing all branches."""
    manager = BranchMemoryManager(temp_dir)
    
    # Create multiple branch memories
    for i in range(3):
        memory = BranchMemoryData(
            branch_name=f"branch-{i}",
            issue_number=i,
        )
        manager.save_branch(memory)
    
    branches = manager.list_branches()
    assert len(branches) == 3
    assert all(b["branch_name"].startswith("branch-") for b in branches)
