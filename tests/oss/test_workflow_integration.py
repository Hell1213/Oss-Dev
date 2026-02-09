"""
Integration tests for OSS workflow.
"""

import pytest
from pathlib import Path

from oss.workflow import OSSWorkflow, WorkflowPhase
from config.config import Config, OSSConfig


@pytest.mark.asyncio
async def test_workflow_start(test_config, temp_dir):
    valid_issue_url = 'https://github.com/Hell1213/Oss-Dev/issues/21'
    """Test workflow start."""
    workflow = OSSWorkflow(test_config, repository_path=temp_dir)
    workflow.state.phase = WorkflowPhase.PLANNING
    
    # Mock issue URL
    issue_url = valid_issue_url
    
    # Start workflow (will execute phases 1-2)
    state = await workflow.start(issue_url)
    
    assert state.issue_url == issue_url
    assert state.issue_number == 123
    assert state.phase == WorkflowPhase.PLANNING  # Should be at planning after start


@pytest.mark.asyncio
async def test_workflow_phase_prompts(test_config, temp_dir):
    """Test workflow phase prompts."""
    workflow = OSSWorkflow(test_config, repository_path=temp_dir)
    workflow.state.phase = WorkflowPhase.PLANNING
    
    # Test each phase prompt
    workflow.state.phase = WorkflowPhase.REPOSITORY_UNDERSTANDING
    prompt = workflow.get_phase_prompt()
    assert "repository" in prompt.lower() or "analyze" in prompt.lower()
    
    workflow.state.phase = WorkflowPhase.PLANNING
    prompt = workflow.get_phase_prompt()
    assert "plan" in prompt.lower()


@pytest.mark.asyncio
async def test_workflow_phase_transition(test_config, temp_dir):
    """Test workflow phase transitions."""
    workflow = OSSWorkflow(test_config, repository_path=temp_dir)
    workflow.state.phase = WorkflowPhase.PLANNING
    
    # Start at planning
    workflow.state.phase = WorkflowPhase.PLANNING
    
    # Mark complete - should transition to implementation
    await workflow.mark_phase_complete(WorkflowPhase.PLANNING)
    assert workflow.state.phase == WorkflowPhase.IMPLEMENTATION
