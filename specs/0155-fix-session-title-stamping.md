---
kind: dev
spec: "0155"
slug: fix-session-title-stamping
title: "Fix: lifecycle skills' session-title stamping is unimplemented"
type: bug
label: bug
version_bump: PATCH
target_version: 1.19.1
status: merged
queue_position: 1
depends_on: ["0154"]
complexity: S
created: 2026-05-22
queued_at: 2026-05-22T13:02:02Z
started_at: "2026-05-22T13:13:22Z"
merged_at: "2026-05-22T13:19:18Z"
deployed_at: ""
pr: "https://github.com/Lexiz/dual-research/pull/178"
handover: ""
failure_step: ""
source_session: orchestrator-hardening-2026-05-22
promoted_from_draft: ""
---

# Spec 0155 — Fix: lifecycle skills' session-title stamping is unimplemented

> **Type:** bug  |  **Severity:** P2  |  **Affects:** spec lifecycle workflow (since spec 0152)
> **Bump:** PATCH — bug fix
> **Evidence:** spec 0154's session was queued, never got stamped `[DR · 0154 · O]`. Auto-prefix hook fell back to bare `[DR]`. Skill instructions at `~/.claude/skills/spec-queue/SKILL.md:101-103`, `spec-draft/SKILL.md:78-82`, `spec-promote/SKILL.md:125-127`, `dev-next/SKILL.md:13, 73, 117` describe the desired title format but hand-wave the write mechanism.

---

## 1. Reproduction

**Environment:** any Claude Code session opened in `/Users/alexlisitzky/dual-research-author/` or `/Users/alexlisitzky/dual-research/`, after spec 0152 landed.

**Steps:**

1. Open a fresh session in `~/dual-research-author/`.
2. Have a conversation that warrants a dev spec.
3. Invoke `/spec-queue`.
4. After the skill commits the spec, observe the session title in the Claude Desktop sidebar.

**Expected:** title is `[DR · NNNN · O] <slug>` per [`spec-queue/SKILL.md:101-103`](/Users/alexlisitzky/.claude/skills/spec-queue/SKILL.md).

