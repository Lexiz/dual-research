# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Version bumps map to the `label` field on each merged spec:

- `breaking` → MAJOR
- `new-feature` → MINOR
- `bug` / `refactoring` / `test` → PATCH

## [Unreleased]

(Nothing yet.)

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
