---
spec: "0228"
date: 2026-05-27
kind: post-deploy
version: 1.47.0
pr: https://github.com/Lexiz/dual-research/pull/267
---

# Spec 0228 — Emit `ProtocolViolation` on state-machine-invalid ops; flip verifier I4.4 to gating

## What landed

- **Six new emission sites in `apply_turn` at [`src/dual_research/orchestrator/deep_research.py`](src/dual_research/orchestrator/deep_research.py).** The pre-fix silent `continue`s after state-machine guards now emit a `ProtocolViolation`:
  - `resolve_wrong_raiser` — `ResolveBlock` where `ent.raiser != agent`.
  - `resolve_from_non_addressed` — `ResolveBlock` where `ent.current_state != ADDRESSED` (the dead-fixture smoking gun: four such drops on `runs/20260526-102321-backend-language-choice/phase2/round-02-claude.md:230/236/242/248`).
  - `withdraw_wrong_raiser` — `WithdrawBlock` where `ent.raiser != agent`.
  - `withdraw_terminal_state` — `WithdrawBlock` where `is_terminal(ent.current_state)`.
  - `acknowledge_terminal_state` — `AcknowledgeBlock` where `is_terminal(ent.current_state)`.
  - `address_already_addressed` — `AddressBlock` where `from_state == to_state == ADDRESSED` (the "ADDRESS on non-open" sibling rejection, previously documented as a silent "no-op").
- **Compound guard split.** The pre-fix `if ent is None or ent.raiser != agent: continue` on `ResolveBlock` and `WithdrawBlock` was split — `ent is None` stays silent (parser/validator concern per the spec 0228 §2.1 identification rule), `ent.raiser != agent` emits. Three regression tests pin the silent path so it can't drift.
- **`ProtocolViolation` payload extended** at [`src/dual_research/events/types.py:526-540`](src/dual_research/events/types.py:526). Three new optional fields with defaults: `op_kind` (`"resolve"` / `"address"` / `"acknowledge"` / `"withdraw"`), `expected_state` (comma-joined allowed states, or `""` if state-agnostic), `reason` (one-line human-readable). Defaults preserve every pre-0228 emit site and every serialised event.
- **Existing emit sites enriched.** `raiser_self_address` (spec 0216) and `terminal_state_re_address` (spec 0141) now populate the new fields so downstream consumers (verifier diff, UI chip, dashboard) see structured diagnostics across every violation code.
- **Verifier I4.4 severity promotion** at [`src/dual_research/contract/verifier.py:918-994`](src/dual_research/contract/verifier.py:918). `reporting` → `gating`. The turn-file ⇄ transcript-diff logic for ops present in turn files but absent from `item_transitioned` + `protocol_violation` events is unchanged; only the severity tightens. Docstring updated to cite spec 0228 as the activation point.
- **Anchor-run baselines regenerated** at `tests/fixtures/anchor-runs/{20260521-010637-dvs-backend-language-choice,20260525-135006-backend-language-choice,20260526-102321-backend-language-choice}/expected.json`. Severity-only flip for I4.4 (`reporting` → `gating`); verdict unchanged on all three (`fail` on all three — the frozen fixtures predate this spec's runtime emission, so the verifier's turn-file⇄transcript diff still reports the same op mismatches).
- **MINOR bump 1.46.2 → 1.47.0** in [`pyproject.toml:3`](pyproject.toml:3), [`src/dual_research/__init__.py:1`](src/dual_research/__init__.py:1), `uv.lock` refreshed. `CHANGELOG.md` entry under `## [1.47.0] — 2026-05-27` directly below `## [Unreleased]`. In-app changelog sidecar regenerated at [`src/dual_research/ui/static/version-notes.json`](src/dual_research/ui/static/version-notes.json) via `scripts/build_version_notes.py` (217 entries).

## Verification

