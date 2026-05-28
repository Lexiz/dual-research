---
kind: dev
spec: "0243"
slug: operational-guard-refuse-running-inside-claude-code
title: "Operational guard: dual-research CLI refuses to run inside Claude Code (env-var detection + env-var escape + CLAUDE.md rule + skill amend)"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-28
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Four consecutive runs hosted as Claude Code background tasks died silently in phase 2-4 with no Python exception, no signal, no jetsam log — the hosting Claude Code session's background-task manager reaps long-running children at parent-session lifecycle events. The first plain-Terminal.app run (20260528-094743) completed cleanly ($8.66, 39KB final.md, clean shutdown, all gating invariants green). H4 confirmed by Cowork at cowork/briefs/2026-05-28-h4-plain-terminal-next.md. This spec routes the user around the H4 surface by making the CLI refuse-by-default in any Claude-Code-hosted invocation, with a documented env-var escape for power users."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0243 — Operational guard: refuse running inside Claude Code

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** MINOR — adds a new CLI-level contract ("the orchestrator refuses to run in a host environment known to reap it"), a CLAUDE.md operational rule, a `/dual-research-run` skill amendment, and a documented env-var escape. Operational contracts ARE the contract per CLAUDE.md "contract-changing specs are not bugs".
> **Evidence:** four dead Claude-Code-hosted runs (`20260527-200213`, `20260528-000411`, `20260528-061323`, `20260528-073509`, `20260528-082137`); first plain-Terminal.app run `20260528-094743` cleanly completes; Cowork sign-off `cowork/briefs/2026-05-28-h4-plain-terminal-next.md` + execution sign-off `cowork/briefs/2026-05-28-0243-0244-execution-signoff.md`.

---

## 1. Context

The dual-research orchestrator was repeatedly being killed mid-run for **days** with no Python-level exception, no signal log entry, no macOS jetsam record, no tombstone. Spec 0241's per-turn heartbeat instrumentation made this surface visible: heartbeats fire normally, then stop mid-cadence, then the process simply ceases to exist. The xpc-services-lost-connection signature at process-exit time pointed to graceful-ish termination, not a kernel-level kill. All internal failure hypotheses (parser exception, mid-stream stall, idle sleep, OOM/jetsam) were empirically ruled out across 4 runs.

The plain-Terminal.app diagnostic surfaced the actual cause: **the dual-research process was spawned as a Claude Code background task, and the hosting Claude Code session's background-task manager terminates long-running children at parent-session lifecycle events** (idle timeout, suspend, session close, etc.). Once the same command was fired directly from Terminal.app, the run completed end-to-end ($8.66, 39KB `final.md`, `metrics.ended_at` populated, all gating invariants green except the known Finding 3).

This is not a bug in dual-research code. It is a host-environment incompatibility: dual-research's runtime profile (20-30 min, mostly idle-await on streaming network calls) is exactly the shape Claude Code's background-task manager terminates. The fix is to route users to a host that does not impose that incompatibility — and to make the CLI refuse to start in the incompatible host so the failure mode does not silently re-occur.

## 2. Proposed change

Single PR. Four layers ship together.

### 2.1 — CLI guard in `src/dual_research/cli.py`

Add a check at the entry of every `dual-research run` (and any sibling subcommand that fires an E2E run — `dual-research resume` when 0242 ships, etc.):

