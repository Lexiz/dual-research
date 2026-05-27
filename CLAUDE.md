# CLAUDE.md — dual-research project conventions

This file is auto-loaded by every Claude Code session opened in this repo. It encodes the standing rules that apply to **all** work here — manual edits, scripted runs, and the spec-driven `/dev-next` cycle alike.

## Design system

The dual-research design system is canonical. Before touching anything that will land under `src/dual_research/ui/static/` or `design-system/`:

- **Read `design-system/SPEC.md` first.** It is the single source of truth for tokens, primitives, composed components, palette, density, motion, badge governance, and accessibility. The neighboring `design-system/README.md` is the entry-point pointer.
- **Tokens only for color.** No hex codes inside `src/dual_research/ui/static/components.css` or `design-system/assets/styles/composed-components.css`. Read from `--md-*` and `--p-*` CSS custom properties defined in `design-system/assets/styles/tokens-and-primitives.css`.
- **New components land in two places in one commit.** Authoritative definition in `design-system/assets/styles/composed-components.css`; live-app copy in `src/dual_research/ui/static/components.css`. The two files MUST stay in sync — if you add a class to one, add it to the other in the same commit.
- **Live primitives reference.** Browse the running primitives at the `/#/language` route on the live app (`https://dual-research-alex.fly.dev/#/language`) when reasoning about how a component looks.
- **DS gate at spec time.** Specs that propose UI work must cite the relevant `design-system/SPEC.md` section / primitive for each proposed element. Specs that touch UI without a DS citation will be flagged by `/dev-next` step 15 before any code lands.

## Versioning and CHANGELOG

Every merged PR ships a version bump and a CHANGELOG entry. This rule applies to PRs from `/dev-next` AND to manual PRs.

- **Bump `pyproject.toml` and `src/dual_research/__init__.py`** per the spec's `version_bump` field (or pick the bump explicitly on manual PRs):
  - `breaking` → MAJOR
  - `new-feature` → MINOR
  - `bug` / `refactoring` / `test` → PATCH
- **Write a new `## [X.Y.Z] — YYYY-MM-DD` section in `CHANGELOG.md`** directly under the `## [Unreleased]` heading (or, equivalently, treat each spec as its own release — no `[Unreleased]` accumulation). The first ## heading below the file header should be the version this PR ships.
- **Bullet content under `### Added` / `### Changed` / `### Removed` / `### Fixed`.** Link to the spec under which the work landed when one exists (e.g. `[spec 0154](specs/0154-orchestrator-hardening-ds-steering-and-queue-runner.md)`).

## Spec workflow

Five skills drive the spec lifecycle. Use them — do not improvise.

- `/spec-draft` — park an idea. Writes `specs/drafts/draft-NNN-<slug>.md` from the author worktree. Drafts may carry unresolved questions.
- `/spec-queue` — turn the current authoring conversation into a queued dev spec. Classifies type, runs the validator, commits `specs/NNNN-<slug>.md` with `status: queued` to `main`. No branch.
- `/spec-promote <id>` — promote a draft into a queued dev spec. Walks unresolved questions, restructures into the type template, validates, commits.
- `/dev-next` — drive **one** queued dev spec end-to-end from the queue session at `/Users/alexlisitzky/dual-research/`. Pre-flight → reconcile → branch → implement → tests → PR → admin squash-merge → watch GH Actions deploy → handoff. Deploys to `dual-research-alex.fly.dev` are driven by `.github/workflows/deploy.yml` on push-to-main; `/dev-next` watches the GH Actions run rather than invoking `flyctl` locally (spec 0211).
- `/dev-queue-run` — drive **the whole queue** sequentially from the same queue session. Single confirmation at start, halts on first failure.

Two-worktree split:

- **Authoring worktree** at `/Users/alexlisitzky/dual-research-author/` — where `/spec-draft`, `/spec-queue`, `/spec-promote` run. Stays on `main`.
- **Queue worktree** (this checkout) at `/Users/alexlisitzky/dual-research/` — where `/dev-next` and `/dev-queue-run` run. Operates from a detached HEAD at `origin/main`; cuts feature branches off that HEAD during `/dev-next`. Never holds the `main` ref locally — all main-side writes (queue state, handoffs, archive) go through the push-via-plumbing helper in `scripts/spec_lifecycle/queue_state.py` (spec 0210).

