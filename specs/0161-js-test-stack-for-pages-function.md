---
kind: dev
spec: "0161"
slug: js-test-stack-for-pages-function
title: "Tests: JS test stack for Pages Function and dashboard-bootstrap.js"
type: test
label: test
version_bump: PATCH
target_version: 1.23.1
status: merged
queue_position: 1
depends_on: []
complexity: M
created: 2026-05-22
queued_at: ""
started_at: "2026-05-22T14:58:36Z"
merged_at: "2026-05-22T15:04:00Z"
deployed_at: ""
pr: "https://github.com/Lexiz/dual-research/pull/184"
handover: ""
failure_step: ""
source_session: deferred-from-spec-0160
promoted_from_draft: ""
---

# Spec 0161 — Tests: JS test stack for Pages Function and dashboard-bootstrap.js

> **Type:** test  |  **Complexity:** M
> **Bump:** PATCH — test additions only, plus the node tooling needed to run them.
> **Evidence:** Spec 0160 §6 listed four JS tests (`functions/api/data.test.js` × 3 cases + `dashboard/site/dashboard-bootstrap.test.js` × 1 case) but they were deferred during implementation because the repo has no node test stack. See `handoffs/2026-05-22-spec-0160-dashboard-live-data-via-pages-function.md:77` ("Deferred during implementation"). The Python renderer tests (`tests/spec_lifecycle/test_render_dashboard_shell_only.py`, `tests/spec_lifecycle/test_render_dashboard_default_still_works.py`) cover the build-time shell contract, but the runtime JS — the Pages Function at `functions/api/data.js` and the bootstrap-JS string constant baked into the renderer — is currently exercised only via the manual checks from spec 0160's test plan. Spec 0160's deferral note is the explicit prompt for this follow-up.

---

## 1. Coverage gap

Two production surfaces have zero automated coverage today:

- **`functions/api/data.js:39`** — the `onRequest` handler is the live-data backbone for the dashboard. It does an edge-cache lookup (`functions/api/data.js:45`), a fine-grained PAT check (`functions/api/data.js:48`), a `git/trees/?recursive=1` fetch + N parallel `git/blobs/{sha}` fetches (`functions/api/data.js:92` and `functions/api/data.js:111`), YAML frontmatter parsing (`functions/api/data.js:199`), and shapes the JSON response with a `generated_at` ISO timestamp (`functions/api/data.js:149`). Every code path here is currently exercised only by hitting `/api/data` against the live Cloudflare Pages deployment.
- **`scripts/spec_lifecycle/render_dashboard.py:1457`** — the `DASHBOARD_BOOTSTRAP_JS` string constant (~280 lines) is written verbatim to `dashboard-bootstrap.js` in the build output at `scripts/spec_lifecycle/render_dashboard.py:1833`. It fetches `/api/data`, paints the five live `[data-region]` sections (`scripts/spec_lifecycle/render_dashboard.py:1715` and the following lines for queue / feed / drafts / all-specs), polls every 15s, and falls back to `localStorage` on error. None of the painting logic is covered by automated tests today.

The Python renderer tests added in spec 0160 cover the build-time shell contract (skeleton markers present, no spec content leaks, scripts referenced) but they cannot exercise the JS that runs in the browser or the Function that runs at the edge.

## 2. Test approach

Add a node-based unit test stack. Four tests across two files, run via `vitest`.

### 2.1 — Tooling additions

