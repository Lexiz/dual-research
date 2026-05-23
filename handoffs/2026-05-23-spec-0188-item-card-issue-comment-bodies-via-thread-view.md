---
spec: "0188"
date: 2026-05-23
version: 1.37.0
pr: "https://github.com/Lexiz/dual-research/pull/217"
---

# Spec 0188 — Issue + Comment bodies thread through ItemCardThreadView — shipped

Closes spec 0173 §2.9's "all four kinds threaded" promise. `ItemCardIssueBody`
and `ItemCardCommentBody` now end with `<ItemCardThreadView item={item} />`,
so expanded Issue + Comment cards render the QuestionThread bubble anatomy
already used by Question + Disagreement.

## What landed

- **[src/dual_research/ui/static/run-detail.jsx:1698](../src/dual_research/ui/static/run-detail.jsx)** — `ItemCardIssueBody` body trailer: `<ItemCardThreadView item={item} />` after the optional inline anchor blockquote. Doc-comment header rewritten to mention spec 0188 and the new layout (`<markdown body> · > quote: <anchor> · <ItemCardThreadView />`).
- **[src/dual_research/ui/static/run-detail.jsx:1719](../src/dual_research/ui/static/run-detail.jsx)** — `ItemCardCommentBody`: same trailer + doc-comment update. Most Comments have only the raise transition, so the timeline collapses to a single bubble; that's the canonical anatomy spec 0173 §2.9 prescribed.
- **CHANGELOG / version** — `1.36.9` → `1.37.0` (MINOR per new-feature type, visible behavior change).

No CSS / schema / token edits. `ItemCardThreadView` is kind-agnostic; the existing `.item-card__qt-row{,--claude,--gpt}` styles in [components.css:4582–4620](../src/dual_research/ui/static/components.css) and [composed-components.css:2184–2210](../design-system/assets/styles/composed-components.css) cover Issue + Comment without additions.

## Spec drift note

Spec 0188 was authored assuming pre-0179 state — it described replacing `.item-card__seen-row` chip strips in Issue + Comment bodies with `ItemCardThreadView`. Spec 0179 had already removed those strips, so the actual current Issue / Comment bodies were just `<markdown body>` + optional inline anchor. The work simplified to **adding** `ItemCardThreadView` at the end of each body rather than **replacing** anything. The spec's broader intent (route both bodies through `ItemCardThreadView` for parity with Q/D) is delivered.

Spec §2.4 explicitly preserves the markdown body block above the thread view. The raise bubble inside `ItemCardThreadView` also carries `item.body` as its quote, so the body text now appears twice for thin items (single-bubble Comments / Issues). This is the spec's literal reading and §7 noted the visual-density concern. A follow-up spec can de-duplicate (e.g. drop the markdown block in Issue / Comment bodies for parity with Q/D) if it reads heavy in practice.

## Live smoke

```
$ curl -sS -o /dev/null -w "%{http_code}\n" https://dual-research-alex.fly.dev/
200
```

`fly status -a dual-research-alex`: two app machines on version 483 running
image `dual-research-alex:deployment-01KSAEF57S4PA1JAMGV3E3CWBF` (the v1.37.0
build with spec 0188 wired in).

## Deploy notes

- `fly deploy` hit the same lease-drift pattern documented in
  [memory: project-fly-lease-drift-recovery](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md):
  new greens were created and promoted, blue-sweep failed due to held leases
  on `89f4c34c-…@tokens.fly.io`. Recovered by running
  `bash scripts/sweep_stale_blues.sh` directly rather than retrying
  `fly deploy`. Sweep destroyed 2/2 stale v481 blues.
- Image: `dual-research-alex:deployment-01KSAEF57S4PA1JAMGV3E3CWBF` running on
  two v483 machines, both healthy.
- The release-history string fly tracked: v477 (spec 0187) → v478..v481
  intermediate (failed-then-succeeded attempts for 0188's first deploy)
  → v482 failed → v483 running (current).

## What this DOES NOT do

- **De-duplicate the markdown body vs. raise-bubble text.** Per spec §2.4
  explicit guidance; follow-up spec if needed.
- **Kind-aware vocabulary in `_transitionVerb`.** Spec §2.3 noted this as
  optional polish; the existing verb map is reused for Issue / Comment too.
- **DS reference HTML §13 catch-up.** Already shipped in
  [spec 0187](specs/0187-ds-v2-item-card-examples-refresh.md) — the example
  pairs there cover I + C in the new shape too (the bubble anatomy is
  kind-agnostic).
- **Per-bubble interactivity, single-bubble compact modifier, anchor-quote
  changes.** All explicitly out of scope per spec §5 + §7.

## Rebase note

PR #217's first squash-merge attempt failed with `DIRTY` mergeable state, same
pattern as 0185 / 0187: the `--push-to-main` event commits had advanced main
while the branch was open. Resolved by rebasing onto `origin/main`, keeping
both sides' append-only additions on `dashboard/events/0188.jsonl`,
force-with-lease-pushing, then admin-squashing. This is the standard pattern
for the queue workflow when `--push-to-main` events are heavy.
