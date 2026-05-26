---
kind: dev
spec: "0225"
slug: lifecycle-trace-verifier
title: Add lifecycle-trace verifier asserting the 0114 unified contract
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: L
created: 2026-05-26
queued_at: "2026-05-26T20:39:21Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

# Spec 0225 — Add lifecycle-trace verifier asserting the 0114 unified contract

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — net-new tooling (`src/dual_research/contract/verifier.py` + `dual-research verify` CLI + corpus CI), no behavior change to the orchestrator.
> **Evidence:** Cowork synthesis `../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md` §3 (the contract) + §6 action 4 (this spec); Cowork sign-off `../cowork/briefs/2026-05-26-verifier-spec-v2-signoff.md`; predecessor specs 0114, 0141, 0214, 0218, 0219, 0222 (v1.45.3), 0224 (v1.45.5).

---

## 1. Context

Every spec since 0114 has been "patches that look like bug fixes but were actually amending the unified contract" (synthesis §1.4). The contract — what a well-formed run *is* — lives only in scattered prose across 0114, 0141, 0214, and the synthesis itself. The remedy is two-part: (a) reclassify the offenders (separate follow-up spec, see §5), and (b) give the contract a **runnable** form so future drift surfaces in CI on a PR rather than in a dead run a week later. This spec ships (b). The verifier IS the contract, in executable form.

Live contract substrate already exists and is cited below — this spec reuses it, never re-spells it:

- [`src/dual_research/contract/ids.py:29`](src/dual_research/contract/ids.py) — `ID_PATTERN = re.compile(r"^([QDIC])-(input|plan|review)-([cg])-(\d{2})$")`.
- [`src/dual_research/contract/categories.py:47`](src/dual_research/contract/categories.py) — `RAISABLE_IN` matrix (phase 0/2 → Q+D, phase 4 → Q/D/I/C); [`categories.py:36`](src/dual_research/contract/categories.py) — `PHASE_TOKEN`.
- [`src/dual_research/events/types.py:450`](src/dual_research/events/types.py) — `ItemTransitioned` (carries `via: str | None` valued `"hard_cap"` / `"ghost_cap"` for orchestrator caps); [`types.py:562`](src/dual_research/events/types.py) — `PhaseConverged` with `via_closeout` / `via_ghost_cap` / `via_hard_cap` / `via_artifact_promotion`; [`types.py:135`](src/dual_research/events/types.py) — `TurnEnded.finish_reason`; [`types.py:503`](src/dual_research/events/types.py) — `ProtocolViolation` (for the I4.4 cross-check).
- [`src/dual_research/orchestrator/deep_research.py:482`](src/dual_research/orchestrator/deep_research.py) — the silent-drop site (`if ent.current_state != State.ADDRESSED: continue`) detected by I4.4. **Out of scope to fix here**; closed in a follow-up `ProtocolViolation`-emission spec (synthesis §6 action 3).

### Source-artifact traceability

| Source item | Source quote / ref | Spec section |
|---|---|---|
| Synthesis §3 Area 1 (Phases) — five invariants + `[NEW]` phase-4 budget | "Phases 1 & 3 emit no item events. Items freeze (terminal, read-only) at phase boundaries." | §2.2 Area 1 (I1.1–I1.5) |
| Synthesis §3 Area 2 (Negotiations) — convergence triad + `[NEW]` addressee obligation + `[NEW]` ledger-vs-self-report | "the reconstructed ledger + computed hash are authoritative; the agents' self-reported counts are a cross-checked signal, never the source of truth." | §2.2 Area 2 (I2.1–I2.5) |
| Synthesis §3 Area 3 (Categorisation) — held, no amendments | "Four kinds (Q/D/I/C); IDs `<kind>-<phase>-<raiser>-<seq>`, … immutable; per-phase raisable matrix; `claim` removed." | §2.2 Area 3 (I3.1–I3.5) |
| Synthesis §3 Area 4 (Resolution lifecycle) — six states, four terminal + `[NEW]` ProtocolViolation + `[NEW]` RESOLVE-from-open coercion | "RESOLVE is valid only from `addressed`. RESOLVE-from-open is invalid." | §2.2 Area 4 (I4.1–I4.7) |
| Synthesis §3 Area 5 (Liveness / terminal events) — `[NEW]` area | "For every `run_started`, exactly one terminal event … is emitted and `metrics.ended_at` is set — including on `BaseException` and on out-of-process kills." | §2.2 Area 5 (I5.1–I5.3) |
| Synthesis §6 action 4 | "Build the lifecycle-trace verifier. … Acceptance: it flags every run where a phase converged with a non-terminal item, or a `run_started` lacks a terminal event, or an op was dropped silently." | §2.1 (the CLI shape) + §6 (acceptance) |
| Synthesis §7.2 | "the verifier should assert against observed code behaviour" | §2.3 (reference runs as regression corpus) |
| Sign-off v2 §"Required correction" | "the actual Bug-A detector is I4.4 … I4.4's pre-action-3 detection requires comparing each turn `.md`'s emitted ops to the transitions/violations in the transcript" | §2.2 I4.4 + §2.4 implementation note |
| Sign-off v2 §"Build-time note" | "I4.7 … assumes the `item_transitioned` event carries `via` (`ghost_cap` / `hard_cap`) provenance." | §2.4 build-time note (verified: field exists) |
| Stabilisation snapshot `../cowork/feedback/2026-05-26-orchestrator-stabilisation-resume.md` | Names the three reference-run IDs | §2.3 |

