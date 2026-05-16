"""
Tests for OSS Workflow orchestrator.
"""

import pytest

from oss.workflow import OSSWorkflow, WorkflowPhase


@pytest.mark.asyncio
async def test_workflow_initialization(test_config, temp_dir):
    """Test workflow initialization."""
    workflow = OSSWorkflow(test_config, repository_path=temp_dir)
    
    assert workflow.repository_path == temp_dir
    assert workflow.state.phase == WorkflowPhase.REPOSITORY_UNDERSTANDING
    assert workflow.state.repository_path == temp_dir


@pytest.mark.asyncio
async def test_workflow_state_management(test_config, temp_dir):
    """Test workflow state management."""
    workflow = OSSWorkflow(test_config, repository_path=temp_dir)
    
    state = workflow.get_state()
    assert state.phase == WorkflowPhase.REPOSITORY_UNDERSTANDING
    
    # Test state update
    workflow.state.phase = WorkflowPhase.ISSUE_INTAKE
    updated_state = workflow.get_state()
    assert updated_state.phase == WorkflowPhase.ISSUE_INTAKE


@pytest.mark.asyncio
async def test_workflow_starts_without_branch(test_config, temp_dir):
    """Test initial workflow branch state."""
    workflow = OSSWorkflow(test_config, repository_path=temp_dir)

    assert workflow.state.branch_name is None
    assert workflow.state.changes_made is False
    assert workflow.state.tests_passed is False