```python
import os
import sys

def _running_inside_claude_code() -> bool:
    """Heuristic: process was spawned inside any Claude Code surface.

    Env-var presence varies across surfaces (interactive Claude Code,
    `claude -p` background mode, Cowork sandbox). Cowork's sign-off
    in cowork/briefs/2026-05-28-0243-0244-execution-signoff.md flags
    that interactive Code sets CLAUDE_CODE_ENTRYPOINT but Cowork's
    own sandbox sees CLAUDE_CODE_HOST_* without it. Widen the check:
    detect ANY CLAUDECODE flag or CLAUDE_CODE_* env var, not just one.
    """
    if os.environ.get("CLAUDECODE"):
        return True
    return any(k.startswith("CLAUDE_CODE_") for k in os.environ)

def _maybe_refuse_claude_code_host() -> None:
    """Refuse to run if inside Claude Code unless explicit env-var escape."""
    if not _running_inside_claude_code():
        return
    if os.environ.get("DUAL_RESEARCH_ALLOW_CLAUDE_P") == "1":
        return
    sys.stderr.write(
        "dual-research: refusing to run inside Claude Code.\n"
        "\n"
        "Claude Code's background-task manager terminates long-running\n"
        "children at parent-session lifecycle events (idle timeout,\n"
        "suspend, session close), reaping the dual-research process\n"
        "mid-run with no Python exception, no signal, no traceable\n"
        "termination. Four consecutive runs died this way; the first\n"
        "plain-Terminal.app run completed cleanly. See spec 0243 +\n"
        "cowork/briefs/2026-05-28-h4-plain-terminal-next.md for full\n"
        "evidence.\n"
        "\n"
        "Run instead from a plain Terminal.app session:\n"
        "\n"
        "  cd /Users/alexlisitzky/ClaudeCode/dual-research-workspace/dual-research && \\\n"
        "  eval \"$(grep -hE '^export (ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_(URL|ANON_KEY|SERVICE_ROLE_KEY))=' ~/.zshrc)\" && \\\n"
        "  caffeinate -i uv run dual-research \\\n"
        "    --notion '<url>' --models prod --push-while-running \\\n"
        "    --name <slug> 2>&1 | tee /tmp/dr-run-<slug>.log\n"
        "\n"
        "Override (NOT RECOMMENDED — kills will recur silently):\n"
        "  DUAL_RESEARCH_ALLOW_CLAUDE_P=1 dual-research run ...\n"
    )
    sys.exit(2)
```

Call `_maybe_refuse_claude_code_host()` at the top of every E2E-firing subcommand's handler. Verify command (`dual-research verify`), the dashboard helper subcommands (`serve`, etc.), and other read-only subcommands are NOT guarded — only commands that actually fire a multi-turn LLM run.

### 2.2 — CLAUDE.md "Operational" section

Add a new top-level section to [`CLAUDE.md`](CLAUDE.md), positioned after "Tests":

```markdown
## Operational — running dual-research E2E

Always invoke dual-research E2E runs from a **plain Terminal.app session**.
**Never** as a Claude Code background task (`claude -p` background mode
or any other Claude Code surface that spawns dual-research as a child
process).

Claude Code's background-task manager terminates long-running children at
parent-session lifecycle events (idle timeout, suspend, session close),
reaping the dual-research process mid-run with no Python exception, no
signal, no traceable termination. Evidence: four consecutive
Claude-Code-hosted runs died silently in phase 2–4
(`20260527-200213`, `20260528-000411/061323/073509/082137`); the first
plain-Terminal.app run (`20260528-094743`) completed cleanly ($8.66, 39KB
`final.md`, all gating invariants green). See spec 0243 +
`cowork/briefs/2026-05-28-h4-plain-terminal-next.md`.

The CLI enforces this contract: `dual-research run` refuses to start if
any `CLAUDECODE` / `CLAUDE_CODE_*` env var is set, unless
`DUAL_RESEARCH_ALLOW_CLAUDE_P=1` is also set.

### Canonical invocation

```bash
cd /Users/alexlisitzky/ClaudeCode/dual-research-workspace/dual-research && \
eval "$(grep -hE '^export (ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_(URL|ANON_KEY|SERVICE_ROLE_KEY))=' ~/.zshrc)" && \
caffeinate -i uv run dual-research \
  --notion "<url>" --models prod --push-while-running --name <slug> \
  2>&1 | tee /tmp/dr-run-<slug>.log
```

`caffeinate -i` prevents macOS idle sleep for the duration of the run;
`tee` captures stdout/stderr so the post-mortem has evidence if the
process exits abnormally.

### `DUAL_RESEARCH_ALLOW_CLAUDE_P=1` — intended use

Sets the escape valve to allow `dual-research run` from inside a Claude
Code surface. Intended **only** for:

- CI / test environments where the guard's host-detection false-positives
  on a Claude Code env-var presence that does not actually carry the H4
  reap behaviour.
- Deliberate sandbox-mode invocations (e.g. Cowork running dual-research
  inside its own sandbox for code review).

**Not intended** for "I'm in a hurry, just run it" workflows — the
silent-kill behaviour returns the moment you override the guard. Spec
0243 documents the failure mode; this escape is for opting into it
knowingly, not for forgetting it exists.
```

