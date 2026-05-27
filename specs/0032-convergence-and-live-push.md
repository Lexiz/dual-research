---
spec: 0032
title: Phase-2 hash-drift escape, P2 summaries, live-push flag, dual-research-run skill
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.30.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/34"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0032 — Convergence escape + operational quality-of-life

## Context

First-pass testing of the spec-0029/0030/0031 work surfaced two real
bugs and two operational gaps. They share a single test loop (the test
run that surfaced them) and ship together:

### 1. Phase 2 hash-drift loop (the smoking gun)

The test run for the web-components-catalogue brief looped from
round 4 through round 8 of Phase 2 with no convergence, was stopped
manually, and showed this pattern when inspected:

```
ROUND 4  claude AGREED  hash=deefd293f5d9 …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 4  openai AGREED  hash=abefc1f04c02 …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 5  claude AGREED  hash=deefd293f5d9 …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 5  openai AGREED  hash=ee769c42bec6 …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 6  claude AGREED  hash=deefd293f5d9 …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 6  openai AGREED  hash=c3c5c90ef4be …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 7  claude AGREED  hash=deefd293f5d9 …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 7  openai AGREED  hash=c3c5c90ef4be …    drafter=claude  OQ=0 BD=0 FSD=0
ROUND 8  claude AGREED  hash=deefd293f5d9 …    drafter=claude  OQ=0 BD=0 FSD=0
```

Every substantive gate passes — OpenAI even agrees Claude should be
the drafter — but the **AGREED_PLAN hashes don't match** because
OpenAI re-paraphrases the canonical plan each round instead of
copying Claude's verbatim. The protocol prompt anticipates this
case explicitly:

> Same-round AGREED with mismatched plans is a parse error and
> triggers a repair turn.

…but the orchestrator never implements that branch. It just keeps
firing the normal `negotiation_turn_prompt` and hopes the next round
will magically converge — which it doesn't, because the model keeps
drifting.

### 2. Empty Phase 2 timeline cards

Unrelated to the convergence loop, but reinforced by it: Phase 2 turn
files have no `## Summary` section. The `negotiation_round1_prompt`
and `negotiation_turn_prompt` don't ask for one — unlike Phase 0
(preflight), Phase 1 (research draft), Phase 3 (converged draft),
and Phase 4 (review). So `phase_summaries["phase2_round{N}_<agent>"]`
stays empty, the inline-unfold body has nothing under the gist line,
and the cards look "blank" — exactly what the user saw on rounds
4–7 of the failed run.

### 3. Live updates to the hosted UI

Today the hosted UI only sees a run *after* the orchestrator
completes and someone runs `dual-research --push`. The user expected
to watch a run progress on the hosted instance the same way they
can on the local `dual-research serve` server (SSE off the live
transcript). Three paths were discussed; **Path A — a
`--push-while-running` flag that forks a 30 s timer running the
existing push command in parallel** — was the chosen one. The
`events` and `session_files` tables are already keyed for idempotent
upsert (`(run_id, seq)` and `(run_id, path)` respectively), and
`latest_event_seq()` is already implemented for the hosted UI's
polling loop — so the building blocks are in place.

### 4. `/dual-research-run` Claude Code skill

