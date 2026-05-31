---
kind: dev
spec: "0260"
slug: name-flag-doubles-as-run-display-title
title: Make --name double as the run display title by overriding brief.md's first H1
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-31
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
disposition_reason: "Self-contained UX fix the user explicitly asked to queue and ship; one chokepoint, one helper, one test."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0260 — Make --name double as the run display title by overriding brief.md's first H1

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** MINOR — `--name` gains new behavior (now drives display title, not just the slug).
> **Evidence:** Every run on `dual-research-alex.fly.dev` and the local UI displays as "Research Brief" regardless of the `--name` passed.

---

## 1. Context

Every research run displays as **"Research Brief"** in both UIs (local and the hosted `dual-research-alex.fly.dev`). The `--name` flag passed on every run has no effect on the displayed title — it only feeds the run slug / directory name.

The display title is derived from the **first `# ` H1 line** in `brief.md`, in both UIs:

- Local: [`_read_topic`](src/dual_research/ui/aggregator.py:451), called from `summarize_run` via `topic = _read_topic(session_dir / "brief.md")`.
- Hosted: [`_extract_h1`](src/dual_research/ui/server.py:1136) over the uploaded `brief.md` (`topic = _extract_h1(briefs.get(r["id"], ""))`).

`brief.md` is uploaded to Supabase via the `*.md` glob ([`SESSION_FILE_GLOBS`](src/dual_research/persistence/remote.py:30)), so the same H1 drives the hosted title. For Notion-sourced runs, the ingest hardcodes that H1 as `# Research brief` ([`notion.py:431`](src/dual_research/ingest/notion.py:431)) — which is why every run shows "Research Brief". Meanwhile `--name` only feeds [`_derive_slug`](src/dual_research/cli.py:266) → the `run_id` slug, and is never propagated into the title.

## 2. Proposed change

Make `--name` double as the run title by overriding the first H1 of `brief.md` when `--name` is set. The override is applied at **one source-agnostic chokepoint** — right before `brief.md` is written at [`cli.py:400`](src/dual_research/cli.py:400):

```python
brief_path.write_text(_apply_title(brief.content, args.name), encoding="utf-8")
```

plus a helper in [`cli.py`](src/dual_research/cli.py):

```python
def _apply_title(content: str, name: str | None) -> str:
    if not name:
        return content
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):      # replace first H1 (e.g. "# Research brief")
            lines[i] = f"# {name}"
            return "\n".join(lines)
    return f"# {name}\n\n{content}"      # no H1 present → prepend one
```

Rationale:

- **No new flag** — `--name` already exists and is already passed on every run; it now does double duty (human-readable title + slug, slug still auto-derived from it as today via [`_derive_slug`](src/dual_research/cli.py:266)).
- **Source-agnostic** — applied at the single write point, so it works for `--notion`, `--prompt`, and `--brief` sources alike.
- **Local AND hosted in one change** — both surfaces read the same `brief.md` H1 ([`aggregator.py:451`](src/dual_research/ui/aggregator.py:451), [`server.py:1136`](src/dual_research/ui/server.py:1136)); the hosted upload carries the same file via the `*.md` glob ([`remote.py:30`](src/dual_research/persistence/remote.py:30)).
- **Unchanged when omitted** — when `--name` is absent, `_apply_title` returns `content` verbatim, preserving the existing H1 / topic-extraction fallback behavior.

## 3. User stories & acceptance criteria

This spec does not modify any renderer under `src/dual_research/ui/` or `design-system/` — it only changes which string the existing topic element is populated with. Stories and scenarios are included below because the visible outcome is a UI title change.

### 3.1 — User stories

> As a `researcher`, I want the `--name` I pass on a run to show up as that run's title in the app, so that I can tell my runs apart instead of seeing every one labelled "Research Brief".

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** named run shows its name
> GIVEN a run launched with `--name "GPU inference cost"` whose ingested `brief.md` starts with `# Research brief`
> WHEN the run row renders in the local or hosted run list
> THEN the displayed topic text content matches "GPU inference cost"

> **Scenario 2:** unnamed run keeps source title
> GIVEN a run launched without `--name` whose ingested `brief.md` starts with `# Research brief`
> WHEN the run row renders in the local or hosted run list
> THEN the displayed topic text content matches "Research brief"

## 4. Data / Schema deltas

None. No migrations, no schema changes. The change only alters the content of the existing `brief.md` artifact already uploaded via the `*.md` glob.

## 5. Out of scope

- No changes to the UI renderers ([`aggregator.py`](src/dual_research/ui/aggregator.py), [`server.py`](src/dual_research/ui/server.py)) — they already read the H1 correctly; only the source string changes.
- No changes to slug derivation ([`_derive_slug`](src/dual_research/cli.py:266)) — slug behavior is preserved exactly.
- No new CLI flag, and no change to the Notion-ingest hardcoded `# Research brief` default ([`notion.py:431`](src/dual_research/ingest/notion.py:431)); that string remains the fallback when `--name` is omitted.
- No retroactive title fix for runs already uploaded.

## 6. Test plan

- [ ] CLI-level test: after ingest + write, `brief.md`'s first H1 equals the `--name` value when `--name` is set (covers the "H1 present → replace" branch against a brief that already has `# Research brief`).
- [ ] CLI-level test: when `--name` is absent, `brief.md`'s first H1 is left unchanged (returns `content` verbatim).
- [ ] `_apply_title` unit test: a brief with **no** H1 gets `# {name}` prepended (the no-H1 fallback branch).
- [ ] `_apply_title` unit test: only the **first** H1 is replaced; a later `# ` heading in the body is untouched.

## 7. Risks

- **Low risk.** The change is a pure string transform at a single write point, gated on `args.name` being truthy. When `--name` is omitted the function is a verbatim pass-through, so existing behavior is bit-for-bit preserved.
- A brief whose intended title legitimately differs from `--name` would be overridden — but `--name` is already the user's chosen human label for the run, so this is the desired behavior, not a regression. Mitigation: omit `--name` to keep the source's own H1.
- Not a captured-live-failure fix, so the spec-0238 real-entry-point test rule is not triggered; CLI-level tests against the write path are sufficient.
