"""Queue v2 — autonomous spec-execution orchestration.

The package implements the 8-step lifecycle (Read · Reason · Rewrite ·
Implement · Verify · PR · Deploy · Handover) that processes the queued
specs at specs/0092-*.md … specs/0104-*.md end-to-end with a Read →
Reason → Rewrite safety triad at the start of every spec.

Discovery and design context live in docs/queue-v2/CURRENT-STATE.md.

Runtime layout, written to ``queue/`` at the repo root (gitignored):

    queue/
      state.json            queue position, in-flight spec, last-completed
      timings.json          accumulated per-step durations (median in dashboard)
      runs/<NNNN>/          per-spec artifacts
        spec-parsed.json
        reason-notes.md
        rewrite-log.md
        implement-log.md
        verify-report.md
        screenshots/<NN>-<viewport>-<theme>.png
        pr-url.txt
        deploy-log.md
        handover-path.txt
        events.jsonl        step transitions for the live dashboard
"""

from dual_research.queue_v2 import state, timings  # noqa: F401
