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

// Paths that pass the data.js category regexes, in the same order data.js
// concatenates them (specs, drafts, handoffs, events). The GraphQL mock
// produces `f0..fN` aliases keyed off this order.
const FIXTURE_BLOB_PATHS = [
  'specs/0001-foo.md',
  'specs/0002-bar.md',
  'dashboard/events/0001.jsonl',
];

function readFixture(rel) {
  return readFileSync(resolve(FIX_ROOT, rel), 'utf-8');
}

function textForPath(path) {
  if (path === 'specs/0001-foo.md') return readFixture('specs/0001-foo.md');
  if (path === 'specs/0002-bar.md') return readFixture('specs/0002-bar.md');
  if (path === 'dashboard/events/0001.jsonl') return readFixture('events/0001.jsonl');
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
  return vi.fn(async (url, init) => {
    const u = String(url);
    if (overrides.trees && u.includes('/git/trees/')) return overrides.trees;
    if (u.includes('/git/trees/')) return jsonResponse(TREE_BODY);
    if (overrides.graphql && u.endsWith('/graphql')) return overrides.graphql;
    if (u.endsWith('/graphql')) {
      // Sanity: the request should be a POST with a JSON body containing
      // aliased object() fields. We don't inspect the query string deeply,
      // but we do assert it's the expected shape.
      if (!init || init.method !== 'POST') {
        throw new Error('graphql call must be a POST');
      }
      return graphqlResponseFor(FIXTURE_BLOB_PATHS);
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
});
