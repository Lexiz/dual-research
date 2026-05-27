---
kind: draft
draft_id: "002"
slug: user-facing-classifier-over-flags-context-only-citations
title: "User-facing classifier over-flags entries that cite UI files only for context"
status: draft
created: 2026-05-26
source_session: deferred-from-0220
parent_spec: "0220"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Draft 002 — User-facing classifier over-flags entries that cite UI files only for context

> **Source:** spec 0220 handoff, "Deferred during implementation" — [handoffs/2026-05-26-spec-0220-in-app-changelog-auto-generated.md:49](handoffs/2026-05-26-spec-0220-in-app-changelog-auto-generated.md:49).

## Context

The auto-generated in-app Changelog uses a narrow heuristic to classify each version as user-facing or internal: a version is `user_facing: true` iff any spec it cites has a body that matches the regex `src/dual_research/ui/static/|design-system/`. Implementation at [scripts/build_version_notes.py:222](scripts/build_version_notes.py:222), regex defined at [scripts/build_version_notes.py:58](scripts/build_version_notes.py:58).

This is structurally sound — the narrow heuristic was a deliberate choice over a broader one (`src/dual_research/ui/`) in spec 0220 to avoid classifying backend-only specs as user-facing. Result: 54 of 208 entries (~26%) classify as internal, a defensible default-hide cohort.

But the heuristic still over-flags. A spec body that **mentions** a UI file for context (e.g. "the existing chip-render at `src/dual_research/ui/static/run-detail.jsx:1298`" — quoted from spec 0218's body without that spec actually modifying `run-detail.jsx`) trips the regex and gets classified `user_facing: true`. Net effect: 150 of 208 entries default-visible, more than ideal for a user-oriented changelog surface.

## Why this is a draft, not a spec (yet)

Spec 0220 shipped the structurally correct remediation channel: [src/dual_research/ui/static/version-notes-overrides.json](src/dual_research/ui/static/version-notes-overrides.json) accepts per-entry `user_facing: false` overrides. Any entry that the heuristic mis-classifies can be fixed by hand in the overrides file. This is **triage**, not a code change.

The question is whether to:

1. **Just triage.** Hand-flag the over-reported entries in `version-notes-overrides.json` and call it done. No code change. The override file grows; that's fine — it's what it's for.
2. **Sharpen the classifier.** Move from "spec body matches a UI-path regex" to "spec body has a UI-path citation in §2.N (the change description)" — i.e. parse the spec's structure, distinguish §1 Context citations from §2 Proposed-change citations, only count the latter. More accurate but adds spec-parsing complexity to a build script that's currently pure-regex.
3. **Both.** Land the override flags now, sharpen the classifier later if the override list grows large enough to be unwieldy.

Until we know how often option 1 alone suffices, options 2 and 3 are speculative work.

## Unresolved questions

- **What's the threshold for graduating from option 1 to option 2/3?** Suggest: if the override count exceeds 25 entries flipped from `true` to `false`, the heuristic itself needs sharpening — at that point a hand-curated override per false positive is no longer a small ask. Below 25, just triage.
- **Is structural §-section parsing the right sharpening?** Specs aren't strictly enforced to put change-description citations only in §2 — bug specs cite root-cause locations in §2 and reproduction context in §1, both of which are legitimate UI-touch signals. A structural-section heuristic might trade one over-flag class for another. Alternative: count UI-path citations vs. total citations and threshold by ratio (e.g. `user_facing: true` iff ≥ 25% of cited paths are under UI/DS).
- **Operator triage workflow.** Today the only way to find over-flagged entries is to eyeball the rendered list. A `--report` mode on `scripts/build_version_notes.py` that prints `user_facing: true` entries whose ratio of UI-path citations to total citations is < 10% would surface the candidates for triage without committing to a classifier change.

## Sketch of "just triage" path (option 1)

For each over-flagged entry (eyeball the rendered list at `/#/how-it-works` with the Internal toggle OFF, look for entries whose summary is clearly backend-only), add an entry to `src/dual_research/ui/static/version-notes-overrides.json`:

```json
{
  "1.40.5": { "user_facing": false }
}
```

The build script's per-version override merge ([scripts/build_version_notes.py](scripts/build_version_notes.py)) does full-record replace at merge time — partial overrides like `{"user_facing": false}` flip just that field. Triage pass takes ~30 min for the current 150-entry user-facing cohort; result lands as a single commit.

## Sketch of "sharpen the classifier" path (option 2)

Replace the unconditional `UI_FACING_RE.search(body)` in `classify_user_facing` at [scripts/build_version_notes.py:222](scripts/build_version_notes.py:222) with:

```python
def classify_user_facing(spec_ids: list[str]) -> bool:
    if not spec_ids:
        return True
    for sid in spec_ids:
        matches = list(SPECS_DIR.glob(f"{sid}-*.md"))
        if not matches:
            return True
        body = matches[0].read_text(encoding="utf-8")
        # Extract §2.N body only — that's where actual changes are described.
        proposed_change = re.search(
            r"^##\s+2[\.\s].*?(?=^##\s+\d|\Z)",
            body,
            re.MULTILINE | re.DOTALL,
        )
        if proposed_change and UI_FACING_RE.search(proposed_change.group(0)):
            return True
    return False
```

Add a unit test asserting that a hypothetical spec body with a UI path cited only in §1 Context classifies as `user_facing: false`, and one with a UI path in §2 Proposed change classifies as `user_facing: true`.

## Promotion criteria

Promote this draft to a queued dev spec when **either**:

1. A manual triage pass through `version-notes-overrides.json` lands ≥ 25 entries flipped from `true` to `false` — at that point the override file is clearly carrying load the classifier should be doing, and option 2 or 3 is justified.
2. A new use case for the classification metadata appears (e.g. "auto-tag PRs with `user-facing` based on this signal") — at which point a more accurate classifier is worth investing in regardless of the override count.

Until then: triage by hand via `version-notes-overrides.json` on an ad-hoc basis; this draft documents the structural choice if/when it needs revisiting.