### 2.3 — `/dual-research-run` skill amendment

Amend (not replace) the existing skill at [`.claude/skills/dual-research-run/SKILL.md`](.claude/skills/dual-research-run/SKILL.md). The skill currently fires `uv run dual-research …` directly as a background task from within Claude Code — exactly the failure path 0243 closes.

Replace the "Firing the run" section with a "refuse-and-redirect" pattern:

> ## Firing the run (UPDATED — spec 0243)
>
> **Do not fire the run from inside this Claude Code session.** The
> dual-research CLI refuses to run inside Claude Code (CLI guard added
> in spec 0243); even if the guard were bypassed, the run would be
> silently reaped mid-execution by Claude Code's background-task
> manager.
>
> Instead, emit the canonical Terminal.app command to the user and ask
> them to paste it in a plain Terminal.app window:
>
> ```bash
> cd /Users/alexlisitzky/ClaudeCode/dual-research-workspace/dual-research && \
> eval "$(grep -hE '^export (ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_(URL|ANON_KEY|SERVICE_ROLE_KEY))=' ~/.zshrc)" && \
> caffeinate -i uv run dual-research \
>   --<input-flag> "<input>" --models prod --push-while-running \
>   --name <slug> 2>&1 | tee /tmp/dr-run-<slug>.log
> ```
>
> Substitute `<input-flag>` with `--prompt` / `--brief` / `--notion`
> per the input shape; `<slug>` is the derived run name (4-6
> meaningful words, kebab-case, ≤ 30 chars).
>
> Reporting URLs: tell the user where the run will live —
> `http://127.0.0.1:6173/runs/<id>` and
> `https://dual-research-alex.fly.dev/runs/<id>` — once they share the
> Run ID printed early in the terminal output.

The reporting and post-run sections of the skill (verifying `runs/<id>/final.md` exists, etc.) remain unchanged; only the firing mechanism flips.

### 2.4 — CLI `--help` mention of `DUAL_RESEARCH_ALLOW_CLAUDE_P`

In the `dual-research --help` epilog (or per-subcommand help where the guard is active), add a one-line mention:

> ENVIRONMENT VARIABLES:
>   DUAL_RESEARCH_ALLOW_CLAUDE_P=1   Allow `dual-research run` inside a
>                                    Claude Code surface despite the
>                                    spec-0243 guard. See CLAUDE.md
>                                    "Operational" for intended use.

So the escape is discoverable from the tool itself, not just from the spec.

## 3. User stories & acceptance criteria

Not a UI spec. §3 is non-applicable per the new-feature template. Acceptance is encoded as falsifiable items in §6.

## 4. Data / Schema deltas

None. No new event types, no state-file fields, no migrations.

## 5. Out of scope

- **Promoting the guard to gating on a stricter detection signal** (e.g. parent-process-name belt-and-suspenders). Per Cowork sign-off Q1: env-var detection is sufficient; adding process-name introduces false-positive risk (renames, sudo, etc.) without closing a real false-negative.
- **Detecting non-Claude-Code host environments that have similar reap behaviour** (e.g. some CI runners, some terminal emulators with watchdogs). If a real failure surfaces from a non-Claude host, draft a follow-up spec; not in scope here.
- **Auto-cron / scheduled dual-research runs** that would need to bypass the guard. The escape var handles this for now; a dedicated "scheduled run" spec is a separate concern.
- **0242 (checkpoint + resume)** — deferred per Cowork sign-off until first real interruption. The terminal-launch operational fix closes the H4 surface; 0242 closes the residual set (power loss, kernel panic, true OOM, accidental Ctrl-C). Trigger condition: any future real interruption.

## 6. Test plan

Tests live in a new file [`tests/test_spec_0243_claude_code_guard.py`](tests/test_spec_0243_claude_code_guard.py). Pure stdlib + `pytest` + `monkeypatch`.

