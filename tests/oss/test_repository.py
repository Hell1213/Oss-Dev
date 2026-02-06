"""
Tests for Repository Manager.
"""

import pytest
from pathlib import Path

from oss.repository import RepositoryManager
from config.config import Config, OSSConfig


@pytest.mark.asyncio
async def test_repository_manager_initialization(temp_dir):
    """Test repository manager initialization."""
    manager = RepositoryManager(temp_dir)
    
    assert manager.repository_path == Path(temp_dir).resolve()
    assert manager.start_here_path == Path(temp_dir) / "START_HERE.md"


@pytest.mark.asyncio
async def test_repository_analysis(temp_dir):
    """Test repository analysis."""
    manager = RepositoryManager(temp_dir)
    
    # First analysis should create START_HERE.md
    analysis = await manager.analyze()
    
    assert analysis["start_here_exists"] is True
    assert manager.start_here_path.exists()
    
    # Second analysis should use cache
    cached_analysis = await manager.load_analysis()
    assert cached_analysis is not None
