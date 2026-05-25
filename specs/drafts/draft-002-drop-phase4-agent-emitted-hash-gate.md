---
kind: draft
draft_id: "002"
slug: drop-phase4-agent-emitted-hash-gate
title: "Drop Phase 4 agent-emitted SHA-256 gate; converge on version equality"
type: bug
status: draft
created: 2026-05-25
source_session: phase4-hash-gate-investigation-followup
---

# Draft 002 — Drop Phase 4 agent-emitted SHA-256 gate; converge on version equality

> **Type:** bug  |  **Severity:** P0 (deadlock)  |  **Affects:** orchestrator phase 4 cross-review convergence
> **Bump:** PATCH — bug fix
> **Evidence:** [`runs/20260521-010637-dvs-backend-language-choice/`](../../runs/20260521-010637-dvs-backend-language-choice/) — agents content-agreed at round 3, hard-capped at round 8 chasing the hash. See [`phase4-hash-gate-investigation.md`](../../phase4-hash-gate-investigation.md) for the full diagnosis.

This is **Spec 1 of 3** in a sequenced bug-fix batch from the phase-4 / phase-2 investigation. Bug #2 (in-round blindness in `_drive_interaction_phase`) and Bug #3 (raiser self-ADDRESS validator gap) land as separate PATCH specs.

## 1. Reproduction

**Environment:** dual-research orchestrator at HEAD on 2026-05-25; Deep Research protocol phase 4 (cross-review). Models: prod-tier `claude` + `openai`. Run launcher: `dual-research-run` skill.

**Steps:**

1. Fire any phase-4 run that reaches the cross-review phase — e.g. `/dual-research-run` on the backend-language-choice briefing.
2. Wait for both agents to substantively agree on the draft body (typically rounds 3–4).
3. Observe phase 4 continue past content-convergence and burn rounds until the hard cap at round 8.

**Expected:** Phase 4 converges in the round both agents emit `STATUS: AGREED` with matching `draft_version` pointers and a terminal ledger. The drafter has not revised the draft this round. The orchestrator records the converged draft's canonical SHA in `PhaseConverged` for provenance.

**Actual:** Convergence is gated on a SHA-256 `draft_hash` field that **each agent computes itself** from the visible draft body — a hash an LLM cannot reliably produce because the orchestrator's `canonical_hash` applies `_normalize_for_hash` (smart-quote folding + whitespace collapsing) before hashing. Either side will:

- **Fabricate** a digest and emit `STATUS: AGREED` (Claude, round 7); or
- **Refuse on principle** and emit `STATUS: IN_PROGRESS` (OpenAI, round 7), citing artifact-exposure as the procedural blocker.

The two hashes never match, the gate at [`dr_run.py:1391-1400`](../../src/dual_research/orchestrator/dr_run.py:1391) rejects, and the phase runs to the hard cap.

**Run-level evidence ([`runs/20260521-010637-dvs-backend-language-choice/`](../../runs/20260521-010637-dvs-backend-language-choice/)):**

| Round | Claude | OpenAI |
|---|---|---|
| 3 | revised draft, well-structured | substantively aligned, refused on hash grounds |
| 7 | full v7 draft + AGREED with fabricated hash | "cannot emit STATUS: AGREED" — hash-exposure refusal |
| 8 | re-emits "v8", AGREED again | STATUS: IN_PROGRESS — still refusing |

Cost burned past content-convergence: ~$5 of the run's $13.51 total; +5 rounds of agent calls.

**Smoking-gun quote** ([`runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md:5`](../../runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md)):

> "The honest answer is that I cannot generate a real SHA-256 hash of a file I haven't saved to disk; neither can OpenAI. The `AGREED_DRAFT_ACCEPTANCE` blocks with hashes are orchestrator-managed protocol artifacts, not things either agent computes. The orchestrator assigns draft versions and hashes based on what it tracks. My job is to produce the best complete draft and emit AGREED; the orchestrator matches the hash. OpenAI should do the same."

Claude's reasoning is correct — the design itself is the bug.

## 2. Root cause hypothesis

The convergence gate is structurally unsatisfiable. Two independent sites collude:

**Site A — the prompt asks each agent to compute the hash itself** ([`src/dual_research/protocol/prompts.py:2129-2133`](../../src/dual_research/protocol/prompts.py:2129)):

```
### AGREED_DRAFT_ACCEPTANCE

draft_version: v<N>
draft_hash: <SHA-256 hex of the draft file content>
endorsement: |
  <one sentence on why this draft satisfies the brief>
```

**Site B — the orchestrator's canonical hash is non-trivial** ([`src/dual_research/contract/artifacts.py:30-50`](../../src/dual_research/contract/artifacts.py:30)):

```python
_WS_RE = re.compile(r"\s+")
_SMART_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"}

def _normalize_for_hash(text: str) -> str:
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    for smart, plain in _SMART_QUOTES.items():
        out = out.replace(smart, plain)
    out = _WS_RE.sub(" ", out)
    return out.strip()

def canonical_hash(artifact_text: str) -> str:
    return hashlib.sha256(_normalize_for_hash(artifact_text).encode("utf-8")).hexdigest()
```

No LLM can replicate this normalization + SHA-256 in its head reliably. The two agents will diverge on whitespace handling alone.

**Site C — the gate requires byte-equal hashes** ([`src/dual_research/orchestrator/dr_run.py:1391-1400`](../../src/dual_research/orchestrator/dr_run.py:1391)):

```python
def _phase4_artifact_hash_match(a, b) -> bool:
    ta = _render_for_extract(a)
    tb = _render_for_extract(b)
    acc_a = extract_agreed_draft_acceptance(ta)
    acc_b = extract_agreed_draft_acceptance(tb)
    if acc_a is None or acc_b is None:
        return False
    ver_a, hash_a, _ = acc_a
    ver_b, hash_b, _ = acc_b
    return ver_a == ver_b and hash_a == hash_b
```

The orchestrator already owns the canonical draft on disk and already computes `canonical_hash` for provenance — it never actually needs the agents to repeat the computation. The hash adds **no safety**: the orchestrator is the only thing that writes a draft file. Spec 0036 previously proved that echo-the-hash schemes (option A in the investigation) are also fragile — agents emit `----` separators that pass through, and refusal/fabrication asymmetry remains.

Spec 0137/0140 introduced an escape valve (`via_artifact_promotion`) that fires on `both_agreed + terminal_ledger + round_no >= soft_cap`. It fires too late — round 8 in this run, not round 3.

## 3. Fix

Replace the agent-emitted `draft_hash` ask with an orchestrator-computed version-equality gate cross-checked against `ctx.state.draft_round`. Persist the orchestrator-computed canonical SHA in the `PhaseConverged` event so provenance is preserved — but anchored to the on-disk file, not the agent's mental math.

### Code changes (verified file:line refs at HEAD on 2026-05-25)

**1. `src/dual_research/orchestrator/dr_run.py:1391-1400` — rewrite the gate.**

Rename `_phase4_artifact_hash_match` → `_phase4_artifact_version_match`. Replacement body:

```python
def _phase4_artifact_version_match(a, b) -> bool:
    ta = _render_for_extract(a)
    tb = _render_for_extract(b)
    acc_a = extract_agreed_draft_acceptance(ta)
    acc_b = extract_agreed_draft_acceptance(tb)
    if acc_a is None or acc_b is None:
        return False
    ver_a, _ = acc_a
    ver_b, _ = acc_b
    return ver_a == ver_b == ctx.state.draft_round
```

Implementation note: `ctx` is captured by closure from the enclosing `run_dr_phase4` scope (same pattern `_build` already uses one level up at [`dr_run.py:1330-1389`](../../src/dual_research/orchestrator/dr_run.py:1330)). The `artifact_hash_match=` wiring at [`dr_run.py:1412`](../../src/dual_research/orchestrator/dr_run.py:1412) is then `artifact_hash_match=_phase4_artifact_version_match`. Field name on the orchestrator stays `artifact_hash_match` (the parameter is the phase-specific cross-check callable; renaming it is a separate refactor out of scope).

**2. `src/dual_research/protocol/prompts.py:2082-2086` — rewrite the convergence-description paragraph.**

