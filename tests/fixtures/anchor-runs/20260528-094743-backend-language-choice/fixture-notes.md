# Fixture: 20260528-094743-backend-language-choice

First end-to-end clean reference run in project history. Completed
post-spec-0238 (parser hardening) and post-H4 mitigation (Claude Code
reap surfaced by spec 0243's operational guard). Plain-Terminal.app
invocation; $8.66; 39KB `final.md`; `metrics.ended_at` populated;
clean shutdown.

## Why it's in the corpus

This is the verification artifact for spec 0244 — the promotion of
I2.6 (STATUS-RAISED-array cross-check), I2.7 (empty-turn retry
hardening), and I2.8 (turn termination) from `reporting` to `gating`
severity. All three invariants pass `gating pass` on this fixture.

## Pre-fix conditions that would have killed this run

- **0231 / 0238 parser bugs** — phase-2 `extract_fenced_section` drop
  on the live OpenAI turn shape; the fixture's phase-2 r1 OpenAI turn
  hits the same code path.
- **0241 silent-hang surface** — phase-4 dead-turn detection. The
  fixture's phase-4 turns terminate cleanly; pre-0241 a stuck turn
  would have been invisible.
- **H4 Claude Code reap** — pre-0243 this run could not have
  completed inside any Claude Code surface (the OS-level reap killed
  five consecutive prior attempts silently).

## Maintenance

If a future verifier change legitimately flips a verdict on this
fixture, regenerate via `tests._fixture_regen.regenerate_baseline` and
commit the delta. Do not edit `expected.json` by hand.