The first attempt to fire a test run cost me three round-trips
(missing `OPENAI_API_KEY` in the sandbox shell, then `ANTHROPIC_API_KEY`,
then realising I should also start `dual-research serve` for live
viewing). All operational knowledge that shouldn't have to be
rediscovered. A small project-local skill at
`.claude/skills/dual-research-run/SKILL.md` captures the canonical
recipe so future "run a test" requests are one prompt away.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **New convergence helper: `all_substantive_gates_pass_except_plan_hash`.** | Mirrors `all_substantive_gates_pass_except_drafter` but inverted: returns True when STATUS/drafter/OQ/BD/FSD all align AND `has_agreed_plan` is True on both, but `normalized_hash(c.agreed_plan) != normalized_hash(o.agreed_plan)`. Lives in `protocol/convergence.py`. |
| D2 | **First-detection response: force a verbatim-copy repair turn.** | When the new helper fires for the first time in a run, the orchestrator picks the **drafter's** plan (by the agreed `DRAFTER:` field) as the canonical block, then re-invokes the NON-drafter agent with a new `force_verbatim_copy_prompt` that hands them the canonical AGREED_PLAN and explicitly instructs: "Emit your next turn with this exact AGREED_PLAN block, byte-for-byte, and `STATUS: AGREED`. Do not paraphrase. Do not amend." That repair fires *in place of* a normal next-round turn for that agent — the drafter's already-AGREED turn for the current round is preserved. |
| D3 | **Second-detection response: auto-promote, exit Phase 2.** | If the repair turn STILL produces a hash-mismatched plan (the model refuses to copy verbatim), the orchestrator promotes the drafter's plan as canonical, marks Phase 2 converged via tiebreak-style escape, and proceeds to Phase 3. This is a deliberate "good enough" escape — the agents have agreed on substance, only their wording differs; we shouldn't deadlock on a hash. The event stream records this as `drafter_canonical_promoted` (new event kind) so the UI can surface it. |
| D4 | **The "agreed-except-hash" detection only fires on rounds ≥ 2.** | Same as the existing convergence gate. Round 1 cannot agree by protocol. |
| D5 | **Add `## Summary` to Phase 2 prompts.** | A new required section at the top of each Phase 2 turn — 3–5 sentence TL;DR of the agent's position in this round. Matches Phase 1 / 3 / 4 conventions. Purely additive: doesn't change convergence gates, doesn't change parse behaviour, just gives the existing `extract_summary` something to find for `phase_summaries`. Cards unfold to a meaningful TL;DR instead of just a gist line. |
| D6 | **`--push-while-running` flag on the run CLI.** | When set, the orchestrator forks an in-process background task at startup that calls `RemoteSession.push_session_dir` every 30 s on the session dir, then cancels itself when the run exits and does one final synchronous push. Requires `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` in env (same as the existing `--push`). Failures during the timer are logged but don't kill the run — Supabase blip ≠ run abort. |
| D7 | **30 s default push interval is hard-coded; no knob in v1.** | Matches the round-trip latency of the agent calls. Knob can be added later if needed; not worth the surface area now. |
| D8 | **`.claude/skills/dual-research-run/SKILL.md` is a project-local skill.** | Lives in the repo so it versions with the code. When invoked, the skill: (a) sources keys from `~/.zshrc` via the established eval-grep pattern, (b) checks if `dual-research serve` is already up on port 6173 and starts it if not, (c) fires the run with `--models prod --push-while-running --name <slug>` defaulting to the user's prompt, (d) reports BOTH the local and hosted run URLs at startup so the user has somewhere to watch immediately. |
| D9 | **Skill stays passive after invoking the run.** | Doesn't poll, doesn't tail by default. The user already has the live UI in their browser. If the user explicitly asks for a status check, the skill can `tail -20` the run log; otherwise it stays out of the way. |

## Proposed change

### 1. New convergence helper — `src/dual_research/protocol/convergence.py`

```python
@dataclass(frozen=True)
class PlanHashDrift:
    detected: bool
    drafter: str | None = None           # which agent was named drafter
    canonical_plan: str | None = None    # plan from the drafter's turn
    other_agent: str | None = None       # "claude" | "gpt" — the one to repair
    other_hash: str | None = None        # hash of the non-canonical plan


def all_substantive_gates_pass_except_plan_hash(
    claude_turn: str, openai_turn: str
) -> PlanHashDrift:
    """Spec 0032 — detects the 'agreed on everything except the hash' state.

    Returns `PlanHashDrift(detected=False)` whenever any substantive gate
    fails. When all gates pass except the plan hash, returns a populated
    dataclass naming the canonical plan (the one written by the named
    drafter) and which agent needs to copy it verbatim.
    """
```

Mirrors `all_substantive_gates_pass_except_drafter` in structure but
checks the inverse failure mode. Both helpers can return positively
for the same turn pair only if BOTH the drafter AND the hash differ —
in which case the existing drafter-tiebreak code path wins.

### 2. Force-verbatim-copy repair prompt — `src/dual_research/protocol/prompts.py`

