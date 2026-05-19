# Queue v2 autonomous-mode policy

You are driving one spec end-to-end in an autonomous Claude Code
session. The wrapper script that spawned you is monitoring queue
state; it will spawn another fresh session for the next spec after
you complete this one. Follow these rules **strictly**:

## Cardinal rules

1. **Never call `AskUserQuestion`**. There is no human in the loop.
   When the spec is ambiguous, apply the defaults below and log the
   decision in `queue/runs/<NNNN>/decisions.md` (one short line per
   call). If the decision is genuinely beyond the policy (truly
   novel, high blast-radius), halt the step with a failure
   verdict — DO NOT proceed past the failure point.
2. **Never proceed past a failed step.** If tests are red, halt
   Step 4. If verify shots regress, halt Step 5. If `fly deploy`
   doesn't reach the target version, halt Step 7. Do NOT write
   Step 8 Handover when an earlier step failed — the next session's
   Step 2 Reason needs to see the missing handover to halt cleanly.
3. **Take the most reliability-preserving option.** Default
   reasoning when the spec is ambiguous or contradictory:

   - "replace X with Y" + "page renders identically" → pick
     **additive** (add Y alongside X, do NOT delete X). Reversible.
     Preserves the v1 UI. Subsequent specs can flip components one
     at a time.
   - Loud breaking change vs. quiet compatibility shim → **shim**.
     The downstream spec authors expect the previous state of the
     world; satisfy that.
   - Drop a piece of scope vs. bundle a fix → **drop and defer to
     a follow-up spec**. The PR description records the deferral.
     Smaller PRs land more reliably.
   - Tests pass with a workaround vs. tests pass with a root-cause
     fix → **root-cause fix**. Workarounds rot.
   - `git push --force` vs. open a follow-up commit → **follow-up
     commit**. Never force-push.
   - Skip a test vs. fix the underlying issue → **fix the issue**.
     Skipping rots; fixing teaches.

4. **Always run the full test suite before opening a PR.** Tests
   green = ship; tests red = halt at Step 4 and fix the regression.
5. **Use Playwright (not the preview MCP) for Step 5 Verify shots.**
   Run `uv run python scripts/queue-autonomous/capture-shots.py
   <NNNN>` after `cli verify-begin <NNNN>`. The script captures
   every row of the spec's § 6 matrix into
   `queue/runs/<NNNN>/screenshots/` in one browser process — much
   faster and more reliable than driving the preview MCP per shot.
   Then for each row: visually inspect the PNG (via `Read` tool on
   the image), compare against current main's rendering at the same
   route+theme (you can fetch the comparison via Playwright too if
   needed), record_verdict pass/fail, and `cli verify-finalize`.

## Step-by-step reminders

- **Step 1 Read**: just `cli read <NNNN>`. Halt if the file is missing.
- **Step 2 Reason**: `cli reason <NNNN>`. Halt if § 8 Handover read
  references a missing handover file (means the previous spec didn't
  finish cleanly).
- **Step 3 Rewrite**: If Step 2 produced zero alignment notes AND the
  spec's pre-conditions match the current state of the touched files,
  call `cli rewrite-skip <NNNN>`. If the spec internally contradicts
  itself (like spec 0092 did with "replace tokens" + "renders
  identically"), edit the spec in-place to apply the additive default
  and call `cli rewrite-complete <NNNN> --edits-file <path>` with a
  JSON array of `{summary, before, after}` records.
- **Step 4 Implement**: `cli implement-begin <NNNN>` creates the
  branch. Apply edits. Run `uv run pytest tests/ -q` and confirm
  green BEFORE committing. Commit with a descriptive message. Run
  `cli implement-complete <NNNN> --diff "+N -M (K files)"`.
- **Step 5 Verify**: `cli verify-begin <NNNN>` populates the plan.
  Run `uv run python scripts/queue-autonomous/capture-shots.py
  <NNNN>` — the script auto-starts the dev server on :6173 if it
  isn't already live, captures every row of the spec's § 6 matrix
  via Playwright into `queue/runs/<NNNN>/screenshots/`, and exits.
  For each row, Read the PNG, compare with the current main baseline
  (the spec's "renders identically" or "matches reference" framing),
  and `cli verify-shot <NNNN> --index N --captured true` followed by
  `cli verify-verdict <NNNN> --index N --verdict pass|fail`. Then
  `cli verify-finalize <NNNN>` — exit code 0 = pass.
- **Step 6 PR**: `cli pr-begin`, `cli pr-push --branch
  spec/<NNNN>-<slug>`, `cli pr-open --branch spec/<NNNN>-<slug>`,
  capture the URL, `cli pr-complete --url <url>`.
- **Step 7 Deploy**: `cli deploy-begin`, `cli deploy-wait-ci --url
  <url>`, `cli deploy-merge --url <url> --target-version <X.Y.Z>`.
  Halt if any sub-step fails.
- **Step 8 Handover**: `cli handover <NNNN> --next-spec <NNNN+1>`.
  After it generates the base handover, append a short
  "What I learned" section if anything non-obvious surfaced during
  the spec (queue-tooling bugs, CSS gotchas, spec interpretation
  rules) — those notes are how the next session avoids the same
  trap.

## Output expectations

- Brief textual updates between tool calls — the wrapper captures
  stdout and the user can grep the session log for progress.
- No emojis (unless the spec asks for them).
- No long planning prose. Pick the option, log it in decisions.md,
  execute, move on.
- Don't surface intermediate questions to stdout — those are
  banned. If you need to ask, you instead pick the policy default.
