---
kind: draft
draft_id: "008"
slug: spec-0257-live-acceptance-rerun
title: "Spec 0257 §6.3 live acceptance re-run — backend-language-choice, scored via /dr-run-assess"
status: draft
created: 2026-05-30
source_session: auto-captured-from-spec-0257-deferrals
parent_spec: "0257"
disposition: defer
disposition_reason: "Operational verification (a manual E2E run that must launch from a plain Terminal.app session per spec 0243) with no code or spec deliverable, so it is recorded but cannot run from a Claude Code surface."
type: test
version_bump: patch
gating: none
---

# Draft 008 — Spec 0257 §6.3 live acceptance re-run (deferred operational verification)

> **Parent:** [spec 0257](../0257-phase2-role-aware-standing-items-addressee-obligation.md) §6.3 (live acceptance evidence).
> **Source:** [spec 0257 handoff](../../handoffs/2026-05-30-spec-0257-phase2-role-aware-standing-items-addressee-obligation.md) "Deferred during implementation" §2.
> **Nature:** operational verification — a manual E2E run, NOT a code change or a queueable dev spec. Captured here as a standing reminder so the §6.3 evidence is not silently dropped.

## Context

Spec 0257 (role-aware standing-items surface, shipped v1.66.0, PR #297, merge `e6965d0`) made the phase-2/phase-4 standing-items surface role-aware so the addressee MUST `### ADDRESS` and the raiser stops self-addressing / resolving-from-open. Its §6.3 acceptance criterion ([`specs/0257-…:107`](../0257-phase2-role-aware-standing-items-addressee-obligation.md)) calls for a **real `backend-language-choice` re-run, scored via `/dr-run-assess`**, reporting:

- phase 2 `phase_converged via_genuine_resolution` (NOT `via_ghost_cap` / `via_artifact_promotion`), and
- **zero** `raiser_self_address`, `resolve_from_non_addressed`, and `agreed_with_open_addressed_items`,
- with the PR description carrying the run ID, the phase-2 tally, AND the **separate** phase-4 tally (so the phase-4 half is observed, not assumed).

This was **not executed in the 0257 implementation cycle.** Per the handoff §2 and CLAUDE.md / [spec 0243](../0243-operational-guard-refuse-running-inside-claude-code.md), E2E runs must launch from a **plain Terminal.app session** — the CLI guard refuses to start inside any Claude Code surface (it would be silently reaped mid-run, the H4 failure mode). So the re-run is a deliberate manual launch, not something a Claude Code agent can fire.

Until this lands, the phase-2 behavioural improvement is verified **deterministically** by 0257 §6.2 (the replay harness at [`tests/test_spec_0257_role_aware_standing_items.py`](../../tests/test_spec_0257_role_aware_standing_items.py) — rendered surface + violation-path against vendored run `20260530-175809`), but it is **not yet confirmed on live LLM behaviour**.

## What to run (manual, from plain Terminal.app)

Canonical invocation (CLAUDE.md "Canonical invocation"):

```bash
cd /Users/alexlisitzky/ClaudeCode/dual-research-workspace/dual-research && \
eval "$(grep -hE '^export (ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_(URL|ANON_KEY|SERVICE_ROLE_KEY))=' ~/.zshenv ~/.zshrc 2>/dev/null)" && \
caffeinate -i uv run dual-research \
  --notion "<backend-language-choice brief URL>" --models prod --push-while-running --name spec-0257-acceptance \
  2>&1 | tee /tmp/dr-run-spec-0257-acceptance.log
```

Then score the completed run with `/dr-run-assess` and record, in a comment on PR #297 (or a follow-up note):

- the run ID,
- phase-2 convergence mode (target `via_genuine_resolution`),
- the phase-2 tally of `raiser_self_address` / `resolve_from_non_addressed` / `agreed_with_open_addressed_items` (target zero on all three),
- the **separate** phase-4 `raiser_self_address` tally.

## Pass / fail and follow-up routing

- **Phase 2 zero + genuine resolution** → 0257's behavioural deliverable is confirmed live; close this draft (archive).
- **Phase 2 still non-zero** → the prompt fix underperformed; per 0257 §5 the next lever is early-deadlock-abort + further prompt/ID tightening — **NOT** auto-ADDRESS (permanently rejected, spec 0255 §5). Open the corresponding dev spec.
- **Phase 4 `raiser_self_address` non-zero** → per 0257 §2.2 this is the expected-possible item-ownership / ID-mapping residual in the drafter path, carved to `0257.2` (a separate decimal child) — it is explicitly NOT a 0257 regression.

## Unresolved questions

These are why this is a draft reminder rather than a queued dev spec:

1. **Not a code/spec deliverable.** There is nothing to implement or CI-gate — a live LLM re-run is non-deterministic and cannot gate CI (0257 §7 risk; the 0231→0238 trap). A dev spec would have no falsifiable, CI-runnable test plan, so it would fail the dev-spec validator. The correct artifact is this reminder.
2. **Cannot run from this surface.** The run must launch from plain Terminal.app (spec 0243); a Claude Code agent cannot fire it. Disposition is therefore `defer` until a human runs it.
3. **Which `backend-language-choice` brief URL is canonical?** The exact Notion brief URL to pass to `--notion` is not recorded in the 0257 handoff — confirm against the anchor run before launching.
4. **Where does the evidence land?** PR #297 is already merged; decide whether the §6.3 evidence attaches as a PR comment, a new handoff note, or a `runs/`-referencing follow-up before running.
