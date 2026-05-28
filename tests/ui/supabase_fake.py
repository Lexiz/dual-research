"""In-memory fake supabase-py client supporting the read-side chain.

Tests for spec 0020 use this to exercise the supabase backend of the UI
server without hitting a live Supabase project. The chain mirrors the
PostgREST builder API that supabase-py wraps:

    client.table("runs").select("*").eq("id", x).order("created_at", desc=True).limit(10).execute()

Supports: select (no-op projection), eq, in_, order, range, limit. Returns
a result object with .data (and .count if available).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass
class FakeResult:
    data: list[dict[str, Any]]
    count: int | None = None


class FakeBuilder:
    def __init__(self, rows: Iterable[dict[str, Any]]):
        # Hold a reference to the underlying list so mutations (upsert/delete)
        # are visible to the next builder for the same table.
        self._rows: list[dict[str, Any]] = rows if isinstance(rows, list) else list(rows)
        self._filters: list[Callable[[dict[str, Any]], bool]] = []
        self._sort: tuple[str, bool] | None = None
        self._range: tuple[int, int] | None = None
        self._limit: int | None = None
        self._upsert: list[dict[str, Any]] | None = None
        self._on_conflict: str | None = None
        self._delete: bool = False
        self._update: dict[str, Any] | None = None

    # ─── chain ───────────────────────────────────────────────────────────────

    def select(self, columns: str = "*", **_kw: Any) -> "FakeBuilder":
        return self

    def eq(self, col: str, val: Any) -> "FakeBuilder":
        self._filters.append(lambda r: r.get(col) == val)
        return self

    def neq(self, col: str, val: Any) -> "FakeBuilder":
        self._filters.append(lambda r: r.get(col) != val)
        return self

    def in_(self, col: str, vals: list[Any]) -> "FakeBuilder":
        valset = set(vals)
        self._filters.append(lambda r: r.get(col) in valset)
        return self

    def order(self, col: str, *, desc: bool = False) -> "FakeBuilder":
        self._sort = (col, desc)
        return self

    def range(self, start: int, end: int) -> "FakeBuilder":
        # PostgREST range is inclusive on both ends.
        self._range = (start, end + 1)
        return self

    def limit(self, n: int) -> "FakeBuilder":
        self._limit = n
        return self

    def upsert(self, rows: list[dict[str, Any]], on_conflict: str = "") -> "FakeBuilder":
        self._upsert = list(rows)
        self._on_conflict = on_conflict
        return self

    def update(self, patch: dict[str, Any]) -> "FakeBuilder":
        # Spec 0125: in-place UPDATE on rows matching the chain's eq/neq/in_
        # filters. PostgREST always requires a filter; we mirror that by
        # returning empty if no filters were applied.
        self._update = dict(patch)
        return self

    def delete(self) -> "FakeBuilder":
        self._delete = True
        return self

    # ─── terminator ──────────────────────────────────────────────────────────

    def execute(self) -> FakeResult:
        if self._update is not None:
            if not self._filters:
                return FakeResult(data=[])
            updated: list[dict[str, Any]] = []
            for r in self._rows:
                if all(f(r) for f in self._filters):
                    r.update(self._update)
                    updated.append(r)
            return FakeResult(data=updated)

        if self._delete:
            if not self._filters:
                # Refuse to delete-all by accident — same as PostgREST's guard.
                return FakeResult(data=[])
            kept: list[dict[str, Any]] = []
            removed: list[dict[str, Any]] = []
            for r in self._rows:
                if all(f(r) for f in self._filters):
                    removed.append(r)
                else:
                    kept.append(r)
            self._rows.clear()
            self._rows.extend(kept)
            return FakeResult(data=removed)

        if self._upsert is not None:
            # Replace-by-PK semantics; on_conflict is a comma-joined column list.
            keys = [k.strip() for k in (self._on_conflict or "").split(",") if k.strip()]
            existing_index: dict[tuple, int] = {}
            for i, r in enumerate(self._rows):
                if keys:
                    pk = tuple(r.get(k) for k in keys)
                    existing_index[pk] = i
            for new_row in self._upsert:
                if keys:
                    pk = tuple(new_row.get(k) for k in keys)
                    if pk in existing_index:
                        self._rows[existing_index[pk]] = new_row
                        continue
                self._rows.append(new_row)
            return FakeResult(data=list(self._upsert))

        rows = self._rows
        for f in self._filters:
            rows = [r for r in rows if f(r)]
        if self._sort:
            col, desc = self._sort

            def _key(r: dict[str, Any]) -> Any:
                v = r.get(col)
                return (v is None, v)

            rows = sorted(rows, key=_key, reverse=desc)
        if self._range:
            s, e = self._range
            rows = rows[s:e]
        if self._limit is not None:
            rows = rows[: self._limit]
        return FakeResult(data=list(rows))


@dataclass
class _FakeUser:
    email: str


@dataclass
class _FakeUserResult:
    user: _FakeUser | None


@dataclass
class FakeAuth:
    """A stand-in for supabase-py's `client.auth` namespace.

    Tests seed `users_by_token` with `token → email`; `get_user(token)` returns
    a result object whose `.user.email` matches what the real SDK returns.
    Every call is recorded in `calls` so tests can assert on caching.
    """
    users_by_token: dict[str, str] = field(default_factory=dict)
    raise_on: set[str] = field(default_factory=set)
    calls: list[str] = field(default_factory=list)

    def get_user(self, token: str) -> _FakeUserResult:
        self.calls.append(token)
        if token in self.raise_on:
            raise RuntimeError("simulated invalid token")
        email = self.users_by_token.get(token)
        if not email:
            return _FakeUserResult(user=None)
        return _FakeUserResult(user=_FakeUser(email=email))


@dataclass
class FakeSupabaseClient:
    runs: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    session_files: list[dict[str, Any]] = field(default_factory=list)
    attachment_blobs: list[dict[str, Any]] = field(default_factory=list)
    approved_emails: list[dict[str, Any]] = field(default_factory=list)
    # Spec 0125 — single-row table holding the global onboarding_required flag.
    system_settings: list[dict[str, Any]] = field(
        default_factory=lambda: [{"id": 1, "onboarding_required": False}]
    )
    auth: FakeAuth = field(default_factory=FakeAuth)

    def table(self, name: str) -> FakeBuilder:
        # Spec 0245 — `runs_active` is a DB view: SELECT * FROM runs WHERE
        # deleted_at IS NULL. Mirror it as a read-only snapshot so the
        # server's reader sites can switch from `runs` to `runs_active`
        # under the same fake. Writes via this name produce no row.
        if name == "runs_active":
            snapshot = [r for r in self.runs if r.get("deleted_at") is None]
            return FakeBuilder(snapshot)
        bucket = getattr(self, name)
        return FakeBuilder(bucket)
