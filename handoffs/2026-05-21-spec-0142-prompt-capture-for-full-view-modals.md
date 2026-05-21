# Handover — Spec 0142 — Prompt capture for full-view modals (v1.9.3)

- **Date:** 2026-05-21
- **PR:** [Lexiz/dual-research#164](https://github.com/Lexiz/dual-research/pull/164) (merged, squash, branch deleted)
- **Spec:** [specs/0142-prompt-capture-for-full-view-modals.md](../specs/0142-prompt-capture-for-full-view-modals.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice`
- **Backlog row fixed:** B05 (Initial Brief full-view shows empty prompts)
- **Version:** `1.9.2 → 1.9.3` (PATCH — bug fix only; no schema changes)

## What landed

Two surgical persistence-side fixes close B05. The hosted UI's Initial Brief full-view modal (`turnKey='input'` on the Phase 0 timeline row) hydrates from a real recorded row instead of the spec-0085 synthesis fallback that stamps `system_source: "agent-default"`. Phase-0 per-round input bundles now also survive on disk independently, matching the spec-0135 round-keying already in `_on_turn_ended`.

### Edit 1 — Persist `inputs/input.json` at session setup

[`src/dual_research/orchestrator/run.py`](../src/dual_research/orchestrator/run.py) — new private helper `_persist_initial_brief_bundle(session_root, brief_text)` called once after `brief.md` is read at the top of `run_session`. The helper mirrors `aggregator.build_phase0_input_bundle()` (same 8-key `pieces` shape via `preflight_input_bundle(brief=brief_text, agent_name="<both>")`, same `agent="shared"` / `phase="phase0"` / `label="phase0-input"` envelope) but stamps `system_source: "recorded"` instead of `"agent-default"`. Idempotent: if the file already exists (resumed run) the helper returns without rewriting. The atomic-write via `write_atomic` reuses the existing `state.py` helper; no new file utilities. The file is then picked up by the existing `_iter_file_rows` rglob and pushed to Supabase like every other input bundle.

### Edit 2 — Round-key Phase-0 turn-keys

[`src/dual_research/orchestrator/_call.py::_derive_turn_key`](../src/dual_research/orchestrator/_call.py) and the two matching sites in [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) (`_on_turn_inputs` and `_on_turn_searches`) widened the round-key gate from `phase ∈ {2, 4}` to `phase ∈ {0, 2, 4}`. Pre-spec, four Phase-0 rounds collided on `inputs/phase0_<agent>.json` and only the final round's bundle survived; the live-data timeline's `phase0_round{1..4}_<agent>` cards all pointed at the same file. Post-spec, each Phase-0 round writes to `inputs/phase0_round{N}_<agent>.json` and the timeline cards land on real per-round bundles. Legacy single-shot Phase-0 transcripts whose labels carry no `-r{N}-` segment continue to map to `phase0_<agent>` (the `idx > 0` clause is unchanged), so pre-0114 fixtures and older runs keep working. This brings the input / search persistence paths in line with the spec-0135 round-keying that `_on_turn_ended` already performed.

### Edit 3 — Modal hydration (no code change)

Both server-side handlers ([`server.py::_read_input_bundle_fs`](../src/dual_research/ui/server.py) and [`_read_input_bundle_supabase`](../src/dual_research/ui/server.py)) already preferred a persisted bundle over the synth fallback for `"input"` and for round-keyed keys; they were starved for backend data. The JSX (`InputBriefModal` opens with `turnKey={item.turnKey || 'input'}`, the timeline stamps `turnKey: 'input'` on the brief card, per-round Phase-0 cards already used `phase0_round{R}_<agent>` keys) was also already correct. No frontend changes shipped in this patch.

The spec-0085 synth fallback is intentionally retained for runs that pre-date this patch (see Open questions and Backfill plan below). The user's prose summary at step 4 said "remove the synth-path fallback," but the spec §6 / §Risks explicitly preserves it as the documented "older run" caveat path. Following "Follow §5 literally," the spec is authoritative — synth stays.

## Files touched

- `src/dual_research/orchestrator/run.py` — added `_persist_initial_brief_bundle` helper + invocation at session setup right after the brief is read.
- `src/dual_research/orchestrator/_call.py` — Phase 0 added to the round-key gate in `_derive_turn_key`.
- `src/dual_research/ui/aggregator.py` — Phase 0 added to the round-key gate in `_on_turn_inputs` (line 752) and `_on_turn_searches` (line 817) to mirror.
- `tests/orchestrator/test_session_setup.py` — new file; 3 cases on the persistence helper (writes input.json with `system_source="recorded"`, idempotent on re-entry, creates inputs/ subdir).
- `tests/orchestrator/test_call.py` — new file; 7 cases on `_derive_turn_key` Phase-0 round-keying (rounds 1/2/3 round-keyed, openai → gpt alias, no-round label keeps legacy key, repair suffix preserved, Phase 1 still single-shot, Phase 2 regression-pin).
- `tests/ui/test_aggregator_input_bundles.py` — added `test_phase0_round_keyed_inputs_survive_per_round` (two events at `phase0-r1-claude` / `phase0-r2-claude` produce two distinct files; pre-fix flat-key path absent).
- `tests/ui/test_server_input_bundles.py` — added `test_persisted_input_json_overrides_synth_fallback` (persisted `inputs/input.json` returned over the synth path with `system_source="recorded"`).
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.9.2 → 1.9.3`.
- `CHANGELOG.md` — `[1.9.3]` entry.

## Schema / env / token changes

None. `inputs/input.json` is a new file that slots into the existing `inputs/<key>.json` shape (per spec 0033). No DB migration, no env var, no token, no cache-bust.

## Tests

```
1257 passed in 9.89s
```

Up from 1245 (Spec 0141 baseline) — **+12 new tests**:

- 3 × persistence-helper cases (writes, idempotent, mkdir)
- 7 × `_derive_turn_key` cases (Phase 0 rounds 1/2/3, alias, no-round, repair, Phase 1, Phase 2 regression-pin)
- 1 × aggregator round-keyed-survives test (two Phase-0 round events produce two files)
- 1 × server integration test (persisted bundle overrides synth)

## Deploy

```
fly deploy
…
✖ Unrecoverable error: timeout reached waiting for health checks (fly machines.dev API timed out mid-rolling-deploy)
```

Same fly-side flake the spec 0141 handover documented: the machines.dev API stalls during health-check polling, leaving one machine in `stopped` state. Resolved by `fly machine start d8d04d3fe402d8` and re-running `fly deploy`. Both machines now `started` + 1/1 health passing on version 185.

Live: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.9.3","backend":"supabase"}`.

### Smoke

- **Local persistence smoke** — re-derived `inputs/input.json` on disk for the anchor run via `_persist_initial_brief_bundle`. `system_source="recorded"`, `pieces.brief` round-trips the 18 377-char anchor brief verbatim, `pieces.system` is 4 914 chars (matches the spec's description of the system-prompt size).
- **Push smoke** — `uv run dual-research --push runs/20260521-010637-dvs-backend-language-choice` → `events=275  files=105  duration=42.2s`. Supabase `session_files` count for `path=like.inputs%` went from **0 → 34** rows (33 historical bundles + 1 new `inputs/input.json`, 24 155 bytes). Direct Supabase read of `inputs/input.json` content confirms `system_source: "recorded"` round-tripped to the hosted store.
- **Hosted UI smoke** — `curl https://dual-research-alex.fly.dev/api/runs/<id>/inputs/input` returns HTTP 401 (`missing_token`); the endpoint is auth-gated and I don't have a session token. Data-layer correctness has been verified two independent ways (FS-mode integration test + direct Supabase read), and the JSX path is unchanged from current `main` — the UI is deterministic given the recorded row. The visible-in-browser smoke is left as a user-side check.

## Open questions resolved

§9: chose the **placeholder variant** for `pieces.system` (current `preflight_input_bundle` behaviour with `_placeholder("brief")` substituted in the system body). Two reasons: (a) it matches what the agent actually saw at call time — system was cached with the brief inlined via prompt caching — and (b) it stays consistent with the per-turn bundles already on disk. The literal-brief alternative would have created a `pieces.system` that contains the entire brief verbatim AND a separate `pieces.brief` that contains the same content, which is redundant and inconsistent with how the per-turn bundles render.

## Backfill plan for historic runs

**Deferred to a follow-up.** Spec §6 explicitly keeps backfill out of scope. The anchor run got an opportunistic re-push as part of this spec's smoke (so B05's specific repro case is now fixed live, not just for future runs); other historic runs continue hydrating via the synth path with the `system_source: "agent-default"` caveat the UI already renders.

A backfill is feasible if we want to retire the synth path: for every run with `brief.md` on disk and no `inputs/input.json`, run `_persist_initial_brief_bundle` against the on-disk dir and push. Estimated scope: a one-shot script reading `runs/*/brief.md` and pushing per-run. Surfacing for a separate decision rather than bundling in this PR; the synth fallback is functioning correctly as the bridge for now.

## Known follow-ups

- **Push-CLI gap on `inputs/*.json`.** The spec's §6 noted that the anchor run had 33 inputs files on disk but 0 rows in Supabase. After the manual `--push` in this spec's smoke step, all 33 + the new `input.json` landed (count = 34). That suggests the original gap was likely a push-while-running timing issue (the push CLI was launched against a running session and the inputs files were either incomplete or filtered out by some other mechanism), not a `_iter_file_rows` defect. No further investigation in this spec; if a future run shows the same gap, file a follow-up.
- **`live-data.jsx` legacy preflight cards** still use `turnKey: 'phase0_claude'` / `'phase0_gpt'` (lines 567, 575) for the legacy single-shot Phase 0 shape. Those keys remain correct under the new gate because the matching labels carry no `-r{N}-` segment, so the no-round branch fires. No action; documented for completeness.
- **Spec 0145 downstream.** The canonical prompt-piece registry now has the non-empty persistence path it depends on. 0145's rename pass (`system → system_prompt`, `brief → user_prompt`, etc.) plus per-piece metadata can land cleanly on top of this PR. The 8-key `pieces` dict shape is preserved; 0145 is a rename, not a restructure.
- **Backfill follow-up.** As above — script to retire the synth path for historic runs by re-deriving `inputs/input.json` from `brief.md` and pushing. Separable.
- **Hosted UI visual smoke.** The `/api/runs/<id>/inputs/input` endpoint is auth-gated; user-side check confirms the Initial Brief modal renders the recorded brief instead of the "agent default" caveat. Should be straightforward given the data-layer verification above.
