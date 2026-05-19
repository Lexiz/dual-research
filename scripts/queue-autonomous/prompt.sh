#!/usr/bin/env bash
# Emit the per-spec user prompt for an autonomous queue session.
#
# Reads $1 (spec number) and prints the prompt body that gets passed
# to `claude --print`. The prompt tells the inner session which spec
# to drive, where to find its instructions (the policy file is loaded
# via --append-system-prompt by the wrapper), and which step to
# resume from (since spec 0092 fixed-mode and re-runs may have
# partial state).

set -euo pipefail

SPEC="${1:?usage: prompt.sh <NNNN>}"
SPEC=$(printf "%04d" "$((10#${SPEC}))")

NEXT=$(printf "%04d" "$((10#${SPEC} + 1))")
# Cap at 0104 (last queue spec). Beyond that, no --next-spec is passed
# and the prompt tells the inner session this is the final spec.
if (( 10#${NEXT} > 104 )); then
  NEXT_FLAG=""
  NEXT_BLURB="This is the final spec in the queue. After Step 8 the wrapper will exit cleanly."
else
  NEXT_FLAG="--next-spec ${NEXT}"
  NEXT_BLURB="When you're done with the handover (or you've halted at a failed step), exit. The wrapper script that spawned you will start the next session for spec ${NEXT}."
fi

cat <<EOF
Drive dual-research queue v2 spec ${SPEC} end-to-end through all 8
steps (Read → Reason → Rewrite → Implement → Verify → PR → Deploy →
Handover). The autonomous-mode policy in your system prompt is
authoritative — follow it strictly:

- Never call AskUserQuestion. Apply policy defaults and log decisions
  in queue/runs/${SPEC}/decisions.md.
- Halt the spec at the first failed step. Do NOT proceed past a
  failure.
- Use Playwright (scripts/queue-autonomous/capture-shots.py ${SPEC})
  for Step 5 shot capture.
- Run the full pytest suite green before opening the PR.

Start by checking queue/state.json to see whether spec ${SPEC} is
already active (resume from where the last session stopped) or
fresh (start from Step 1 Read).

Exact CLI commands you'll use (run each via Bash):

    cd /Users/alexlisitzky/dual-research
    uv run python -m dual_research.queue_v2.cli read ${SPEC}
    uv run python -m dual_research.queue_v2.cli reason ${SPEC}
    uv run python -m dual_research.queue_v2.cli rewrite-skip ${SPEC}      # OR
    uv run python -m dual_research.queue_v2.cli rewrite-complete ${SPEC} --edits-file /tmp/spec${SPEC}-rewrite-edits.json
    uv run python -m dual_research.queue_v2.cli implement-begin ${SPEC}
        # ... apply edits, run pytest green ...
    uv run python -m dual_research.queue_v2.cli implement-complete ${SPEC} --diff "+N -M (K files)"
    uv run python -m dual_research.queue_v2.cli verify-begin ${SPEC}
    uv run python scripts/queue-autonomous/capture-shots.py ${SPEC}
        # ... record_shot + record_verdict per row ...
    uv run python -m dual_research.queue_v2.cli verify-finalize ${SPEC}
    uv run python -m dual_research.queue_v2.cli pr-begin ${SPEC}
    uv run python -m dual_research.queue_v2.cli pr-push ${SPEC} --branch spec/${SPEC}-<slug>
    uv run python -m dual_research.queue_v2.cli pr-open ${SPEC} --branch spec/${SPEC}-<slug>
    uv run python -m dual_research.queue_v2.cli pr-complete ${SPEC} --url <pr-url>
    uv run python -m dual_research.queue_v2.cli deploy-begin ${SPEC}
    uv run python -m dual_research.queue_v2.cli deploy-wait-ci ${SPEC} --url <pr-url>
    uv run python -m dual_research.queue_v2.cli deploy-merge ${SPEC} --url <pr-url> --target-version <X.Y.Z>
    uv run python -m dual_research.queue_v2.cli handover ${SPEC} ${NEXT_FLAG}

${NEXT_BLURB}

Read these references before starting (just enough to internalize
context — not the full files):

- docs/queue-v2/RUNBOOK.md — operator runbook
- specs/${SPEC}-*.md — the spec itself
- handoffs/2026-05-19-spec-\$((${SPEC} - 1))-*.md  (or whichever
  handover the spec's § 8 points at) — previous spec's handover
- docs/design-system-v2/README.md — design-system v2 reference (skim
  the index; deep-dive only the sections relevant to spec ${SPEC})

Read concisely; act decisively. Brief textual updates between tool
calls — no long planning prose.
EOF
