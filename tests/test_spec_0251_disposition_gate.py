"""Spec 0251 — the carve-out disposition gate is executable in the queue picker.

CLAUDE.md's doctrine ("a carve-out reaches `/dev-next` only when its
disposition is `ship`") was enforced by nothing. Spec 0251 makes the gate
executable and expands it from carve-out-only to **all** queued dev specs,
with four coordinated changes:

  §2.1 — `current_queue` requires frozen-frontmatter `disposition == "ship"`.
  §2.2 — `skipped_queued_specs` surfaces the excluded specs (never silent);
          a Parked lane is derived on both dashboard surfaces.
  §2.3 — `parked` joins `VALID_STATUSES`; the authoring skills set status
          from disposition.
  §2.4 — doctrine + a deferrals.py step-number-drift cleanup.

The dashboard and skill assertions are pure-stdlib source-pattern checks
(spec 0206 UI doctrine + the spec 0247 skip-when-absent precedent for the
out-of-repo skill files).
"""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path

import pytest

from scripts.spec_lifecycle.pick_next_number import (
    current_queue,
    skipped_queued_specs,
)
from scripts.spec_lifecycle.validator import VALID_STATUSES

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_spec(
    specs_dir: Path,
    number: str,
    *,
    disposition: str,
    status: str = "queued",
    slug: str = "fixture",
) -> Path:
    body = (
        f"---\nkind: dev\nspec: \"{number}\"\nslug: {slug}\n"
        f"status: {status}\ndisposition: {disposition}\n---\n\n# Spec {number}\n"
    )
    path = specs_dir / f"{number}-{slug}.md"
    path.write_text(body)
    return path


# ── §2.1 + §2.2a — the gate and the skip collector ──────────────────────────


