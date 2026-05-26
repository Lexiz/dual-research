"""Spec 0225 — ``dual-research verify <run-dir> ...`` CLI.

Audits each supplied run-dir against the 0114-unified contract using the
22 invariants in :mod:`dual_research.contract.verifier`. Compares the
report against a frozen ``expected.json`` baseline next to the run (when
present) and reports any pass → fail regressions.

Exit code (per :func:`main`):
- ``0`` — every supplied run passed the gate (no unexpected gating
  failures + no baseline regressions).
- ``1`` — at least one supplied run had a gating failure not in the
  baseline, OR any verdict (gating or reporting) regressed from ``pass``
  to ``fail`` against the baseline.
- ``2`` — a supplied path is not a directory.

The dual mode (standalone vs baseline-gated) is per spec 0225 §2.5 — CI
wires the corpus job to ``tests/fixtures/anchor-runs/*`` where every
fixture carries ``expected.json``, so the dead-run fixtures (which fail
I5.1 + I5.2 by design) pass CI as long as their verdicts match the
frozen baseline. Standalone use against a live run dir without
``expected.json`` falls back to "fail iff any gating fails."
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dual_research.contract.verifier import (
    InvariantResult,
    VerifierReport,
    baseline_regressions,
    verify_run,
)


def _render_report(report: VerifierReport, regressions: list[tuple[str, str, str]]) -> str:
    lines: list[str] = []
    lines.append(f"Lifecycle-trace verifier — {report.run_dir}")
    lines.append("")
    width = 6
    for r in report.results:
        mark = {
            "pass": "✓",
            "fail": "✗",
            "not_applicable": "·",
        }.get(r.verdict, "?")
        sev = f"[{r.severity}]"
        lines.append(f"  {mark} {r.id:<{width}} {sev:<11} {r.verdict}")
        for e in r.evidence:
            lines.append(f"      {e.location}: {e.detail}")
    lines.append("")
    if regressions:
        lines.append("Baseline regressions (pass → fail):")
        for inv_id, b, c in regressions:
            lines.append(f"  ✗ {inv_id}: baseline {b} → current {c}")
    return "\n".join(lines)


def _verdict_match(
    report_results: list[InvariantResult], baseline: dict
) -> list[tuple[str, str, str]]:
    """Return ``[(invariant_id, baseline_verdict, current_verdict), …]`` for any
    invariant whose verdict differs from baseline at all (regression, improvement,
    or N/A flip). Used for the strict-equality variant of the gate."""
    base = {item["id"]: item["verdict"] for item in baseline.get("results", [])}
    out: list[tuple[str, str, str]] = []
    for r in report_results:
        b = base.get(r.id)
        if b is None:
            continue
        if b != r.verdict:
            out.append((r.id, b, r.verdict))
    return out


def _audit_one(run_dir: Path, json_out: bool) -> tuple[int, str]:
    """Audit a single run directory.

    Returns ``(exit_code, output_text)``:
    - ``exit_code == 0`` — passed the gate (matches baseline / no gating fails).
    - ``exit_code == 1`` — failed the gate.
    - ``exit_code == 2`` — bad path.
    """
    if not run_dir.exists() or not run_dir.is_dir():
        return 2, f"verify: not a directory: {run_dir}"

    report = verify_run(run_dir)

    expected_path = run_dir / "expected.json"
    regressions: list[tuple[str, str, str]] = []
    diffs: list[tuple[str, str, str]] = []
    has_baseline = expected_path.exists()
    if has_baseline:
        try:
            baseline = json.loads(expected_path.read_text(encoding="utf-8"))
            regressions = baseline_regressions(report, baseline)
            diffs = _verdict_match(list(report.results), baseline)
        except json.JSONDecodeError:
            return 2, f"verify: cannot parse {expected_path}"

    if has_baseline:
        gate_failed = bool(diffs)
    else:
        gate_failed = report.has_gating_failure

    if json_out:
        payload = report.to_dict()
        payload["baseline_regressions"] = [
            {"id": i, "baseline": b, "current": c} for (i, b, c) in regressions
        ]
        payload["baseline_diffs"] = [
            {"id": i, "baseline": b, "current": c} for (i, b, c) in diffs
        ]
        payload["gate_failed"] = gate_failed
        out = json.dumps(payload, indent=2)
    else:
        out = _render_report(report, regressions)
        if has_baseline and diffs and not regressions:
            out += "\n\nBaseline drift (non-regression — verdict diverged from baseline):"
            for inv_id, b, c in diffs:
                out += f"\n  · {inv_id}: baseline {b} → current {c}"

    return (1 if gate_failed else 0), out


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="dual-research verify",
        description=(
            "Audit one or more finished Deep Research runs against the "
            "0114-unified contract via the 22 invariants defined in "
            "dual_research.contract.verifier. If a run dir carries an "
            "expected.json baseline, the gate fires on any verdict "
            "difference (including pass→fail regression). Otherwise the "
            "gate fires on any gating-invariant failure."
        ),
    )
    p.add_argument(
        "run_dirs",
        nargs="*",
        type=Path,
        help="One or more run directories. Defaults to the current working directory.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit per-run JSON payloads instead of the human-readable text format.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    run_dirs = args.run_dirs or [Path.cwd()]
    overall_rc = 0
    for rd in run_dirs:
        rc, out = _audit_one(rd.expanduser().resolve(), args.json)
        sys.stdout.write(out + "\n")
        if rc != 0:
            overall_rc = max(overall_rc, rc)
    return overall_rc


if __name__ == "__main__":
    sys.exit(main())
