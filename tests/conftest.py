"""Global test fixtures.

Spec 0082 — clear the production ``HIDDEN_RUN_IDS`` filter for every
test by default. The hidden-runs allowlist is a deployment-time setting
for the live Fly UI; pre-existing tests use real run ids that happen to
overlap with the production hidden set, and they should keep behaving
as if no runs are hidden. Individual tests that need to exercise the
hidden-runs filter monkeypatch the set back to specific values.

Spec 0243 — strip the Claude Code host-detection env vars
(``CLAUDECODE`` / ``CLAUDE_CODE_*``) before every test so the spec-0243
CLI guard is dormant by default. The full suite is run from inside
a Claude Code session during dev, so without this stripper any
``cli.main(...)`` invocation in a pre-existing test would now exit 2
with the H4 refusal message before the test's own assertion fires.
The dedicated spec-0243 tests re-inject the env vars they need via
``monkeypatch.setenv(...)`` inside the test body, which still wins.
"""

from __future__ import annotations

import os

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


@pytest.fixture(autouse=True)
def _strip_claude_code_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip ``CLAUDECODE`` / ``CLAUDE_CODE_*`` / ``DUAL_RESEARCH_ALLOW_CLAUDE_P``
    before every test (spec 0243).

    The spec-0243 CLI guard fires on any of these env vars at
    ``cli.main()`` entry. The test process inherits the host's env, so
    tests that ``cli.main()`` directly would now refuse with H4 instead
    of exercising the test's own code path. Spec-0243 tests re-inject
    the vars they need via ``monkeypatch.setenv(...)``.
    """
    for key in list(os.environ.keys()):
        if key == "CLAUDECODE" or key.startswith("CLAUDE_CODE_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("DUAL_RESEARCH_ALLOW_CLAUDE_P", raising=False)
