// Spec 0161 — Pages Function unit tests.
// Spec 0174 — fixtures updated for the GraphQL-batched blob fetch.
//
// Exercises functions/api/data.js's onRequest handler across:
//   - happy: tree REST + GraphQL POST return fixtures → JSON payload shape
//     correct, AND the total subrequest count is exactly 2 (regression-
//     prevention test for the spec-0174 subrequest blowup).
//   - cache hit: caches.default.match returns a Response → onRequest
//     returns it without calling fetch.
//   - upstream error: trees fetch returns 401 → onRequest returns 502 with
//     a structured error body.
//   - missing GITHUB_TOKEN: 502 with a helpful message.
//
// `caches.default` is a Cloudflare Workers global — vitest's node env
// doesn't expose it. We stub it as a global with the two methods onRequest
// uses (`match`, `put`). `fetch` is the global, mocked per-test.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIX_ROOT = resolve(__dirname, '..', '..', 'tests', 'js', 'fixtures');

const TREE_BODY = {
  tree: [
    { path: 'specs/0001-foo.md', sha: 'sha-0001-spec', type: 'blob' },
    { path: 'specs/0002-bar.md', sha: 'sha-0002-spec', type: 'blob' },
    { path: 'dashboard/events/0001.jsonl', sha: 'sha-0001-events', type: 'blob' },
    // Filtered-out blobs to confirm the regex gates are exercised.
    { path: 'README.md', sha: 'sha-readme', type: 'blob' },
    { path: 'docs/', sha: 'sha-docs', type: 'tree' },
  ],
};

// Spec 0203.1 §3.1 — TREE_BODY variant that includes queue-state.json so
// the layering + events-merge paths can be exercised end-to-end.
const TREE_BODY_WITH_QUEUE_STATE = {
  tree: [
    { path: 'specs/0001-foo.md', sha: 'sha-0001-spec', type: 'blob' },
    { path: 'specs/0002-bar.md', sha: 'sha-0002-spec', type: 'blob' },
    { path: 'dashboard/events/0001.jsonl', sha: 'sha-0001-events', type: 'blob' },
    { path: 'dashboard/queue-state.json', sha: 'sha-queue-state', type: 'blob' },
  ],
};

// Paths that pass the data.js category regexes, in the same order data.js
// concatenates them (specs, drafts, handoffs, events). The GraphQL mock
// produces `f0..fN` aliases keyed off this order.
const FIXTURE_BLOB_PATHS = [
  'specs/0001-foo.md',
  'specs/0002-bar.md',
  'dashboard/events/0001.jsonl',
];

// Spec 0203.1 §3.1 — queue-state.json is appended LAST to allBlobs in
// data.js so existing alias indices stay stable.
const FIXTURE_BLOB_PATHS_WITH_QUEUE_STATE = [
  'specs/0001-foo.md',
  'specs/0002-bar.md',
  'dashboard/events/0001.jsonl',
  'dashboard/queue-state.json',
];

const QUEUE_STATE_FIXTURE = {
  version: 1,
  updated_at: '2026-05-24T01:55:00Z',
  specs: {
    // Spec 0001 — frontmatter is frozen at 'in_progress' (per fixture),
    // queue-state flips it to 'deployed' and adds deployed_at + pr.
    '0001': {
      status: 'deployed',
      queued_at: '2026-01-01T00:00:00Z',
      started_at: '2026-01-01T00:00:10Z',
      deployed_at: '2026-01-01T01:00:00Z',
      pr: 'https://example/pr/1',
      events: [
        { ts: '2026-01-01T00:00:00Z', step: 'queued', data: {} },
        { ts: '2026-01-01T00:00:10Z', step: 'in_progress', data: {} },
        // Spec 0203.1 §3.2 — these step names must round-trip through
        // the response unchanged for the dashboard's vocab to render
        // them correctly.
        { ts: '2026-01-01T00:30:00Z', step: 'checkpoint_written',
          data: { next_subsection: '2.5', completed_subsections: ['2.1', '2.2'] } },
        { ts: '2026-01-01T01:00:00Z', step: 'deployed', data: { version: '0.1.0' } },
      ],
    },
    '0002': {
      status: 'queued',
      queued_at: '2026-01-02T00:00:00Z',
      events: [
        { ts: '2026-01-02T00:00:00Z', step: 'queued', data: {} },
      ],
    },
  },
};

function readFixture(rel) {
  return readFileSync(resolve(FIX_ROOT, rel), 'utf-8');
}

function textForPath(path) {
  if (path === 'specs/0001-foo.md') return readFixture('specs/0001-foo.md');
  if (path === 'specs/0002-bar.md') return readFixture('specs/0002-bar.md');
  if (path === 'dashboard/events/0001.jsonl') return readFixture('events/0001.jsonl');
  if (path === 'dashboard/queue-state.json') return JSON.stringify(QUEUE_STATE_FIXTURE);
  throw new Error(`unexpected blob path: ${path}`);
}

