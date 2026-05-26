---
spec: "0208"
date: 2026-05-24
version: 1.44.7
pr: https://github.com/Lexiz/dual-research/pull/240
---

# Spec 0208 — Fix: provider chip dim in critique → promote identity tones into base Chip

## What landed

The 30 % `color-mix` tint and light-mode text token that made identity chips legible — previously scoped to `.tl-card-head` and `.item-card__lifecycle-section .lc-row-chips` — are now the BASE `.chip.tone-claude` / `.chip.tone-gpt` rule. Three previously-broken consumers (critique card head, DS gallery at `/#/language`, how-it-works pane) now render readable identity chips. Two-file lockstep maintained: base rules added to the DS-side `composed-components.css` (where they were missing entirely — its `.tl-card-head` override had been stranded), scoped overrides removed from both files.

### Files touched

- [src/dual_research/ui/static/components.css](src/dual_research/ui/static/components.css:144) — base `.chip.tone-claude` / `.chip.tone-gpt` updated to `color-mix(... var(--p-{sable,sage}) 30%, transparent)`; `.tl-card-head` claude/gpt scopes deleted; `.lc-row-chips` claude/gpt scopes deleted; light-mode hex backstop replaced with global `body.light .chip.tone-{claude,gpt}` rule reading `--md-on-{primary,secondary}-container`.
- [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css:570) — base `.chip.tone-claude` / `.chip.tone-gpt` rules added (DS file previously had no base for these tones); same scoped overrides + hex backstop removed as the live-app file.
- [design-system/SPEC.md](design-system/SPEC.md) — §3 Primitives gains a new "Identity-chip rendering rule" paragraph documenting the forbidden-override structural rule; §4.4 chip-polish table shrunk to the two System-only rows; §2.6 light-mode-backstop paragraph rewritten to point at the global rule.
- [tests/test_spec_0208_chip_identity_tones.py](tests/test_spec_0208_chip_identity_tones.py) — new source-pattern test file (spec 0206 doctrine), 8 assertions covering post-fix shape + antipodal absence across both stylesheets + SPEC.md.
- [CHANGELOG.md](CHANGELOG.md), [pyproject.toml](pyproject.toml), [src/dual_research/__init__.py](src/dual_research/__init__.py) — 1.44.6 → 1.44.7.

### Tests

`uv run pytest tests/ -q` — 1880 passed (8 new tests in `test_spec_0208_chip_identity_tones.py`).

## Deploy notes

**Initial deploy hit lease drift.** First `fly deploy` failed with `Failed to acquire lease for 2870421c037148` and `Failed to acquire lease for 2873d39cd92438` — leases held by `tokens.fly.io` with expiries at 11:59:23Z / 12:00:24Z respectively. At deploy time the cluster was in a pre-existing oddly-divergent state: the started machine (v683) was on image `01KSCXDNKE0HAR6M1N7DESHSAK` (older than the latest release `01KSCXEGYA05A0A293CTHY1SBK`, which was sitting on the stopped machine v684). Per spec 0200 §2.2 the orchestrator marked `status=failed failure_step=deploy` and halted without retrying.

**User authorized a retry once leases expired.** The second `fly deploy` ran cleanly with the rolling strategy: both machines updated to `deployment-01KSCXJJYD26EEEZFX3M8RHGRJ`, lease acquired + cleared on both. The "WARNING The app is not listening on the expected address" smoke nuisance fired once on machine 2870421c037148 but the subsequent machine + health check passed (`HTTP/2 200` on `/`).

**Sweep:** `sweep: no stale blues on dual-research-alex` — no stale machines under the rolling strategy.

**Smoke verification:** `curl https://dual-research-alex.fly.dev/components.css?v=0181a | grep "color-mix(in srgb, var(--p-sable) 30%, transparent)"` returned a match — the new base rule is live on the served CSS.

## What to watch next

- **Fly lease-drift recurrence.** This is the second `/dev-next` cycle in recent memory that hit lease drift on the first deploy attempt. The user has flagged it as worth investigating ("fly, every single time" — see also [project_fly_lease_drift_recovery.md](~/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md)). A follow-up spec to root-cause why lease drift recurs (rolling-strategy timing, machine-config drift, `tokens.fly.io`-held leases not being released cleanly) is likely the right next move — defer to the next planning cycle.
- **Identity-chip rendering parity** across all five consumers (Timeline head, Critique head, Critique lifecycle rows, DS gallery, how-it-works pane). The source-pattern tests lock the CSS shape; a visual spot-check on the live app is worth doing before assuming pixel parity.