- `package.json` at repo root (new). Declares the test stack as **devDependencies** only:
  ```json
  {
    "name": "dual-research-js-tests",
    "private": true,
    "type": "module",
    "scripts": { "test": "vitest run" },
    "devDependencies": {
      "vitest": "^1.6.0",
      "happy-dom": "^14.0.0"
    }
  }
  ```
  Pinned major versions. No production JS dependencies — the Pages Function and bootstrap script remain zero-dep in production (the hand-rolled YAML parser noted in spec 0160's handoff "Deviations" stays in place; this spec does not reverse that decision).
- `vitest.config.js` at repo root (new). Configures two environments via test-file globs: node-default for `functions/**/*.test.js`, `happy-dom` for `dashboard/site/**/*.test.js`.
- `.gitignore` adds `node_modules/`.
- `Makefile` gets a `test-js` target: `cd $(REPO_ROOT) && npm install --no-audit --no-fund && npm test`. The existing default `test` target (Python `uv run pytest tests/ -q`) is unchanged — JS tests run on opt-in via `make test-js`, not as part of the default Python suite.
- CI wiring is **out of scope** (see §5) — this spec ships the local runner only. The deferred decision is whether to add the JS suite to `.github/workflows/`, which the user can pick up in a follow-up once we have one cycle of running it locally.

### 2.2 — `functions/api/data.test.js` (vitest, node environment)

Three cases, exactly matching spec 0160 §6:

1. **Happy path.** Mock the global `fetch` to return:
   - `/repos/Lexiz/dual-research/git/trees/main?recursive=1` → a `tree` array containing two `specs/0001-*.md` and `specs/0002-*.md` blobs plus one `dashboard/events/0001.jsonl` blob.
   - Each `git/blobs/{sha}` call → the corresponding fixture body (frontmatter for specs, one JSONL line for the event sidecar).
   - Stub `caches.default` with `match: () => undefined` and `put: () => undefined`.
   - Provide `env.GITHUB_TOKEN = 'fake'`.
   - Assert: response `status === 200`; parsed body has `specs.length === 2`, `events["0001"].length === 1`, `generated_at` is a valid ISO 8601 string (`new Date(body.generated_at).toString() !== 'Invalid Date'`).
2. **Cache hit.** Same setup, but `caches.default.match` returns a pre-built `Response`. Assert the handler returns that cached response and `fetch` was never called (`expect(fetchMock).not.toHaveBeenCalled()`).
3. **Error case.** Mock the trees-API fetch to return `{ status: 401 }`. Assert the handler returns status `502`, content-type `application/json`, body parses to an object with an `error` key (string) and `generated_at: null`.

### 2.3 — `dashboard/site/dashboard-bootstrap.test.js` (vitest, happy-dom environment)

One case, exactly matching spec 0160 §6:

- Extract the bootstrap-JS source into a runnable form. Two options; pick (b):
  - (a) Copy the `DASHBOARD_BOOTSTRAP_JS` constant into a checked-in `dashboard/site/dashboard-bootstrap.js` source file and have `render_dashboard.py` read from it. Adds a coupling between build and test layouts.
  - (b) **Chosen.** Write a tiny test helper that calls `python -m scripts.spec_lifecycle.render_dashboard --shell-only --repo-root . --out <tmp>` once before the test suite (via `vitest`'s `globalSetup`), then the test loads the emitted `dashboard-bootstrap.js` from the tmp dir. This keeps the constant as the single source of truth and tests the artefact actually shipped.
- Test body:
  - Bootstrap a `happy-dom` document with the shell HTML (also generated by the same `--shell-only` render: load `index.html` from the tmp dir).
  - Stub `window.fetch` to return a fixture `/api/data` payload: two specs (one `status: in_progress`, one `status: queued`), one handoff, one event for the in-progress spec.
  - Execute the bootstrap JS in the document context (`new Function(jsSource).call(window)` or equivalent).
  - Advance any pending microtasks; assert:
    - `[data-region="queue"] table tbody tr` count matches the number of queued specs in the fixture.
    - `[data-region="hero"]` contains the slug or title of the in-progress spec.

### 2.4 — Fixtures

- `tests/js/fixtures/specs/0001-foo.md`, `tests/js/fixtures/specs/0002-bar.md`, `tests/js/fixtures/events/0001.jsonl`, `tests/js/fixtures/handoffs/2026-01-01-spec-0001-foo.md`. Each fixture is the minimal frontmatter shape the Function's parser handles (`scripts/spec_lifecycle/render_dashboard.py:1457` JS mirrors the Python-side shape; the Function's parser is at `functions/api/data.js:199`).
- Fixtures live under `tests/js/fixtures/` so they don't get picked up by `pytest`'s collector. A `pytest` `conftest.py` already exists at `tests/conftest.py`; verify it doesn't recurse into `tests/js/` (default pytest collection only matches `test_*.py` so we're safe, but add an explicit `collect_ignore = ["js"]` if pytest noise appears).

## 3. What it would catch

Concrete failure modes this coverage prevents:

- **YAML parser regressions in the Pages Function.** The hand-rolled parser at `functions/api/data.js:199` handles our schema but not nested mappings or block scalars (per spec 0160's "Deviations from the spec body" note). If a future spec adds a frontmatter shape the parser doesn't handle, the happy-path test would catch the breakage at PR time instead of after deploy.
- **Cache-key drift.** If a future change to `onRequest` accidentally varies the cache key (e.g. by including a `Date` header), the cache-hit test would catch it — the second request would re-fetch instead of returning the stub `Response`.
- **Error-path silent success.** If `errorResponse` (`functions/api/data.js:74`) stops returning `502` because of a refactor (e.g. someone wraps the JSON body in a redirect), the error case would catch it. Currently the bootstrap script's localStorage fallback depends on a non-2xx response to trigger.
- **Bootstrap renderer drift vs. the data shape.** The bootstrap script reads `payload.specs[*].status` and groups by it to populate queue / feed / drafts (`scripts/spec_lifecycle/render_dashboard.py` around line 1715–1725). If the Function's response shape changes (e.g. renames `status` to `state`) without the bootstrap being updated, the dashboard goes blank silently. The happy-dom test would fail loudly.
- **`localStorage` cache-key collision.** The bootstrap uses `CACHE_KEY = 'dr-dashboard-data-v1'` (`scripts/spec_lifecycle/render_dashboard.py:1469`). If that constant is renamed but the stale-data fallback path still reads the old key, returning users would see no cached data on the first failed fetch. happy-dom tests can simulate a primed cache and assert the fallback works.

The historical analogue: spec 0156 introduced a meta-refresh that spec 0160 retired; the only thing that caught the meta-refresh assertion change at PR time was the renderer test. Without JS-side tests, an equivalent removal on the bootstrap side (e.g. someone deletes the polling loop) would only be caught manually.

## 4. Risks

- **Flakiness from happy-dom timing.** happy-dom's microtask queue can be ordered differently than a real browser's. Mitigation: use `vi.useFakeTimers()` and flush explicitly via `vi.runAllTimersAsync()`; avoid asserting on `setTimeout`-delayed UI without advancing the timer.
- **Slow test runs from `globalSetup` calling Python.** Running the renderer once per test session is acceptable (~1s on the live fixtures). Running it per test would be too slow — `globalSetup` runs once.
- **False confidence from over-mocking the Function.** The mocked `fetch` returns ideal-shaped responses; real GitHub responses can be larger / truncated (`tree.truncated` flag). The happy-path test asserts the happy path; spec 0160 §7 already documents the rate-limit risk and the response-truncation mitigation lives in production code, not in tests. Acceptable — the unit tests here are about regression detection, not about exhaustively simulating GitHub.
- **New tooling surface (`package.json` + `npm install`).** Brings a `node_modules/` tree into local dev (gitignored). Mitigation: pinned versions; no transitive native compilation in `vitest` or `happy-dom`; install runs only when the user opts in via `make test-js`.

## 5. Out of scope

- **CI wiring.** This spec ships the local runner only. Adding a `.github/workflows/js-tests.yml` job is deferred until we have at least one local cycle confirming the suite works. Do not add CI in this PR.
- **Production JS dependencies.** No `package.json` `dependencies` field — only `devDependencies`. The Pages Function and bootstrap stay zero-dep in production. Replacing the hand-rolled YAML parser with the [`yaml`](https://www.npmjs.com/package/yaml) npm package (spec 0160 §2.1, "Deviations") stays deferred.
- **Tests for per-spec page bootstrap.** Spec 0160 §5 explicitly excludes live-data for `spec-NNNN.html` pages; no JS to test on those.
- **Tests for `dashboard-live.js`** (`scripts/spec_lifecycle/render_dashboard.py:1400`). Existing pre-spec-0160 file. Its per-second ticker logic is exercised end-to-end via the dashboard; bringing it under unit tests is a separate, larger spec.
- **Snapshot/regression tests for the painted HTML.** The happy-dom test asserts presence of rows and the hero label — not pixel-perfect or HTML-snapshot identity. Snapshot churn would dominate signal.
- **End-to-end tests against the live Pages deployment.** This spec is unit-level only. The manual checks from spec 0160 §6 remain the integration-level verification.
- **Adding `playwright` or any browser test runner.** happy-dom is the lightest tool that exercises DOM mutations; full browser automation is overkill for two test cases.

## 6. Test plan

The artefact this spec produces *is* the test plan. Acceptance:

- [ ] `npm install && npm test` (run via `make test-js`) exits 0 with at least 4 passing tests across `functions/api/data.test.js` (3) and `dashboard/site/dashboard-bootstrap.test.js` (1).
- [ ] The default Python suite still passes (`uv run pytest tests/ -q`) — no collection regressions from the new `tests/js/fixtures/` tree.
- [ ] `make test-js` works from a clean checkout (no global `vitest` or `npm` config dependencies).