New `force_verbatim_copy_prompt` function:

```python
def force_verbatim_copy_prompt(
    *,
    agent_name: str,
    other_name: str,
    drafter_name: str,
    canonical_plan: str,
    round: int,
) -> str:
    """Spec 0032 — a special Phase 2 repair prompt for the hash-drift case.

    Hand the agent the canonical AGREED_PLAN block (from the drafter's
    turn) and demand byte-for-byte reproduction in their next turn. All
    other required sections (## Answers, ## Plan as I currently propose
    it, etc.) may be re-emitted in skeletal form — the orchestrator only
    cares about the AGREED_PLAN block matching.
    """
```

The prompt: re-states the protocol's "copy verbatim or emit NEGOTIATING"
rule (lifted from `negotiation_turn_prompt` adoption procedure
section), inlines the canonical plan block in a fenced section, and
explicitly forbids paraphrasing. Required output: a complete Phase 2
turn (all standard sections) with the canonical block verbatim under
`## AGREED_PLAN`.

### 3. Orchestrator wiring — `src/dual_research/orchestrator/phase2.py`

After the existing `is_plan_agreed` + tiebreak check, add a third
check:

```python
drift = all_substantive_gates_pass_except_plan_hash(claude_text, openai_text)
if drift.detected:
    if hash_drift_repair_attempts.get(drift.other_agent, 0) >= 1:
        # D3 — second detection: auto-promote.
        ctx.state.drafter = drift.drafter
        ctx.state.agreed_plan = drift.canonical_plan
        fsd_items = extract_canonical_fsd_items(drift.canonical_plan)
        ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
        await event_bus.publish(DrafterCanonicalPromoted(round=r, drafter=drift.drafter, ...))
        converged = True
        via_canonical_promotion = True
        break
    # D2 — first detection: fire a verbatim-copy repair turn.
    hash_drift_repair_attempts[drift.other_agent] = (
        hash_drift_repair_attempts.get(drift.other_agent, 0) + 1
    )
    other_agent = openai_agent if drift.other_agent == "gpt" else claude_agent
    repair_prompt = force_verbatim_copy_prompt(
        agent_name=drift.other_agent, ...
    )
    repair_result = await run_one_call(
        agent=other_agent, prompt=repair_prompt, ...
        label=f"phase2-r{r}-{drift.other_agent}-hashdrift-repair",
        ...
    )
    # Overwrite the agent's round file with the repaired turn:
    write_atomic(<their round file>, repair_result.text)
    # Re-evaluate convergence with the repaired turn — fall through
    # to the next iteration; the standard is_plan_agreed gate will
    # pick it up.
    continue
```

`hash_drift_repair_attempts` is a per-agent counter initialised
empty at the start of `run_phase2` — survives across rounds.

### 4. New event type — `src/dual_research/events/types.py`

```python
@dataclass(frozen=True, kw_only=True)
class DrafterCanonicalPromoted(Event):
    round: int
    drafter: str
    other_agent: str               # the one whose plan was rejected
    canonical_hash: str            # for transcript / debug
    other_hash: str
    kind: str = "drafter_canonical_promoted"
```

Aggregator handler: same shape as `drafter_tiebreak_resolved` — marks
the run as converged-via-escape, surfaces a small chrome chip on
the run-detail header so the user knows the agreement was nudged
rather than reached cleanly.

### 5. `## Summary` in Phase 2 prompts — `src/dual_research/protocol/prompts.py`

Both `negotiation_round1_prompt` and `negotiation_turn_prompt` get a
new first required section:

```
## Summary
3–5 sentences summarising your position in this round: what you've
held onto, what you've conceded or updated, and what's still in
question. The UI extracts this for the timeline-card TL;DR; keep it
factual and short.
```

Doesn't change any other behaviour. Parser already handles
`## Summary` via `extract_summary` (used in P1/P3/P4); aggregator's
`_read_phase_summaries` already walks the round files. Cards on the
Conversation tab gain content; the click-to-unfold UX from spec
0030 finally has something to show.

### 6. `--push-while-running` CLI flag

`src/dual_research/cli.py` — new flag, mutually compatible with
`--prompt` / `--brief` / `--notion`:

