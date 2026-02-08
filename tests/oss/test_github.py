"""
Tests for GitHub client.
"""


import pytest

from oss.github import GitHubClient
from config.config import Config, OSSConfig

import pytest
import asyncio

@pytest.mark.asyncio
async def test_fetch_issue_error_handling():
    """
    Test error handling of fetch_issue method.
    """
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)
    
    with pytest.raises(RuntimeError, match='Failed to fetch issue via GitHub CLI'):
        await client.fetch_issue('https://invalid-url.com')


    """
    Test error handling of fetch_issue method.
    """
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)
    
    with pytest.raises(RuntimeError, match='Failed to fetch issue via GitHub CLI'):
        await client.fetch_issue('https://invalid-url.com')


@pytest.mark.asyncio
async def test_create_pr_error_handling():
    """
    Test error handling of create_pr method.
    """
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)
    
    with pytest.raises(RuntimeError, match='Failed to create PR via GitHub CLI'):
        await client.create_pr('owner', 'repo', 'title', 'body', 'head')


    """
    Test error handling of create_pr method.
    """
    config = Config(oss=OSSConfig())
    client = GitHubClient(config)
    
    with pytest.raises(RuntimeError, match='Failed to create PR via GitHub CLI'):
        await client.create_pr('owner', 'repo', 'title', 'body', 'head')
