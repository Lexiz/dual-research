---
kind: dev
spec: "0230"
slug: reconciler-skip-out-of-tree-paths
title: "Reconciler: configurable prefix-skip list (default `cowork/`) treats out-of-tree citations as informational, eliminating the spurious exit-3 class for specs citing external Cowork briefs"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0227.1"]
complexity: S
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Fixes a recurring false-positive class — pre-flight reconcile already required a manual override on specs 0227.1 and 0229; the third repeat in a row is the trigger to ship the fix rather than the workaround."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0230 — Reconciler: skip out-of-tree prefix paths

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0227.1 (reconciler display-text skip — same author surface)
> **Bump:** MINOR — new configurable behaviour (a prefix-skip list with a default value); observable change is `cowork/`-prefixed citations no longer trip `has_blocking_drift`.
> **Evidence:** Spec 0229 implementation handoff at [`handoffs/2026-05-27-spec-0229-addressee-obligation-invariant.md:31`](handoffs/2026-05-27-spec-0229-addressee-obligation-invariant.md) — pre-flight reconcile reported 3 semantic-drift hits all citing `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md`; operator override was required to proceed. Spec 0227.1 handoff records the same operator-override pattern from one cycle earlier (a different but adjacent false-positive class for the same reconciler).

---

## 1. Context

The reconciler at [`scripts/spec_lifecycle/reconcile.py:74-108`](scripts/spec_lifecycle/reconcile.py:74) classifies every extracted citation against the on-disk repo tree. Citations whose path neither exists at `repo_root / cit.path` nor matches a basename in `git ls-files` are bucketed as `semantic` — a single one flips `has_blocking_drift` to `True`, mapping to CLI exit-code 3 and a `/dev-next` halt per [`reconcile.py:153-166`](scripts/spec_lifecycle/reconcile.py:153). The check is intentionally strict for in-tree citations and has worked well for that class.

The class of citations the project conventions actively encourage — references to `cowork/briefs/...` or `cowork/feedback/...` — sit outside the repo by design. The CLAUDE.md "Cowork channel lives outside the repo" memory and the project memory file at `~/.claude/projects/.../cowork_channel_lives_outside_repo.md` both direct authors to use `../cowork/...` or `cowork/...` paths. Every such citation lands in the `semantic` bucket because no `cowork/` directory is tracked in the repo (`_find_candidates` at [`scripts/spec_lifecycle/reconcile.py:126-137`](scripts/spec_lifecycle/reconcile.py:126) only sees `git ls-files` output). Spec 0227.1 closed one variant of this false-positive class (citations buried inside markdown-link display text). Spec 0229 hit the same class one cycle later from the href side: pre-flight reconcile reported 3 hits on `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:NNN` — bare prose citations whose path is a legitimate `cowork/` reference, scrubbed neither by the display-text skip of 0227.1 nor by any other rule. The implementer manually overrode exit 3 in both cases.

This is the third recurrence in two cycles. The reconciler should grow a configurable prefix-skip list — default `["cowork/"]` — and treat citations whose path begins with any listed prefix as informational (logged as an `out_of_tree` bucket for visibility) rather than feeding them into the `clean / mechanical / semantic` classifier. This closes the override habit before it becomes load-bearing.

### Source-artifact traceability

| source item | source quote/ref | spec section |
|---|---|---|
| Spec 0229 deferral 1 — "Reconciler should skip out-of-tree paths" | `handoffs/2026-05-27-spec-0229-addressee-obligation-invariant.md:31` | §2.1 + §2.2 |
| Pre-flight reconcile false-positive at spec 0229 | same handoff §"Deferred during implementation" first bullet | §1 second paragraph |
| Spec 0227.1 (the adjacent prior fix to the same surface) | `specs/0227.1-reconciler-skip-markdown-link-display-text-citations.md` | §2 strategy pattern + §6 R3 |
| CLAUDE.md Cowork channel convention | `CLAUDE.md` "Cowork channel lives outside the repo" / user memory `cowork_channel_lives_outside_repo.md` | §1 second paragraph |

## 2. Proposed change

### 2.1 — Add a module-level `OUT_OF_TREE_PREFIXES` constant + a per-call override

Add to [`scripts/spec_lifecycle/reconcile.py`](scripts/spec_lifecycle/reconcile.py), near the existing module-level regexes at [`reconcile.py:25-29`](scripts/spec_lifecycle/reconcile.py:25):

```python
# Spec 0230 §2.1 — citations whose path begins with any of these prefixes are
# treated as informational rather than fed into the clean/mechanical/semantic
# classifier. Cowork artefacts live outside the repo by CLAUDE.md convention
# (the "Cowork channel lives outside the repo" subsection); without this skip
# every spec body citing `cowork/briefs/...` trips a false-positive exit-3.
OUT_OF_TREE_PREFIXES: tuple[str, ...] = ("cowork/",)
```

The tuple is the default; callers that need a different skip set pass `out_of_tree_prefixes=(...)` to `reconcile_spec`. Default is canonical — most callers (including the `/dev-next` step and the CLI `main`) use it untouched.

### 2.2 — Add an `out_of_tree` bucket to `ReconcileReport`

