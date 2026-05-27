---
spec: "0232"
date: 2026-05-27
version: 1.52.0
pr: https://github.com/Lexiz/dual-research/pull/273
---

# Spec 0232 — Verifier I2.6 STATUS-RAISED-array event cross-check

## What landed

`_check_i2_6` adjacent to `_check_i2_5` in [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py), registered in the aggregator after `_check_i2_5(events, turn_files)`. The new invariant compares the count of IDs in each phase-0/2/4 turn file's `RAISED_THIS_TURN` STATUS array against the count of `item_raised` events scoped to the same `(phase, round, raiser)` triple.

Severity `reporting`. Promotion to `gating` is gated on spec 0231 having shipped (done) plus a fresh clean baseline regen against the 054652 / 142625 failing fixtures (separate small spec per §5).

## The directional rule

Spec body was amended mid-implementation per the [2026-05-27 cowork adjudication brief](cowork/briefs/2026-05-27-0232-i2-6-directional-adjudication.md). The original spec text said `declared != registered` flags. Empirically, every OpenAI turn using `[pending]`-style placeholders (clean fixture phase 0 r1 openai: declared 1 / registered 8; 010637 phase 2 r1 openai: declared 7 prose-shaped / registered 7) would have surfaced as fail under equality.

Cowork's resolution: change `!=` to `>`. Only the drop class (`declared > registered`) flags; benign under-reporting (`declared <= registered`) does not. The 142625 phase-2 r1 claude fixture demonstrates why ID-shape inspection (a canonical-ID-skip guard) would have been wrong — five SLUG-shaped declarations registered 0 events, and the directional rule catches that drop because it never inspects ID shape.

Empirical verification across all five fixtures:

| Fixture | I2.6 verdict | Evidence row |
| --- | --- | --- |
| 20260521-010637 (clean) | pass | — |
| 20260525-135006 | pass | — |
| 20260526-102321 | pass | — |
| 20260527-054652 | fail | `phase 2 r1 claude: declared 6 registered 0` |
| 20260527-142625 | fail | `phase 2 r1 claude: declared 5 registered 0` |

## Files touched

- [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py) — `_I26_RAISED_RE` constant + `_check_i2_6` function + aggregator registration.
- [`tests/test_verifier.py`](tests/test_verifier.py) — three synthetic tests (`test_i2_6_count_match_pass`, `test_i2_6_benign_under_report_pass`, `test_i2_6_drop_class_fail`) plus two fixture snapshot tests (`test_snapshot_054652_i2_6_drop_class_fail`, `test_snapshot_142625_i2_6_slug_drop_fail`).
- All five `tests/fixtures/anchor-runs/*/expected.json` baselines grew by one I2.6 entry (matching the table above). The 142625 baseline's special `spec: "0238"` / `note:` annotation preserved.
- [`specs/0232-verifier-i2-6-status-raised-event-cross-check.md`](specs/0232-verifier-i2-6-status-raised-event-cross-check.md) — §2 / §6 / §7 folded the directional resolution.
- [`CHANGELOG.md`](CHANGELOG.md), [`pyproject.toml`](pyproject.toml), [`src/dual_research/__init__.py`](src/dual_research/__init__.py), [`src/dual_research/ui/static/version-notes.json`](src/dual_research/ui/static/version-notes.json), `uv.lock` — MINOR bump 1.51.0 → 1.52.0.

`pytest tests/ -q` → 2181 passed. Deploy `success` on GH Actions run 26530160923. `/api/health` reports `version: 1.52.0`.

## Notes for follow-ups

- **Severity promotion spec.** The promotion-to-gating trigger documented in §6 unblocks now (spec 0231 shipped, and the clean fixture's I2.6 is `pass`). The promotion spec is unblocked the moment **both** conditions hold: (a) 0231 has shipped — done; (b) re-running the verifier against a regenerated 20260527-054652 baseline reports I2.6 as `pass` — pending 0231-aware regen of that fixture. Both are objectively checkable; no fresh design work needed.
- **`gh run watch` exit code 1.** During deploy, the local `gh run watch` exited 1 due to a transient network reset (`connection reset by peer`). The run itself reached `conclusion: success`; both `test/test` and `deploy` jobs succeeded. This is a `gh` client-side behaviour, not a deploy issue. If it recurs frequently, `/dev-next` step 20 should treat watch RC=1 with `conclusion=success` as a non-fatal transient.
