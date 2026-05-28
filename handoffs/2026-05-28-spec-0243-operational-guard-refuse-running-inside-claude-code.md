---
spec: "0243"
date: 2026-05-28
version: 1.57.0
pr: https://github.com/Lexiz/dual-research/pull/278
---

# Spec 0243 — Operational guard: dual-research CLI refuses to run inside Claude Code

## What landed

Four layers ship together in one PR, closing the H4 silent-kill surface that killed five consecutive Claude-Code-hosted runs (`20260527-200213`, `20260528-000411`, `20260528-061323`, `20260528-073509`, `20260528-082137`) in phase 2–4 with no Python exception, no signal, no jetsam log. The first plain-Terminal.app run (`20260528-094743`) completed cleanly ($8.66, 39 KB `final.md`, `metrics.json.ended_at` populated, all gating invariants green). Root cause is host-environmental, not in dual-research code: Claude Code's background-task manager terminates long-running children at parent-session lifecycle events (idle timeout, suspend, session close), and dual-research's runtime profile (20–30 min, mostly idle-await on streaming network calls) is exactly the shape that gets reaped.

**Layer 1 — CLI guard at [`src/dual_research/cli.py`](src/dual_research/cli.py).** New helpers `_running_inside_claude_code()` and `_maybe_refuse_claude_code_host()` plus the canonical refusal message constant `_CLAUDE_CODE_REFUSAL_MESSAGE`. Detection widens to ANY `CLAUDECODE` truthy value OR any `CLAUDE_CODE_*` prefixed env var — Cowork sign-off's load-bearing case is that the Cowork sandbox sets `CLAUDE_CODE_HOST_*` without `CLAUDECODE`, so a guard that only checked `CLAUDECODE` would false-negative in sandbox-mode invocations. The guard is wired immediately after `parser.parse_args(argv)` and is conditional on `not args.push` — the read-only Supabase upload path (`--push`) is exempt because it never fires an LLM call, while the LLM-firing paths (default `--prompt`/`--brief`/`--notion` firing, plus `--resume`) all hit the guard before any ingest, cred load, or session-dir creation. Stderr prints the canonical Terminal.app command with `cd` to the post-restructure repo path + `eval` of `~/.zshrc` keys + `caffeinate -i uv run dual-research`; `sys.exit(2)`. Read-only subcommands (`serve`, `verify`, `validate-run`, `recompute-costs`, `reconcile-costs`) are dispatched at the top of `main()` before the parser ever runs and are not guarded.

**Layer 2 — CLAUDE.md "Operational" section.** New top-level section positioned after "Tests" documents the canonical Terminal.app invocation (with `caffeinate -i` to prevent idle sleep and `tee` for post-mortem evidence) and the `DUAL_RESEARCH_ALLOW_CLAUDE_P=1` escape's intended use (CI / Cowork sandbox), with an explicit "Not intended" anti-pattern call-out for "I'm in a hurry, just run it" workflows — the silent-kill behaviour returns the moment the escape is set. Links to spec 0243 and Cowork's `2026-05-28-h4-plain-terminal-next.md` brief.

**Layer 3 — `/dual-research-run` skill amendment.** Replaces the "Firing the run" section with a refuse-and-redirect pattern: the skill emits the canonical Terminal.app command for the user to paste into a plain Terminal.app window rather than firing the run as a Claude Code background task. Post-run reporting (URLs, completion check, failure modes) is unchanged per spec §2.3.

**Layer 4 — `--help` epilog.** `dual-research --help` now lists `DUAL_RESEARCH_ALLOW_CLAUDE_P=1` under an `ENVIRONMENT VARIABLES` section so the escape is discoverable from the tool itself, not just from the spec.

**Test hermeticity (spec §6 + observed regression during impl).** Three pre-existing tests at `tests/orchestrator/test_resume.py` (`test_resume_rejects_missing_path`, `test_resume_rejects_dir_without_state`, `test_resume_mutually_exclusive_with_prompt`) started failing because they invoke `cli.main(...)` directly and the dev shell exports `CLAUDECODE=1` plus nine `CLAUDE_CODE_*` env vars. The structurally correct fix lands in [`tests/conftest.py`](tests/conftest.py): a new autouse `_strip_claude_code_env` fixture that strips `CLAUDECODE` / `CLAUDE_CODE_*` / `DUAL_RESEARCH_ALLOW_CLAUDE_P` before every test, making the entire suite hermetic against host env state. Spec-0243 tests re-inject via `monkeypatch.setenv` inside the test body, which still wins.

## Files touched

