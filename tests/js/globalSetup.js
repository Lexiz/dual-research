// Spec 0161 — one-time test setup. Runs the Python renderer in shell mode
// against the live repo to produce a clean copy of `dashboard-bootstrap.js`
// and `index.html` in a session-scoped tmp dir. The bootstrap test reads
// those artefacts so we exercise the JS the build actually ships, not a
// copy that could drift.

import { spawnSync } from 'node:child_process';
import { mkdtempSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..', '..');

export default function setup() {
  const outDir = mkdtempSync(join(tmpdir(), 'dr-dashboard-test-'));

  // Render once per session in shell-only mode. We need `uv` on PATH (the
  // existing Python toolchain dependency the rest of the repo assumes).
  const result = spawnSync(
    'uv',
    [
      'run', 'python', '-m', 'scripts.spec_lifecycle.render_dashboard',
      '--repo-root', REPO_ROOT,
      '--out', outDir,
      '--shell-only',
    ],
    { encoding: 'utf-8', cwd: REPO_ROOT },
  );

  if (result.status !== 0) {
    throw new Error(
      `render_dashboard --shell-only failed (status ${result.status}):\n` +
      `stdout: ${result.stdout}\nstderr: ${result.stderr}`,
    );
  }

  if (!existsSync(join(outDir, 'dashboard-bootstrap.js'))) {
    throw new Error(`render did not produce dashboard-bootstrap.js in ${outDir}`);
  }

  // Expose the dir to the test files via env var. Read in tests as
  // `process.env.DR_DASHBOARD_OUT`.
  process.env.DR_DASHBOARD_OUT = outDir;

  // No-op teardown — tmp dirs get cleaned up by the OS.
  return () => {};
}