Before:

```
Phase 4 converges when both of you emit STATUS: AGREED in the same
round, all items are terminal, your AGREED_DRAFT_ACCEPTANCE blocks
match (same draft_version, same draft_hash), and the drafter has not
revised the draft in this round.
```

After:

```
Phase 4 converges when both of you emit STATUS: AGREED in the same
round, all items are terminal, your AGREED_DRAFT_ACCEPTANCE blocks
agree on the same draft_version (the orchestrator anchors the version
pointer to the on-disk draft), and the drafter has not revised the
draft in this round.
```

**3. `src/dual_research/protocol/prompts.py:2129-2133` — drop the `draft_hash:` line from the prompt template.**

Before:

```
### AGREED_DRAFT_ACCEPTANCE

draft_version: v<N>
draft_hash: <SHA-256 hex of the draft file content>
endorsement: |
  <one sentence on why this draft satisfies the brief>
```

After:

```
### AGREED_DRAFT_ACCEPTANCE

draft_version: v<N>
endorsement: |
  <one sentence on why this draft satisfies the brief>
```

**4. `src/dual_research/contract/artifacts.py:93-100` — drop the `draft_hash:` line from `AGREED_DRAFT_ACCEPTANCE_TEMPLATE`.** Same subtractive edit as Site 3.

Update the module docstring at [`artifacts.py:12-15`](../../src/dual_research/contract/artifacts.py:12) — the sentence "Phase 4's artifact also carries the draft's content hash; the parser verifies both agents agreed to the same ``draft_version`` and same ``draft_hash``…" needs rewording to reflect version-only agreement.

**5. `src/dual_research/contract/markers.py:197-200` — remove `DRAFT_HASH_RE`.** No other consumers outside `parse.py:16` (grep-verified).

**6. `src/dual_research/protocol/parse.py:1478-1496` — narrow `extract_agreed_draft_acceptance` return type.**

Before: `tuple[int, str, str] | None` — `(draft_version, draft_hash, endorsement)`.
After: `tuple[int, str] | None` — `(draft_version, endorsement)`.

Drop the `hash_m = DRAFT_HASH_RE.search(body)` lookup and the digest field. Drop the `DRAFT_HASH_RE` import at [`parse.py:16`](../../src/dual_research/protocol/parse.py:16). Update the docstring. No change to `src/dual_research/protocol/__init__.py:23,78` (name unchanged).

Migrate [`tests/protocol/test_parse_v2.py:530-590`](../../tests/protocol/test_parse_v2.py:530) (`test_extract_agreed_draft_acceptance`) — assert the two-tuple return shape.

**7. `src/dual_research/orchestrator/deep_research.py:1004-1017` — leave `_default_artifact_hash_match` untouched.**

Phase 0 and phase 2 still use real canonical hashing of artifact text the agents echo verbatim from the orchestrator-rendered prompt (see `_phase0_artifact_hash_match` at [`dr_run.py:690`](../../src/dual_research/orchestrator/dr_run.py:690) and `_phase2_artifact_hash_match_factory` at [`dr_run.py:1121`](../../src/dual_research/orchestrator/dr_run.py:1121)). Those paths are not affected — only phase 4 overrides with version equality.

**8. `src/dual_research/orchestrator/dr_run.py` phase-4 driver — compute and thread the orchestrator-side SHA.**

After the `_drive_interaction_phase` call returns at [`dr_run.py:1404-1416`](../../src/dual_research/orchestrator/dr_run.py:1404), when `result.converged` is true, read the on-disk draft via `current_draft_path(ctx.session, ctx.state.draft_round)` (helper already in use at [`dr_run.py:1318`](../../src/dual_research/orchestrator/dr_run.py:1318)) and compute `draft_file_sha256 = hash_draft_content(text)` (helper already exported from `contract/artifacts.py:113`). Thread the SHA into the `PhaseConverged` event the driver emits.

Plumbing: `_drive_interaction_phase` constructs `PhaseConverged` internally in `deep_research.py` (see sites 9 + 10 below). The phase-4 driver in `dr_run.py` does **not** itself construct `PhaseConverged`; it relies on the events the inner driver emits. Two options for threading:

