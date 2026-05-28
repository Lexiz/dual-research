"""Spec 0248 — All Runs card refinements + rich provider metric bands.

UI anatomy is locked via source-pattern tests (spec 0206 doctrine): a
positive regex on the post-fix shape + an antipodal-absence regex on the
pre-fix shape, per anatomical contract. The backend tally is exercised
against a synthetic fixture session dir through the *real* entry point
(``compute_critique_by_agent`` → item pipeline), plus a cheap-path guard
asserting ``summarize_run`` never replays transcripts.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

_RUN_LIST = ("src", "dual_research", "ui", "static", "run-list.jsx")
_APP = ("src", "dual_research", "ui", "static", "app.jsx")
_CSS_LIVE = ("src", "dual_research", "ui", "static", "components.css")
_CSS_DS = ("design-system", "assets", "styles", "composed-components.css")


# ── §2.5 — Provider metric band ─────────────────────────────────────────────


def test_provider_card_renders_rich_band() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_contains(
        jsx, r"function ProviderCard\(",
        msg="§2.5: run-list.jsx must define ProviderCard",
    )
    assert_jsx_contains(
        jsx, r"className=\{'rc-prov rc-prov--'",
        msg="§2.5: ProviderCard must render the .rc-prov band",
    )
    assert_jsx_contains(
        jsx, r"<BrandMark name=\{brand\}",
        msg="§2.5: provider band must render the brand logo via BrandMark",
    )
    assert_jsx_contains(
        jsx, r'className="rc-prov__tok"',
        msg="§2.5: band must surface total tokens (.rc-prov__tok)",
    )
    assert_jsx_contains(
        jsx, r'className="rc-prov__cost"',
        msg="§2.5: band must surface cost (.rc-prov__cost)",
    )
    for cls in ("rc-rs--raised", "rc-rs--solved", "rc-rs--count"):
        assert_jsx_contains(
            jsx, cls,
            msg=f"§2.5: band must carry the {cls} badge",
        )


def test_legacy_agent_row_shape_is_gone() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_lacks(
        jsx, r"function AgentRow\(",
        msg="§2.5 antipodal: the pre-fix AgentRow component must be removed",
    )
    assert_jsx_lacks(
        jsx, r"rc-agent__chips",
        msg="§2.5 antipodal: the cost+chips-only AgentRow markup must be gone",
    )


# ── §2.4 — Note constrained to phase-strip width ────────────────────────────


def test_run_card_grid_places_note_in_left_column() -> None:
    for parts in (_CSS_LIVE, _CSS_DS):
        css = read_repo_text(*parts)
        assert_jsx_contains(
            css, r'"note\s+agents"',
            msg=f"§2.4: {parts[-1]} must place note in the left column, agents spanning",
        )
        assert_jsx_lacks(
            css, r'"note note"',
            msg=f"§2.4 antipodal: the full-width \"note note\" row must be gone in {parts[-1]}",
        )


# ── §2.2 — Avatar menu restored in chrome ───────────────────────────────────


def test_chrome_mounts_avatar_menu() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_contains(
        jsx, r"function AvatarMenu\(",
        msg="§2.2: AvatarMenu must be defined in run-list.jsx (lifted from app.jsx)",
    )
    assert_jsx_contains(
        jsx, r"function AvatarDisc\(",
        msg="§2.2: AvatarDisc must be defined in run-list.jsx",
    )
    assert_jsx_contains(
        jsx, r"<AvatarMenu\b",
        msg="§2.2: AllRunsChrome must mount <AvatarMenu>",
    )


def test_bare_avatar_initial_and_project_strip_are_gone() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_lacks(
        jsx, r'className="ar-avatar"',
        msg="§2.2 antipodal: the bare .ar-avatar initial span must be gone",
    )
    assert_jsx_lacks(
        jsx, r"function ProjectStrip\(",
        msg="§2.1 antipodal: the ProjectStrip wordmark component must be removed",
    )
    # The definitions must also leave app.jsx (single source of truth).
    app = read_repo_text(*_APP)
    assert_jsx_lacks(
        app, r"function AvatarMenu\(",
        msg="§2.2: AvatarMenu must no longer be defined in app.jsx",
    )


# ── §2.3 — Inline archive tray ──────────────────────────────────────────────


def test_inline_archive_tray_present() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_contains(
        jsx, r"function RunArchiveTray\(",
        msg="§2.3: run-list.jsx must define the RunArchiveTray",
    )
    assert_jsx_contains(
        jsx, r"'rc-tray'",
        msg="§2.3: the tray must render the .rc-tray row",
    )
    assert_jsx_contains(
        jsx, r"is-confirming",
        msg="§2.3: the tray must carry .is-confirming during the confirm state",
    )


def test_floating_button_and_modal_dialogs_are_gone() -> None:
    jsx = read_repo_text(*_RUN_LIST)
    assert_jsx_lacks(
        jsx, r"rc-archive-btn",
        msg="§2.3 antipodal: the floating .rc-archive-btn must be removed",
    )
    assert_jsx_lacks(
        jsx, r"ConfirmArchiveDialog",
        msg="§2.3 antipodal: the full-screen ConfirmArchiveDialog must be removed",
    )
    assert_jsx_lacks(
        jsx, r"ConfirmUnarchiveDialog",
        msg="§2.3 antipodal: the full-screen ConfirmUnarchiveDialog must be removed",
    )


# ── DS sync — both CSS files carry the new classes ──────────────────────────


def test_both_css_files_carry_new_classes() -> None:
    for parts in (_CSS_LIVE, _CSS_DS):
        css = read_repo_text(*parts)
        for cls in (".rc-prov", ".rc-rs--raised", ".rc-rs--solved",
                    ".rc-rs--count", ".rc-tray"):
            assert_jsx_contains(
                css, re.escape(cls),
                msg=f"DS sync: {parts[-1]} must define {cls}",
            )


# ── §2.5 backend — write-time tally + cheap-path guard ──────────────────────


def _write_fixture_run(root: Path) -> None:
    """A minimal v2 session dir: a transcript with item_raised /
    item_transitioned events for two agents across the three categories."""
    events = [
        # Claude: 2 questions raised, 1 resolved.
        {"event": "item_raised", "id": "Q1", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "q1"},
        {"event": "item_transitioned", "id": "Q1", "from_state": "open",
         "to_state": "resolved", "actor": "claude", "phase": 2, "round": 2},
        {"event": "item_raised", "id": "Q2", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "q2"},
        # OpenAI: 1 disagreement raised + resolved, 1 issue raised, still open.
        {"event": "item_raised", "id": "D1", "item_kind": "disagreement",
         "phase": 2, "round": 1, "raiser": "openai", "body": "d1"},
        {"event": "item_transitioned", "id": "D1", "from_state": "open",
         "to_state": "resolved", "actor": "openai", "phase": 2, "round": 2},
        {"event": "item_raised", "id": "I1", "item_kind": "issue",
         "phase": 4, "round": 1, "raiser": "openai", "body": "i1"},
    ]
    root.mkdir(parents=True, exist_ok=True)
    (root / "transcript.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )


def test_compute_critique_by_agent_tallies_real_path(tmp_path: Path) -> None:
    from dual_research.ui.critique_tally import compute_critique_by_agent

    root = tmp_path / "20260528-000000-fixture"
    _write_fixture_run(root)
    totals = {
        "claude": {"input_tokens": 100, "output_tokens": 50,
                   "cache_read_tokens": 10, "cache_write_tokens": 5, "searches": 3},
        "openai": {"input_tokens": 200, "output_tokens": 80,
                   "cache_read_tokens": 0, "cache_write_tokens": 0, "searches": 1},
    }
    out = compute_critique_by_agent(root, totals)

    assert out["claude"]["questions"] == [2, 1]
    assert out["claude"]["disagreements"] == [0, 0]
    assert out["claude"]["issues"] == [0, 0]
    assert out["openai"]["disagreements"] == [1, 1]
    assert out["openai"]["issues"] == [1, 0]
    # Tokens fold from totals_by_agent (cheap, single source of truth).
    assert out["claude"]["tokens"] == 165
    assert out["claude"]["searches"] == 3
    assert out["openai"]["tokens"] == 280
    assert out["openai"]["searches"] == 1


def test_derive_agent_breakdowns_reads_persisted_tally() -> None:
    from dual_research.ui.aggregator import derive_agent_breakdowns

    metrics = {
        "totals_by_agent": {
            "claude": {"cost_usd": 1.0, "search_cost": 0.0, "searches": 3,
                       "input_tokens": 100, "output_tokens": 50,
                       "cache_read_tokens": 10, "cache_write_tokens": 5},
        },
        "critique_by_agent": {
            "claude": {"tokens": 165, "searches": 3,
                       "questions": [4, 2], "disagreements": [1, 1], "issues": [0, 0]},
        },
    }
    out = derive_agent_breakdowns(metrics)
    a = out["a"]
    assert a.tokens == 165
    assert a.searches == 3
    assert a.critique["questions"] == (4, 2)
    assert a.critique["disagreements"] == (1, 1)


def test_old_runs_without_tally_degrade_to_zero() -> None:
    from dual_research.ui.aggregator import derive_agent_breakdowns

    metrics = {
        "totals_by_agent": {
            "claude": {"cost_usd": 1.0, "searches": 0,
                       "input_tokens": 10, "output_tokens": 5},
        },
        # no critique_by_agent — pre-0248 run
    }
    out = derive_agent_breakdowns(metrics)
    assert out["a"].critique == {}
    assert out["a"].tokens == 15  # tokens are still cheaply derivable


def test_summarize_run_stays_cheap_no_reconstruct() -> None:
    """Cheap-path guard (spec 0248 §7): the list-row builder must never
    replay transcripts — no reconstruct_* call may appear in its body."""
    from dual_research.ui import aggregator

    src = inspect.getsource(aggregator.summarize_run)
    assert "reconstruct" not in src, (
        "summarize_run must not call any reconstruct_* parser — the rich "
        "tallies are read from the write-time-persisted critique_by_agent"
    )
