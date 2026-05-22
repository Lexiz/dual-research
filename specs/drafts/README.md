# Drafts

Spec ideas captured before they're ready to ship. Each draft is a single file: `draft-NNN-<slug>.md` with `kind: draft` frontmatter.

Drafts:

- Do not reserve a dev spec number.
- Do not create a branch.
- Can carry "Unresolved questions" sections (this is what makes them drafts).
- Are created by the `/spec-draft` skill from an authoring session.
- Are promoted to dev specs via `/spec-promote <draft-id>` once they're complete.

When `/spec-promote` runs, the draft is validated against the dev-spec contract for its declared `type`, any unresolved questions are walked through with the user, and on success the draft file is deleted and a new `specs/NNNN-<slug>.md` is written.

To discard a draft you no longer want: just delete the file.
