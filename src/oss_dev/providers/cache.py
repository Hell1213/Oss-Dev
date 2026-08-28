"""Cache abstraction for provider API responses.

Provides a TTL-based, file-backed cache to avoid redundant
gh CLI calls within and across sessions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default cache settings
DEFAULT_TTL_SECONDS = 300          # 5 minutes
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "oss_dev" / "github"


class CacheEntry:
    """A single cached value with its expiry timestamp."""

    def __init__(self, value: Any, ttl: int) -> None:
        self.value = value
        self.expires_at: float = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "expires_at": self.expires_at}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        entry = cls.__new__(cls)
        entry.value = data["value"]
        entry.expires_at = data["expires_at"]
        return entry


class ResponseCache:
    """TTL-based, file-backed cache for GitHub CLI API responses.

    Each cache key maps to a JSON file on disk so that cache
    entries survive process restarts (up to their TTL).

    Usage::

        cache = ResponseCache(ttl=60)
        cache.set("my_key", {"some": "data"})
        value = cache.get("my_key")   # None if missing / expired
    """

    def __init__(
        self,
        ttl: int = DEFAULT_TTL_SECONDS,
        cache_dir: Path | None = None,
        enabled: bool = True,
    ) -> None:
        self._ttl = ttl
        self._enabled = enabled
        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR

        # In-memory layer (avoids repeated disk reads in the same process)
        self._memory: dict[str, CacheEntry] = {}

        if self._enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Cache initialised at %s (TTL=%ds)", self._cache_dir, ttl)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Return the cached value for *key*, or ``None`` if absent/expired."""
        if not self._enabled:
            return None

        # 1. Check in-memory layer first
        if key in self._memory:
            entry = self._memory[key]
            if not entry.is_expired():
                logger.debug("Cache hit (memory): %s", key)
                return entry.value
            # Stale – remove from memory and fall through to disk
            del self._memory[key]

        # 2. Check disk layer
        entry = self._load_from_disk(key)
        if entry is not None and not entry.is_expired():
            logger.debug("Cache hit (disk): %s", key)
            self._memory[key] = entry   # promote to memory layer
            return entry.value

        logger.debug("Cache miss: %s", key)
        return None

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key* with the configured TTL."""
        if not self._enabled:
            return

        entry = CacheEntry(value, self._ttl)
        self._memory[key] = entry
        self._save_to_disk(key, entry)
        logger.debug("Cache set: %s (expires in %ds)", key, self._ttl)

    def invalidate(self, key: str) -> None:
        """Remove a single entry from both memory and disk."""
        self._memory.pop(key, None)
        path = self._key_path(key)
        if path.exists():
            path.unlink()
            logger.debug("Cache invalidated: %s", key)

    def clear(self) -> None:
        """Wipe the entire cache (memory + disk)."""
        self._memory.clear()
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
        logger.debug("Cache cleared")

    def purge_expired(self) -> int:
        """Delete all expired disk entries. Returns the number of files removed."""
        removed = 0
        if not self._cache_dir.exists():
            return removed
        for path in self._cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                entry = CacheEntry.from_dict(data)
                if entry.is_expired():
                    path.unlink(missing_ok=True)
                    removed += 1
            except (json.JSONDecodeError, KeyError, OSError):
                path.unlink(missing_ok=True)   # corrupt file – remove it
                removed += 1
        logger.debug("Purged %d expired cache entries", removed)
        return removed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(*parts: str) -> str:
        """Build a safe cache key by hashing the given string parts."""
        raw = ":".join(str(p) for p in parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _key_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def _save_to_disk(self, key: str, entry: CacheEntry) -> None:
        path = self._key_path(key)
        try:
            path.write_text(json.dumps(entry.to_dict()))
        except OSError as exc:
            logger.warning("Cache write failed for key %s: %s", key, exc)

    def _load_from_disk(self, key: str) -> CacheEntry | None:
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return CacheEntry.from_dict(data)
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.warning("Cache read failed for key %s: %s", key, exc)
            return None