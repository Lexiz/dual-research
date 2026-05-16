---
name: dual-research-run
description: |
  Fire a dual-research test run on a research prompt. Handles env-key
  sourcing from ~/.zshrc, ensures the local UI server is up for live
  viewing, fires the run with the prod-tier models and
  --push-while-running so the hosted UI updates as the run progresses,
  and reports both the local and hosted run URLs. Use when the user
  wants to test the dual-research pipeline end-to-end on a fresh prompt.
---

# dual-research-run

Canonical recipe for firing a dual-research test run from within Claude
Code. Captures the operational knowledge that should not need
rediscovering each time:

- where the API keys live (`~/.zshrc`, not the sandbox shell)
- which model tier to use for real runs (`prod` — Sonnet 4.6 + GPT-5.5
  on the 1 M-context tier)
- how to expose the run for live viewing on **both** local and hosted
  UIs
- where to look for the run afterwards

## When to invoke this skill

The user says something like:

- "run dual-research on <prompt>"
- "fire a dual-research run for <prompt>"
- "test dual-research with <prompt>"
- "let's do a test run on <prompt>"

…where `<prompt>` is the research brief text (anything from a sentence
to several paragraphs). The skill ships with the `--prompt` mode; for
`--brief <path>` or `--notion <url>` inputs, follow the same recipe
but substitute the input flag (mention this to the user if their input
looks like a file path or Notion URL).

## Pre-flight checks

Before firing the run:

1. **You are inside the dual-research repo.** `cwd` should resolve to
   `~/dual-research` or a sibling worktree. If not, ask the user where
   the repo lives — don't guess.
2. **The keys exist in `~/.zshrc`.** Run a single grep to confirm and
   source them in one shot:

   ```bash
   eval "$(grep -hE '^export (ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_(URL|ANON_KEY|SERVICE_ROLE_KEY))=' ~/.zshrc)"
   env | grep -E '^(ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_)' | sed 's/=.*/=<set>/'
   ```

   Confirm all four/five values are set. If any are missing, ask the
   user before proceeding — don't guess about their environment.

3. **The local UI server is reachable** on `http://127.0.0.1:6173`. If
   it isn't, start it in the background:

   ```bash
   curl -s http://127.0.0.1:6173/api/health \
     || (uv run dual-research serve --port 6173 \
          > /tmp/dr-local-ui.log 2>&1 &)
   sleep 1 && curl -s http://127.0.0.1:6173/api/health
   ```

   The first `||` branch only fires when the server isn't up. The
   server keeps running across runs.

## Firing the run

Always include in the same shell that just sourced the env keys:

```bash
uv run dual-research \
  --prompt "<the user's research prompt, verbatim>" \
  --models prod \
  --push-while-running \
  --name <short-slug-derived-from-prompt> \
  2>&1 | tee /tmp/dr-run-<slug>.log
```

Notes:

- **`--push-while-running`** (spec 0032) is what makes the hosted UI
  reflect progress every ~30 s. Don't omit it for test runs.
- **`--models prod`** is the 1 M-context tier (Sonnet 4.6 + GPT-5.5
  with web search). Test-tier (`--models test`) uses Haiku + GPT-5-mini
  with smaller windows — use only if the user explicitly asks for the
  cheap version.
- **`--name <slug>`** keeps the session-dir name human-readable. Derive
  the slug from the prompt's first 4–6 meaningful words, kebab-case,
  ≤ 30 chars.
- Always launch with `run_in_background: true` from the Bash tool — a
  prod-tier run typically takes **20–30 minutes** to complete. Schedule
  a wakeup at ~25 min to push (if `--push-while-running` is set, this
  is a sanity check, not a requirement).

## Reporting URLs

Once the run kicks off (you'll see the session-dir log line on stdout),
report **both** URLs immediately so the user has somewhere to watch:

```
Local  (live SSE):  http://127.0.0.1:6173/#/runs/<session-id>
Hosted (~30s lag):  https://dual-research-alex.fly.dev/#/runs/<session-id>
```

The session-id is the timestamped folder name under `runs/`, of the
form `YYYYMMDD-HHMMSS-<slug>`. Pull it from the log line:

```
[run] session dir: /Users/alexlisitzky/dual-research/runs/<session-id>
```

Or fetch the latest from `runs/` if the log line scrolled by:

```bash
ls -td runs/*/ | head -1
```

## Stay quiet after fire-and-report

Don't poll, don't tail, don't auto-summarise the run as it streams. The
user has the UI in their browser — that's the surface for inspection.
If the user wants a status check, use `tail -40
/tmp/dr-run-<slug>.log` to peek at recent orchestrator output. If they
want to stop the run, use the Bash tool's TaskStop on the background
task id.

## On completion

When the background task notification arrives (`exit code 0` typically
means clean run; non-zero indicates a parse failure or deadlock —
inspect `tail -60` of the log to diagnose), confirm the run landed:

```bash
ls runs/<session-id>/final.md && wc -l runs/<session-id>/final.md
```

Report the completion status and the two URLs again so the user can
inspect the result.

## Failure modes worth knowing

- **Missing OPENAI/ANTHROPIC key in shell** — the eval-grep pattern
  above is the fix; `~/.zshrc` is the source of truth.
- **Local UI 404 on `/#/runs/<id>`** — refresh the page; the run-list
  endpoint might not have picked up the new session yet.
- **Hosted UI still empty after 60 s** — check Supabase env keys are
  set; the `--push-while-running` log line at run start should report
  the supabase URL. If keys are missing, the CLI fails fast with a
  clear error.
- **Run stuck in Phase 2 with both `STATUS: AGREED`** — spec 0032's
  hash-drift escape should kick in within one extra round (force-
  verbatim repair → canonical promotion). If the run sits past round 6
  without progress, check the log for `phase2_hash_drift_detected`
  events.

## Skill-versioning note

This skill ships in the repo at
`.claude/skills/dual-research-run/SKILL.md`. Project-local so it
versions with the code. Recipes change when the CLI changes; keep this
file in sync with the actual flag names if a future spec renames or
removes anything mentioned above.