- **Option A — pass a post-converge hook into `_drive_interaction_phase`** that mutates the in-flight `PhaseConverged` before emission. Adds API surface.
- **Option B — let the inner driver emit `PhaseConverged` with `draft_file_sha256=None`, then the phase-4 wrapper emits a follow-on event** (e.g. extend `Phase4Complete` at [`dr_run.py:1422-1427`](../../src/dual_research/orchestrator/dr_run.py:1422) with a `draft_file_sha256` field). Cleaner separation; provenance lives on the phase-completion event rather than the generic convergence event.

**Choose Option B.** Rationale: `PhaseConverged` is the generic phase-agnostic convergence signal; `Phase4Complete` already exists as the phase-4-specific summary event and is the right home for phase-4-specific provenance. This keeps the `PhaseConverged` schema phase-agnostic.

That changes site 9 below:

**9. `src/dual_research/events/types.py` — extend `Phase4Complete` (not `PhaseConverged`) with a `draft_file_sha256` field.**

Locate `Phase4Complete` in [`events/types.py`](../../src/dual_research/events/types.py) (grep `class Phase4Complete`). Add optional kw-only field:

```python
draft_file_sha256: str | None = None
```

Update the docstring noting this is the orchestrator-computed `canonical_hash` (smart-quote-folded, whitespace-collapsed SHA-256) of the on-disk draft at the converged round. `None` if the phase did not converge organically (hard-cap / artifact-promotion paths still set it when a draft is on disk; document the contract explicitly).

`PhaseConverged` is left untouched — preserves the phase-agnostic invariant.

**10. `src/dual_research/orchestrator/dr_run.py:1422-1427` — populate the new field at the publish site.**

```python
await event_bus.publish(Phase4Complete(
    rounds=result.rounds,
    approved=approved,
    final_draft_round=ctx.state.draft_round,
    revisions=revisions_count,
    draft_file_sha256=_compute_draft_sha_if_present(ctx),
))
```

Helper `_compute_draft_sha_if_present(ctx)` reads `current_draft_path(ctx.session, ctx.state.draft_round)`, returns `hash_draft_content(text)` if the file exists, else `None`. Add the same field to the `ctx.transcript.write("phase4_complete", ...)` call immediately below at [`dr_run.py:1428-1434`](../../src/dual_research/orchestrator/dr_run.py:1428).

## 4. User stories & acceptance criteria

Not a UI bug — skipped per the bug template's "REQUIRED for UI bug fixes" gate. The §5 regression-prevention tests are the load-bearing acceptance criteria.

## 5. Regression-prevention test

**New test file: `tests/orchestrator/test_spec_NNNN_phase4_version_gate.py`** (NNNN filled in at `/spec-promote` time):

