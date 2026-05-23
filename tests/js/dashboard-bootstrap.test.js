// Spec 0161 — bootstrap-script unit test (happy-dom).
//
// We don't import the bootstrap script via ES `import` because it's an IIFE
// without exports, and it's the build-emitted artefact (from the
// DASHBOARD_BOOTSTRAP_JS string constant in render_dashboard.py) that we
// actually want to exercise. Strategy:
//   1. globalSetup.js runs the renderer in --shell-only mode once per
//      session and exposes the output dir via DR_DASHBOARD_OUT.
//   2. This test reads index.html + dashboard-bootstrap.js from that dir.
//   3. Stub window.fetch to return a fixture payload.
//   4. Inject the shell HTML body into happy-dom's document.
//   5. Execute the IIFE source via `new Function()` and let it paint.
//   6. Assert the [data-region="queue"] table and [data-region="hero"]
//      content match the fixture's queued spec / in-flight spec.

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function loadArtefacts() {
  const out = process.env.DR_DASHBOARD_OUT;
  if (!out) throw new Error('DR_DASHBOARD_OUT not set — did globalSetup run?');
  return {
    html: readFileSync(join(out, 'index.html'), 'utf-8'),
    js: readFileSync(join(out, 'dashboard-bootstrap.js'), 'utf-8'),
  };
}

const fixturePayload = () => ({
  generated_at: '2026-01-01T12:00:00Z',
  specs: [
    {
      number: '0001',
      slug: 'foo',
      title: 'In-flight fixture spec',
      type: 'new-feature',
      status: 'in_progress',
      target_version: '0.1.0',
      depends_on: [],
      complexity: 'S',
      created: '2026-01-01',
      queued_at: '2026-01-01T00:00:00Z',
      started_at: '2026-01-01T11:00:00Z',
      merged_at: '',
      deployed_at: '',
      pr: '',
      handover: '',
      failure_step: '',
      source_session: 'fixture',
      promoted_from_draft: '',
    },
    {
      number: '0002',
      slug: 'bar',
      title: 'Queued fixture spec',
      type: 'bug',
      status: 'queued',
      target_version: '0.1.1',
      depends_on: [],
      complexity: 'S',
      created: '2026-01-02',
      queued_at: '2026-01-02T00:00:00Z',
      started_at: '',
      merged_at: '',
      deployed_at: '',
      pr: '',
      handover: '',
      failure_step: '',
      source_session: 'fixture',
      promoted_from_draft: '',
    },
  ],
  drafts: [],
  handoffs: [{ spec: '0001', date: '2026-01-01', version: '0.1.0', pr: '' }],
  events: {
    '0001': [{ ts: '2026-01-01T11:00:00Z', step: 'in_progress', data: {} }],
  },
});

describe('dashboard-bootstrap.js (happy-dom)', () => {
  beforeEach(() => {
    // happy-dom resets between tests via vitest's environment, but we still
    // clear any localStorage state from a prior run.
    if (typeof localStorage !== 'undefined') localStorage.clear();
  });

  it('paints the queue table and in-flight hero from /api/data fixture', async () => {
    const { html, js } = loadArtefacts();

    // Strip everything outside <body>…</body> so document.body innerHTML
    // contains the shell's data-region containers.
    const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
    if (!bodyMatch) throw new Error('shell HTML missing <body>');
    document.body.innerHTML = bodyMatch[1];

    // Stub fetch BEFORE the IIFE runs.
    const fetchMock = vi.fn(async (url) => {
      if (!String(url).endsWith('/api/data')) {
        throw new Error(`unexpected fetch URL: ${url}`);
      }
      return new Response(JSON.stringify(fixturePayload()), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    globalThis.fetch = fetchMock;

    // Execute the IIFE in the global scope. The script wraps itself in
    // (function () { ... })() so direct eval-like execution paints the
    // current document.
    // eslint-disable-next-line no-new-func
    new Function(js)();

    // The script kicks off via setInterval + an immediate refresh; await
    // the microtask queue + the fetch promise to flush.
    await vi.waitFor(() => {
      const queueRows = document.querySelectorAll('[data-region="queue"] .qrow:not(.qrow--header):not(.qrow--empty)');
      expect(queueRows.length).toBe(1);
    }, { timeout: 2000 });

    // Hero shows the in-flight spec.
    const heroText = document.querySelector('[data-region="hero"]').textContent;
    expect(heroText).toMatch(/In-flight fixture spec/);
    expect(heroText).toMatch(/0001/);

    // The hero's inner skeleton lines have been replaced by real content.
    // (Note: the bootstrap script swaps innerHTML but leaves the outer
    // `class="region-skeleton"` attribute on the wrapper. That keeps the
    // pulse animation visible underneath the painted content — flagging
    // as deferred in this cycle's handoff so a follow-up spec can drop
    // the class on swap.)
    const hero = document.querySelector('[data-region="hero"]');
    expect(hero.innerHTML).not.toMatch(/skeleton__line/);
    expect(hero.querySelector('.hero')).toBeTruthy();

    // Header `data-last-updated` got rewritten with a relative time.
    const updated = document.querySelector('[data-last-updated]');
    expect(updated.textContent).toMatch(/updated .*/);

    expect(fetchMock).toHaveBeenCalled();
  });
});
