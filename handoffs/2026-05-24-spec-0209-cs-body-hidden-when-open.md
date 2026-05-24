---
spec: "0209"
date: 2026-05-24
version: "1.44.8"
pr: "https://github.com/Lexiz/dual-research/pull/241"
---

# Spec 0209 — namespace legacy how-it-works disclosure to fix CollapsibleSection bodies stay hidden when open

PR: [#241](https://github.com/Lexiz/dual-research/pull/241) · admin-squash-merged · live on `dual-research-alex` as `v1.44.8` (image `deployment-01KSCZBW2T8EJQ9V1ZRD43MZWM`, machine version `697`).

## What landed

- **Root cause clarified.** Two unrelated `.cs-*` rule blocks lived in [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) — the canonical CollapsibleSection primitive at lines ~1404-1444 (modern `<CollapsibleSection>` from [`shared.jsx:1620`](src/dual_research/ui/static/shared.jsx:1620), used by Input Brief modal sections, critique pane section headers, timeline phase groups, agent-input entries) and a CSS-only how-it-works block at lines ~3675-3699 with selectors `.cs-section`, `.cs-section.is-open .cs-body { display: block }`, and an unscoped `.cs-body { display: none }`. The unscoped rule at specificity 0,1,0 won the cascade for every modern `<div class="cs-body cs-open">` — the modern block only sets `transition: none` on `.cs-body.cs-open`, never re-declares `display`. The legacy `is-open` override didn't fire because the modern primitive wraps DOM as `<div class="cs">`, not `<section class="cs-section">`. End state: every modern `<div class="cs-body cs-open">` computed `display: none` and rendered invisible. Spec 0178 was a wrong-cause patch (JSX `defaultOpen` props) that left the CSS conflict intact.
- **Rename, not delete.** [`components.css:3675-3699`](src/dual_research/ui/static/components.css:3675) renamed wholesale: `.cs-section` → `.hiw-cs-section`, `.cs-header` → `.hiw-cs-header`, `.cs-chevron` → `.hiw-cs-chevron`, `.cs-title` → `.hiw-cs-title`, `.cs-body` → `.hiw-cs-body`, plus the descendant rules `.cs-section:first-child` → `.hiw-cs-section:first-child`, `.cs-section.is-open .cs-chevron` → `.hiw-cs-section.is-open .hiw-cs-chevron`, `.cs-section.is-open .cs-body` → `.hiw-cs-section.is-open .hiw-cs-body`. Modern block at [`components.css:1404-1444`](src/dual_research/ui/static/components.css:1404) untouched.
- **JSX consumer updated in lockstep.** [`how-it-works.jsx:614`](src/dual_research/ui/static/how-it-works.jsx:614) — the only React consumer of the legacy class names — now emits `className={'hiw-sec hiw-cs-section' + (open ? ' is-open' : '')}` plus `hiw-cs-header` / `hiw-cs-chevron` / `hiw-cs-title` / `hiw-cs-body` on the inner spans/divs. Prose at [`how-it-works.jsx:76`](src/dual_research/ui/static/how-it-works.jsx:76) updated to reference `.hiw-cs-section`.
- **Cache-buster bumped.** All 26 occurrences of `?v=0181a` in [`src/dual_research/ui/static/index.html`](src/dual_research/ui/static/index.html) bumped to `?v=0209a` so returning users actually fetch the renamed CSS + JSX.
- **No DS-side mirror change.** `grep` on [`design-system/assets/styles/composed-components.css`](design-system/assets/styles/composed-components.css) returns zero `.cs-*` hits — the legacy block was never mirrored, so the CLAUDE.md dual-write rule doesn't apply. The status of the modern `.cs-*` primitive's DS mirror is unchanged by this spec (see spec 0209 §7 — separate hygiene follow-up if the user wants it backfilled).
- **Regression locked at [`tests/test_spec_0209_cs_namespace.py`](tests/test_spec_0209_cs_namespace.py)** following the spec 0206 source-pattern doctrine. Seven assertions: zero unscoped `.cs-section` rules; zero unscoped `.cs-body { … }` rules; canonical `.cs-body.cs-closed { display: none }` still present (modern primitive intact); zero `.cs-section.is-open .cs-body` / `.cs-section.is-open .cs-chevron` descendant rules; full `.hiw-cs-*` block declared (including `.hiw-cs-section.is-open .hiw-cs-body { display: block }`); `how-it-works.jsx` uses the renamed classes; `how-it-works.jsx` carries no orphan `cs-section` / `cs-body` / `cs-header` / `cs-chevron` / `cs-title` references.

## Verification (Claude Preview MCP, local + production)

| Scenario | Where checked | Result |
| --- | --- | --- |
| Input Brief modal — `User prompt` open on first paint | local dev | `div.cs-body.cs-open` computes `display: block`; body contains 17,7xx chars |
| Input Brief modal — click `Derived inputs` header to expand | local dev | `cs-closed` → `cs-open`, `display: none` → `block`, 6 piece rows render |
| How-It-Works page — renamed `.hiw-cs-*` classes render correctly, no orphan legacy classes | local dev | 11 sections discovered, `.hiw-cs-section.is-open` opens to `display: block`, 0 orphan `.cs-section` |
| Live CSS smoke | `https://dual-research-alex.fly.dev/components.css?v=0209a` | HTTP 200, 208KB, modern `.cs-body.cs-open` / `.cs-body.cs-closed` present, `.hiw-cs-section` block live, no unscoped `.cs-section` or `.cs-body { … }` |

## Test plan

- `uv run pytest tests/ -q` — 1887 passed, including the 7 new spec-0209 assertions.

## Deploy notes

- **Cycle 1 attempt:** `fly deploy` from correct cwd hit a real lease conflict — both machines' leases held by `<uuid>@tokens.fly.io`, expiring at 12:26-12:27Z. New image (`deployment-01KSCZ332A3H08E9TVKXXVRQ2S`) was built + pushed to the registry but never landed on a machine. Per `/dev-next` step 21 (spec 0200 §2.2) this routed to **matrix case 3**, marked the spec `status: failed, failure_step: deploy`, and halted.
- **Cycle 2 attempt (user-requested clean retry):** bare `fly deploy` failed with `Error: the config for your app is missing an app name`. Diagnosed as a cwd issue — Claude Code's Bash tool default cwd is `/Users/alexlisitzky` (no `fly.toml` there). The `/dev-next` skill's "never prepend `cd …`" rule is scoped to `git` commands (untrusted-hooks safety prompt); it does NOT apply to `fly` commands. **Captured at [`feedback_fly_deploy_cd.md`](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/feedback_fly_deploy_cd.md).**
- **Cycle 3 attempt:** `cd /Users/alexlisitzky/dual-research && fly deploy` — clean rolling deploy, both machines updated to version 697 on image `deployment-01KSCZBW2T8EJQ9V1ZRD43MZWM`. Leases acquired + cleared cleanly; the lease holder from cycle 1 had expired naturally between attempts.
- **Sweep:** `sweep: no stale blues on dual-research-alex` — clean post-rolling-deploy cluster, no fallback needed.
- **Spec status reconciliation:** queue-state went `queued → in_progress → merged → (deploy failed) → deployed`. The `failed` entry remains in the event history; status flipped to `deployed` once the retry converged.

## Followups worth noting

- **`/dev-next` step 21 over-triggers on transient lease errors.** Spec 0204's memory note ([`project_fly_lease_drift_recovery`](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md)) already documents the "expires within ~5 min → wait + single retry" nuance, but the skill body's literal language ("MUST NOT invoke `fly deploy` a second time within the same `/dev-next` invocation, regardless of which case fires") overrides the memory. The result is repeated user intervention for transient lock contention that resolves on its own. Worth a separate dev spec to update the step-21 matrix so case-3 with `<expires-at> within ≤ 5 min` routes to a bounded single retry instead of an unconditional halt.
- **DS mirror status for the modern `.cs-*` primitive.** Spec 0209 §7 deferred this. The legacy block was never mirrored, but the modern primitive's mirror status is currently unverified — `design-system/assets/styles/composed-components.css` carries zero `.cs-*` rules. The CLAUDE.md dual-write rule says new DS components land in both files; whether the canonical primitive *should* be backfilled into the DS mirror is a separate hygiene call.

## Deferred during implementation

_None._ Everything called out in the spec body landed in this PR. The two out-of-scope items above are the spec's pre-declared §7 deferrals, not implementer-side deferrals.