Extend the dataclass at [`scripts/spec_lifecycle/reconcile.py:58-72`](scripts/spec_lifecycle/reconcile.py:58):

```python
@dataclass
class ReconcileReport:
    spec_path: Path
    clean: list[Citation] = field(default_factory=list)
    mechanical: list[Citation] = field(default_factory=list)
    semantic: list[Citation] = field(default_factory=list)
    out_of_tree: list[Citation] = field(default_factory=list)  # NEW
    ...
```

`has_drift` and `has_blocking_drift` are unchanged — out-of-tree citations contribute to neither. The new bucket is purely informational and surfaces in `format_report` for operator visibility.

### 2.3 — Route prefix-matched citations into the new bucket before classification

Modify the classification loop at [`scripts/spec_lifecycle/reconcile.py:80-107`](scripts/spec_lifecycle/reconcile.py:80) so the prefix check fires before the on-disk existence check. Pseudo-shape:

```python
for cit in citations:
    if any(cit.path.startswith(p) for p in out_of_tree_prefixes):
        cit.classification = "out_of_tree"
        cit.note = f"path begins with skip-list prefix; not classified against tree"
        report.out_of_tree.append(cit)
        continue
    target = root / cit.path
    if target.exists():
        # … existing clean / mechanical logic unchanged
```

The `Citation.classification` string-enum grows one value, `"out_of_tree"`, alongside the existing `"clean" / "mechanical" / "semantic" / "unknown"` set documented at [`reconcile.py:52`](scripts/spec_lifecycle/reconcile.py:52).

### 2.4 — Surface the bucket in `format_report`

Extend [`format_report`](scripts/spec_lifecycle/reconcile.py:140) at lines 140-150 to include a one-line summary `"  out-of-tree (informational): {n}"` after the `clean:` line, plus per-citation detail lines under it. The line is emitted unconditionally (matching the existing `clean / mechanical / semantic` lines, which also emit when their lists are empty).

### 2.5 — Reconcile-CLI exit-code contract unchanged

`main` at [`reconcile.py:153-166`](scripts/spec_lifecycle/reconcile.py:153) continues to return 3 on `has_blocking_drift` and 0 otherwise. Because `out_of_tree` is excluded from `has_blocking_drift`, a spec whose only "drift" is cowork citations now exits 0 — the override pattern observed on specs 0227.1 and 0229 is no longer needed.

### 2.6 — Version bump + CHANGELOG

PATCH-aware: this adds a new field on a public dataclass and a new value on a string-enum; both are additive. Per [CLAUDE.md](CLAUDE.md) "Versioning and CHANGELOG", `new-feature` → MINOR.

- Bump [`src/dual_research/__init__.py`](src/dual_research/__init__.py) `__version__`.
- Bump [`pyproject.toml`](pyproject.toml) `version`.
- Add a `## [X.Y.Z] — YYYY-MM-DD` section to [`CHANGELOG.md`](CHANGELOG.md) with one `### Added` bullet: "Reconciler: `OUT_OF_TREE_PREFIXES` default `('cowork/',)`; matching citations route into a new `out_of_tree` informational bucket and do not contribute to `has_blocking_drift`. Closes the spurious exit-3 class for specs citing external Cowork briefs ([spec 0230](specs/0230-reconciler-skip-out-of-tree-paths.md))."

## 3. User stories & acceptance criteria

Not a UI-touching spec — User stories / BDD scenarios omitted per template (§3 is REQUIRED only for frontend specs).

Implementer-facing acceptance criteria:

- `uv run python -m scripts.spec_lifecycle.reconcile specs/0229-addressee-obligation-invariant.md` returns exit 0 (today it returns 3); the rendered report shows the 3 prior `semantic` hits now under `out-of-tree (informational)`.
- `uv run python -m scripts.spec_lifecycle.reconcile specs/0227-reclassify-contract-amending-specs-and-process-rule.md` returns exit 0 (matches the post-0227.1 result; the 0227.1 fix targets display text, this fix targets href prefixes — both apply).
- `uv run pytest tests/ -q` passes with new tests covering the prefix-skip behaviour.

## 4. Data / Schema deltas

No on-disk schema changes. The `ReconcileReport` dataclass grows one field (`out_of_tree: list[Citation]`); the `Citation.classification` string-enum gains one value (`"out_of_tree"`). Both changes are additive and backwards-compatible with any external reader (the field is initialised to an empty list; existing callers that only read `clean / mechanical / semantic` see no behavioural change beyond fewer entries in `semantic` for cowork-citing specs).

## 5. Out of scope

