# Handover — 2026-05-19 data-integrity arc complete (v0.69.13 → v0.72.0)

**Date:** 2026-05-19
**Branch:** `main` (clean)
**Latest commit on `main`:** `52ac4a9 Spec 0091 — Phase 4 drafter-engagement gate (#94)`
**Version:** `0.69.13` → `0.72.0` (1 PATCH + 3 MINOR bumps across 4 PRs)
**Hosted:** [`dual-research-alex.fly.dev/api/health`](https://dual-research-alex.fly.dev/api/health) → `{"ok":true,"version":"0.72.0","backend":"supabase"}`
**Static-asset cache-bust:** `v=0089` → `v=0093`
**Tests:** 895 green
**Working tree:** clean
**Open PRs:** 0

---

## 0 · Bottom line for the new session

You are picking up after a **data-integrity arc** sparked by a user
observation on two recent runs:

- `27de` = `20260518-083618-backend-language-choice` (Phase 4 errored, exit 52)
- `2c4f` = `20260518-065852-backend-language-choice-briefing-for-dual-research` (Phase 2 hard-cap deadlock at 12 rounds)

The investigation surfaced four distinct bug classes plus one latent
parser bug. All four landed as four specs (0088 → 0091) over four PRs.
Live production is at v0.72.0.

The arc closed two visible UX issues (timeline omission, question
ghosting) and two systemic protocol issues (stuck-AGREED loops,
Phase 4 sycophantic-APPROVED). One follow-up thread is explicitly
deferred with a clear data signal for when to revisit.

The investigation runs (`27de`, `2c4f`) remain materialized under
`runs/` locally for further inspection (user explicitly opted to
keep them). Production has not been re-run with the fixes; future
runs benefit immediately.

---

## 1 · What shipped (PR-by-PR)

### Spec 0088 — Stop hiding Phase 3 / Phase 4 timeline rows on errored & deadlocked runs ([PR #90](https://github.com/Lexiz/dual-research/pull/90))

**Version bump:** `0.69.13` → `0.69.14` (PATCH, `bug` label)
**Spec doc:** [`specs/0088-timeline-phase-omission-on-errored-runs.md`](../specs/0088-timeline-phase-omission-on-errored-runs.md)

#### What
`buildLiveTimeline()` in `live-data.jsx` was gating Phase 3 + Phase 4 sections on `st !== 'errored' && st !== 'deadlocked'`. Any run that died after Phase 2 had its real on-disk P3 draft + P4 review-round artifacts silently stripped from the Timeline pane, while the Critique pane (sourced from `phaseLedgers` / `phaseReviewItems` / `phaseStats`) continued to show the corresponding data. The two panes disagreed.

#### Fix
- Outer gates: `if (ph >= 3)` / `if (ph >= 4)` (dropped the status clause).
- Live-card branches scoped explicitly to `st === 'running'` so a stopped-in-phase run surfaces completed artifacts without a ghost streaming placeholder.
- Adjacent bug: when a run dies after a `phase{2,4}_round_complete` event lands but before `round.current` advances, `cur` lags behind disk reality. Both phases now compute `Math.max(cur, Object.keys(phaseStats.phase{N}).length)` when stopped — 27de Phase 4 had `phaseStats.phase4` keys `'1'..'6'` but `round.current = 5`, so the pre-fix code would have lost round 6.

#### Verified
Run `27de` DOM `data-phase-id` went from `[0,1,2]` to `[0,1,2,3,4]` with the Phase 4 chip reading "6 review rounds." `2c4f` and `3a4a` unchanged.

---

### Spec 0089 — Convergence escape hatches for stuck-AGREED loops ([PR #91](https://github.com/Lexiz/dual-research/pull/91))

**Version bump:** `0.69.14` → `0.70.0` (MINOR, `new-feature` label)
**Spec doc:** [`specs/0089-convergence-escape-hatches-for-stuck-agreed.md`](../specs/0089-convergence-escape-hatches-for-stuck-agreed.md)

#### What
Three coordinated escapes for the "agents emit AGREED for many rounds but orchestrator's secondary gates keep blocking" failure class. Plus one latent canonical-FSD scope bug fix that the work exposed.

#### Fix

**§ A — Canonical-FSD synthesis escape.** New helpers in `protocol/convergence.py`:
- `all_substantive_gates_pass_except_canonical_fsd()` — detection
- `synthesize_canonical_fsd_section_from_standalone()` — pure-function synthesis of the canonical sub-section from the standalone Final-surfaced disagreements section (4 canonical fields are a strict subset of the 8 standalone fields)
- `splice_canonical_into_agreed_plan()` + `compose_full_agreed_plan()` — markdown splice helpers
- New event `CanonicalFsdSynthesized`. Phase 2 only.

**§ B — Stuck-AGREED escape valve.** New `is_plan_agreed_lenient()` + `is_review_approved_lenient()` (strict checks minus the ledger cross-check). Phase 2 + Phase 4 orchestrators track consecutive `lenient_agreed=True / strict_agreed=False` rounds; after `STUCK_AGREED_K = 2` such rounds, promote via the valve. New event `StuckAgreedPromoted` (carries phase / round / streak / ledger_open_count).

**§ C — Hard ledger feedback.** Rewrote `_INSTRUCTION` in `ledger/prompt.py` from soft ("informational, not output-required") to hard ("convergence will be blocked"). New `build_blocked_convergence_warning()` renders a `## ⚠ Convergence blocked in prior round` section in the next-round prompt when the prior round emitted AGREED but the ledger blocked. Wired into `negotiation_turn_prompt` and `review_turn_prompt` via a new optional `blocked_warning` kwarg.

**Latent bug exposed by the work** — `is_plan_agreed` looked up the canonical FSD sub-section inside `c.agreed_plan`, but `parse_turn`'s `extract_fenced_section` truncates at the next `##` heading. Since the canonical sub-section IS a `##` heading, it never lives inside `agreed_plan` — making the gate structurally impossible to pass for any FSD>0 turn. Corrected the lookup scope to the full turn body. Phase 2/4 success paths now call `compose_full_agreed_plan()` to splice the canonical back into stored `ctx.state.agreed_plan` so Phase 3 + `extract_canonical_fsd_items` see a self-contained block.

#### Tests
- 30 unit tests in `tests/protocol/test_convergence_spec0089.py`
- 5 replay tests in `tests/protocol/test_convergence_spec0089_replay.py` (pinned to checked-in 2c4f r04 turn files)
- Ledger prompt extensions in `tests/ledger/test_prompt.py`

#### Note
The 2c4f replay tests were later reframed by spec 0090: pre-fix, 2c4f r04 showed the stuck-AGREED signature (`lenient=True, strict=False`) because the parse-fence bug made both `agreed_plan` fields hash trivially equal as `` ```markdown ``. Post-spec-0090 the parser sees the real plan bodies, which differ by ~4 hunks. So 2c4f's "stuck-AGREED" was actually a spec-0032 hash-drift case — but at the time we believed it was a true stuck-AGREED state. The escape valve still serves its purpose for genuine cases.

---

### Spec 0090 — Parser robustness for cross-round Q/A/issue linkage + code-fence awareness ([PR #93](https://github.com/Lexiz/dual-research/pull/93))

**Version bump:** `0.70.0` → `0.71.0` (MINOR, `new-feature` label)
**Spec doc:** [`specs/0090-parser-robustness-and-data-integrity.md`](../specs/0090-parser-robustness-and-data-integrity.md)

#### What
**The headline arc result.** A forensic dig into 2c4f and 27de uncovered that the system was **asymmetrically blind to roughly half of what Claude wrote**. The agents were largely doing the right work; the answer-extraction parser only recognised numbered-list format while Claude consistently used bold-header per-Q blocks. Pre-fix: 2c4f had 12/24 questions marked "ghosted"; arithmetic exactly matched the volume of Claude's invisible bold-header answers.

#### Fix

**§ A — Answer-detection robustness** (`ui/questions.py`, `ui/issues.py`):
- New `_extract_answer_blocks()` accepts numbered-list (`1. **Q-g-r1-01:** body`), bold-header (`**Q-g-r1-01 — title**\n\nbody`), and H3 (`### Q-g-r1-01: title`) head formats.
- New `_block_head_id()` extracts protocol IDs from the head line — supports the full alphabet (Q-N, OAI-N, OAI-P4-N, C-N, D-N, FSD-N, I-g-rN-NN, Cl-c-pN-NN).
- `reconstruct_questions()` uses ID-based primary matching with positional fallback for IDless heads.
- Look-ahead extended from `round_n + 1` only to `MAX_ANSWER_LOOKAHEAD_ROUNDS = 5`; first-match-wins.
- `ui/issues.py`'s `_ID_TOKEN_RE` broadened to also match lowercase-initial system IDs (`I-g-r1-01`, `Cl-c-p1-04`).

**§ B — Prompt tightening** (`protocol/prompts.py`): inline numbered-list examples in both `negotiation_turn_prompt` and `review_turn_prompt`; explicit ID-in-first-line requirement; symmetric treatment for P4 `## Issue ledger`.

**§ C — Code-fence awareness** (`protocol/parse.py`): new `_fenced_ranges()` + `_next_h2_outside_fences()` helpers mask out fenced code block contents (both ```` ``` ```` and ```` ~~~ ````) before the `##` boundary regex runs. Closes the latent bug where `parse_turn(text).agreed_plan` was just the fence opener for every FSD>0 turn.

#### Tests
- 12 tests in `tests/protocol/test_parse_fence_aware.py`
- 18 tests in `tests/ui/test_questions_spec0090.py`
- 6 tests in `tests/ui/test_issues_spec0090.py`
- 9 tests in `tests/protocol/test_prompts_spec0090.py`
- 4 replay tests in `tests/protocol/test_spec0090_replay.py` (pinned to 2c4f r01-r04 turn files under `tests/fixtures/spec0090/`)

#### Verified
2c4f UI now shows **33 resolved / 0 open / 0 ghosted** (was 12 ghosted pre-fix). 27de P2 ghosting dropped from 10/19 to 2/19.

#### Reframed (spec 0089 § B)
The stuck-AGREED escape valve was previously over-firing as a workaround for the parser bug. Post-fix the ledger reports accurate open counts and the valve becomes a true safety net for genuine deadlocks. The 2c4f r04 replay tests were updated to reflect post-fix reality.

---

### Spec 0091 — Phase 4 drafter-engagement gate (close the round-1 sycophantic-APPROVED loophole) ([PR #94](https://github.com/Lexiz/dual-research/pull/94))

**Version bump:** `0.71.0` → `0.72.0` (MINOR, `new-feature` label)
**Spec doc:** [`specs/0091-phase4-drafter-engagement-gate.md`](../specs/0091-phase4-drafter-engagement-gate.md)

#### What
With spec 0090's parser fix exposing the underlying behaviour, run `27de`'s Phase 4 was clearly showing Claude as drafter emitting `STATUS: APPROVED` with `OPEN_ISSUES: 0` on round 1 — before reading any reviewer feedback. Verbatim from his r1: *"(No prior issues. No new issues raised this round — the draft is the product of consensus reached in Phase 2.) **Issue ledger: 0 open items.**"* followed by `STATUS: APPROVED`. He then re-emitted APPROVED/oi=0 every subsequent round he wrote successfully; GPT continued to surface 5+ open issues throughout. The dance never resolved and contributed to `27de`'s `exit_code: 52` deadlock.

#### Fix

**§ A — Orchestrator gate** (`orchestrator/phase4.py`): one-line `if r == 1 and approved: approved = False` at both the main convergence-check site AND the resume-replay path. Mirrors the existing Phase 2 "round 1 cannot agree" rule. Also gated: the spec-0089 § B lenient check is skipped in r1 so the streak counter doesn't pre-load.

**§ B — Drafter-engagement prompt requirement** (`protocol/prompts.py`): new paragraph in `review_turn_prompt` explicitly tells the drafter that r1 cannot be APPROVED and frames the round-1 expectation as engagement (re-read the draft from the reviewer's perspective, list at least one issue, explain why it resolves to non-blocking).

**§ C — Dropped during implementation.** Originally proposed as validator-level rejection in `assert_well_formed_review_turn`. Dropped because it conflicted with § A: the existing orchestrator catches `ProtocolParseError` and breaks the loop with `parse_failure = True`. A stubborn agent re-emitting APPROVED on retry would trigger parse-failure abort instead of falling through to § A's silent downgrade. Documented in the spec doc; § A alone covers the case cleanly.

#### Tests
- 2 integration tests in `tests/orchestrator/test_phase4_spec0091.py`
- 4 prompt tests in `tests/protocol/test_review_prompt_spec0091.py`
- 3 pre-existing tests updated: `test_phase4_converges_in_round_1` renamed + rewritten; both `test_phase4_resume.py` tests updated to pre-populate r1+r2; `is_review_approved` calls in 2 test files bumped from `round=1` to `round=2` in 8 places.

---

## 2 · Files touched (cumulative across all 4 PRs)

```
specs/0088-timeline-phase-omission-on-errored-runs.md          (new, 291 lines)
specs/0089-convergence-escape-hatches-for-stuck-agreed.md      (new, ~500 lines)
specs/0090-parser-robustness-and-data-integrity.md             (new, ~400 lines)
specs/0091-phase4-drafter-engagement-gate.md                   (new, ~250 lines)
handoffs/2026-05-19-data-integrity-arc-complete.md             (this doc, new)

src/dual_research/__init__.py                  (0.69.13 → 0.72.0)
pyproject.toml                                 (0.69.13 → 0.72.0)
uv.lock                                        (mirrors version bumps)
CHANGELOG.md                                   (4 new release entries)

src/dual_research/protocol/parse.py            (+95 lines — fence-aware extract_fenced_section)
src/dual_research/protocol/convergence.py      (+340 lines — synthesis helpers, lenient checks, scope corrections)
src/dual_research/protocol/prompts.py          (+80 lines — answer-format examples, drafter-engagement requirement, blocked_warning kwarg)
src/dual_research/ledger/prompt.py             (+50 lines — strengthened instruction + blocked-convergence warning)
src/dual_research/ledger/__init__.py           (+2 lines — export new helper)
src/dual_research/orchestrator/phase2.py       (+150 lines — wiring spec-0089 §A/§B/§C)
src/dual_research/orchestrator/phase4.py       (+90 lines — wiring spec-0089 §B/§C + spec-0091 §A)
src/dual_research/ui/questions.py              (+180 lines — block extraction overhaul, ID-based matching)
src/dual_research/ui/issues.py                 (+20 lines — broader ID regex)
src/dual_research/ui/static/live-data.jsx      (+70 lines — phase 3/4 timeline gate fix)
src/dual_research/ui/static/index.html         (cache-bust v=0089 → v=0093 across 22 references)
src/dual_research/events/types.py              (+50 lines — CanonicalFsdSynthesized + StuckAgreedPromoted)
src/dual_research/events/__init__.py           (+2 lines — exports)

tests/protocol/test_convergence_spec0089.py            (new, 30 tests)
tests/protocol/test_convergence_spec0089_replay.py     (new, 5 tests)
tests/protocol/test_parse_fence_aware.py               (new, 12 tests)
tests/protocol/test_prompts_spec0090.py                (new, 9 tests)
tests/protocol/test_spec0090_replay.py                 (new, 4 tests)
tests/protocol/test_review_prompt_spec0091.py          (new, 4 tests)
tests/ui/test_questions_spec0090.py                    (new, 18 tests)
tests/ui/test_issues_spec0090.py                       (new, 6 tests)
tests/orchestrator/test_phase4_spec0091.py             (new, 2 tests)
tests/ledger/test_prompt.py                            (+5 tests for the new helper)
tests/orchestrator/test_phase3_4_final.py              (1 test renamed + rewritten)
tests/orchestrator/test_phase4_resume.py               (2 tests updated)
tests/protocol/test_convergence_ledger.py              (round=1 → round=2 in 3 places)

tests/fixtures/spec0089/2c4f-r04-*.md                  (new, 2 checked-in fixtures)
tests/fixtures/spec0090/2c4f-p2-r0[1-4]-*.md           (new, 8 checked-in fixtures)
```

**Net diff vs `921a3a5` (design-system bootstrap, the last commit before this arc):** ~6700 lines added across source + tests + docs.

---

## 3 · What's deferred (with explicit signals for when to revisit)

### `STUCK_AGREED_K = 1` evaluation

**Status:** keep at K=2. **Revisit if:** production runs show the spec-0089 § B escape valve over-blocking (i.e., agents stuck for 2+ consecutive lenient-True rounds when they really were converged, costing extra unnecessary rounds).

**Why K=2 today:**
- Pre-spec-0090, K=2 was a workaround for the parser inflating the ledger's open count
- Post-spec-0090, the ledger reports accurate counts, so the escape valve should fire only on genuine deadlocks
- Post-spec-0091, round 1 sycophantic-APPROVED is structurally prevented
- K=2 gives the strengthened § C standing-items prompt one round of nudging before the orchestrator overrides
- K=1 would override too aggressively

**Empirical signal to tighten K to 1:** if we observe two or more production runs where the orchestrator promoted via stuck-AGREED escape AFTER a round of "agents really were converged but ledger said no," AND we can trace those to mis-counted ledger items that the agent prompt couldn't shift. Currently no such signal exists.

### Phase 4 parse-failure cascade

**Status:** unaddressed. **Revisit when:** a new run exhibits Claude regressing into malformed outputs mid-Phase-4 (like `27de`'s r3/r5).

**Why deferred:** the parse-with-repair retry loop already exists; the question is *why* Claude regressed after several rounds. That requires:
- A reproduction case post-spec-0091 (the round-1 gate may have eliminated the upstream cause)
- Possibly model-prompt tuning rather than orchestrator changes
- Specific telemetry: was Claude running out of context window? Did the cumulative prompt grow past a quality cliff?

If a fresh post-spec-0091 run exhibits this, the investigation starts there.

### Phase 4 reviewer mirror-sycophancy

**Status:** no evidence of this yet. **Revisit if:** post-spec-0091 data shows the REVIEWER prematurely approving (the symmetric failure to what spec 0091 fixed for the drafter).

**Why mention:** spec 0091 § A applies symmetrically (any agent's APPROVED in r1 is downgraded), so the structural protection covers both directions. But the prompt requirement in § B is specifically for the drafter. If post-spec-0091 the reviewer shows premature-approval patterns we'd need a reviewer-side analogue.

### Backfill of old runs (`27de`, `2c4f`, others)

**Status:** intentionally not done. **Revisit if:** the user wants to retroactively see what the post-fix ledgers + timelines would look like for old runs.

**Why not now:** all parsers + ledgers are re-derived from the on-disk `phase{N}/round-NN-{agent}.md` files every time the UI loads, so locally-materialized runs DO benefit immediately. But Supabase-persisted `state.agreed_plan` values from old runs were written pre-spec-0089 / pre-spec-0090 and are frozen. A "rederive state.json + ledger.json from disk" CLI would be cheap (~50 lines) and is an obvious follow-up if needed.

The 27de and 2c4f runs are still on production as `errored` / `deadlocked` respectively — not re-run.

---

## 4 · Source-of-truth artifacts

- **Specs:** [`0088`](../specs/0088-timeline-phase-omission-on-errored-runs.md), [`0089`](../specs/0089-convergence-escape-hatches-for-stuck-agreed.md), [`0090`](../specs/0090-parser-robustness-and-data-integrity.md), [`0091`](../specs/0091-phase4-drafter-engagement-gate.md) — each is self-contained with Context, Proposed Change, Out of Scope, Test Plan, Risks, Open Questions.
- **PRs:** [#90](https://github.com/Lexiz/dual-research/pull/90), [#91](https://github.com/Lexiz/dual-research/pull/91), [#93](https://github.com/Lexiz/dual-research/pull/93), [#94](https://github.com/Lexiz/dual-research/pull/94) — all squash-merged.
- **CHANGELOG:** [`CHANGELOG.md`](../CHANGELOG.md) — entries `[0.69.14]` through `[0.72.0]` describe per-version changes.
- **Production runs that drove the investigation:**
  - `27de` = `20260518-083618-backend-language-choice` (Phase 4 errored, exit 52)
  - `2c4f` = `20260518-065852-backend-language-choice-briefing-for-dual-research` (Phase 2 deadlock at 12 rounds)
  - Both still on production in their pre-fix state; both materialized locally under `runs/` (user opted to keep).
- **Test fixtures:** `tests/fixtures/spec0089/` (2c4f r04 pair), `tests/fixtures/spec0090/` (2c4f r01-r04 pairs). Both small enough to live in git.

---

## 5 · Workflow lessons learned this arc

- **Pause between specs, even when blanket-greenlit.** The "do everything" greenlight covers spec-internal work but NOT the boundary between specs. Surface the next spec for review before drafting/implementing.
- **Before drafting a spec, ask scope questions in `AskUserQuestion`.** Scope + format-choice + proceed-style questions in one round-trip drove good outcomes consistently (specs 0089, 0090, 0091 all used this pattern).
- **Empirically check the data before scoping a fix.** The user's "ghosting is everywhere" observation turned out to be a parser bug, not an agent behaviour bug. Without dumping the ledger + sampling specific Q-IDs + comparing Claude's vs OpenAI's answer format, we'd have shipped a wrong fix.
- **The "drop § C during implementation if it conflicts" pattern is good.** Spec 0091's § C looked clean on paper; landed in the spec doc; got dropped at implementation time when it conflicted with § A's downgrade semantic. Documented the drop in the spec doc so future-readers see both the original design and the reason for the change.
- **All UI verification at 2200×1300.** Smaller viewports hide layout gaps.
- **Canonical fixture: `partner-vetting-arch-critique` (display id `3a4a`).** Other runs may not exercise critique pane / consumption tab.

---

## 6 · Fresh-session bootstrap prompt

Paste the block below into a fresh Claude Code session to pick up where this arc left off:

```
You are picking up dual-research development from a freshly-deployed
state. The 2026-05-19 data-integrity arc closed cleanly across 4 PRs
(specs 0088 → 0091) — every visible bug from the user's investigation
of runs 27de + 2c4f is now shipped to production at
https://dual-research-alex.fly.dev/ (version 0.72.0).

Before doing ANY work:

1. Read the handover at
   /Users/alexlisitzky/dual-research/handoffs/2026-05-19-data-integrity-arc-complete.md
   end-to-end. It documents what shipped, what's deferred, where the
   source-of-truth artifacts live, and the small open follow-ups.

2. Read CHANGELOG.md entries [0.69.14] through [0.72.0] for a
   feature-level diff against the previous release.

3. Spin up the dev server with the existing launch config via the
   `preview_start name="dual-research-ui"` MCP tool. Confirm
   /api/health reports 0.72.0. Open the canonical fixture at
   #/runs/20260516-035048-partner-vetting-arch-critique and confirm
   the visual state matches the deployed UI at 2200×1300.

4. Confirm readiness. When you have read the handover + skimmed the
   live UI, say literally: "I'm ready for the next briefing." Then
   stop and wait for the user.

Three threads were explicitly deferred from the 2026-05-19 arc:

- STUCK_AGREED_K = 1 (currently K=2; revisit only if production runs
  show the spec-0089 § B escape valve over-blocking after we have
  post-spec-0091 data — i.e. agents really were converged but ledger
  said no for 2+ rounds).
- Phase 4 parse-failure cascade (Claude regressing into malformed
  outputs mid-phase, like 27de r3/r5). Needs a fresh reproduction
  case post-spec-0091 to investigate; the spec-0091 round-1 gate may
  have eliminated the upstream cause.
- Phase 4 reviewer mirror-sycophancy. No evidence of this yet; § A's
  structural gate is symmetric (any agent's APPROVED in r1 is
  downgraded), but the § B prompt requirement is drafter-specific.
  Revisit if post-spec-0091 data shows reviewer-side premature-APPROVED.

Plus one potential follow-up not yet scoped:

- Backfill old persisted runs' state.agreed_plan + ledger.json from
  on-disk turn files via a small CLI. Locally-materialized runs DO
  benefit from the parser fixes immediately (everything is re-derived
  from round files), but Supabase-persisted state.agreed_plan from
  pre-fix runs is frozen. ~50-line CLI if the user wants this.

Critical reminders the prior session learned the hard way:

- Take all UI verification screenshots at 2200×1300 or wider. Smaller
  viewports hide layout gaps.
- The canonical fixture for run-detail verification is the partner-
  vetting run (display id 3a4a). Other runs may exhibit Phase-0-only
  data and won't exercise the critique pane / consumption tab.
- Pause between specs even when blanket-greenlit. Surface the next
  spec for review before drafting; the "do everything" greenlight
  covers spec-internal work but NOT the boundary between specs.
- Before drafting a spec, use AskUserQuestion to ask scope + format-
  choice + proceed-style questions in one round-trip.
- Empirically check the data before scoping a fix. The user's
  "ghosting is everywhere" observation turned out to be a parser
  bug, not an agent behaviour bug. The investigation that surfaced
  this was the heart of the arc.
- "dual research" / "DR" = /Users/alexlisitzky/dual-research/.
```

---

## 7 · Tests

```
$ uv run pytest tests/ -q
895 passed in 6.s
```

New test surfaces this arc:

- `tests/protocol/test_convergence_spec0089.py` — 30 tests (canonical-FSD detection, synthesis, splice, lenient checks)
- `tests/protocol/test_convergence_spec0089_replay.py` — 5 tests (2c4f r04 pinned)
- `tests/protocol/test_parse_fence_aware.py` — 12 tests (fence-aware boundary search)
- `tests/protocol/test_prompts_spec0090.py` — 9 tests (answer-format examples present)
- `tests/protocol/test_spec0090_replay.py` — 4 tests (2c4f r01-r04 pinned)
- `tests/protocol/test_review_prompt_spec0091.py` — 4 tests (drafter-engagement block present)
- `tests/ui/test_questions_spec0090.py` — 18 tests (block extraction, ID matching, look-ahead)
- `tests/ui/test_issues_spec0090.py` — 6 tests (broader ID regex)
- `tests/orchestrator/test_phase4_spec0091.py` — 2 integration tests (r1 downgrade + r3+ termination sanity)
- `tests/ledger/test_prompt.py` — +5 tests for the new blocked-convergence warning helper

Existing tests updated:
- `tests/orchestrator/test_phase3_4_final.py::test_phase4_converges_in_round_1` renamed + rewritten as `test_phase4_cannot_converge_in_round_1_but_converges_in_round_2`
- `tests/orchestrator/test_phase4_resume.py` — both tests updated for post-spec-0091 round-1 behaviour
- `tests/protocol/test_convergence_ledger.py` — `round=1` → `round=2` in 3 places
- `tests/protocol/test_convergence_spec0089.py` — `round=1` → `round=2` in 5 places