---

## 2. Proposed change

### 2.1 — CLI surface

New subcommand on the existing CLI:

```
uv run dual-research verify [<run-dir>...]
```

- Reads each `<run-dir>` (defaults to current working dir if no args) and runs every invariant in §2.2.
- Exits non-zero iff (a) any **gating** invariant fails on any of the supplied runs, or (b) any invariant — gating or reporting — regressed from `pass` → `fail` against the last-known-good baseline frozen in `tests/fixtures/anchor-runs/<run-id>/expected.json`.
- Output: a structured report per run — per-invariant verdict (`pass` / `fail` / `not_applicable`) + severity (`gating` / `reporting`) + evidence (event line numbers in `transcript.jsonl`, turn-file paths + line numbers, values that triggered the verdict).
- Two severities by design:
  - **gating** — failure fails CI; merge-blocking.
  - **reporting** — failure is logged + visible; does not fail CI on its own. Each reporting invariant has a documented promotion trigger (named below) where it becomes gating once the corresponding fix spec ships.

Extension lands in [`src/dual_research/cli.py`](src/dual_research/cli.py).

### 2.2 — Invariants (the contract, executable)

#### Area 1 — Phases

| ID | Severity | Invariant |
|---|---|---|
| I1.1 | gating | `phase_entered` and `phase_exited` are balanced — each `phase_entered(P)` followed by exactly one `phase_exited(P)`, in order. |
| I1.2 | gating | Phase 1 and phase 3 emit zero `item_raised` and zero `item_transitioned` events. |
| I1.3 | gating | At every `phase_exited`, the phase's reconstructed ledger has all items in terminal states (`resolved` / `acknowledged` / `withdrawn` / `capped`). No `open` / `addressed` survives the boundary. |
| I1.4 | gating | Phase order is linear `0 → 1 → 2 → 3 → 4 → done`. No phase repeats; no loop-back. |
| I1.5 | reporting | Every phase-4 drafter `turn_ended` event has `finish_reason ∉ {max_tokens, length}`. Catches the spec-0218→0219 truncation signature. **Promotes to gating after the phase-4 budget contract lands.** |

#### Area 2 — Negotiations

| ID | Severity | Invariant |
|---|---|---|
| I2.1 | gating | Convergence requires (both `STATUS: AGREED`) AND (zero non-terminal items) AND a per-phase third gate: phase 0 + phase 2 require artifact hash-match; phase 4 requires draft-version equality (post-0214; the `version` field on `AGREED_DRAFT_ACCEPTANCE` is the equality token). A `phase_converged` event with all four `via_*` flags False (organic) must satisfy all three gates. |
| I2.2 | gating | Round 1 of any multi-round phase never emits `STATUS: AGREED`. |
| I2.3 | gating | Every `phase_converged` event has exactly one `via_*` flag True, OR all four False (organic). No combination of two or more True. |
| I2.4 | reporting | **Addressee obligation:** no agent emits `STATUS: AGREED` in a round where an `open` item raised by the other agent and addressed at it has not yet transitioned to `addressed` from that agent's turn. **Promotes to gating after the addressee-obligation spec ships** (synthesis §6 action 6). |
| I2.5 | reporting | **Self-report ⇄ ledger divergence.** For every `turn_ended`, compare the turn's self-reported `OPEN_QUESTIONS` and `OPEN_DISAGREEMENTS` counts to the orchestrator-reconstructed ledger's open count for that turn's phase. Divergence is logged with the delta. **Reporting forever** — synthesis §3 Area 2 is explicit: self-report is a cross-checked signal, never the source of truth. |

