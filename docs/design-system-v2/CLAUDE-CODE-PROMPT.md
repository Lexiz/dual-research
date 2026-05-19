# Prompt for Claude Code — open the PR, then plan

Paste the block below into Claude Code's working directory's chat (where it has push access to `Lexiz/dual-research`). It does two things in sequence: (1) opens the PR carrying the briefing + design-system bundle, (2) reads the briefing and responds with a spec plan.

---

```
You have a PR-ready bundle waiting for you. It's a folder called `pr/` that the user just downloaded as a zip (most likely sitting in `~/Downloads/pr.zip` or `~/Downloads/Dual-research dashboard pr.zip`, with the exact name depending on the user's browser).

If you can't find the bundle:
1. Ask the user where the zip is. Common locations: `~/Downloads/`, the current working dir, or `/tmp/`.
2. Unzip it into the dual-research repo root. The unzipped folder is `pr/`.
3. If after unzipping the folder is still not at `pr/`, ask the user to confirm the path. Do not guess.

The bundle contains a briefing README and the new Material 3 design system. Your job has two phases.

PHASE 1 — Open the PR.

1. In the Lexiz/dual-research repo, create a new branch off main called `design-system-v2-briefing`.
2. Commit the contents of the unzipped `pr/` bundle under `docs/design-system-v2/` at the repo root, preserving the folder structure:
     docs/design-system-v2/README.md                       ← the briefing
     docs/design-system-v2/CLAUDE-CODE-PROMPT.md           ← this prompt, for the record
     docs/design-system-v2/assets/Design System v2.html    ← canonical visual reference
     docs/design-system-v2/assets/styles/v2-m3.css         ← M3 token + primitive CSS
     docs/design-system-v2/assets/styles/v2-m3-page.css    ← page-level component CSS
   Use commit message: "docs(design-system): add v2 (Material 3) briefing + canonical reference".
3. Push the branch and open a pull request against main with:
   - Title: "Design System v2 (Material 3) — briefing + canonical reference"
   - Body: link to docs/design-system-v2/README.md and a one-line summary that says this PR is a briefing-only PR; no application code changes; the deliverable for review is the spec plan in Phase 2.
4. Reply in this chat with the PR URL once it's open.

PHASE 2 — Read the briefing, then plan.

Open `docs/design-system-v2/README.md` and read it end-to-end. Open the design system HTML at `docs/design-system-v2/assets/Design System v2.html` in a browser. Pull the Notion page (link inside the README, section §5) via your Notion connector and pull each screenshot from S3 so you can compare the current implementation to the spec.

Your deliverable is a spec plan. Tell me, at the top of your response:

> N specifications.

Where N is your count. Then list every spec with: # · title · scope · references (Notion issue numbers + design-system anchors like #critique, #consumption) · depends-on · backend-touched (almost always no — flag explicitly when yes) · rough complexity (S / M / L).

Sequence the plan: token layer first, then primitive components (buttons, chips, status pills, cards, badges), then composed components (consumption, critique, question thread, timeline pane), then page-level features (How It Works overlay, onboarding overlay), then polish issues.

Before posting, run yourself through the validation checklist at §11 of the README and tick every box explicitly in your reply.

Do not start implementing anything. Plan first. The product owner reviews the slicing before any spec is picked up.
```

---

## Why this works

- **Phase 1 is mechanical** — Claude Code lands the bundle on a branch, opens the PR, posts the URL back. No interpretation needed.
- **Phase 2 is the planning round** — the README walks itself; the validation checklist forces Claude Code to self-verify before posting.
- **No implementation creep** — the prompt explicitly forbids starting any spec until the plan is approved.

## If the connector path differs

If your Claude Code instance can't reach `Lexiz/dual-research` directly, swap the first sentence of Phase 1 with: *"Clone Lexiz/dual-research locally first, then proceed with the branch + commit + push + PR steps below."* Everything else stays.
