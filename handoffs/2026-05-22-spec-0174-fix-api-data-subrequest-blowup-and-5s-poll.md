---
spec: "0174"
date: 2026-05-22
version: 1.30.1
pr: https://github.com/Lexiz/dual-research/pull/193
---

# Spec 0174 — Fix `/api/data` subrequest-limit blowup (502) + 5s dashboard poll

v1.30.1 restores the dashboard's live-data path. The Cloudflare Pages Function at `functions/api/data.js` had been returning `502 — Too many subrequests by single Worker invocation` on every request since the repo grew past ~50 spec/handoff/event files (Cloudflare's free-tier subrequest cap). The dashboard at `https://dual-research.pages.dev/` was rendering build-time-baked content and never refreshing.

## What landed

- **GraphQL batched blob fetch** ([functions/api/data.js:170–211](functions/api/data.js)). Replaced the per-file REST `/git/blobs/<sha>` calls with a single POST to GitHub's GraphQL endpoint that asks for `Repository.object(expression: "<ref>:<path>")` as one aliased field per file. At today's repo state (167 specs + 2 drafts + 21 handoffs + 22 event sidecars = 212 files), that's **one GraphQL POST** instead of 212 REST calls. Net subrequest count drops from `1 + N` to **~2**. Batched at `GRAPHQL_BATCH_SIZE = 400` fields/POST — current state fits in one batch; growth past 400 files cleanly bumps to two POSTs.
- **Poll interval: 15s → 5s** ([scripts/spec_lifecycle/render_dashboard.py:2104](scripts/spec_lifecycle/render_dashboard.py)). The Function returns in ~300–500 ms and is edge-cached for 15s + `stale-while-revalidate=60s`, so most polls hit Cloudflare's cache. Perceived `origin/main` → dashboard latency drops from ~15s to ~5–7s.
- **Regression-prevention test** ([functions/api/data.test.js:142–146](functions/api/data.test.js)). Happy-path test asserts `fetchMock.mock.calls.length === 2` (1 tree REST + 1 GraphQL POST) and asserts both URLs are hit. Any future regression that reintroduces per-file fetches blows the count and trips the test.
- **New error-path test** ([functions/api/data.test.js:175–190](functions/api/data.test.js)). GraphQL response with an `errors` array → 502 with structured error body.

## Tests

- `uv run pytest tests/ -q` — **1534 passed in 19.52s**, zero failures.
- `npm test` (vitest, happy-dom) — **10 passed (10)**: 5 in `functions/api/data.test.js` (happy + 2-subrequest regression / cache hit / tree-401 → 502 / graphql-errors → 502 / missing-token → 502), 1 in `tests/js/dashboard-bootstrap.test.js`, 4 in `tests/js/staleness-chip.test.js`.

## Deploy notes

- **Fly deploy hit the multi-image-cluster gate on the first attempt** (the 0169 handoff's "2 stale machines" follow-up — machine `811e96b9757258` was still on the cluster running an old image). Resolved by `flyctl machine destroy 811e96b9757258 --force --app=dual-research-alex` then retrying `fly deploy`. **Second deploy was clean** — no lease-table errors, all blue→green transitions succeeded, both old machines destroyed normally.
- Post-deploy sweep: **`sweep: no stale blues on dual-research-alex`** — clean cluster.
- `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.30.1","backend":"supabase"}` (confirmed via cache-busted curl).
- **Cloudflare Pages /api/data smoke.** Cloudflare's build trigger from `main` push is async and took ~60–75s to propagate the new code. Polled at 15s intervals: 4× 502 (old code still cached / building) → attempt 5 returned **200** with the full payload (167 specs + 2 drafts + 21 handoffs + 22 event sidecars). GraphQL fetch is working in production.
- **Worktree-lock pattern.** `gh pr merge --admin --squash --delete-branch` failed locally with `'main' is already used by worktree at /Users/alexlisitzky/dual-research-author` — but the GitHub-side merge had already succeeded. Recovered with `git switch --ignore-other-worktrees main && git pull`, then `git push origin --delete spec/...` to clean up the remote branch the gh CLI hadn't gotten to.

## Open follow-ups

- **Fly bluegreen multi-image-cluster keeps recurring.** Tied to the lease-table issue from the 0169 handoff. This deploy was clean only because the stale machine got manually destroyed first. Worth a dedicated spec: either (a) build the stale-image cleanup into a pre-deploy step in the `/dev-next` skill, or (b) file upstream with Fly.
- **Cloudflare Pages build latency is unobservable from our tooling.** The dashboard URL took ~75s to start serving 1.30.1's code after the merge to main. No webhook into our event stream, no logged "Pages build finished" anchor. Cost: when a deploy completes, the dashboard might show 502s for a minute. Acceptable but worth surfacing somewhere if it gets worse.