#### Area 3 — Categorisation

| ID | Severity | Invariant |
|---|---|---|
| I3.1 | gating | Every item ID matches `dual_research.contract.ids.ID_PATTERN`. **Import the regex from [`ids.py:29`](src/dual_research/contract/ids.py); do not re-spell it.** Live pattern: `^([QDIC])-(input|plan|review)-([cg])-(\d{2})$`. |
| I3.2 | gating | Item IDs are immutable across rounds within a phase. |
| I3.3 | gating | `STATUS` action arrays (`RAISED_THIS_TURN` / `RESOLVED_THIS_TURN` / `ADDRESSED_THIS_TURN` / `WITHDRAWN_THIS_TURN` / `ACKNOWLEDGED_THIS_TURN`) contain only canonical IDs matching I3.1. No prose strings. |
| I3.4 | gating | No item has `kind=claim` (removed at 0114). |
| I3.5 | gating | **Raisable-in matrix.** Items respect `dual_research.contract.categories.RAISABLE_IN`. **Import the matrix from [`categories.py:47`](src/dual_research/contract/categories.py); do not re-spell it.** Phase 0 + phase 2 only allow Q + D; phase 4 allows Q/D/I/C. |

#### Area 4 — Resolution lifecycle

| ID | Severity | Invariant |
|---|---|---|
| I4.1 | gating | Every `item_transitioned` event's (`from_state` → `to_state`) edge is in the permitted table: `{open→addressed, addressed→resolved, addressed→open, *→withdrawn, *→acknowledged, *→capped}`. |
| I4.2 | gating | Once an item reaches a terminal state, it has no further `item_transitioned` events. |
| I4.3 | gating | Every `item_transitioned` event has a non-empty `reason` field. |
| I4.4 | reporting | **Silent-drop closed — turn-file ⇄ transcript diff.** For every op block (`### RAISE` / `### ADDRESS` / `### RESOLVE` / `### WITHDRAW` / `### ACKNOWLEDGE`) parsed from a turn `.md` file, the transcript MUST contain a corresponding `item_transitioned` event OR a `ProtocolViolation` event citing the same op. An op in a turn file with neither = a silent drop; log this op as an I4.4 failure with the turn file path + line range. **The verifier MUST parse turn `.md` files for this check; a transcript-only scan cannot detect the bug** — the drop at [`deep_research.py:482`](src/dual_research/orchestrator/deep_research.py) leaves no transcript event by design. **Promotes to gating after the ProtocolViolation-emission spec ships** (synthesis §6 action 3). |
| I4.5 | gating | No `item_transitioned` event has edge `open → resolved`. **Future-proofing guard-rail** — today's dead run passes I4.5 (the drop is upstream of any transition write); I4.5 catches a *future* change re-introducing the edge. |
| I4.6 | gating | **Acknowledged is mutual.** An item only reaches `acknowledged` after both agents have emitted ACKNOWLEDGE for it in consecutive turns. No single-agent `* → acknowledged` transition. |
| I4.7 | gating | **Capped is orchestrator-only.** An item only reaches `capped` via an orchestrator action. **Primary predicate:** `event.via in {"hard_cap", "ghost_cap"}` (the [`ItemTransitioned.via`](src/dual_research/events/types.py) field, verified to exist at line 469). **Build-time fallback** (in case `via` is renamed or removed between spec and build): `event.actor == "orchestrator"`. The verifier's module docstring MUST record which predicate was used. |

#### Area 5 — Liveness / terminal events

| ID | Severity | Invariant |
|---|---|---|
| I5.1 | gating | For every `run_started` event, exactly one terminal event (`run_completed` / `run_failed` / `run_aborted`) exists with the same run scope. |
| I5.2 | gating | `metrics.json` `ended_at` is non-null whenever `run_started` is present in the transcript. |
| I5.3 | gating | The terminal event's timestamp ≥ every non-terminal event timestamp in the same run (no time-travel). |

