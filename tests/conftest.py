"""Global test fixtures.

Spec 0082 — clear the production ``HIDDEN_RUN_IDS`` filter for every
test by default. The hidden-runs allowlist is a deployment-time setting
for the live Fly UI; pre-existing tests use real run ids that happen to
overlap with the production hidden set, and they should keep behaving
as if no runs are hidden. Individual tests that need to exercise the
hidden-runs filter monkeypatch the set back to specific values.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_hidden_runs_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``HIDDEN_RUN_IDS`` with an empty frozenset for the duration
    of each test. Imported lazily — the constant only exists in the UI
    server module, and not every test triggers that import."""
    try:
        from dual_research.ui import server as _server
    except Exception:
        return
    monkeypatch.setattr(_server, "HIDDEN_RUN_IDS", frozenset())
