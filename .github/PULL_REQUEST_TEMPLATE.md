<!-- PR title should match the spec title exactly. It becomes the squash-merge subject on `main`. -->

## Spec

Implements [`specs/NNNN-<slug>.md`](./specs/NNNN-<slug>.md).

<!-- Required: apply ONE of these GitHub labels to this PR -->
<!-- spec/new-feature | spec/bug | spec/refactoring | spec/test | spec/breaking -->

## Summary

One or two sentences. The full rationale lives in the spec.

## Changes

- Bullet
- Bullet
- Bullet

## Version

- Spec label: `<label>`
- Version bump: `<MAJOR | MINOR | PATCH>`
- Old → new: `X.Y.Z → X.Y.Z`

## Checklist

- [ ] Spec file exists at `specs/NNNN-<slug>.md` with status `merged` and `pr:` populated
- [ ] `pyproject.toml` version bumped
- [ ] `src/dual_research/__init__.py` `__version__` bumped
- [ ] `CHANGELOG.md` updated under the new version heading
- [ ] GitHub `spec/*` label applied to this PR
- [ ] Tests pass locally (`uv run pytest`)
- [ ] Branch named `spec/NNNN-<slug>` to match the spec