### 2.3 — Reference-run regression corpus

Three fixtures land under `tests/fixtures/anchor-runs/<run-id>/`. Per run include: `transcript.jsonl`, `state.json`, `metrics.json`, the turn `.md` files from `phase0/`, `phase2/`, `phase4/`, **and** an `expected.json` capturing the frozen per-invariant verdict (the regression baseline). Exclude: `phase1/`, `phase3/` (no item events), `inputs/`, the assembled draft, `searches/` audit bundles.

| Run ID | Expected verdict (current code) | Why |
|---|---|---|
| `20260521-010637-dvs-backend-language-choice` | All gating invariants pass. All reporting invariants pass or `not_applicable`. | Clean successful E2E run — regression detector. |
| `20260526-102321-backend-language-choice` | Gating **I5.1 + I5.2 FAIL** (drive the non-zero exit — no terminal event written). Reporting **I4.4 logs** the 4 dropped RESOLVE ops from claude round-02 (items `D-plan-c-02 / D-plan-c-04 / D-plan-c-05 / Q-plan-c-01`). Reporting **I2.5 logs** the false `OPEN_DISAGREEMENTS: 0` on rounds 3–4. **I4.5 PASSES** (drop is upstream of any transition write, so no `open→resolved` edge exists in the ledger; I4.5 is a future-proofing guard-rail, not Bug-A's detector). | Today's primary failing run. After the SIGHUP-handler (0224, v1.45.5) and the ProtocolViolation-emission spec land, replays pass I5; I4.4 then promotes to gating. |
| `20260525-135006-backend-language-choice` | Gating **I5.1 + I5.2 FAIL** (no terminal event); ledger otherwise clean. | Second silent-death control; isolates Bug B from Bug A. |

### 2.4 — Implementation notes for the build

- **Turn-file parsing is mandatory** for I4.4 and the I2.5 self-report check. The verifier diffs each turn `.md` file's op blocks against the transcript's `item_transitioned` + `ProtocolViolation` events to surface silent drops. A transcript-only scan can never detect the bug at [`deep_research.py:482`](src/dual_research/orchestrator/deep_research.py).
- **Reuse the live contract.** Import `ID_PATTERN` from `dual_research.contract.ids`, `RAISABLE_IN` and `PHASE_TOKEN` from `dual_research.contract.categories`. Do not re-spell them in the verifier module — the assertion is that runs match the **observed code's** contract (synthesis §7.2).
- **I4.7 predicate.** [`events/types.py:450`](src/dual_research/events/types.py) defines `ItemTransitioned` with `via: str | None = None`, set to `"hard_cap"` or `"ghost_cap"` for orchestrator-driven caps. Use `event.via in {"hard_cap", "ghost_cap"}` as the primary predicate; if the field is missing at build time, fall back to `event.actor == "orchestrator"` and document the choice in the verifier's module docstring.
- **VerifierReport dataclass.** `verify_run(run_dir: Path) -> VerifierReport`. `VerifierReport` carries per-invariant entries (`InvariantResult(id, severity, verdict, evidence: list[Evidence])`), plus the overall exit-code decision (gating-fail OR baseline-regression).

### 2.5 — CI wiring

New workflow `.github/workflows/verifier-corpus.yml` running `uv run dual-research verify tests/fixtures/anchor-runs/*` on every PR. Fails the PR on (a) any gating-invariant failure, or (b) any baseline regression — pass→fail vs the frozen `expected.json` — even for reporting invariants. The clean fixture `20260521-010637-dvs-backend-language-choice` is the live regression detector.

## 3. User stories & acceptance criteria

Non-UI spec — §3.1 user stories and §3.2 BDD scenarios are not required. The acceptance bar is the test plan in §6 + the CI job in §2.5.

## 4. Data / Schema deltas

None. No new event types, no schema changes, no migrations. New fixture data under `tests/fixtures/anchor-runs/` is verifier-internal.

## 5. Out of scope

- **Reclassifying the offending bug-labeled specs** (0137, 0140, 0218, 0219) — deferred to a separate `breaking`-or-process spec per synthesis §6 action 5.
- **Closing the silent-drop at [`deep_research.py:482`](src/dual_research/orchestrator/deep_research.py)** — deferred to the `ProtocolViolation`-emission spec (synthesis §6 action 3). Once that lands, I4.4 promotes from reporting to gating.
- **The addressee-obligation enforcement** in the orchestrator — deferred to its own feature spec (synthesis §6 action 6). Once that lands, I2.4 promotes from reporting to gating.
- **The phase-4 budget contract** — deferred to a follow-up spec covering the 0218/0219 truncation signature. Once that lands, I1.5 promotes from reporting to gating.
- **Self-report becoming authoritative** — synthesis §3 Area 2 is explicit: self-report is a cross-checked signal, never the source of truth. I2.5 is **reporting forever** by design.
- **Running the verifier across all 31 historical transcripts in CI.** This spec wires only the three named fixtures; broader corpus replay is a follow-up.
- **The "why claude emitted RESOLVE-from-open in the first place" prompt-side investigation** (synthesis §7.1) — separate authoring track.

## 6. Test plan

- [ ] `uv run pytest tests/test_verifier.py -q` passes.
- [ ] Per-invariant unit tests on synthetic minimal transcripts + turn files: for every invariant ID in §2.2, one positive case (passes) and one antipodal-absence case (fails with the expected evidence). I4.4 needs three cases — (a) op in turn file + matching `item_transitioned` = pass; (b) op in turn file + matching `ProtocolViolation` = pass; (c) op in turn file + neither = fail (logs the dropped op with file path + line range).
- [ ] Snapshot test against `tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/` — verifier output equals the frozen `expected.json`; CLI exits 0.
- [ ] Snapshot test against `tests/fixtures/anchor-runs/20260526-102321-backend-language-choice/` — CLI exits non-zero; report cites gating failures I5.1 + I5.2; reporting invariant I4.4 logs the four dropped RESOLVE ops on the named items; reporting invariant I2.5 logs the self-report divergence on rounds 3–4; gating invariant I4.5 reports `pass`.
- [ ] Snapshot test against `tests/fixtures/anchor-runs/20260525-135006-backend-language-choice/` — CLI exits non-zero citing only I5.1 + I5.2; ledger otherwise clean.
- [ ] `uv run dual-research verify tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/` exits 0 and reports all gating invariants as `pass`.
- [ ] `uv run dual-research verify tests/fixtures/anchor-runs/20260526-102321-backend-language-choice/` exits non-zero with the exact citations named above.
- [ ] `uv run dual-research verify tests/fixtures/anchor-runs/20260525-135006-backend-language-choice/` exits non-zero citing only I5.1 + I5.2.
- [ ] The `.github/workflows/verifier-corpus.yml` CI job is visible on the PR for this spec and runs `dual-research verify` over all three fixtures.
- [ ] CHANGELOG entry added under a new `## [X.Y.Z] — 2026-05-26` heading per `CLAUDE.md`; `pyproject.toml` and `src/dual_research/__init__.py` MINOR-bumped.

## 7. Risks

- **Fixture drift.** Future event-payload changes (e.g. a renamed field in `ItemTransitioned`) will break the snapshots. Mitigation: I4.7's documented build-time fallback predicate pattern. If a snapshot diverges legitimately, regenerate `expected.json` in the same PR that lands the rename.
- **Turn-file format drift.** I4.4 parses the agent turn `.md` files; if the agent prompt evolves the `### RAISE` / `### ADDRESS` / `### RESOLVE` / `### WITHDRAW` / `### ACKNOWLEDGE` op-block syntax, the parser breaks. Mitigation: keep the op-block regexes in one module-level constant block; unit-test against today's verbatim turn files in the fixtures. If the format changes deliberately, that's a coordinated change (turn-file shape + verifier op parser + fixtures).
- **CI cost.** Three fixtures × every PR is cheap; broader 31-run corpus replay would not be. The follow-up to extend corpus reach can run nightly rather than per-PR if needed.
- **Reporting invariants being ignored.** Reporting-severity failures don't fail CI; a maintainer could miss them. Mitigation: the report is printed to stdout on every CI run and rendered in the workflow summary; each reporting invariant has a documented promotion trigger named in §5.
- **False I4.4 positives** if the op-block parser is over-eager (e.g. matching prose snippets that look like `### RAISE`). Mitigation: require the canonical heading shape + a canonical ID line + a body, and unit-test the parser on both well-formed and near-miss synthetic inputs.
