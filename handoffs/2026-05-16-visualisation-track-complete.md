# Session handover — visualisation track complete (2026-05-16)

Snapshot taken at the end of the session that shipped specs **0025,
0027, 0028** — the full inline-comments / side-by-side review track.
Companion to `handoffs/2026-05-16-session-handover.md`, which closed
the hosted-deployment track. Read this first if you're picking up
work after the visualisation track lands.

---

## 1 · Where the project is

**Local tool:** `~/dual-research`, on `main`, at **v0.26.0**.

**Hosted UI:** **https://dual-research-alex.fly.dev/** — live,
reports **v0.24.0** (lags `main` by two specs — 0027 and 0028 are
not deployed yet). Single Fly machine in `iad`, auto-stops when
idle, Google OAuth + email allowlist gate intact from spec 0021.

**Tests:** **372 pytest cases green** — `uv run pytest tests/ -q`.
Up from 277 at the start of this track.

---

## 2 · What shipped in this session (specs 0025 → 0028)

The track is referenced throughout the user's original ask as "the
inline-comments / Google-Docs-style review UX". This handover is
the final point on that track; the next spec is **0029** (in a
separate session — see §3).

| Spec | Title | What landed |
|---|---|---|
| 0025 | Visualisation foundations — modal pattern, summary cards, preflight tabs, attachment ingest | Replaces inline expand-in-place on every timeline card with a **summary card + big centred modal**. Preflight gets **tabs** (Content / Sources / Files). New `Attachment` dataclass + `ingest/attachments.py`; markdown / Notion / `--attach VALUE` CLI all feed it. New supabase migration `0003_attachment_blobs.sql` + base64 push/restore path. Two new server endpoints (`/api/runs/{id}/attachments` and `/api/runs/{id}/attachment-blobs/{rel_path}`). Hash-stable `id="b-<hash>"` on every rendered block. `Modal` component + `useAttachments` hook. |
| 0026 | (interstitial) How-it-works restructure | Filed by the user mid-session. Pure UI on `#/how-it-works`. Doesn't affect the inline-comments track. Renumbered our planned sequence after this — the next inline-comments spec became 0027 instead of 0026. |
| 0027 | Negotiate inline comments — side-by-side modal with anchored critique cards | Phase 2 turn cards open a **side-by-side modal**: left pane shows the prior content (other agent's Phase 1 draft for round 1, their round N-1 turn for N≥2); right pane shows numbered questions / D-N disagreements / resolved items as anchored cards. Click → scroll + amber flash. `> after:` items mount a dashed "insert here" ghost block under the named heading. `j` / `k` walk; `Esc` close. New `ReviewItem` dataclass + `extract_review_items` in `protocol/parse.py`. Prompt addition: optional `> quote: <verbatim ≤25-word span>` / `> after: <heading>` blockquote sub-line under each item. Anchoring is best-effort with graceful fallback (un-anchored items still render). |
| 0028 | Cross-review inline comments — Phase 4 side-by-side modal | Same modal applied to Phase 4 turn cards. Left pane = **latest converged-document version** (highest `phase4/draft-v*.md` if drafter revisions have landed, else `phase3/draft-v1.md`). Right pane = Issue ledger items + Comments-on-the-current-draft items + Substantive disagreements. New `Run.current_draft_path` field (`currentDraftPath` at the wire). Parser learns two new section recognisers. Frontend dispatcher routes both phase-2 and phase-4 turn cards to `NegotiateReviewModal`. |

**Mental model after the track:** every place an agent critiques
prior content has a side-by-side modal with anchored comment cards.
Phase 1 plan drafts, Phase 3 single-shot drafting, and the final
document still use the single-pane modal from 0025 — there's no
critique structure there to anchor.

---

## 3 · What's open / next

### Spec 0029 (parallel session)

A separate Claude Code session is currently set up to implement
**spec 0029**. As of this handover, `main` is at v0.26.0 and clean;
the spec-0029 session should `git pull` and start from this point.
The content of spec 0029 is owned by that session — this handover
doesn't dictate it.

The next available spec number after 0028 is **0029**.

### Carryovers from earlier tracks (still deferred)

Originally noted in `handoffs/integration-state.md` and the
hosted-deployment handover; intentionally not fixed in 0025–0028:

| # | Issue | File |
|---|---|---|
| I6 | Old fixture runs show as `running` forever; no liveness probe | `ui/labels.py` |
| I8 | `currentTurn.body` keeps full final-doc in every SSE snapshot post-completion | `ui/aggregator.py` |
| I9 | "connected" pill on the All-runs view (no SSE there) | `ui/static/app.jsx` |
| I10 | `final.md` metadata header reports wrong duration | `orchestrator/finalize.py` |
| I11 | `ErrorCard` may crash on errored runs | `ui/static/run-detail.jsx::ErrorCard` |

None block any feature; bundle into a single PATCH spec when
convenient.

### Cosmetic papercuts introduced or known in this track

- **Anchoring degrades on older runs.** Phase 2 / Phase 4 turn files
  that predate the `> quote:` / `> after:` prompt convention render
  un-anchored — the cards still appear but don't auto-jump. Fresh
  runs get full functionality. Acceptable; documented in 0027/0028.
- **Phase 4 left-pane is run-wide, not per-turn.** A comment written
  against draft v2 may flash on draft v4 today. Per-round draft
  history is the right follow-up if it becomes a real issue.
- **No quote-fallback to fuzzy diff-match-patch.** Anchor resolution
  is hash → substring. Rare miss-cases just stay un-anchored.
  TextQuoteSelector with prefix/suffix is a possible 0029+ addition.

### Hosted deploy is behind `main`

Production (`https://dual-research-alex.fly.dev/`) reports
**v0.24.0**. To bring it up to v0.26.0:

```bash
cd ~/dual-research && flyctl deploy --remote-only --yes
```

**No new migrations** for 0027 and 0028 (they're prompt + parser +
frontend only — no schema delta). 0025's migration
(`supabase/migrations/0003_attachment_blobs.sql`) is already applied
on production based on the live v0.24.0 backend responding cleanly.

---

## 4 · How the new pieces are wired

### Inline-comments data flow (specs 0027 + 0028)

```
Phase 2 / 4 round file (markdown)
        │
        │  extract_review_items()           — protocol/parse.py
        ▼
ReviewItem[] { kind, body, quote?, after?, item_id? }
        │
        │  aggregator: phase{N}_round{R}_<agent> key
        ▼
Run.phase_review_items[key]                  — ui/models.py
        │
        │  asdict() + snake→camel
        ▼
snapshot.phaseReviewItems                    — wire format
        │
        ▼
NegotiateReviewModal                         — ui/static/run-detail.jsx
  ├── left pane:  LazyMarkdownBody({ filePath: priorContentPathFor(...) })
  └── right pane: ReviewCard[] grouped by kind, click → scrollAndFlash()
```

`priorContentPathFor` decides which file the left pane renders:
- **Phase 2, round 1**: `phase1/draft-<otheragent>.md`
- **Phase 2, round N≥2**: `phase2/round-{N-1:02d}-<otheragent>.md`
- **Phase 4**: `run.currentDraftPath` (computed by aggregator —
  highest `phase4/draft-v*.md` if any, else `phase3/draft-v1.md`).

`scrollAndFlash(container, { blockId, text, afterHeading })` lives in
`shared.jsx`. Two-step resolution: `getElementById` for stable
`b-<hash>` ids → case-insensitive substring scan across rendered
block elements. Applies `.dr-flash` class for 1.5s amber fade.
`> after:` items also mount a `.dr-ghost-block` (dashed border +
proofreader's caret) under the named heading.

### Attachment ingest (spec 0025)

```
brief.md / Notion blocks / --attach VALUE
        │
        │  scan_markdown_attachments / Notion render_blocks / attach_local_file
        ▼
BriefResult.attachments = list[Attachment]
        │
        │  materialise_local_markdown_attachments → session_dir/attachments/<sha8>-<basename>
        ▼
session_dir/attachments.json + session_dir/attachments/*
        │
        │  --push: session_files (for .json) + attachment_blobs (for binaries)
        ▼
Hosted UI: /api/runs/{id}/attachments + /attachment-blobs/{rel_path}
```

### Summary cards (spec 0025)

The protocol already requires `## Summary` (and `## Summary of
position`) sections in phase 1 / 2 / 3 / 4 outputs. The aggregator
now extracts them via `extract_summary` and surfaces as
`Run.phase_summaries[key]` (and `Run.brief_summary` for `brief.md`,
which uses a heuristic when no explicit Summary section exists).
Every timeline card renders the relevant summary as a TL;DR row
under the header, plus a "View full" button that opens the modal.

---

## 5 · File map for spec 0029 (quick orientation)

If 0029 touches review-modal internals or the visualisation surface:

- `src/dual_research/protocol/parse.py` — `extract_review_items`, `extract_summary`, `synthesise_brief_tldr`.
- `src/dual_research/protocol/prompts.py` — `> quote:` / `> after:` hint paragraphs are inside `negotiation_round1_prompt`, `negotiation_turn_prompt`, `review_turn_prompt` (one under each anchored section).
- `src/dual_research/ui/aggregator.py` — `_read_phase_review_items`, `_find_current_draft_path`, `_read_phase_summaries`, `_read_brief_summary`.
- `src/dual_research/ui/models.py` — `Run.phase_review_items`, `Run.current_draft_path`, `Run.phase_summaries`, `Run.brief_summary`.
- `src/dual_research/ui/static/run-detail.jsx` — `ArtifactModal` dispatcher, `NegotiateReviewModal`, `ReviewCard`, `ReviewGroup`, `priorContentPathFor`, `reviewItemsFor`.
- `src/dual_research/ui/static/shared.jsx` — `Modal`, `scrollAndFlash`, `_injectBlockIds` (markdown post-process), `Markdown` component.
- `src/dual_research/ui/static/theme.css` — `dr-flash`, `dr-ghost-block`, `dr-modal-in` animations.

If 0029 touches ingest or attachments:

- `src/dual_research/ingest/attachments.py` — `Attachment` dataclass, scanners, `attach_local_file`, `attach_url`, `materialise_local_markdown_attachments`.
- `src/dual_research/ingest/__init__.py` — `BriefResult`, `build_brief`.
- `src/dual_research/ingest/notion.py` — `_render_blocks` emits attachments into a passed-in list.
- `supabase/migrations/0003_attachment_blobs.sql` — single binary blobs table.

If 0029 needs to touch hosted endpoints or supabase materialise:

- `src/dual_research/ui/server.py` — both `_make_app` and `_make_supabase_app` carry the attachment endpoints.
- `src/dual_research/ui/datasource.py` — `SupabaseSessionData._write_blobs` decodes base64 back into the tmp dir's `attachments/`.
- `src/dual_research/persistence/remote.py` — `RemoteSession.push_session_dir` upserts blobs alongside transcripts and session files.

---

## 6 · Workflow recap

`CONTRIBUTING.md` is authoritative. Quick checklist for spec 0029:

```
1. cp specs/TEMPLATE.md specs/0029-<slug>.md
2. git checkout -b spec/0029-<slug>
3. implement + tests
4. bump pyproject.toml + __init__.py per label
5. CHANGELOG entry + (if user-visible) VERSION_NOTES entry
6. flip spec front-matter status: in-progress → merged + fill pr:
7. gh pr create + gh pr merge --admin --squash --delete-branch
```

`uv run pytest tests/ -q` is the bar; CI isn't wired through GitHub
Actions yet (the user's session UI shows "CI checks unavailable" —
unrelated to anything in this track).

---

## 7 · Pointers to prior handovers

- `handoffs/2026-05-16-session-handover.md` — hosted-deployment
  track (specs 0019–0024). Pre-visualisation.
- `handoffs/hosted-deployment-kickoff.md` — original kickoff for the
  hosted track.
- `handoffs/integration-state.md` — pre-hosted UI snapshot.
- `handoffs/backend-state.md` — original v0.9.0 backend handoff.

---

*Generated 2026-05-16 at the end of the session that shipped the
inline-comments visualisation track (specs 0025 → 0027 → 0028).*
