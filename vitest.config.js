// Spec 0161 — vitest config for the JS test stack.
//
// Two environments selected per test-file glob:
//   - node (default) for `functions/**/*.test.js` — exercises the Pages
//     Function with a stubbed `fetch` and `caches`.
//   - `happy-dom` for `dashboard/site/**/*.test.js` — DOM-mutation tests
//     for the bootstrap script.
//
// `globalSetup.js` runs `python -m scripts.spec_lifecycle.render_dashboard
// --shell-only` once per test session so the bootstrap test can load the
// emitted `dashboard-bootstrap.js` and `index.html` from a tmp dir. That
// keeps DASHBOARD_BOOTSTRAP_JS (in render_dashboard.py) as the single
// source of truth for the JS we ship.

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    // Spec 0161 — bootstrap tests live under `tests/js/` (not
    // `dashboard/site/` where the spec body referenced them) because
    // `dashboard/site/` is gitignored as the build output dir; the spec's
    // path was a naming convention, not a hard requirement.
    include: ['functions/**/*.test.js', 'tests/js/**/*.test.js'],
    globalSetup: ['./tests/js/globalSetup.js'],
    environmentMatchGlobs: [
      ['tests/js/dashboard-bootstrap.test.js', 'happy-dom'],
      ['functions/**/*.test.js', 'node'],
    ],
    testTimeout: 10_000,
  },
});