```python
p.add_argument(
    "--push-while-running",
    action="store_true",
    help="Periodically push the session-dir to Supabase during the run "
         "(every 30s) so the hosted UI shows live progress. Requires "
         "SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY "
         "in the environment.",
)
```

`src/dual_research/orchestrator/run.py` — when the flag is set,
spawn an `asyncio.create_task(_push_watch_loop(...))` after
`run_started` is emitted. The loop:

```python
async def _push_watch_loop(
    session_dir: Path,
    creds: SupabaseCredentials,
    *,
    interval_seconds: float = 30.0,
    stop: asyncio.Event,
) -> None:
    remote = RemoteSession.from_credentials(creds.url, creds.service_role_key)
    while not stop.is_set():
        try:
            remote.push_session_dir(session_dir)
        except Exception as e:  # broad — Supabase blip shouldn't abort
            logger.warning("Push-while-running tick failed: %s", e)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass
    # Final synchronous push at exit.
    try:
        remote.push_session_dir(session_dir)
    except Exception as e:
        logger.warning("Final push failed: %s", e)
```

Stop event is set in a `finally` block after `Phase4Outcome` /
finalisation lands. Last push runs synchronously inside that finally
so the hosted UI always sees the final state.

### 7. `.claude/skills/dual-research-run/SKILL.md` — new file

Project-local skill with frontmatter:

```yaml
---
name: dual-research-run
description: |
  Fire a dual-research test run on a research prompt. Handles env-key
  sourcing, starts the local UI server for live viewing, fires the run
  with prod-tier models and live-push enabled, and reports both the
  local and hosted run URLs. Use when the user wants to test the
  dual-research pipeline end-to-end on a fresh prompt.
---
```

Body documents the canonical recipe in step form, with executable
shell snippets:

1. **Source env keys** — `eval "$(grep -hE '^export (ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_(URL|ANON_KEY|SERVICE_ROLE_KEY))=' ~/.zshrc)"`.
2. **Ensure local UI server is up** — `curl -s http://127.0.0.1:6173/api/health || (uv run dual-research serve --port 6173 &)`.
3. **Fire the run** — `uv run dual-research --prompt "<prompt>" --models prod --push-while-running --name <slug>` (background).
4. **Report URLs** — local: `http://127.0.0.1:6173/#/runs/<id>`, hosted: `https://dual-research-alex.fly.dev/#/runs/<id>`.
5. **Stay quiet** — don't poll. The user has the UI; the orchestrator handles its own lifecycle. Wakeup checks only at user's request.

### 8. Tests

- `tests/protocol/test_convergence_hash_drift.py` (new) —
  `all_substantive_gates_pass_except_plan_hash`:
  - Detects the test-run case (same FSD/OQ/BD/drafter, different
    plan hashes) and returns `detected=True` with the named-drafter's
    plan as canonical.
  - Returns `detected=False` when drafter mismatches (existing
    helper handles that).
  - Returns `detected=False` when hashes match (the existing
    `is_plan_agreed` path handles success).
- `tests/protocol/test_force_verbatim_copy_prompt.py` (new) —
  the prompt text inlines the canonical plan, names the recipient,
  forbids paraphrasing, and requires the standard Phase 2 output
  sections.
- `tests/orchestrator/test_phase2_hash_drift_escape.py` (new) —
  end-to-end with stubbed agents:
  - First repair attempt successfully copies the plan → converged
    on the next round via `is_plan_agreed`.
  - First repair fails (model still paraphrases) → second iteration
    fires `DrafterCanonicalPromoted` and exits Phase 2 converged.
- `tests/protocol/test_phase2_summary_prompt.py` (new) — both
  Phase 2 prompts contain the `## Summary` required-section marker.
- `tests/protocol/test_extract_summary.py` (extend) — a Phase-2
  fixture with a `## Summary` block extracts cleanly via
  `extract_summary`.
- `tests/cli/test_push_while_running_flag.py` (new) — the CLI
  parser accepts the flag; orchestrator's `run.py` spawns the
  push-loop task only when the flag is set; SupabaseCredentials
  loaded lazily so the flag fails fast with a clear error if
  Supabase env is missing.
