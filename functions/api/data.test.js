// Spec 0161 — Pages Function unit tests.
//
// Exercises functions/api/data.js's onRequest handler across three paths:
//   - happy: tree + blobs return fixtures → JSON payload shape correct
//   - cache hit: caches.default.match returns a Response → onRequest
//     returns it without calling fetch
//   - error: trees fetch returns 401 → onRequest returns 502 with
//     structured error body
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

function readFixture(rel) {
  return readFileSync(resolve(FIX_ROOT, rel), 'utf-8');
}

function toBase64(s) {
  // Node's atob round-trips base64 the Function expects from the blobs API.
  return Buffer.from(s, 'utf-8').toString('base64');
}

function blobBodyFor(sha) {
  if (sha === 'sha-0001-spec') return { content: toBase64(readFixture('specs/0001-foo.md')), encoding: 'base64' };
  if (sha === 'sha-0002-spec') return { content: toBase64(readFixture('specs/0002-bar.md')), encoding: 'base64' };
  if (sha === 'sha-0001-events') return { content: toBase64(readFixture('events/0001.jsonl')), encoding: 'base64' };
  throw new Error(`unexpected blob sha: ${sha}`);
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

function makeFetchMock(overrides = {}) {
  return vi.fn(async (url) => {
    const u = String(url);
    if (overrides.trees && u.includes('/git/trees/')) return overrides.trees;
    if (u.includes('/git/trees/')) return jsonResponse(TREE_BODY);
    const m = u.match(/\/git\/blobs\/([\w-]+)/);
    if (m) return jsonResponse(blobBodyFor(m[1]));
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
  // Re-import the module each test so module-scope state doesn't bleed.
  vi.resetModules();
  // The Function uses the global `caches.default` reference at import time
  // is fine — it's called per-request. Stash + restore globals so we don't
  // pollute the vitest worker.
  originalCaches = globalThis.caches;
  originalFetch = globalThis.fetch;
  ({ onRequest } = await import('./data.js'));
});

afterEach(() => {
  globalThis.caches = originalCaches;
  globalThis.fetch = originalFetch;
});

describe('Pages Function /api/data', () => {
  it('happy path — returns 200 with spec/event/handoff payload', async () => {
    const cacheStub = makeCachesStub();
    globalThis.caches = { default: cacheStub };
    globalThis.fetch = makeFetchMock();

    const ctx = makeContext({ cache: cacheStub });
    const res = await onRequest(ctx);

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.specs).toHaveLength(2);
    expect(body.events['0001']).toHaveLength(1);
    expect(body.events['0001'][0].step).toBe('in_progress');
    expect(body.generated_at).toBeTruthy();
    expect(new Date(body.generated_at).toString()).not.toBe('Invalid Date');

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

  it('error case — upstream 401 produces a 502 with structured error body', async () => {
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
