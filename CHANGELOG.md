# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Version bumps map to the `label` field on each merged spec:

- `breaking` → MAJOR
- `new-feature` → MINOR
- `bug` / `refactoring` / `test` → PATCH

## [Unreleased]

(Nothing yet.)

## [0.5.0] — 2026-05-15

### Added

- **Phases 3 + 4 + final document emission** ([spec 0004](specs/0004-phases-3-4-final.md)) — Phase 3 single-shot drafting by the agreed drafter (hash-verified `agreed_plan_block` + extracted canonical FSDs injected directly into the prompt). Phase 4 turn-based review loop with revised-draft detection (drafter embeds a `## Revised draft` section; orchestrator extracts and writes `draft-vN.md`, bumping `state.draft_round`). Repair flow reused from spec 0003. Soft cap = continue (autonomous); hard cap exits 51 with deadlock appendix in `final.md`. Metadata header rendering (Keep-a-Changelog–style provenance + cost + token totals + confidence tag HIGH/MODERATE/LOW). `final.md` lands in the session directory; `--out PATH` copies it elsewhere. Test-tier E2E demonstrated the Phase 2 hard-cap path cleanly (synthetic brief, test models couldn't hash-match an AGREED_PLAN block within 5 rounds, exit 51 + `phase2-deadlock.md` written). Phase 3 + 4 convergence path is unit-tested with stub agents; a prod-tier E2E to demonstrate the live convergence path is on the spec-0005 verification list. 12 new pytest cases; total: 70 green.

## [0.4.0] — 2026-05-15

### Added

- **Phase 2 — plan negotiation with caps, repair, and drafter tiebreak** ([spec 0003](specs/0003-phase2-negotiation.md)) — turn-based negotiation loop with parallel agent calls per round, written to `phase2/round-NN-{agent}.md`. Convergence detection via `is_plan_agreed` (hash-matched AGREED_PLAN). Drafter tiebreak invocation when substantive gates pass but DRAFTER differs (domain-fit → plan-alignment → hash-of-brief chain). Repair-turn flow with budget=1 per agent per phase + consecutive-failure tracking; second consecutive failure exits 52. Round-1 lenient validation (`assert_well_formed_round1_turn`). Soft cap = logged warning + continue (autonomous mode). Hard cap = `phase2-deadlock.md` emitted, exit 51. Five new event types (`Phase2RoundComplete`, `RepairInvoked`, `SoftCapHit`, `HardCapHit`, `DrafterTiebreakResolved`, `Phase2Complete`). Verified E2E on synthetic brief (4 rounds, genuine convergence after soft-cap warning, $0.29 total, drafter=openai via matching recommendations). 9 new pytest cases; total suite: 58 green.

## [0.3.0] — 2026-05-15

### Added

- **Orchestrator scaffold + Phase 0/1 end-to-end** ([spec 0002](specs/0002-orchestrator-phase01.md)) — session directory layout (`runs/<id>/` with `state.json` + `transcript.jsonl` + `metrics.json` + phase subdirs), atomic state writes, append-only transcript, per-agent cost rollup. Async event bus (`EventBus` with publish/subscribe and failure-isolated delivery). Orchestrator wired to run Phase 0 (preflight, parallel) and Phase 1 (research, parallel) with live cost ticker on stdout. CLI now runs Phases 0 + 1 by default (use `--ingest-only` to stop after brief ingest). Verified end-to-end on a synthetic brief (test tier, $0.03, 68s, two 12K-char Phase 1 drafts produced).

## [0.2.0] — 2026-05-15

### Added

- **Engineering workflow** ([spec 0001](specs/0001-engineering-workflow.md)) — spec-first development, branch-and-PR-per-spec, admin-squash-merge, semver version bumps tied to spec labels (`new-feature`/`bug`/`refactoring`/`test`/`breaking`), CHANGELOG, PR template, and GitHub labels. The first spec is also the spec for the system itself.

## [0.1.0] — 2026-05-15

Initial baseline. Pre-existing commits on `main`, collapsed into a single release entry. No retro specs.

### Added

- Project skeleton: uv-managed Python package, argparse CLI with mutually-exclusive `--prompt`/`--brief`/`--notion` input sources, model tier registry (prod: `claude-sonnet-4-6` 1M + `gpt-5.5`; test: `claude-haiku-4-5` + `gpt-5-mini`), credential loader, `.gitignore`. ([514fac3](https://github.com/Lexiz/dual-research/commit/514fac3))
- Input ingest layer: three modes including recursive Notion-tree fetch via REST API with depth + page caps, markdown block rendering, retry on 429/5xx, distinct 401/404 handling. ([bbfa103](https://github.com/Lexiz/dual-research/commit/bbfa103))
- Per-SDK agent runners: `ClaudeAgent` and `GptAgent` with async streaming, per-call token + USD cost capture, parallel-safe via `asyncio.gather`. Pricing table in `agents/pricing.py`. ([6b050c0](https://github.com/Lexiz/dual-research/commit/6b050c0))
- Protocol module ported from the original `lib/protocol.mjs`: byte-for-byte preservation of the epistemic-duty preamble, V/U source tagging, freshness rule, anti-sycophancy procedures, FSD canonical-section discipline, convergence gates, and repair-prompt structure. Adapted plumbing only (file paths → inlined content, MCP references → SDK-native phrasing). 36 pytest cases covering parsers, well-formedness assertions, convergence, hash tolerance, and tiebreak chain. Fixes two latent regex/parser bugs that existed in the original. ([4ff2af1](https://github.com/Lexiz/dual-research/commit/4ff2af1))
