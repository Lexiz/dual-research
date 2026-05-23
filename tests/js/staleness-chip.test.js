// Spec 0163 §2.4 — staleness chip tone thresholds in dashboard-bootstrap.js.
//
// Strategy mirrors dashboard-bootstrap.test.js: load the built artefact,
// inject the shell HTML, stub fetch with fixtures that vary the latest event
// timestamp relative to a fixed "now", run the IIFE, assert the chip's class
// and data-last-event-at attribute.

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

const NOW = new Date('2026-05-22T12:00:00Z').getTime();

function fixture(eventTsIsoOrSecondsAgo) {
  const eventTs = typeof eventTsIsoOrSecondsAgo === 'number'
    ? new Date(NOW - eventTsIsoOrSecondsAgo * 1000).toISOString()
    : eventTsIsoOrSecondsAgo;
  return {
    generated_at: new Date(NOW).toISOString(),
    specs: [
      {
        number: '0001', slug: 'foo', title: 'Fixture spec', type: 'new-feature',
        status: 'in_progress', target_version: '0.1.0',
        depends_on: [], complexity: 'S', created: '2026-05-22',
        queued_at: '2026-05-22T10:00:00Z', started_at: '2026-05-22T11:00:00Z',
        merged_at: '', deployed_at: '', pr: '', handover: '',
        failure_step: '', source_session: 'fixture', promoted_from_draft: '',
      },
    ],
    drafts: [],
    handoffs: [],
    events: {
      '0001': [
        { ts: '2026-05-22T11:00:00Z', step: 'cycle_started', data: {} },
        { ts: eventTs, step: 'implementing_started', data: {} },
      ],
    },
  };
}

async function paintAndGetChip(payload) {
  const { html, js } = loadArtefacts();
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  document.body.innerHTML = bodyMatch[1];

  globalThis.fetch = vi.fn(async (url) => {
    if (!String(url).endsWith('/api/data')) {
      throw new Error(`unexpected fetch URL: ${url}`);
    }
    return new Response(JSON.stringify(payload), {
      status: 200, headers: { 'content-type': 'application/json' },
    });
  });

  vi.spyOn(Date, 'now').mockReturnValue(NOW);
  // eslint-disable-next-line no-new-func
  new Function(js)();

  await vi.waitFor(() => {
    const chip = document.querySelector('[data-last-event-at]');
    expect(chip).toBeTruthy();
  }, { timeout: 2000 });

  return document.querySelector('[data-last-event-at]');
}

describe('staleness chip (spec 0163 §2.4)', () => {
  beforeEach(() => {
    if (typeof localStorage !== 'undefined') localStorage.clear();
    vi.restoreAllMocks();
  });

  it('tone-ok when the latest event is < 30s old', async () => {
    const chip = await paintAndGetChip(fixture(5));
    expect(chip.classList.contains('tone-ok')).toBe(true);
    expect(chip.classList.contains('tone-warn')).toBe(false);
    expect(chip.classList.contains('tone-err')).toBe(false);
    expect(chip.textContent).toMatch(/last event 5s ago/);
  });

  it('tone-warn when the latest event is 30s–2min old', async () => {
    const chip = await paintAndGetChip(fixture(90));
    expect(chip.classList.contains('tone-warn')).toBe(true);
    expect(chip.classList.contains('tone-ok')).toBe(false);
    expect(chip.classList.contains('tone-err')).toBe(false);
  });

  it('tone-err when the latest event is > 2min old', async () => {
    const chip = await paintAndGetChip(fixture(300));
    expect(chip.classList.contains('tone-err')).toBe(true);
    expect(chip.classList.contains('tone-warn')).toBe(false);
    expect(chip.classList.contains('tone-ok')).toBe(false);
  });

  it('hero carries data-current-step with the latest event step name', async () => {
    const { html, js } = loadArtefacts();
    document.body.innerHTML = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i)[1];
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify(fixture(5))));
    vi.spyOn(Date, 'now').mockReturnValue(NOW);
    // eslint-disable-next-line no-new-func
    new Function(js)();
    await vi.waitFor(() => {
      const hero = document.querySelector('.hero--inflight');
      expect(hero).toBeTruthy();
    });
    const hero = document.querySelector('.hero--inflight');
    expect(hero.getAttribute('data-current-step')).toBe('implementing_started');
    expect(hero.textContent).toMatch(/currently · implementing/);
  });
});
