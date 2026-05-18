"""Bounded LRU cache for the immutable read paths in the UI server (spec 0079).

The supabase-backed UI re-fetches per-turn artifacts (`inputs/<key>.json`,
`searches/<key>.json`) from Postgres on every modal open. These bundles are
append-only-immutable: a run only ever writes a given turn-key once, retries
allocate a new key, and `session_files` rows are never updated in place. That
makes a process-lifetime cache safe with zero invalidation logic.

Bounded by entry count (size-aware eviction is a follow-up if real bundles
turn out larger than expected). Process restart on deploy clears the cache —
no other invalidation hook is needed.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Hashable


_MISSING: Any = object()


class BoundedLRU:
    """Thread-safe LRU keyed by hashable tuples. Stores arbitrary values
    (including ``None``) without collapsing them into a miss."""

    def __init__(self, maxsize: int = 100) -> None:
        self._maxsize = maxsize
        self._cache: OrderedDict[Hashable, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> Any:
        """Return the cached value or the module-private ``_MISSING`` sentinel.

        Callers should compare against :data:`MISSING` rather than truth-test,
        since ``None`` is a legitimate cached value.
        """
        with self._lock:
            value = self._cache.get(key, _MISSING)
            if value is not _MISSING:
                self._cache.move_to_end(key)
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


MISSING = _MISSING

__all__ = ["BoundedLRU", "MISSING"]