- [ ] `test_version_gate_accepts_when_both_emit_same_version_matching_ctx_draft_round` — synthetic phase-4 turn pair both with `draft_version: v3`; build a `ctx` stub with `state.draft_round=3`; the new gate returns `True`. Locks in the green path.
- [ ] `test_version_gate_rejects_when_drafter_revised_same_round` — both agents emit `draft_version: v4`, but `ctx.state.draft_round=3` (drafter revised this round; orchestrator hasn't yet advanced the pointer). Gate returns `False`. Locks in the same-round-revise-then-AGREE failure mode the version-only gate would otherwise silently accept.
- [ ] `test_version_gate_rejects_when_versions_disagree` — Claude `v3`, OpenAI `v2`. Gate returns `False`.
- [ ] `test_version_gate_rejects_when_acceptance_block_missing` — agent omits the `### AGREED_DRAFT_ACCEPTANCE` section entirely. Gate returns `False` (preserves the `acc_a is None` early-exit branch).
- [ ] `test_phase4_complete_event_carries_orchestrator_computed_sha` — drive a phase-4 fixture to convergence; assert the published `Phase4Complete` event has `draft_file_sha256` populated and equal to `hash_draft_content(<on-disk draft text at converged round>)`. Locks in provenance.
- [ ] **Replay fixture test: `test_replay_round03_from_dvs_backend_language_choice_converges_under_new_gate`** — load [`runs/20260521-010637-dvs-backend-language-choice/phase4/round-03-claude.md`](../../runs/20260521-010637-dvs-backend-language-choice/phase4/round-03-claude.md) and [`round-03-openai.md`](../../runs/20260521-010637-dvs-backend-language-choice/phase4/round-03-openai.md) (the content-agreed round the old hash gate rejected). Parse both with `parse_turn_v2`; build a `ctx` stub with `state.draft_round=3`; assert the new gate returns `True`. Locks in that the actual failing run would now converge at round 3 instead of hard-capping at round 8.

**Migrate existing hash-mismatch tests** (currently assert the dropped behaviour):

- [ ] [`tests/protocol/test_convergence_spec0089.py:342`](../../tests/protocol/test_convergence_spec0089.py:342) `test_fails_on_hash_mismatch` — this test lives in the phase-2-plan-equality (`is_plan_agreed_lenient`) suite; it covers the **phase-2** hash path, which is unchanged in this spec. Verify the test still passes; if it touches phase-4 internals, scope-narrow to phase-2 only.
- [ ] [`tests/orchestrator/test_closeout.py:152`](../../tests/orchestrator/test_closeout.py:152) `test_convergence_fails_on_hash_mismatch` — generic boolean test (`check_convergence(artifact_hash_match=False, ...)` → rejects). Independent of phase-4 specifics; should still pass as-is.

**Keep these escape-valve tests** (the spec-0137/0140 valve is preserved as defence in depth and becomes a dead-letter path):

- [ ] [`tests/orchestrator/test_deep_research.py:575`](../../tests/orchestrator/test_deep_research.py:575) `test_artifact_promotion_fires_when_both_agreed_ledger_terminal_hash_drifts`
- [ ] [`tests/orchestrator/test_deep_research.py:720`](../../tests/orchestrator/test_deep_research.py:720) `test_artifact_promotion_does_not_fire_when_only_one_agreed_below_soft_cap`
- [ ] [`tests/orchestrator/test_deep_research.py:758`](../../tests/orchestrator/test_deep_research.py:758) `test_artifact_promotion_fires_when_one_agreed_terminal_past_soft_cap`

## 6. Blast radius

- `_phase4_artifact_hash_match` has a **single call site** at [`dr_run.py:1412`](../../src/dual_research/orchestrator/dr_run.py:1412) — verified by grep.
- `_default_artifact_hash_match` ([`deep_research.py:1004`](../../src/dual_research/orchestrator/deep_research.py:1004)) remains untouched; phase 0 ([`dr_run.py:711`](../../src/dual_research/orchestrator/dr_run.py:711)) and phase 2 ([`dr_run.py:1030`](../../src/dual_research/orchestrator/dr_run.py:1030)) wirings continue to use canonical hashing of orchestrator-rendered artifact text the agents echo verbatim. Those phases do not exhibit this bug.
- `DRAFT_HASH_RE` is imported only by [`parse.py:16`](../../src/dual_research/protocol/parse.py:16) — grep-verified.
- `extract_agreed_draft_acceptance` is called from [`dr_run.py:1394-1395`](../../src/dual_research/orchestrator/dr_run.py:1394) (the gate being rewritten) and [`tests/protocol/test_parse_v2.py:569`](../../tests/protocol/test_parse_v2.py:569) (migrated).
- `Phase4Complete` is consumed by the transcript bridge and the dashboard event pipeline. New optional field with a default rides through without breaking existing consumers — additive change.
- `PhaseConverged` schema is **unchanged** — keeps the phase-agnostic invariant intact.
- Spec 0137/0140 escape valve (`via_artifact_promotion`) is preserved — becomes a dead-letter safety net.

## 7. Out of scope

- **Bug #2** (in-round blindness in `_drive_interaction_phase` — second agent doesn't see first agent's same-round turn) — Spec 2 in this batch.
- **Bug #3** (raiser self-ADDRESS validator gap — Claude in round 4 of the failing run misuses the `## Addressing items raised against me` section for own items) — Spec 3 in this batch.
- Reworking phase 0 / phase 2 hash gates — they don't have this failure mode (orchestrator renders the artifact text; agents echo it byte-for-byte).
- Removing the spec-0137/0140 escape valve — kept as defence in depth.
- Renaming `artifact_hash_match` parameter on `DeepResearchPhase` to a phase-neutral name (e.g. `artifact_match_fn`) — semantic cleanup deferred; current name is internally consistent with phase-0/2 usage.

## 8. Risks

- **Risk:** Naive version-only gate would accept a same-round revise-then-AGREE pair (drafter revises to `v<N+1>` and emits AGREED with `draft_version: v<N+1>` in the same turn; reviewer mirrors `v<N+1>`; both versions match and the gate passes prematurely).
  **Mitigation:** The `ver_a == ver_b == ctx.state.draft_round` cross-check anchors against orchestrator state. `ctx.state.draft_round` only advances inside `_on_revised_draft` ([`dr_run.py:1306-1313`](../../src/dual_research/orchestrator/dr_run.py:1306)), which runs **after** the drafter's turn is parsed and persisted but **before** the next round starts. A same-round revise-then-AGREE produces a version mismatch with `ctx.state.draft_round` and the gate rejects. Covered by `test_version_gate_rejects_when_drafter_revised_same_round`.

- **Risk:** Provenance loss if `Phase4Complete.draft_file_sha256` doesn't make it into persisted artifacts.
  **Mitigation:** The transcript bridge serializes all event fields by introspection; the new optional field rides through. Verify by inspecting one converged run's `transcript.jsonl` post-fix shows the SHA. Covered by `test_phase4_complete_event_carries_orchestrator_computed_sha`.

- **Risk:** Prompt churn confuses agents mid-rollout.
  **Mitigation:** PATCH bump; runs complete in minutes (no in-flight runs span the deploy). The prompt change is purely subtractive — drop the `draft_hash:` line; the rest of the AGREED_DRAFT_ACCEPTANCE block is unchanged. The convergence-description paragraph at L2082-2086 gains one clarifying clause about orchestrator-owned versioning.

- **Risk:** Existing `tests/protocol/test_convergence_spec0089.py:342` is more entangled with phase-4 specifics than the investigation believed.
  **Mitigation:** The test is in the `is_plan_agreed_lenient` suite (phase-2 path) per the file inspection. Verify during implementation; if entangled, scope-narrow as documented in §5. Low-likelihood: the spec 0089 tests cover plan-agreement lenient mode, which is structurally phase-2.

## 9. CHANGELOG language

For the version's `### Fixed` section once promoted:

> ### Fixed
> - **Phase 4 hash-gate deadlock (spec NNNN):** the cross-review convergence gate no longer asks each agent to compute a SHA-256 hash of the draft body. Convergence now requires both agents to emit `STATUS: AGREED` with matching `draft_version` pointers anchored against the orchestrator's `ctx.state.draft_round`. The orchestrator computes the canonical draft hash itself and records it in the new `Phase4Complete.draft_file_sha256` field for provenance. Fixes the deadlock observed in run [`20260521-010637-dvs-backend-language-choice`](runs/20260521-010637-dvs-backend-language-choice/) where agents were content-agreed at round 3 but burned through to the hard cap at round 8 because neither could produce a hash matching the orchestrator's `_normalize_for_hash` canonicalization.

## Pointers

- Full investigation: [`phase4-hash-gate-investigation.md`](../../phase4-hash-gate-investigation.md)
- Failing run: [`runs/20260521-010637-dvs-backend-language-choice/`](../../runs/20260521-010637-dvs-backend-language-choice/)
- Spec 0137 / 0140 escape valve (kept as dead-letter path): see [`src/dual_research/events/types.py`](../../src/dual_research/events/types.py) `ArtifactCanonicallyPromoted` and [`src/dual_research/orchestrator/dr_run.py:410-462`](../../src/dual_research/orchestrator/dr_run.py:410)
- Sibling specs in this batch: Spec 2 (in-round blindness — `for_agent: str | None` on `list_turns`, all 3 interaction phases), Spec 3 (raiser self-ADDRESS validator gap)