function graphqlResponseFor(paths) {
  const repository = {};
  paths.forEach((p, i) => {
    repository[`f${i}`] = { text: textForPath(p), isBinary: false };
  });
  return jsonResponse({ data: { repository } });
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

function makeFetchMock(overrides = {}) {
  const treesBody = overrides.treesBody || TREE_BODY;
  const blobPaths = overrides.blobPaths || FIXTURE_BLOB_PATHS;
  return vi.fn(async (url, init) => {
    const u = String(url);
    if (overrides.trees && u.includes('/git/trees/')) return overrides.trees;
    if (u.includes('/git/trees/')) return jsonResponse(treesBody);
    if (overrides.graphql && u.endsWith('/graphql')) return overrides.graphql;
    if (u.endsWith('/graphql')) {
      // Sanity: the request should be a POST with a JSON body containing
      // aliased object() fields. We don't inspect the query string deeply,
      // but we do assert it's the expected shape.
      if (!init || init.method !== 'POST') {
        throw new Error('graphql call must be a POST');
      }
      return graphqlResponseFor(blobPaths);
    }
    throw new Error(`fetch mock got unexpected URL: ${u}`);
  });
}

function makeCachesStub({ match = async () => undefined } = {}) {
  return {
    match: vi.fn(match),
    put: vi.fn(async () => undefined),
  };
}

function makeContext({ env = { GITHUB_TOKEN: 'fake-pat' }, cache } = {}) {
  return {
    env,
    request: new Request('https://dr-dashboard.pages.dev/api/data'),
    waitUntil: vi.fn(),
    _cache: cache,
  };
}

let onRequest;
let originalCaches;
let originalFetch;

beforeEach(async () => {
  vi.resetModules();
  originalCaches = globalThis.caches;
  originalFetch = globalThis.fetch;
  ({ onRequest } = await import('./data.js'));
});

afterEach(() => {
  globalThis.caches = originalCaches;
  globalThis.fetch = originalFetch;
});

describe('Pages Function /api/data', () => {
  it('happy path — returns 200 with payload AND uses exactly 2 subrequests (spec 0174 regression test)', async () => {
    const cacheStub = makeCachesStub();
    globalThis.caches = { default: cacheStub };
    const fetchMock = makeFetchMock();
    globalThis.fetch = fetchMock;

    const ctx = makeContext({ cache: cacheStub });
    const res = await onRequest(ctx);

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.specs).toHaveLength(2);
    expect(body.events['0001']).toHaveLength(1);
    expect(body.events['0001'][0].step).toBe('in_progress');
    expect(body.generated_at).toBeTruthy();
    expect(new Date(body.generated_at).toString()).not.toBe('Invalid Date');

    // Spec 0174 regression-prevention: exactly 2 subrequests total —
    // 1 REST tree call + 1 GraphQL POST. Any future regression that
    // reintroduces per-file fetches (1 + N) blows this number and trips
    // the test.
    expect(fetchMock.mock.calls.length).toBe(2);
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.some((u) => u.includes('/git/trees/'))).toBe(true);
    expect(urls.some((u) => u.endsWith('/graphql'))).toBe(true);

    // Cache write was scheduled.
    expect(ctx.waitUntil).toHaveBeenCalledTimes(1);
    // Verify the response carries the expected cache-control header so
    // Cloudflare's edge honours the 15s freshness window.
    expect(res.headers.get('cache-control')).toContain('max-age=15');
    expect(res.headers.get('cache-control')).toContain('stale-while-revalidate=60');
  });

  it('cache hit — returns the cached response without calling fetch', async () => {
    const cachedBody = JSON.stringify({ specs: [], events: {}, generated_at: '2026-01-01T00:00:00Z' });
    const cachedResponse = new Response(cachedBody, {
      status: 200,
      headers: { 'content-type': 'application/json', 'x-cache': 'HIT' },
    });
    const cacheStub = makeCachesStub({ match: async () => cachedResponse });
    globalThis.caches = { default: cacheStub };
    const fetchMock = makeFetchMock();
    globalThis.fetch = fetchMock;

    const res = await onRequest(makeContext({ cache: cacheStub }));

    expect(res).toBe(cachedResponse);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('error case — upstream 401 on the tree call produces a 502 with structured error body', async () => {
    const cacheStub = makeCachesStub();
    globalThis.caches = { default: cacheStub };
    globalThis.fetch = makeFetchMock({
      trees: new Response('{"message":"Bad credentials"}', {
        status: 401,
        headers: { 'content-type': 'application/json' },
      }),
    });

    const res = await onRequest(makeContext());

    expect(res.status).toBe(502);
    expect(res.headers.get('content-type')).toContain('application/json');
    const body = await res.json();
    expect(typeof body.error).toBe('string');
    expect(body.error.length).toBeGreaterThan(0);
    expect(body.generated_at).toBeNull();
  });

  it('error case — GraphQL POST returns an `errors` array → 502 with structured error body', async () => {
    const cacheStub = makeCachesStub();
    globalThis.caches = { default: cacheStub };
    globalThis.fetch = makeFetchMock({
      graphql: jsonResponse({
        data: null,
        errors: [{ message: 'Field too large' }],
      }),
    });

    const res = await onRequest(makeContext());
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.error).toMatch(/graphql/);
  });

  it('missing GITHUB_TOKEN — 502 with helpful error', async () => {
    // Bonus assertion that locks in the auth-precondition path noted in
    // spec 0160's HOSTING.md troubleshooting section.
    const cacheStub = makeCachesStub();
    globalThis.caches = { default: cacheStub };
    globalThis.fetch = makeFetchMock();

    const res = await onRequest(makeContext({ env: {} }));
    expect(res.status).toBe(502);
    const body = await res.json();
    expect(body.error).toMatch(/GITHUB_TOKEN/);
  });

  // Spec 0203.1 §3.1 — queue-state.json fetch + layering regression test.
  it('layers queue-state.json over frontmatter and exposes queue_state_updated_at', async () => {
    const cacheStub = makeCachesStub();
    globalThis.caches = { default: cacheStub };
    const fetchMock = makeFetchMock({
      treesBody: TREE_BODY_WITH_QUEUE_STATE,
      blobPaths: FIXTURE_BLOB_PATHS_WITH_QUEUE_STATE,
    });
    globalThis.fetch = fetchMock;

    const res = await onRequest(makeContext({ cache: cacheStub }));
    expect(res.status).toBe(200);
    const body = await res.json();

    // Cycle-mutable fields from queue-state.json win over frozen frontmatter.
    const spec0001 = body.specs.find((s) => s.number === '0001');
    expect(spec0001).toBeTruthy();
    expect(spec0001.status).toBe('deployed');             // queue-state wins
    expect(spec0001.pr).toBe('https://example/pr/1');     // queue-state added
    expect(spec0001.deployed_at).toBe('2026-01-01T01:00:00Z');

    // Shape-immutable fields from frontmatter survive the merge.
    expect(spec0001.slug).toBe('foo');
    expect(spec0001.type).toBe('new-feature');

    // Events: queue-state.json wins over the legacy sidecar bucket. The
    // sidecar fixture has 1 event; the queue-state entry has 4. The
    // `checkpoint_written` step must round-trip unchanged.
    expect(body.events['0001']).toHaveLength(4);
    const stepNames = body.events['0001'].map((e) => e.step);
    expect(stepNames).toContain('checkpoint_written');

    // Response envelope carries the queue-state freshness anchor.
    expect(body.queue_state_updated_at).toBe('2026-05-24T01:55:00Z');

    // Still exactly 2 subrequests — queue-state.json rides the same
    // GraphQL batch (one more aliased field), not a new REST call.
    expect(fetchMock.mock.calls.length).toBe(2);
  });

  // Spec 0203.1 §3.1 — defensive: malformed queue-state.json must NOT
  // 502 the API; the response should fall back to the legacy path.
  it('falls back gracefully when queue-state.json is malformed', async () => {
    const cacheStub = makeCachesStub();
    globalThis.caches = { default: cacheStub };
    const fetchMock = vi.fn(async (url, init) => {
      const u = String(url);
      if (u.includes('/git/trees/')) return jsonResponse(TREE_BODY_WITH_QUEUE_STATE);
      if (u.endsWith('/graphql')) {
        // Build a GraphQL response that returns valid JSON for the spec
        // and event blobs, but garbage for queue-state.json.
        const repository = {};
        FIXTURE_BLOB_PATHS_WITH_QUEUE_STATE.forEach((p, i) => {
          const text = p === 'dashboard/queue-state.json'
            ? '{not valid json'
            : textForPath(p);
          repository[`f${i}`] = { text, isBinary: false };
        });
        return jsonResponse({ data: { repository } });
      }
      throw new Error(`fetch mock got unexpected URL: ${u}`);
    });
    globalThis.fetch = fetchMock;

    const res = await onRequest(makeContext({ cache: cacheStub }));
    expect(res.status).toBe(200);
    const body = await res.json();

    // Fallback: spec 0001 keeps its frontmatter status (in_progress per
    // the fixture) since queue-state didn't parse; events come from the
    // sidecar bucket (1 entry).
    const spec0001 = body.specs.find((s) => s.number === '0001');
    expect(spec0001.status).toBe('in_progress');
    expect(body.events['0001']).toHaveLength(1);
    expect(body.queue_state_updated_at).toBeNull();
  });
});
