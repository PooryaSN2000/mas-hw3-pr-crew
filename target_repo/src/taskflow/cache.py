"""Result caching utilities for avoiding redundant task execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from taskflow.models import TaskSpec


class ResultCache:
    """In-memory (and optionally disk-backed) cache for TaskResult outputs."""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._store: Dict[str, Any] = {}
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.hits: int = 0
        self.misses: int = 0
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def compute_key(
        self,
        task: TaskSpec,
        upstream_outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Compute a deterministic cache key for a task execution.

        `upstream_outputs` is accepted as an optional mapping of upstream
        task names to their produced outputs.
        """
        payload = f"{task.name}:{task.command}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def has(self, key: str) -> bool:
        """Return True if key exists in memory or on disk."""
        if key in self._store:
            return True
        if self.cache_dir is not None:
            return (self.cache_dir / f"{key}.json").exists()
        return False

    def get(self, key: str) -> Any:
        """Retrieve a cached output value by key and record hit/miss stats."""
        if key in self._store:
            self.hits += 1
            return self._store[key]
        if self.cache_dir is not None:
            path = self.cache_dir / f"{key}.json"
            if path.exists():
                value = json.loads(path.read_text(encoding="utf-8"))
                self._store[key] = value
                self.hits += 1
                return value
        self.misses += 1
        raise KeyError(f"Cache key not found: {key}")

    def set(self, key: str, value: Any) -> None:
        """Store a task output value under the given key."""
        self._store[key] = value
        if self.cache_dir is not None:
            path = self.cache_dir / f"{key}.json"
            path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def invalidate(self, key: str) -> bool:
        """Remove a single key from memory and disk; return True if removed."""
        removed = key in self._store
        self._store.pop(key, None)
        if self.cache_dir is not None:
            path = self.cache_dir / f"{key}.json"
            if path.exists():
                path.unlink()
                removed = True
        return removed

    def clear(self) -> None:
        """Remove all cached entries and reset counters."""
        self._store.clear()
        self.hits = 0
        self.misses = 0
        if self.cache_dir is not None and self.cache_dir.exists():
            for item in self.cache_dir.glob("*.json"):
                item.unlink()

    def size(self) -> int:
        """Return the number of entries currently cached in memory."""
        return len(self._store)

    def stats(self) -> Dict[str, Any]:
        """Return cache hit/miss summary statistics."""
        total = self.hits + self.misses
        return {
            "entries": self.size(),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total > 0 else 0.0,
        }