- [`src/dual_research/cli.py`](src/dual_research/cli.py) — `import os`; `_running_inside_claude_code()`; `_maybe_refuse_claude_code_host()`; `_CLAUDE_CODE_REFUSAL_MESSAGE` constant; parser `epilog` extended with `ENVIRONMENT VARIABLES` section; guard call after `parser.parse_args(argv)` conditional on `not args.push`.
- [`tests/test_spec_0243_claude_code_guard.py`](tests/test_spec_0243_claude_code_guard.py) — new file: 20 tests across detection (4), refusal helper (6 — including the escape-var typo guard), `main()` integration (7 — `--prompt`, `--resume`, `--push` exempt, four read-only subcommand exemptions), `--help` epilog presence (1), and source-pattern locks on CLAUDE.md + the amended skill (2).
- [`tests/conftest.py`](tests/conftest.py) — autouse `_strip_claude_code_env` fixture; docstring updated to call out both the spec-0082 hidden-runs filter and the new spec-0243 env stripper.
- [`CLAUDE.md`](CLAUDE.md) — new `## Operational — running dual-research E2E` section after "Tests".
- [`.claude/skills/dual-research-run/SKILL.md`](.claude/skills/dual-research-run/SKILL.md) — "Firing the run" section replaced with the spec-0243 refuse-and-redirect pattern; duplicate Reporting URLs subsection removed.
- [`CHANGELOG.md`](CHANGELOG.md), [`pyproject.toml`](pyproject.toml), [`src/dual_research/__init__.py`](src/dual_research/__init__.py), [`src/dual_research/ui/static/version-notes.json`](src/dual_research/ui/static/version-notes.json), `uv.lock` — MINOR bump 1.56.0 → 1.57.0; in-app changelog sidecar regenerated via `scripts/build_version_notes.py`.

`uv run pytest tests/ -q` → 2283 passed (20 new + 2263 pre-existing). Deploy `success` on GH Actions run [26572316830](https://github.com/Lexiz/dual-research/actions/runs/26572316830). `/api/health` reports `version: 1.57.0`.

**Empirical Claude Code env-var verification (spec §6).** Run from this Claude Code session:

```
CLAUDECODE=1
CLAUDE_AGENT_SDK_VERSION=0.3.149
CLAUDE_CODE_DISABLE_CRON=
CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES=false
CLAUDE_CODE_ENABLE_ASK_USER_QUESTION_TOOL=true
CLAUDE_CODE_ENTRYPOINT=claude-desktop
CLAUDE_CODE_EXECPATH=…/claude
CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH=1
CLAUDE_CODE_SDK_HAS_OAUTH_REFRESH=1
CLAUDE_CODE_SESSION_ID=6d10a14c-890a-4ec2-8021-6f7254b9443a
CLAUDE_EFFORT=xhigh
```

`CLAUDECODE=1` plus nine `CLAUDE_CODE_*` env vars are set. The guard's detection rule (`CLAUDECODE` OR any `CLAUDE_CODE_*` prefix) fires correctly here.

## Notes for follow-ups

- **Guard location is `_maybe_refuse_claude_code_host()` in `main()`, not in `_run_orchestrator()`.** Trade-off: putting the guard at `main()` entry (right after `parser.parse_args`) means the guard fails fast before ingest (Notion / brief load) and before cred load. Putting it in `_run_orchestrator` would have been a single chokepoint covering both the default firing path and `_run_resume`, but at the cost of running ingest first. The spec text said "at the top of every E2E-firing subcommand's handler" — `main()` IS the handler for the default firing path; `_run_resume` is invoked from `main()` so the same guard call also covers it. The `not args.push` condition is the surgical exemption for the only argparse path that doesn't fire an LLM call.
- **Soft escape-var typo guard (`test_guard_escape_var_must_be_exactly_1`).** The spec literal at §2.1 reads `if os.environ.get("DUAL_RESEARCH_ALLOW_CLAUDE_P") == "1"`. A user who tries `DUAL_RESEARCH_ALLOW_CLAUDE_P=true` (sensible-looking but wrong) gets the refusal — the escape must be exactly `"1"`. The test locks this against an accidental future relaxation that would silently accept any truthy value and re-open the H4 surface for anyone with a non-canonical escape var set.
- **`--push` exemption is the only argparse-level carve-out.** If a future spec adds a new operational mode that fires an LLM call (e.g. a hypothetical `--re-converge SESSION_DIR` mode), the `if not args.push:` predicate would mistakenly exempt it only if the new mode aliases `args.push`. New LLM-firing modes need to either keep `args.push` falsy (the common case — they'd add their own arg) or the predicate would need to widen. The test surface at `tests/test_spec_0243_claude_code_guard.py` is the place to lock the new mode's guarded behaviour.
- **Detection rule is broad on purpose.** Spec §7 risks called out a false-positive concern on a non-Claude environment that happens to set a `CLAUDE_CODE_*` env var (extremely unlikely — Anthropic's env-var namespace is project-specific). The escape var resolves it in seconds. The false-positive worry is much smaller than the false-negative cost (returning the silent-kill behaviour). If a real false-positive surfaces in a CI environment, set `DUAL_RESEARCH_ALLOW_CLAUDE_P=1` in that CI's env config.
- **CLAUDE.md path uses the post-restructure root.** All `cd` references in the guard's stderr message, the CLAUDE.md Operational section, and the amended skill use `/Users/alexlisitzky/ClaudeCode/dual-research-workspace/dual-research/` (the post-restructure path, verified working since 2026-05-25/26 per the project memory). If the user ever moves the repo again, three places need updating — the constant in `cli.py`, the CLAUDE.md canonical-invocation block, and the skill's fire-command block.
- **Spec 0212 buffered-events doctrine held cleanly.** `deploy_started` / `deployed` / `deploy_health_check_ok` were emitted local-only between the merge (step 19) and the atomic push at step 23; no `--push-to-main` calls landed in the post-merge window, so the spec 0211.3 cancellation pivot did not need to fire.
