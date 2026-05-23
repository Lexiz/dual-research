---
spec: "0155"
date: 2026-05-22
version: 1.19.1
pr: "https://github.com/Lexiz/dual-research/pull/178"
---

# Handover — Spec 0155 — Fix lifecycle session-title stamping (v1.19.1)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#178](https://github.com/Lexiz/dual-research/pull/178)
- **Merge commit:** `257b866`
- **Cycle time:** ~8 minutes (started 13:13:22Z, deployed 13:21:17Z)

## What landed

### Host-side (NOT in the PR — lives under `~/.claude/hooks/` and `~/.claude/skills/`)

The actual fix is host-side. The PR carries the regression test + version bump.

- **`~/.claude/hooks/session_metadata.py`** (new) — shared module. Pulled `find_meta`, `build_title`, `write_with_retry`, `load_cache` / `save_cache`, `load_locked`, `log`, and the `DESKTOP_DIR` / `PREFIX_CACHE` / `LOCKED_PREFIXES` / `LOG` constants out of `auto-prefix-session.py`. One source of truth so `auto-prefix-session.py` and `stamp-session-title.py` can't drift on metadata-file resolution / atomic-write semantics. The hook's RETRY_ATTEMPTS=4 and RETRY_WAIT_SEC=2 are preserved exactly.
- **`~/.claude/hooks/stamp-session-title.py`** (new) — the helper the lifecycle skills now call. CLI surface:

  ```bash
  ~/.claude/hooks/stamp-session-title.py \
      --prefix-key "DR · 0155 · O" \
      --body "fix-session-title-stamping" \
      --session-id "$CLAUDE_SESSION_ID"
  ```

  Resolution order for the session id: `--session-id` arg → `$CLAUDE_SESSION_ID` / `$CCD_SESSION_ID` env vars → most-recently-modified `local_*.json` under the desktop session dir (with a stderr warning — racey if multiple CCD sessions are active). Exit codes: 0 success, 1 no metadata file found, 2 write-after-retries failure. `--desktop-dir` and `--cache-path` overrides for testing.
- **`~/.claude/hooks/auto-prefix-session.py`** — refactored to import from `session_metadata`. Behavior preserved: constants and function bodies relocated verbatim, no semantic change. The classification logic (`classify_rules`, `classify_llm`, `count_user_turns`, the locked-prefix override, the cache fast-path) stays in the hook.
- **Five lifecycle skills updated** to call `stamp-session-title.py` directly at their stamping steps:
  - `~/.claude/skills/spec-draft/SKILL.md` step 5 — `[DR · draft-NNN · O]`.
  - `~/.claude/skills/spec-queue/SKILL.md` step 8 — `[DR · NNNN · O]`.
  - `~/.claude/skills/spec-promote/SKILL.md` step 9 — `[DR · NNNN · O]`.
  - `~/.claude/skills/dev-next/SKILL.md` step 13 — `[DR · queue · NNNN in flight · O]`; step 25 — `[DR · queue · idle · O]`.
  - `~/.claude/skills/dev-queue-run/SKILL.md` step 5 — `[DR · queue · drain · O]`; queue-empty stop — `[DR · queue · idle · O]`.

### In-repo (this PR)

- `tests/hooks/__init__.py` + `tests/hooks/test_stamp_session_title.py` — regression test. Four cases: title-write + cache-update; second-invocation replaces (no duplicates); missing session exits 1; `build_title` enforces 60-char cap. Skips on CI where the host helper isn't installed.
- `pyproject.toml`, `src/dual_research/__init__.py` → **1.19.1** (PATCH, bug type).
- `CHANGELOG.md` `## [1.19.1] — 2026-05-22` section under Fixed + Added.

## Tests

`uv run pytest tests/ -q` — **1478 passed** (1474 prior + 4 new). End-to-end smoke against the installed helper passes locally.

## Deploy notes

Clean rolling deploy. Both machines on `deployment-01KS7SXSXVF*` running v1.19.1. Smoke: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.19.1","backend":"supabase"}`.

## Live-stamping verification still owed

Real-world confirmation will arrive as the lifecycle skills get used in fresh sessions:

- **Next `/spec-draft` invocation** should produce `[DR · draft-NNN · O] <slug>` in the Claude Desktop sidebar.
- **Next `/spec-queue` and `/spec-promote` invocations** should produce `[DR · NNNN · O] <slug>`.
- **Next `/dev-next` invocation** should set `[DR · queue · NNNN in flight · O]` mid-cycle and return to `[DR · queue · idle · O]` after the deploy commit. The current session (this one) won't pick up the title because the in-flight stamp didn't fire — the stamp now happens at step 13 going forward. **Backfilling existing un-stamped sessions is explicitly out of scope per spec 0155 §6**; the user can stamp manually with the helper if they want a specific session retitled.
- **Cache file `~/.claude/hooks/session-prefixes.json`** will accumulate lifecycle entries (full strings like `"DR · 0155 · O"`) alongside legacy short codes (`"DR-X"`, `"CK-O"`). The auto-prefix hook's fast-path at `auto-prefix-session.py:417-423` handles both via its two regex matches — no migration needed.

## Queue at handoff

- **0156 is queued** ("dashboard live-ness — cycle-started anchor, auto-refresh, live ticker, deploy-pages cleanup"). Was committed in a parallel author session while 0155 was in flight; merged into `main` alongside the 0155 PR.
- Per `feedback_pause_between_specs`: this cycle stops here. Next `/dev-next` is on the user (or `/dev-queue-run` to drain 0156 plus anything else queued).

## File map

```
# In-repo (this PR)
tests/hooks/__init__.py                                  # new
tests/hooks/test_stamp_session_title.py                  # new — 4 cases
CHANGELOG.md                                             # [1.19.1] section
pyproject.toml, src/dual_research/__init__.py            # 1.19.1
specs/0155-fix-session-title-stamping.md                 # status: deployed
dashboard/events/0155.jsonl                              # full event stream
handoffs/2026-05-22-spec-0155-...md                      # this file

# Host-side (not in repo)
~/.claude/hooks/session_metadata.py                      # new
~/.claude/hooks/stamp-session-title.py                   # new (+x)
~/.claude/hooks/auto-prefix-session.py                   # refactored to import shared
~/.claude/skills/spec-draft/SKILL.md                     # step 5 stamp call
~/.claude/skills/spec-queue/SKILL.md                     # step 8 stamp call
~/.claude/skills/spec-promote/SKILL.md                   # step 9 stamp call
~/.claude/skills/dev-next/SKILL.md                       # step 13 + step 25 stamp calls
~/.claude/skills/dev-queue-run/SKILL.md                  # step 5 + stop stamp calls
```