class TestQueuePickerGate:
    def test_ship_included_archive_and_defer_excluded(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        _write_spec(specs, "0001", disposition="ship", slug="runnable")
        _write_spec(specs, "0002", disposition="archive", slug="parked-archive")
        _write_spec(specs, "0003", disposition="defer", slug="parked-defer")

        ids = [sid for sid, _ in current_queue(specs)]
        assert ids == ["0001"], (
            f"only the disposition:ship spec is runnable, got {ids}. "
            "Pre-0251 all three queued specs were returned."
        )

    def test_skipped_collector_returns_non_ship_ids(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        _write_spec(specs, "0001", disposition="ship", slug="runnable")
        _write_spec(specs, "0002", disposition="archive", slug="parked-archive")
        _write_spec(specs, "0003", disposition="defer", slug="parked-defer")

        skipped = [sid for sid, _ in skipped_queued_specs(specs)]
        assert skipped == ["0002", "0003"], (
            f"skipped_queued_specs must surface the non-ship queued specs so the "
            f"picker logs them rather than dropping silently, got {skipped}."
        )

    def test_missing_disposition_is_not_runnable(self, tmp_path: Path) -> None:
        """A queued spec with no disposition at all is treated as non-ship —
        excluded from the run queue but surfaced as skipped."""
        specs = tmp_path / "specs"
        specs.mkdir()
        (specs / "0001-no-disp.md").write_text(
            '---\nkind: dev\nspec: "0001"\nslug: no-disp\nstatus: queued\n---\n\n# x\n'
        )
        assert [sid for sid, _ in current_queue(specs)] == []
        assert [sid for sid, _ in skipped_queued_specs(specs)] == ["0001"]

    def test_gate_covers_decimal_ids(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        _write_spec(specs, "0170", disposition="archive", slug="parent-parked")
        _write_spec(specs, "0170.1", disposition="ship", slug="child-runnable")
        _write_spec(specs, "0171", disposition="ship", slug="next-runnable")

        assert [sid for sid, _ in current_queue(specs)] == ["0170.1", "0171"]
        assert [sid for sid, _ in skipped_queued_specs(specs)] == ["0170"]

    def test_current_queue_signature_preserved(self, tmp_path: Path) -> None:
        """Existing callers (queue_drain_supervisor, tests) depend on the
        `[(spec_id, fm), …]` shape — the §2.1 change must not break it."""
        specs = tmp_path / "specs"
        specs.mkdir()
        _write_spec(specs, "0001", disposition="ship")
        result = current_queue(specs)
        assert len(result) == 1
        spec_id, fm = result[0]
        assert spec_id == "0001"
        assert isinstance(fm, dict) and fm.get("disposition") == "ship"


# ── §2.3 — `parked` is a valid authoring status ─────────────────────────────


class TestValidatorParkedStatus:
    def test_parked_accepted(self) -> None:
        assert "parked" in VALID_STATUSES, (
            "spec 0251 §2.3 — `parked` must be a valid lifecycle status so a "
            "non-ship spec can carry an honest non-runnable status."
        )

    def test_known_statuses_still_present(self) -> None:
        # Adding `parked` must not drop any existing status.
        for status in ("queued", "in_progress", "merged", "deployed", "failed", "cancelled"):
            assert status in VALID_STATUSES

    def test_bogus_status_still_rejected(self, tmp_path: Path) -> None:
        """A non-vocab status must still fail validation."""
        from scripts.spec_lifecycle.validator import validate_dev_spec

        spec = tmp_path / "0001-bogus.md"
        spec.write_text(
            '---\nkind: dev\nspec: "0001"\nslug: bogus\ntype: bug\n'
            'label: bug\nversion_bump: PATCH\nstatus: bogus\n'
            'disposition: ship\ndisposition_reason: "x"\n'
            'depends_on: []\ncomplexity: S\ncreated: 2026-05-29\n---\n\n# x\n'
        )
        result = validate_dev_spec(spec)
        assert any("status" in e for e in result.errors), (
            f"a non-vocab status must be rejected, got errors={result.errors}"
        )

    def test_parked_status_accepted_by_validator(self, tmp_path: Path) -> None:
        """A spec with status:parked must not produce a status error."""
        from scripts.spec_lifecycle.validator import validate_dev_spec

        spec = tmp_path / "0001-parked.md"
        spec.write_text(
            '---\nkind: dev\nspec: "0001"\nslug: parked\ntype: bug\n'
            'label: bug\nversion_bump: PATCH\nstatus: parked\n'
            'disposition: archive\ndisposition_reason: "x"\n'
            'depends_on: []\ncomplexity: S\ncreated: 2026-05-29\n---\n\n# x\n'
        )
        result = validate_dev_spec(spec)
        assert not any("status" in e for e in result.errors), (
            f"status:parked must be accepted, got status errors in {result.errors}"
        )


# ── §2.2b — the Parked lane is derived on BOTH dashboard surfaces ───────────


class TestDashboardParkedLane:
    def test_render_dashboard_pipeline_has_parked_column(self) -> None:
        """`_render_pipeline` emits a Parked lane; the Queued lane counts only
        runnable (disposition:ship) specs, parked/non-ship land in Parked."""
        from scripts.spec_lifecycle.render_dashboard import SpecRow, _render_pipeline

        def row(number: str, status: str, disposition: str) -> SpecRow:
            return SpecRow(
                fm={"status": status, "disposition": disposition},
                path=Path(f"specs/{number}-x.md"),
            )

        specs = [
            row("0001", "queued", "ship"),       # runnable
            row("0002", "queued", "archive"),    # parked (queued + non-ship)
            row("0003", "parked", "defer"),      # parked (explicit status)
            row("0004", "deployed", "ship"),     # neither
        ]
        html = _render_pipeline(specs, [], dt.datetime(2026, 5, 29, 12, 0, 0))

        assert ">Parked<" in html, "Parked lane label must render"
        assert ">Queued<" in html
        # Queued count = 1 (only 0001), Parked count = 2 (0002, 0003).
        assert 'pipe__bar--parked' in html
        # The Queued column's number must be 1, the Parked column's number 2.
        nums = re.findall(
            r'pipe__lbl">(Queued|Parked)</div><div class="pipe__num[^"]*">(\d+)<', html
        )
        as_dict = {label: int(n) for label, n in nums}
        assert as_dict.get("Queued") == 1, f"Queued should count only runnable, got {as_dict}"
        assert as_dict.get("Parked") == 2, f"Parked should count non-ship+parked, got {as_dict}"

    def test_data_js_derives_parked_in_parity_with_renderer(self) -> None:
        """functions/api/data.js must derive the same parked / runnable_queued
        classification as render_dashboard.py — the parity twin (§2.2b)."""
        data_js = (REPO_ROOT / "functions" / "api" / "data.js").read_text(encoding="utf-8")
        # The JS overlay block derives both predicates from status + disposition.
        assert "spec.parked" in data_js, "data.js must derive a `parked` field"
        assert "spec.runnable_queued" in data_js, "data.js must derive `runnable_queued`"
        assert re.search(
            r"spec\.parked\s*=\s*spec\.status\s*===\s*'parked'\s*\|\|"
            r"\s*\(spec\.status\s*===\s*'queued'\s*&&\s*spec\.disposition\s*!==\s*'ship'\)",
            data_js,
        ), "data.js parked derivation must match the render_dashboard `_is_parked` logic"

    def test_renderer_parked_logic_matches_data_js(self) -> None:
        """Lock the Python `_is_parked` / `_is_runnable_queued` source shape so
        the two surfaces cannot silently diverge."""
        renderer = (
            REPO_ROOT / "scripts" / "spec_lifecycle" / "render_dashboard.py"
        ).read_text(encoding="utf-8")
        assert "def _is_parked" in renderer
        assert "def _is_runnable_queued" in renderer
        assert 'col("parked", "Parked"' in renderer


# ── §2.2a + §2.3 — the /dev-next skill contract (skip-when-absent) ──────────

SKILL_PATH = Path(os.path.expanduser("~/.claude/skills/dev-next/SKILL.md"))


def _skill_body() -> str:
    if not SKILL_PATH.exists():
        pytest.skip(f"dev-next skill not present at {SKILL_PATH}")
    return SKILL_PATH.read_text(encoding="utf-8")


class TestDevNextSkillContract:
    def test_step6_logs_skipped_specs(self) -> None:
        body = _skill_body()
        assert "skipped_queued_specs" in body, (
            "spec 0251 §2.2a — /dev-next step 6 must call skipped_queued_specs "
            "and log the excluded ids so a parked spec is never dropped silently."
        )
        assert "disposition≠ship" in body or "disposition != ship" in body, (
            "step 6 must emit the skip-log line naming the disposition≠ship reason."
        )

    def test_step24_5_template_sets_status_from_disposition(self) -> None:
        body = _skill_body()
        # The deferral subagent template must tie status to disposition:
        # ship → queued, else parked.
        assert re.search(r"disposition.*ship.*status.*queued", body, re.IGNORECASE | re.DOTALL)
        assert "parked" in body, (
            "spec 0251 §2.3 — the step 24.5 template must set `status: parked` "
            "for non-ship (defer/archive) deferrals."
        )

    def test_antipodal_no_unconditional_queued_in_template(self) -> None:
        """Antipodal absence: the pre-0251 template committed every auto-spec
        as `(queued)`. After the fix the commit-message status is derived."""
        body = _skill_body()
        assert "(<status>)" in body, (
            "the step 24.5 commit-message must use the derived `<status>` "
            "placeholder, not an unconditional `(queued)`."
        )
