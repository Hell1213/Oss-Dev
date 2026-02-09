"""
Tests for OSS Workflow orchestrator.
"""

import pytest
from pathlib import Path

from oss.workflow import OSSWorkflow, WorkflowPhase
from config.config import Config, OSSConfig


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
async def test_workflow_confirmation(test_config, temp_dir):
    """Test workflow confirmation logic."""
    workflow = OSSWorkflow(test_config, repository_path=temp_dir)
    
    # Testing confirmation functionality for OSSWorkflow
    assert workflow.confirmation_required() is True  # Assuming it should require confirmation