`/dev-next` and `/dev-queue-run` refuse to run from the authoring worktree; the spec-creation skills refuse to run from the queue worktree.

### Contract-changing specs are not `bug`s

A spec that introduces, removes, or modifies behaviour in **any** of:

- phase mechanics (entry / exit / artifact);
- convergence rules or the closeout / escape-valve partition;
- the lifecycle state machine (states, edges, terminal rules);
- the categorisation taxonomy (kinds, ID format, namespace);
- any first-class event type;
- **any verifier invariant (gating or reporting)** — including invariants introduced or modified at implementation time, not just at spec-authoring time;

— must carry a `new-feature`, `breaking`, or `refactoring` label, **not** `bug`. A `bug` label is an assertion of "no contract change"; it should be reviewable on exactly that claim.

Drift was the root cause of the 0114 → 0219 thrash: 0137, 0140, 0218, and 0219 all amended the contract under a `bug` label, hiding the change. See `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md` §5 MF1 for the full diagnosis. The verifier (spec 0225) is the executable form of the contract — its invariants ARE the contract. Implementation-cycle additions to that invariant set count as contract changes too.

### Carve-out follow-ups must triage at carve-out time

When implementing a spec produces a follow-up spec (a "noticed during implementation" carve-out), the carve-out's frontmatter must include a `disposition:` field set to one of `ship` / `defer` / `archive`, with a one-sentence `disposition_reason:`. Default disposition is `archive`. A carve-out reaches `/dev-next` only when its disposition is `ship`. This forces triage at the moment of carving rather than letting the carve-out accrete into the queue and consume a `/dev-next` cycle by default.

The 200+ spec corpus this project carries is partly the result of follow-ups shipping without triage. The discipline this section names is what stops the pattern.

## Dashboard

The spec dashboard at `https://lexiz.github.io/dual-research/` is regenerated by `.github/workflows/dashboard.yml` on every push to `main`. The renderer is `scripts/spec_lifecycle/render_dashboard.py`. Data sources: spec frontmatter (`specs/*.md`), handoff frontmatter (`handoffs/*.md`), and per-spec event sidecars (`dashboard/events/NNNN.jsonl`).

## Tests

Default test runner: `uv run pytest tests/ -q`. New features land with tests where the type warrants. Refactoring specs preserve behavior — their test plan asserts no behavior change.

**UI test doctrine (spec 0206).** UI specs lock anatomy via **source-pattern tests** at `tests/test_spec_NNNN_<surface>.py` — one test pair per anatomical contract (positive regex on the post-fix shape + antipodal-absence regex on the pre-fix shape), pure stdlib, via the helpers at [`tests/_ui_pattern_helpers.py`](tests/_ui_pattern_helpers.py). Runtime rendering is verified via Claude Preview MCP screenshot in the PR description (for ItemCard-touching specs, spec 0179's 8-capture parity grid is mandatory). Playwright / DOM-rendering harnesses are not used — see [`design-system/SPEC.md` §13](design-system/SPEC.md#13--ui-test-doctrine-spec-0206) for the rationale and the trigger that would revisit it.

### Live-failure fix discipline (spec 0238)

A spec whose stated cause-of-death is a captured live-run failure MUST
include at least one test that exercises the **real entry point** of
the failing call path against the captured artifact (e.g. invoke
`parse_turn_v2` on the captured turn file). Function-level unit tests
that exercise a helper are insufficient on their own — they let a fix
land on the wrong function and pass.

Worked example: spec 0231 patched `extract_fenced_section` and tested
it in isolation. The live failure surfaced via `parse_turn_v2 →
_extract_section_body → SECTION_*_RE` — a path the 0231 tests never
exercised. The patch passed CI and the same bug class re-emerged on
the very next live run (spec 0238 root cause). The rule above prevents
the same shape of miss going forward.
