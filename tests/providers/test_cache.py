"""Unit tests for the caching layer and its integration with GitHubCLIProvider.

Run with:
    pytest tests/providers/test_cache.py -v
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from oss_dev.providers.cache import CacheEntry, ResponseCache


# ======================================================================
# Helpers / fixtures
# ======================================================================

@pytest.fixture()
def tmp_cache(tmp_path: Path) -> ResponseCache:
    """A ResponseCache that writes to a temp directory."""
    return ResponseCache(ttl=60, cache_dir=tmp_path, enabled=True)


def _make_config(enabled: bool = True, ttl: int = 300, cache_dir=None):
    """Build a minimal Config-like object with a cache sub-namespace."""
    cache_ns = SimpleNamespace(enabled=enabled, ttl=ttl, dir=cache_dir)
    return SimpleNamespace(cache=cache_ns)


# ======================================================================
# CacheEntry
# ======================================================================

class TestCacheEntry:
    def test_not_expired_within_ttl(self):
        entry = CacheEntry("hello", ttl=60)
        assert not entry.is_expired()

    def test_expired_after_ttl(self):
        entry = CacheEntry("hello", ttl=0)
        # expires_at is set to time.time() + 0, so it may already be expired
        # Force it to be in the past
        entry.expires_at = time.time() - 1
        assert entry.is_expired()

    def test_round_trip_dict(self):
        entry = CacheEntry({"key": "value"}, ttl=30)
        restored = CacheEntry.from_dict(entry.to_dict())
        assert restored.value == {"key": "value"}
        assert restored.expires_at == pytest.approx(entry.expires_at, abs=0.01)


# ======================================================================
# ResponseCache – basic get / set
# ======================================================================

class TestResponseCacheGetSet:
    def test_get_returns_none_on_miss(self, tmp_cache):
        assert tmp_cache.get("nonexistent") is None

    def test_set_then_get_returns_value(self, tmp_cache):
        tmp_cache.set("k1", "hello")
        assert tmp_cache.get("k1") == "hello"

    def test_set_persists_to_disk(self, tmp_cache, tmp_path):
        tmp_cache.set("k2", {"a": 1})
        key = "k2"
        disk_file = tmp_path / f"{key}.json"
        assert disk_file.exists()
        data = json.loads(disk_file.read_text())
        assert data["value"] == {"a": 1}

    def test_get_reads_from_disk_after_memory_eviction(self, tmp_path):
        # Write directly via one instance, read via another (no shared memory)
        c1 = ResponseCache(ttl=60, cache_dir=tmp_path, enabled=True)
        c1.set("disk_key", "disk_value")

        c2 = ResponseCache(ttl=60, cache_dir=tmp_path, enabled=True)
        assert c2.get("disk_key") == "disk_value"

    def test_expired_entry_returns_none(self, tmp_path):
        cache = ResponseCache(ttl=60, cache_dir=tmp_path, enabled=True)
        cache.set("exp_key", "will_expire")
        # Manually expire the disk entry
        key = ResponseCache.make_key()  # not used here; key is literal "exp_key"
        entry_path = tmp_path / "exp_key.json"
        data = json.loads(entry_path.read_text())
        data["expires_at"] = time.time() - 1
        entry_path.write_text(json.dumps(data))
        # Also clear memory to force disk read
        cache._memory.clear()
        assert cache.get("exp_key") is None


# ======================================================================
# ResponseCache – disabled mode
# ======================================================================

class TestResponseCacheDisabled:
    def test_get_always_returns_none_when_disabled(self, tmp_path):
        cache = ResponseCache(ttl=60, cache_dir=tmp_path, enabled=False)
        cache.set("k", "v")   # should be a no-op
        assert cache.get("k") is None

    def test_no_files_written_when_disabled(self, tmp_path):
        cache = ResponseCache(ttl=60, cache_dir=tmp_path, enabled=False)
        cache.set("k", "v")
        assert list(tmp_path.glob("*.json")) == []


# ======================================================================
# ResponseCache – invalidate / clear / purge
# ======================================================================

class TestResponseCacheManagement:
    def test_invalidate_removes_entry(self, tmp_cache):
        tmp_cache.set("del_me", 42)
        tmp_cache.invalidate("del_me")
        assert tmp_cache.get("del_me") is None

    def test_clear_removes_all_entries(self, tmp_cache):
        for i in range(5):
            tmp_cache.set(f"key{i}", i)
        tmp_cache.clear()
        for i in range(5):
            assert tmp_cache.get(f"key{i}") is None

    def test_purge_expired_removes_stale_files(self, tmp_path):
        cache = ResponseCache(ttl=60, cache_dir=tmp_path, enabled=True)
        cache.set("good", "ok")
        cache.set("bad", "stale")

        # Manually expire "bad"
        bad_path = tmp_path / "bad.json"
        data = json.loads(bad_path.read_text())
        data["expires_at"] = time.time() - 1
        bad_path.write_text(json.dumps(data))

        removed = cache.purge_expired()
        assert removed == 1
        assert not bad_path.exists()
        assert (tmp_path / "good.json").exists()


# ======================================================================
# ResponseCache – make_key
# ======================================================================

class TestMakeKey:
    def test_same_parts_produce_same_key(self):
        assert ResponseCache.make_key("a", "b", "c") == ResponseCache.make_key("a", "b", "c")

    def test_different_parts_produce_different_keys(self):
        assert ResponseCache.make_key("a", "1") != ResponseCache.make_key("a", "2")

    def test_key_is_hex_string(self):
        key = ResponseCache.make_key("owner", "repo", "42")
        assert all(c in "0123456789abcdef" for c in key)


# ======================================================================
# GitHubCLIProvider – caching integration
# ======================================================================

class TestGitHubCLIProviderCaching:
    """Validate that the provider uses the cache correctly.

    We patch ``_run_gh`` (the raw subprocess wrapper) so no real
    ``gh`` process is spawned. The cache is an in-process
    ResponseCache with a temp directory.
    """

    def _make_provider(self, tmp_path, enabled=True, ttl=300):
        # Import here so the test file doesn't fail if the module path
        # changes during development
        from oss_dev.providers.github.client import GitHubCLIProvider

        config = _make_config(enabled=enabled, ttl=ttl, cache_dir=str(tmp_path))
        with patch.object(GitHubCLIProvider, "_check_gh", return_value=True):
            provider = GitHubCLIProvider(config)
        # Replace cache dir to use tmp_path
        provider._cache = ResponseCache(ttl=ttl, cache_dir=tmp_path, enabled=enabled)
        return provider

    @pytest.mark.asyncio
    async def test_fetch_issue_cached_on_second_call(self, tmp_path):
        from oss_dev.providers.github.client import GitHubCLIProvider

        provider = self._make_provider(tmp_path)
        issue_json = json.dumps({
            "number": 1, "title": "Test", "body": "Body",
            "state": "open", "labels": [],
        })

        with patch.object(provider, "_run_gh", return_value=issue_json) as mock_gh:
            await provider.fetch_issue("owner", "repo", 1)
            await provider.fetch_issue("owner", "repo", 1)   # should hit cache

        # gh should only have been called once
        assert mock_gh.call_count == 1

    @pytest.mark.asyncio
    async def test_list_issues_cached(self, tmp_path):
        from oss_dev.providers.github.client import GitHubCLIProvider

        provider = self._make_provider(tmp_path)
        line = json.dumps({
            "number": 7, "title": "Issue 7",
            "state": "open", "labels": [], "url": "https://github.com/o/r/issues/7",
        })

        with patch.object(provider, "_run_gh", return_value=line) as mock_gh:
            await provider.list_issues("owner", "repo", limit=1)
            await provider.list_issues("owner", "repo", limit=1)

        assert mock_gh.call_count == 1

    @pytest.mark.asyncio
    async def test_create_pr_never_cached(self, tmp_path):
        """Mutating calls must always hit gh, never cache."""
        from oss_dev.providers.github.client import GitHubCLIProvider

        provider = self._make_provider(tmp_path)
        pr_json = json.dumps({"url": "https://github.com/o/r/pull/1", "number": 1, "title": "PR"})

        with patch.object(provider, "_run_gh", return_value=pr_json) as mock_gh:
            await provider.create_pr("owner", "repo", "Title", "Body", "feat/branch")
            await provider.create_pr("owner", "repo", "Title", "Body", "feat/branch")

        assert mock_gh.call_count == 2   # called every time

    @pytest.mark.asyncio
    async def test_cache_disabled_always_calls_gh(self, tmp_path):
        from oss_dev.providers.github.client import GitHubCLIProvider

        provider = self._make_provider(tmp_path, enabled=False)
        issue_json = json.dumps({
            "number": 1, "title": "T", "body": "B",
            "state": "open", "labels": [],
        })

        with patch.object(provider, "_run_gh", return_value=issue_json) as mock_gh:
            await provider.fetch_issue("owner", "repo", 1)
            await provider.fetch_issue("owner", "repo", 1)

        assert mock_gh.call_count == 2

    @pytest.mark.asyncio
    async def test_get_pr_status_cached(self, tmp_path):
        from oss_dev.providers.github.client import GitHubCLIProvider

        provider = self._make_provider(tmp_path)
        pr_status = json.dumps({
            "state": "OPEN", "isDraft": False,
            "reviewDecision": None, "url": "https://github.com/o/r/pull/5",
        })

        with patch.object(provider, "_run_gh", return_value=pr_status) as mock_gh:
            await provider.get_pr_status("owner", "repo", 5)
            await provider.get_pr_status("owner", "repo", 5)

        assert mock_gh.call_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_forces_fresh_call(self, tmp_path):
        from oss_dev.providers.github.client import GitHubCLIProvider

        provider = self._make_provider(tmp_path)
        issue_json = json.dumps({
            "number": 2, "title": "T", "body": "B",
            "state": "open", "labels": [],
        })

        with patch.object(provider, "_run_gh", return_value=issue_json) as mock_gh:
            await provider.fetch_issue("owner", "repo", 2)
            provider.invalidate_issue_cache("owner", "repo", 2)
            await provider.fetch_issue("owner", "repo", 2)

        assert mock_gh.call_count == 2