**Actual:** title is `[DR]` (bare category, applied by the auto-prefix hook's rules classifier at [`auto-prefix-session.py:189-235`](/Users/alexlisitzky/.claude/hooks/auto-prefix-session.py)) or unprefixed if classification hasn't fired yet. The lifecycle context (`NNNN`, slug) never gets written.

**Live evidence:** spec 0154 was queued in this session at 12:38:45Z; through to 13:00Z, the session title remained `[DR]` (or unprefixed). I explicitly skipped Step 8 because the skill text only describes *what* to write but hand-waves *how* — "Implementation: write the new title into the active CCD session metadata file (the existing `~/.claude/hooks/auto-prefix-session.py` shows the path mechanics — adapt the same approach for one write)." That's "the agent should re-implement `find_meta` + `write_with_retry` at runtime," which doesn't happen reliably.

## 2. Root cause hypothesis

Four skill files describe lifecycle title stamping in their final steps but punt the implementation:

- [`spec-draft/SKILL.md:78-82`](/Users/alexlisitzky/.claude/skills/spec-draft/SKILL.md) — `[DR · draft-NNN · O] <slug>`
- [`spec-queue/SKILL.md:101-103`](/Users/alexlisitzky/.claude/skills/spec-queue/SKILL.md) — `[DR · NNNN · O] <slug>`
- [`spec-promote/SKILL.md:125-127`](/Users/alexlisitzky/.claude/skills/spec-promote/SKILL.md) — `[DR · NNNN · O] <slug>`
- [`dev-next/SKILL.md:13, 73, 117`](/Users/alexlisitzky/.claude/skills/dev-next/SKILL.md) — three stamps: `[DR · queue · NNNN in flight · O]` on start, returning to `[DR · queue · idle · O]` on finish.

Each instruction requires duplicating logic that already exists in [`auto-prefix-session.py:130-142`](/Users/alexlisitzky/.claude/hooks/auto-prefix-session.py) (`find_meta` — glob `~/Library/Application Support/Claude/claude-code-sessions/` for a metadata file matching the active `cliSessionId`) and [`:284-317`](/Users/alexlisitzky/.claude/hooks/auto-prefix-session.py) (`write_with_retry` — atomic write + reverify loop to defeat CCD's mid-flight overwrites). The skill-running LLM hand-implements this inconsistently, so most stamps don't happen.

Downstream effect: the cleanup script's lifecycle-aware short-circuit at [`cleanup-session-prefixes.py:535-552`](/Users/alexlisitzky/.claude/hooks/cleanup-session-prefixes.py) (which derives open/closed status from the DR spec frontmatter — no LLM call, no transcript read) only fires when the title is already in lifecycle format. Un-stamped sessions fall back to transcript-reading + LLM classification, slower and less accurate.

## 3. Fix

### 3.1 — New helper `~/.claude/hooks/stamp-session-title.py`

A small CLI that wraps `find_meta` + `write_with_retry` + cache update. Usage:

```bash
~/.claude/hooks/stamp-session-title.py \
  --prefix-key "DR · 0155 · O" \
  --body "fix-session-title-stamping" \
  --session-id "$CLAUDE_SESSION_ID"
```

Behavior:

- Resolve `--session-id` (if omitted: try `$CLAUDE_SESSION_ID` env var; if neither, fall back to the most-recently-modified `local_*.json` under `~/Library/Application Support/Claude/claude-code-sessions/` and emit a warning).
- Compose the title via `build_title(prefix_key, body)` — same 60-char cap logic as [`auto-prefix-session.py:272-281`](/Users/alexlisitzky/.claude/hooks/auto-prefix-session.py).
- Atomic write via temp + replace.
- Reverify loop (up to 4 attempts, 2s apart) to catch CCD overwrites — identical to [`auto-prefix-session.py:284-317`](/Users/alexlisitzky/.claude/hooks/auto-prefix-session.py).
- Update `~/.claude/hooks/session-prefixes.json` with `{session_id: prefix_key}` (the *full* lifecycle string, not just `"DR"`) so the auto-prefix hook's fast-path at [`auto-prefix-session.py:417-423`](/Users/alexlisitzky/.claude/hooks/auto-prefix-session.py) reapplies the lifecycle title on every subsequent event.

Exit codes: `0` on success, `1` on metadata-not-found, `2` on write-after-retries failure.

### 3.2 — Shared module `~/.claude/hooks/session_metadata.py`

Extract `DESKTOP_DIR`, `find_meta`, `build_title`, `write_with_retry`, `load_cache`, `save_cache` from `auto-prefix-session.py` into a shared module. Both `auto-prefix-session.py` and the new `stamp-session-title.py` import from it. Prevents helper-vs-hook divergence.

### 3.3 — Skill text updates

Replace the hand-wave in each skill's stamping step with a single bash call:

- `spec-draft/SKILL.md:78-82` — `~/.claude/hooks/stamp-session-title.py --prefix-key "DR · draft-NNN · O" --body "<slug>"`
- `spec-queue/SKILL.md:101-103` — same shape, `prefix-key "DR · NNNN · O"`.
- `spec-promote/SKILL.md:125-127` — same shape.
- `dev-next/SKILL.md:13` — `prefix-key "DR · queue · NNNN in flight · O"` (start), `:73` — same, `:117` — `prefix-key "DR · queue · idle · O"` (return to idle).
- New skill from spec 0154 `dev-queue-run/SKILL.md` — add stamps: `prefix-key "DR · queue · drain · O"` at greenlight, restore `"DR · queue · idle · O"` at queue-empty or halt.

Each call becomes one line. No more "adapt the same approach."

## 4. Regression-prevention test

A test that fails before the fix and passes after.

- [ ] Test: `tests/hooks/test_stamp_session_title.py` — set up a tmpdir mirroring CCD's metadata layout (one `local_<uuid>.json` containing `{"cliSessionId":"test-sid", "title":"untitled"}`), monkeypatch `DESKTOP_DIR` to point at it, invoke `stamp-session-title.py --prefix-key "DR · 0155 · O" --body "x" --session-id test-sid`, then assert (a) the metadata file's `title` field equals `[DR · 0155 · O] x`, (b) `~/.claude/hooks/session-prefixes.json` contains `{"test-sid": "DR · 0155 · O"}`, (c) a second invocation with `prefix-key "DR · 0155 · X"` updates both consistently (no duplicate cache entries). Before fix: no helper script exists, test cannot run → fail. After fix: passes.

## 5. Blast radius

- **Helper-vs-hook divergence risk.** Mitigated by §3.2 — both load `find_meta`/`write_with_retry` from the shared module. If hook logic changes, helper inherits.
- **Cache key co-existence.** `session-prefixes.json` already holds a mix of legacy short codes (`"DR-X"`, `"CK-O"`) and (post-this-fix) lifecycle full strings (`"DR · 0155 · O"`). Hook's fast-path at [`auto-prefix-session.py:394-403`](/Users/alexlisitzky/.claude/hooks/auto-prefix-session.py) already handles both via separate regex matches — no new conflict introduced. Verified by reading the current cache at `~/.claude/hooks/session-prefixes.json` which holds entries like `"DR-X"`, `"DR · 0152 · O"` side-by-side.
- **CCD restart still required after writes** (per the auto-prefix hook's existing behavior). The helper inherits this constraint — same as today.
- **Other tools reading the cache.** Only `cleanup-session-prefixes.py` reads it (`:482-488`); it already handles both formats via its `LIFECYCLE_PREFIX_RE` at `:92-94`. No update needed.

## 6. Out of scope

- **Hook auto-derivation of lifecycle context from cwd/branch** (the rejected Option 2 in this session's ideation). Skills know their own state transitions better than the hook can infer from filesystem alone — e.g. a `draft-NNN` session is on no branch at all, and a `queue · NNNN in flight` session needs to know which spec is `status: in_progress` right now.
- **Backfilling existing un-stamped sessions** (like spec 0154's). A one-off `stamp-session-title.py --session-id <0154-session-id> --prefix-key "DR · 0154 · O" --body "<slug>"` invocation can fix any specific session manually; no batch backfill in this spec.
- **Changing the hook's classification logic** (`classify_rules`, `classify_llm`). That path is for unprefixed sessions only; lifecycle-stamped sessions skip it entirely via the fast-path.
- **Removing `auto-prefix-session.py.bak`** in the hooks dir (housekeeping; unrelated).

## 7. Risks

- **`$CLAUDE_SESSION_ID` env var may not be exported by CCD.** If skills can't reliably get the session id, the helper falls back to "most-recently-modified metadata file" — usually correct in practice (the active session's file gets touched on every turn) but racey if two CCD sessions are active simultaneously. Mitigation: at minimum, log a clear warning when falling back to filesystem inference, and document the limitation in the helper's `--help`.
- **Skill writers may forget to call the helper on new lifecycle-tagged skills.** Mitigation: the post-0154 `CLAUDE.md` (or a new section in it) should call out "every lifecycle-tagged skill ends with a `stamp-session-title.py` call." Not enforced by tooling — convention only.
- **Refactor-into-shared-module bug risk** (§3.2). The hook is mature and battle-tested. Extracting `find_meta` + `write_with_retry` into a separate module risks subtle behavior changes (import path, log paths, cache file path). Mitigation: keep the shared module's constants identical to the hook's originals; add a smoke test that runs the hook end-to-end against a fixture metadata dir before merging.