- [ ] **`test_guard_refuses_when_CLAUDECODE_set`** — monkeypatch `os.environ` with `CLAUDECODE=1`; invoke the CLI's run subcommand with mock args; assert `SystemExit(2)` raised and the canonical Terminal.app command appears in stderr.
- [ ] **`test_guard_refuses_when_CLAUDE_CODE_ENTRYPOINT_set`** — monkeypatch `CLAUDE_CODE_ENTRYPOINT=claude-desktop`; same assertions.
- [ ] **`test_guard_refuses_when_CLAUDE_CODE_HOST_set`** — monkeypatch `CLAUDE_CODE_HOST_*=foo` (the Cowork-sandbox failure case named in the execution sign-off); same assertions. **This is the load-bearing test for Cowork's "widen detection" guidance.**
- [ ] **`test_guard_allows_with_escape_var`** — monkeypatch `CLAUDECODE=1` AND `DUAL_RESEARCH_ALLOW_CLAUDE_P=1`; assert no exit, the run proceeds (mock the actual run-firing to no-op).
- [ ] **`test_guard_allows_in_plain_terminal`** — monkeypatch `os.environ` to remove all `CLAUDE*` vars; assert no exit, the run proceeds.
- [ ] **`test_guard_does_not_block_read_only_subcommands`** — `dual-research verify`, `dual-research serve`, and other read-only subcommands are NOT guarded; they should proceed even with `CLAUDECODE=1` set.
- [ ] **`test_cli_help_mentions_escape_var`** — `dual-research --help` output contains the literal string `DUAL_RESEARCH_ALLOW_CLAUDE_P`.
- [ ] **Empirical verification of `claude -p` background-mode env vars** — manual or scripted: run `claude -p 'env | grep -E "^(CLAUDECODE|CLAUDE_)" | sort'` and confirm at least one `CLAUDECODE`-or-`CLAUDE_CODE_*` variable is set. The result confirms the guard's broad detection rule is sufficient; the empirical record lives in the spec's handoff. **If the verification fails (background mode sets none of the guard-detected vars), the guard's detection rule must widen further** — but per current evidence and Cowork's sign-off this is unlikely.
- [ ] **CLAUDE.md "Operational" section** present with canonical command + escape-var documentation.
- [ ] **`/dual-research-run` skill** amended to refuse-and-redirect, not to fire-from-Claude.
- [ ] **`uv run pytest tests/ -q`** passes end-to-end. No pre-existing test changes verdict.
- [ ] **CHANGELOG entry under a new `## [X.Y+1.0] — 2026-05-28` heading** (MINOR bump). `pyproject.toml` and `src/dual_research/__init__.py` bumped to the same X.Y+1.0.

## 7. Risks

- **False-positive on a future Claude Code env-var renaming.** If Anthropic ships a Claude Code version that drops all `CLAUDECODE` / `CLAUDE_CODE_*` env vars, the guard goes silent and the H4 failure mode returns. Mitigation: the empirical verification test in §6 catches this on CI runs that include a `claude -p` invocation; a missed false-negative is preferable to a missed false-positive (preference: refuse-unnecessarily over fail-silently).
- **False-positive on a non-Claude environment that happens to set a `CLAUDE_CODE_*` var.** Extremely unlikely (Anthropic's env-var namespace is project-specific). If it surfaces, the escape var resolves it in seconds.
- **CI environments hitting the guard.** Mitigation: CI sets `DUAL_RESEARCH_ALLOW_CLAUDE_P=1` if/when CI is the firing surface for a real dual-research run. Documented in CLAUDE.md "Operational → DUAL_RESEARCH_ALLOW_CLAUDE_P=1 intended use."
- **Power users annoyed by the redirect.** The guard adds friction to a workflow that was previously one-command. The friction is the point — silent kills are worse than friction. The escape var is the explicit opt-in for power users who knowingly accept the kill risk.
- **Skill amendment misses an edge case** (e.g. the user previously had a custom workflow that depended on the skill firing directly). Mitigation: the skill's prior behaviour is preserved on the post-run side (URL reporting, exit-code check, etc.); only the firing step changes.
- **Revert path.** All artefacts are local: one new CLI helper function, four new test functions, one new CLAUDE.md section, one amended skill markdown file, one CHANGELOG entry. Revert is a single `git revert` of this spec's PR; no migration to unwind.