- **Verifying that out-of-tree paths exist relative to the spec's parent directory** (e.g., literally checking `../cowork/...` is on disk). The CLAUDE.md memory `cowork_channel_lives_outside_repo.md` notes that anything inside `dual-research/cowork/` is swept by the next pre-flight stash, so the canonical location is `../cowork/...` — outside the repo and outside the queue worktree's filesystem traversal. Verifying it would require a path resolution relative to the spec file plus a filesystem call per citation, with no rollback story when the operator runs `/dev-next` from a different worktree. Deferred to a future spec if/when the project decides to git-track `cowork/` (the same deferral target as spec 0227.1 §5).
- **Adding a CLI flag (`--out-of-tree-prefixes`)** to override the default list per-invocation. The default `("cowork/",)` covers 100% of observed cases over two cycles. Adding a flag invites premature configurability. Deferred to a future spec if a second class emerges (e.g., a sibling project that also lives outside the repo).
- **Re-running reconcile retroactively on archived specs** to identify which historical handoffs had operator overrides applied for cowork citations. Forensically interesting but not load-bearing. Deferred to a dashboard audit, not a code spec.
- **Renaming the `semantic` bucket or restructuring the report's bucket taxonomy.** The fix is additive — one new bucket alongside the existing three. A taxonomy refactor would be a `refactoring` spec carved separately if a future class requires it.

## 6. Test plan

- [ ] **Unit — prefix-matched citation lands in `out_of_tree`.** New test in `tests/test_spec_0230_reconciler_out_of_tree.py`: construct a spec body containing the literal string `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:42` (bare prose, no markdown link). Reconcile against a tmp repo root that does NOT contain a `cowork/` directory. Assertion: `report.out_of_tree` has exactly one entry with `path == "cowork/briefs/2026-05-26-logic-cutoff-synthesis.md"` and `line == 42`; `report.semantic == []`; `report.has_blocking_drift is False`.
- [ ] **Unit — non-matching path still classifies normally.** Body: `src/nonexistent/file.py:1`. Reconcile against a tmp repo root. Assertion: `report.semantic` has one entry; `report.out_of_tree == []`; `report.has_blocking_drift is True`.
- [ ] **Unit — custom prefix list overrides the default.** Reconcile with `out_of_tree_prefixes=("../external/",)`. Body: `cowork/briefs/foo.md:1` (now NOT in the skip list) and `../external/notes.md:1` (now IN the skip list). Assertion: the first lands in `semantic`, the second in `out_of_tree`.
- [ ] **Unit — empty skip list reverts to pre-fix behaviour.** Reconcile with `out_of_tree_prefixes=()`. Body: `cowork/briefs/foo.md:1`. Assertion: lands in `semantic` (the pre-0230 baseline).
- [ ] **Source-pattern test — `OUT_OF_TREE_PREFIXES` constant is defined at module level.** Read `scripts/spec_lifecycle/reconcile.py` as text; positive regex: `OUT_OF_TREE_PREFIXES\s*[:=].*"cowork/"`; antipodal-absence regex: no occurrence of `report.semantic.append(cit)` directly inside an unconditional branch (the pre-fix shape would have unconditionally semantic-bucketed every unresolved path).
- [ ] **Regression — spec 0229 reconcile exits 0.** `python -m scripts.spec_lifecycle.reconcile specs/0229-addressee-obligation-invariant.md` returns 0 (pre-fix: returns 3). Add as a subprocess-invoking integration test guarded by the spec file existing.
- [ ] **CHANGELOG + version smoke check.** Assert version bumped and CHANGELOG contains the new entry referencing `[spec 0230]`.

## 7. Risks

- **R1 — A legitimate in-tree `cowork/` path is silently skipped.** If the project ever git-tracks a `cowork/` directory (e.g., a small in-repo cowork-tooling subdir), citations to it would land in `out_of_tree` rather than `clean`, masking real drift. *Mitigation:* the `out_of_tree` bucket is surfaced in `format_report` with full per-citation detail (path + line). An operator reading the report sees exactly which paths were skipped. If `cowork/` ever becomes git-tracked, the default tuple is updated in the same commit that introduces the directory. The skip is opt-in by prefix, not by directory-not-found heuristic, so the change is auditable in one place.
- **R2 — Authors stop noticing real cowork-side drift** because the bucket is informational. Out-of-tree citations remain unverified (the repo cannot check `../cowork/foo.md:42` exists relative to anything). *Mitigation:* this is the pre-existing state — today's `semantic` classification doesn't verify the file exists either; it just halts because `repo_root / "cowork/foo.md"` is not on disk. The new bucket makes the impossibility of verification explicit rather than masquerading as a verifiable check that always fails.
- **R3 — Prefix matching is too coarse.** A citation like `cowork-design-system/file.py:1` (hypothetical sibling directory whose name starts with `cowork`) would be skipped if the prefix is `cowork/`. *Mitigation:* the prefix includes the trailing slash (`"cowork/"`), so `cowork-design-system/...` does NOT match. The default is structurally narrow. The escape valve is the `out_of_tree_prefixes` parameter for any caller that needs a different set.
- **R4 — Spec 0227.1's display-text scrubber and this fix overlap.** A markdown-link citation like `[cowork/briefs/foo.md:1](cowork/briefs/foo.md:1)` would have its display text scrubbed by 0227.1 and its href captured by 0230's skip-list. *Mitigation:* the layering is correct — 0227.1 removes the display-text shadow first, then the href runs through the classifier which routes it to `out_of_tree`. Both fixes compose; the test in §6 explicitly covers a bare-prose `cowork/` citation (no markdown link) to exercise the layer that 0227.1 doesn't touch.
