---
spec: "0187"
date: 2026-05-23
version: 1.36.9
pr: "https://github.com/Lexiz/dual-research/pull/216"
---

# Spec 0187 — DS reference §13 ItemCard examples refresh — shipped

The Critique card §13 in `design-system/assets/Design System v2.html` now
mirrors the post-0173 ItemCard anatomy that already ships live: tight head
(`[provider][kind][evidence-needed?][lifecycle]`), `data-expanded="false"`
default, QuestionThread-anatomy bubbles for the expanded view.

## What landed

- **[design-system/assets/Design System v2.html:1010–1272](../design-system/assets/Design System v2.html)** — full §13 rewrite:
  - Lede paragraph rewritten to reflect tight-head + collapse + bubble timeline anatomy.
  - Section index annotated: `§13 · components · NEW · spec 0144 · refreshed 0173 / 0187`.
  - Stacking-order callout rewritten — old item 1 (id chip + sources chip head row) replaced by post-0173 chip composition; old item 3 (evidence-needed body banner) dropped and folded into item 1 as inline modifier; new "collapse affordance" item added; expanded-view item rewritten around QT bubbles.
  - **Pair 1** (Resolved Question): collapsed-resolved (head only) + expanded-resolved (head + body + 3 bubbles + sources). Bubble timeline uses live `.item-card__qt-row{--claude,--gpt}` classes already in [composed-components.css:2184–2210](../design-system/assets/styles/composed-components.css).
  - **Pair 2** (Open Disagreement · evidence-required): collapsed-open + expanded-open. Evidence-needed surfaces as inline `<span class="chip tone-warn no-dot">⚠ evidence needed</span>` between kind chip and head-spacer; no body banner. Lifecycle chip uses single-chip open form (kind-toned `raised · r2 · GPT`).
  - The former third standalone "open Disagreement · with evidence-needed body banner" full-width card is removed. Its purpose (showing evidence-needed) is now covered by pair 2's expanded-open example with the inline head chip. SourceRow detail card + governance notes preserved verbatim.

- **§13b QuestionThread (legacy) untouched** per spec §5 — the legacy block intentionally documents the pre-0114 fallback and remains useful as historical reference.

- **CHANGELOG / version** — `1.36.8` → `1.36.9` (PATCH per refactoring type).

No JSX, no CSS, no token edits. Reference HTML catches up to live; live does not move.

## Live smoke

```
$ curl -sS -o /dev/null -w "%{http_code}\n" https://dual-research-alex.fly.dev/
200
```

`fly status -a dual-research-alex`: two app machines on version 477 running
image `dual-research-alex:deployment-01KSADV038EZDX390SQX9EKYE7`.

The §13 catch-up is in the reference HTML, not in the live app's served
surfaces, so the deploy itself doesn't surface visible changes — but the
new spec 0187 cap from spec 0185 / the v1.36.9 build are now shipped.

## Deploy notes

- First two `fly deploy` attempts errored with `failed to get lease on VM …
  lease currently held by 89f4c34c-…@tokens.fly.io`. Behind the scenes,
  the bluegreen had still rolled out the new image successfully — `fly
  status` showed two new-version machines healthy alongside two stale
  blues. Recovery: invoke `bash scripts/sweep_stale_blues.sh` directly
  rather than retrying `fly deploy` (which kept burning time without
  ever acquiring the held leases). Sweep output: `sweep: destroyed 2/2
  stale blues on dual-research-alex (failed=0)`. Saved this recipe as
  [memory: project-fly-lease-drift-recovery](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md)
  for future cycles.
- Image: `dual-research-alex:deployment-01KSADV038EZDX390SQX9EKYE7` running on two machines.

## What this DOES NOT do

- **Move live JSX or CSS.** Reference HTML catches up to live; live does not move. Any further ItemCard live-app changes lay outside this spec.
- **Touch §13b QuestionThread (legacy).** Out of scope per spec §5; the legacy block intentionally documents the pre-0114 fallback.
- **Refresh §13's SOURCES (N) example rows for spec 0173's per-source provider/round attribution.** Out of scope; that catch-up is a separate follow-up if anyone notices the gap.
- **Renumber §13 or its sub-IDs.** §13 stays §13; §13b stays §13b. Fragment anchors (`#itemcard`, `ic-1a` / `ic-1b` / `ic-2a` / `ic-2b`) — the old `ic-1` / `ic-2` / `ic-3` are removed; no other doc currently links to those fragments (grepped the design-system/ tree before editing).

## Rebase note

PR #216's first squash-merge attempt failed with `DIRTY` mergeable state because the `--push-to-main` event commits had advanced main while the branch was open. Resolved by rebasing the branch onto `origin/main`, resolving the append-only conflict on `dashboard/events/0187.jsonl` by keeping main's additions + the branch's content commit, force-with-lease-pushing, then admin-squashing as normal. Same workflow as spec 0185's earlier rebase.