- `uv run pytest tests/ -q` — **2113 passed in 27.29s** (+20 vs. pre-change 2093; no regressions).
- New tests at [`tests/orchestrator/test_spec_0228_protocol_violation_emission.py`](tests/orchestrator/test_spec_0228_protocol_violation_emission.py) — 16 cases: one per-site positive for each of the 6 new emission sites (each asserts `violation_code` + `op_kind` + `expected_state` + `reason` + `from_state` and that the ledger item's state is preserved); two carry-through tests for the pre-0228 `raiser_self_address` + `terminal_state_re_address` sites confirming the new fields populate; three "ent is None stays silent" tests pinning the identification-rule exclusion; one replay test that loads the dead-fixture `round-02-claude.md` verbatim, seeds the four items in `open`, and asserts exactly four `resolve_from_non_addressed` events fire against `D-plan-c-02` / `D-plan-c-04` / `D-plan-c-05` / `Q-plan-c-01` with `from_state="open"` + `expected_state="addressed"`.
- New tests at [`tests/test_spec_0228_verifier_i4_4_gating.py`](tests/test_spec_0228_verifier_i4_4_gating.py) — 4 cases: parametrised assertion that the live verifier reports `severity="gating"` on I4.4 across all three anchor-run fixtures, parametrised assertion that each fixture's frozen `expected.json` records `severity: "gating"`, the CLI standalone-mode gate (no `expected.json`) on the dead fixture asserting `rc == 1` with `[gating] I4.4` + the four item IDs in rendered output, and a regression test that the baseline-included CLI invocation continues to return `0`.
- Two over-strict pre-0228 tests in [`tests/orchestrator/test_deep_research.py`](tests/orchestrator/test_deep_research.py) (`test_addressed_to_addressed_no_op_emits_address_already_addressed_violation`, `test_anchor_run_double_close_scenario_now_blocked_at_orchestrator`) flipped from "no violation" to "exactly one ProtocolViolation with the expected code". One assertion in [`tests/ledger/test_replay_spec_0141.py`](tests/ledger/test_replay_spec_0141.py:115) widened to admit the six new codes alongside the previous two on the `raiser_self_address_replay` anchor run.
- GH Actions deploy.yml run [26480511379](https://github.com/Lexiz/dual-research/actions/runs/26480511379) — `success`.
- Live fly app at `https://dual-research-alex.fly.dev/` returns HTTP 200; `dual_research.__version__ == "1.47.0"`.

## Behavioural change scope

The ledger does not transition on any of the six new emission sites — the pre-fix drop semantics are preserved exactly. The only behavioural change is that the rejection is now logged as an event. Downstream consumers (verifier I4.4, UI `ViolationChip` at [`src/dual_research/ui/static/run-detail.jsx:1115`](src/dual_research/ui/static/run-detail.jsx:1115), dashboard event stream) automatically pick up the new codes without code changes — the UI renders the event JSON via `JSON.stringify`, the verifier's diff already accepted `protocol_violation` as a satisfying signal.

## Notes for the next cycle

- **Cowork synthesis action 6 (addressee-obligation invariant).** Spec 0228 §5 names this as the natural next spec — provisionally `0229-addressee-obligation-invariant`. Once it lands, I2.4 promotes from `reporting` to `gating` (same pattern as I4.4 in this spec). Not queued yet.
- **Verdict on the three anchor-run fixtures stays `fail`** for I4.4 because the frozen transcripts predate the runtime emission. The expected.json baselines now record `severity: "gating"` so the CLI baseline-match continues to return 0 (the baseline matches what the live verifier reports against the fixture today). This is by design — the fixtures are frozen historical evidence, not re-recorded.

## Deferred during implementation

(none — the spec body fully covered the implementation surface. The `address_already_addressed` site interpretation (initially documented as "Allow" in the pre-fix comment) was resolved against the spec §2.1 sibling enumeration "ADDRESS on non-`open`" — emit, preserving the no-transition drop semantics. No follow-ups identified.)

## Next in queue

`uv run python -c "from scripts.spec_lifecycle.pick_next_number import current_queue; q = current_queue('specs'); print(q[0][1] if q else 'EMPTY')"` to identify, or check the dashboard.