- `tests/orchestrator/test_push_watch_loop.py` (new) — with a fake
  `RemoteSession`, the loop pushes once per tick, handles errors
  without raising, fires a final push on stop.
- The Claude skill is documentation; no automated test (matches the
  project's existing skill / docs convention).

### 9. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.29.0 → 0.30.0.
- `CHANGELOG.md` entry.
- `VERSION_NOTES` entry on the how-it-works page summarising the
  four items.

## Out of scope

- **Detecting drift earlier (rounds 1–3).** The check fires only
  after the existing `is_plan_agreed` gate has already returned
  False. Earlier rounds may legitimately have different plans
  (agents are still negotiating); only "AGREED except hash" is
  the pathological state.
- **A configurable push interval.** Hard-coded 30 s in v1 (D7).
- **A live-push for transcript events ONLY** (without files).
  Current spec pushes the full session-dir on each tick. Cheaper
  delta-push is Path B from the prior conversation; out of scope
  here.
- **Skill auto-tail / progress-poll.** Skill stays passive (D9).
- **Skill global vs project-local.** v1 ships project-local;
  promoting to `~/.claude/skills/` is a one-mv if needed.
- **Anthropic vs OpenAI drift behaviour analysis.** This spec
  treats either agent's drift symmetrically. If empirically only
  one model paraphrases, that's a future tuning project.
- **Forcing agents to emit `STATUS: NEGOTIATING` when they amend.**
  Per the protocol prompt, an agent should emit NEGOTIATING when
  amending. The repair turn doesn't try to enforce that retroactively;
  it just hands the canonical plan and asks for verbatim copy.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0032 adds at
      least 12 new tests.
- [ ] Manual: re-run the web-components catalogue brief. Phase 2
      now exits within ~2 extra rounds of the hash-drift
      condition (one repair, then either convergence or canonical
      promotion). The hosted UI streams updates every ~30 s.
- [ ] Manual: open any Phase 2 turn card on the Conversation tab
      after the new prompts land — it unfolds with a real TL;DR
      paragraph from the agent's `## Summary` section.
- [ ] Manual: with `--push-while-running` set and supabase env
      configured, the hosted run page populates within 30 s of run
      start and updates as phases land.
- [ ] Manual: ask in a fresh Claude Code session "run dual-research
      on <prompt>" — the `dual-research-run` skill triggers,
      reports both URLs, fires cleanly, and stays quiet thereafter.

## Risks

- **The model still refuses to copy verbatim.** The canonical-
  promotion fallback (D3) is the explicit escape — agents have
  agreed on substance and we don't deadlock on wording. Acceptable.
- **Push-loop hits a transient Supabase error mid-run.** Caught
  and logged (D6); does not abort the run. Final push at exit will
  catch up.
- **Adding `## Summary` to Phase 2 prompts costs ~50 tokens per
  turn.** Negligible. The summary itself ~3–5 sentences ≈ 100–200
  output tokens — a small fraction of typical Phase 2 turn output
  (~3–5k tokens).
- **Skill file in `.claude/skills/` is git-tracked but env-key
  paths assume zsh + `~/.zshrc`.** A bash-shell user would need
  one line of adaptation. Documented in the skill body.
- **Hash-drift repair fires `run_one_call` mid-round.** The
  existing transcript schema already tolerates intermediate calls
  (repair turns from `parse_with_repair` work the same way); no
  schema change.

## Open questions

- Whether to also surface the canonical-promotion event with a
  small banner in the UI (e.g. `Plan agreed via canonical
  promotion — wording drift escape`). v1 publishes the event but
  doesn't render a banner; the new event kind is there for a
  follow-up if useful.
- Whether the `--push-while-running` interval should be exposed
  via env var (`DR_PUSH_INTERVAL_SECONDS`?) rather than CLI flag.
  v1 hard-codes 30 s — knob is one-line later.
- Whether the dual-research-run skill should also handle `--brief`
  / `--notion` paths, not just `--prompt`. v1 ships `--prompt`-only;
  the skill body mentions the other modes for the user to invoke
  manually.
