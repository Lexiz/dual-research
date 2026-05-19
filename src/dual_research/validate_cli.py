"""Spec 0115 — ``dual-research validate-run <session-dir>`` CLI.

Loads a finished run, walks the new event stream + every turn file,
and prints a structured contract-violation report.

Exit codes:
- ``0`` — no errors (may have warnings)
- ``1`` — at least one error
- ``2`` — invalid session directory (not a recognised run)

The CLI is a thin wrapper around ``contract.validator`` and the
unified Item aggregation in ``ui.items``; the contract rules live in
exactly one place and the CLI doesn't duplicate them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dual_research.contract.artifacts import display_name
from dual_research.contract.evidence import validate_evidence
from dual_research.contract.lifecycle import is_terminal
from dual_research.contract.validator import validate_turn
from dual_research.protocol.parse import parse_turn_v2
from dual_research.ui.items import aggregate_items_from_transcript


@dataclass
class ValidationFinding:
    severity: str  # "error" | "warning"
    code: str
    message: str
    location: str  # human-readable: "phase2-r3-claude" / "cross-phase" / ...


@dataclass
class ValidationReport:
    session_dir: Path
    findings: list[ValidationFinding] = field(default_factory=list)
    summary_per_phase: dict[int, list[ValidationFinding]] = field(default_factory=dict)
    converged_phases: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)


_TURN_FILE_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")


def _read_transcript_events(session_dir: Path) -> list[dict]:
    transcript = session_dir / "transcript.jsonl"
    if not transcript.exists():
        return []
    out: list[dict] = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _phase_int_from_dir(name: str) -> int | None:
    m = re.match(r"^phase(\d+)$", name)
    return int(m.group(1)) if m else None


def validate_session(session_dir: Path) -> ValidationReport:
    """Audit a session directory against the Deep Research contract."""
    report = ValidationReport(session_dir=session_dir)

    if not session_dir.exists() or not session_dir.is_dir():
        return report  # caller handles exit code 2

    transcript_path = session_dir / "transcript.jsonl"
    if not transcript_path.exists():
        report.findings.append(ValidationFinding(
            severity="warning",
            code="no_transcript",
            message=f"transcript.jsonl not found in {session_dir}",
            location="session",
        ))

    # 1. Per-turn structural validation for every interaction-phase turn file.
    for phase_int in (0, 2, 4):
        phase_dir = session_dir / f"phase{phase_int}"
        if not phase_dir.exists():
            continue
        for turn_file in sorted(phase_dir.iterdir()):
            if not turn_file.is_file():
                continue
            m = _TURN_FILE_RE.match(turn_file.name)
            if not m:
                continue
            round_no = int(m.group(1))
            agent = m.group(2)
            try:
                text = turn_file.read_text(encoding="utf-8")
            except OSError as exc:
                report.findings.append(ValidationFinding(
                    severity="error",
                    code="turn_unreadable",
                    message=f"cannot read {turn_file}: {exc}",
                    location=f"phase{phase_int}-r{round_no}-{agent}",
                ))
                continue
            try:
                parsed = parse_turn_v2(text)
            except Exception as exc:
                report.findings.append(ValidationFinding(
                    severity="error",
                    code="turn_parse_crash",
                    message=f"parser raised {type(exc).__name__}: {exc}",
                    location=f"phase{phase_int}-r{round_no}-{agent}",
                ))
                continue
            result = validate_turn(
                text,
                phase=phase_int,
                round=round_no,
                agent=agent,
                is_closeout_round=False,  # CLI doesn't reconstruct closeout state
            )
            for err in result.errors:
                report.findings.append(ValidationFinding(
                    severity=err.severity,
                    code=err.code,
                    message=err.message,
                    location=f"phase{phase_int}-r{round_no}-{agent}",
                ))

    # 2. Cross-phase: lifecycle invariants on the aggregated Item ledger.
    bundle = aggregate_items_from_transcript(transcript_path)
    for item in bundle.items:
        final_state = item.current_state
        if not is_terminal(final_state):
            # An item that didn't reach terminal — only a warning, since
            # an interrupted run might leave non-terminal items legitimately.
            report.findings.append(ValidationFinding(
                severity="warning",
                code="item_non_terminal",
                message=f"item {item.id} ended in non-terminal state {final_state!r}",
                location="cross-phase",
            ))
            continue
        last = item.transitions[-1] if item.transitions else None
        if last is None or not (last.reason or "").strip():
            report.findings.append(ValidationFinding(
                severity="error",
                code="terminal_missing_reason",
                message=f"item {item.id} reached terminal state {final_state!r} without a rationale",
                location="cross-phase",
            ))
        if final_state == "capped" and (last is None or not last.via):
            report.findings.append(ValidationFinding(
                severity="error",
                code="capped_missing_via",
                message=f"item {item.id} is capped but has no via:hard_cap|ghost_cap tag",
                location="cross-phase",
            ))
        if item.evidence_required and final_state == "resolved":
            if not item.evidence:
                report.findings.append(ValidationFinding(
                    severity="error",
                    code="evidence_missing_on_resolved",
                    message=(
                        f"item {item.id} was raised with evidence_required: true "
                        "but resolved without any linked evidence records"
                    ),
                    location="cross-phase",
                ))

    # 3. Convergence — confirm every phase that emitted PhaseConverged.
    events = _read_transcript_events(session_dir)
    for ev in events:
        if (ev.get("kind") or ev.get("event_type")) == "phase_converged":
            via = []
            if ev.get("via_closeout"): via.append("closeout")
            if ev.get("via_ghost_cap"): via.append("ghost_cap")
            if ev.get("via_hard_cap"): via.append("hard_cap")
            tag = (" via " + " + ".join(via)) if via else " organically"
            report.converged_phases.append(
                f"phase {ev.get('phase')}{tag} in round {ev.get('final_round')}"
            )

    return report


_LOCATION_RE = re.compile(r"^phase(?P<phase>\d+)-r(?P<round>\d+)-(?P<agent>[a-z]+)$")


def _location_artifact_id(location: str) -> str | None:
    """Map a phase-round-agent location tag to its canonical artifact ID.

    ``phase2-r3-claude`` → ``phase2.claude.r3``. Returns ``None`` for
    non-canonical locations (``cross-phase``, ``session``, …).
    """
    m = _LOCATION_RE.match(location)
    if not m:
        return None
    return f"phase{m.group('phase')}.{m.group('agent')}.r{m.group('round')}"


def _render_report(report: ValidationReport) -> str:
    lines: list[str] = []
    lines.append(f"Deep Research Run Audit — {report.session_dir}")
    lines.append("")
    err_n = len(report.errors)
    warn_n = len(report.warnings)
    lines.append(f"Status: {warn_n} warning(s), {err_n} error(s)")
    lines.append("")

    for ph in report.converged_phases:
        lines.append(f"  ✓ converged: {ph}")
    if report.converged_phases:
        lines.append("")

    grouped: dict[str, list[ValidationFinding]] = {}
    for f in report.findings:
        grouped.setdefault(f.location, []).append(f)
    for loc in sorted(grouped.keys()):
        # Spec 0117 §6 — print the registry display name alongside the
        # canonical location tag so human readers can scan the report
        # without translating phase{N}-r{M}-{agent} in their head.
        artifact_id = _location_artifact_id(loc)
        if artifact_id is not None:
            header = f"== {display_name(artifact_id)}  ·  {loc} =="
        else:
            header = f"== {loc} =="
        lines.append(header)
        for f in grouped[loc]:
            mark = "✗ ERROR  " if f.severity == "error" else "⚠ WARN   "
            lines.append(f"  {mark}[{f.code}] {f.message}")
        lines.append("")

    if not report.findings:
        lines.append("(no findings — run is clean)")
    return "\n".join(lines)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="dual-research validate-run",
        description=(
            "Audit a finished Deep Research run against the contract. "
            "Reports per-turn structural violations + cross-phase "
            "lifecycle invariants."
        ),
    )
    p.add_argument(
        "session_dir",
        type=Path,
        help="Path to the run directory (e.g. runs/20260519-...)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON instead of the structured text format.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))
    session = args.session_dir.expanduser().resolve()
    if not session.exists() or not session.is_dir():
        sys.stderr.write(f"validate-run: not a directory: {session}\n")
        return 2
    if not (session / "transcript.jsonl").exists() and not any(
        (session / f"phase{p}").exists() for p in (0, 2, 4)
    ):
        sys.stderr.write(
            f"validate-run: {session} does not look like a dual-research run\n"
        )
        return 2

    report = validate_session(session)
    if args.json:
        out = {
            "session_dir": str(session),
            "errors": [
                {"code": f.code, "message": f.message, "location": f.location}
                for f in report.errors
            ],
            "warnings": [
                {"code": f.code, "message": f.message, "location": f.location}
                for f in report.warnings
            ],
            "converged": report.converged_phases,
        }
        sys.stdout.write(json.dumps(out, indent=2) + "\n")
    else:
        sys.stdout.write(_render_report(report) + "\n")

    return 1 if report.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
