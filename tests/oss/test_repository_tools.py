"""
Tests for repository analysis tools.
"""

import pytest
from pathlib import Path

from tools.oss.analyze_repository import AnalyzeRepositoryTool, AnalyzeRepositoryParams
from tools.oss.check_start_here import CheckStartHereTool, CheckStartHereParams
from tools.oss.create_start_here import CreateStartHereTool, CreateStartHereParams
from config.config import Config, OSSConfig


@pytest.mark.asyncio
async def test_analyze_repository_tool(test_config, temp_dir):
    """Test analyze repository tool."""
    # Create a simple Python project structure
    (temp_dir / "main.py").write_text("# Main entry point")
    (temp_dir / "requirements.txt").write_text("requests>=2.0.0")
    (temp_dir / "tests").mkdir()
    (temp_dir / "tests" / "test_main.py").write_text("# Tests")

    tool = AnalyzeRepositoryTool(test_config)

    params = AnalyzeRepositoryParams(path=str(temp_dir))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': temp_dir
    })()

    result = await tool.execute(invocation)
    assert result.success is True
    assert "Repository Analysis" in result.output
    assert "Python" in result.output


@pytest.mark.asyncio
async def test_check_start_here_exists(test_config, temp_dir):
    """Test check START_HERE.md when it exists."""
    start_here = temp_dir / "START_HERE.md"
    start_here.write_text("# START_HERE.md\n\nTest content")

    tool = CheckStartHereTool(test_config)

    params = CheckStartHereParams(path=str(temp_dir))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': temp_dir
    })()

    result = await tool.execute(invocation)
    assert result.success is True
    assert "START_HERE.md exists" in result.output


@pytest.mark.asyncio
async def test_check_start_here_missing(test_config, temp_dir):
    """Test check START_HERE.md when it doesn't exist."""
    tool = CheckStartHereTool(test_config)

    params = CheckStartHereParams(path=str(temp_dir))
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': temp_dir
    })()

    result = await tool.execute(invocation)
    assert result.success is True
    assert "does not exist" in result.output


@pytest.mark.asyncio
async def test_create_start_here_tool(test_config, temp_dir):
    """Test create START_HERE.md tool."""
    # Create a simple project structure
    (temp_dir / "main.py").write_text("# Main")
    (temp_dir / "requirements.txt").write_text("requests")

    tool = CreateStartHereTool(test_config)

    params = CreateStartHereParams(path=str(temp_dir), force=False)
    invocation = type('obj', (object,), {
        'params': params.model_dump(),
        'cwd': temp_dir
    })()

    result = await tool.execute(invocation)
    assert result.success is True
    assert "Created START_HERE.md" in result.output

    # Verify file was created
    start_here = temp_dir / "START_HERE.md"
    assert start_here.exists()
