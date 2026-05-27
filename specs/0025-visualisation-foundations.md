---
spec: 0025
title: Visualisation foundations — modal pattern, summary cards, preflight tabs, attachment ingest
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.23.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/25"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0025 — Visualisation foundations

## Context

Each timeline phase card currently expands inline into a wall of raw
markdown. For long inputs and dense negotiation turns this is
unreadable: there's no shape to the content, no quick read of "what
does this round actually say", and there's no room for a real document
view without crowding the right-pane disagreement explorer.

This is the **first of three specs** building toward a Google-Docs-/
GitHub-PR-style review experience across the run timeline:

- **0025 (this spec)** — foundations. Replaces inline expansion with a
  **summary card** that shows a TL;DR + key stats and a "View full"
  button. The button opens a **big centred modal** with a greyed
  overlay. Preflight gets a **tabbed modal** (Content / Sources /
  Files); attachments (images, PDFs, files, links) are now first-class
  in the ingest layer. Markdown rendering grows hash-stable block ids
  so future specs can anchor comments to text. The full-document view
  in the modal is single-pane in this spec.
- **0026** — side-by-side inline comments for Phase 2 (negotiate).
  Left pane shows the prior draft; right pane shows the AI critic's
  questions and remarks as inline-comment cards; clicking a card
  scrolls + highlights the referenced span. Adds a one-line prompt
  hint asking each question/remark to carry an inline quote.
- **0027** — applies the 0026 pattern to Phase 3 (refine) and Phase 4
  (final-against-prior).

Research for this track is captured in
`handoffs/2026-05-16-session-handover.md` §3 (the "actual new feature"
referenced there). Inline-comments UX patterns were investigated and
the recommended stack documented in the session transcript that
preceded this spec.

The current pipeline does not extract structured summaries from agent
output, even though phase 1 / 2 / 3 / 4 prompts all require agents to
include a `## Summary` (or `## Summary of position`) section. This
spec wires that extraction up — no prompt changes needed. Ingest does
not currently capture files, images, or PDFs as first-class entities;
the brief is a plain text blob. This spec adds an `Attachment` model
threaded through ingest → session-dir → supabase → UI.

## Proposed change

### 1. Attachment ingest

New module `src/dual_research/ingest/attachments.py`:

```python
@dataclass(frozen=True)
class Attachment:
    kind: str         # "image" | "pdf" | "file" | "link"
    source: str       # provenance: "markdown:./foo.png" | "notion:<block-id>" | "cli:/abs/path" | "url:https://…"
    title: str | None        # short label (filename, link text, alt text)
    caption: str | None      # optional human-readable description
    url: str | None          # external URL when one is known
    rel_path: str | None     # path under session_dir/attachments/ for local-stored files
    mime: str | None
    size_bytes: int | None
    sha256: str | None
```

Helpers:
- `scan_markdown_attachments(text, *, base_dir, prefer_external) -> list[Attachment]`
  — parses `![alt](url)`, `[label](url)`, and bare `https?://` URLs
  out of a markdown body. Local relative paths are resolved against
  `base_dir`. Kind picked by extension (`.png/.jpg/.jpeg/.gif/.webp/.svg`
  → image; `.pdf` → pdf; remote URLs → image/pdf/link by suffix; else
  → file).
- `attach_local_file(path, *, dest_dir) -> Attachment` — hashes,
  copies into `dest_dir/<sha8>-<basename>`, returns the dataclass.
- `attach_url(url, *, label=None) -> Attachment` — wraps a remote URL
  without download.

Extended in `src/dual_research/ingest/__init__.py`:

```python
@dataclass
class BriefResult:
    content: str
    source_kind: str
    source_ref: str
    notion: NotionIngestResult | None = None
    attachments: list[Attachment] = field(default_factory=list)  # NEW
```

`build_brief()` runs the appropriate scanner after producing
`content` and assembles the attachment list:

- `prompt` mode — `scan_markdown_attachments(content, base_dir=cwd,
  prefer_external=True)` plus any `--attach` values.
- `brief` mode — same scanner with `base_dir=Path(args.brief).parent`
  so relative images resolve from the brief's directory; local
  matches get copied via `attach_local_file` later (at session-dir
  setup time in `cli.py`). Plus `--attach` values.
- `notion` mode — Notion ingestor returns attachments inline; plus
  `--attach` values.

### 2. CLI surface

Add to `cli.py::_build_parser`:

```
--attach VALUE   Add an image, PDF, file, or URL alongside the brief.
                 Repeatable. Local paths are copied into the session-dir's
                 attachments/ directory; URLs are recorded as link entries.
```

`action="append"`, `default=[]`, no short flag.

After `brief.md` is written, `cli.py::main` materialises attachments:
- Creates `session_dir/attachments/` if any local files are present.
- Calls `attach_local_file` for each local path in
  `args.attach + brief.attachments(local-only)`.
- Writes `session_dir/attachments.json` — a single JSON document with
  `{"attachments": [Attachment dict, ...]}`. Pretty-printed for
  readability.
- The launch summary prints a one-line `attachments : N item(s)
  (images=A, pdfs=B, files=C, links=D)` if any are present.

### 3. Notion ingestor — capture attachments

In `ingest/notion.py::_render_blocks`, in addition to the markdown
output it currently produces, also emit `Attachment` records for:

- `image` blocks — `kind="image"`, `url=<image-url>`,
  `caption=<rendered caption>`, `source="notion:<block-id>"`.
- `file`, `pdf` blocks — kind picked by mime/extension; same shape as
  image.
- `bookmark`, `embed`, `link_preview` blocks — `kind="link"`,
  `url=<block-url>`, `title=<host>`, `source="notion:<block-id>"`.

Rich-text spans with `href` and a non-trivial `plain_text` also emit a
`kind="link"` attachment (deduped by URL).

`notion_to_brief` returns its `NotionIngestResult.attachments`
field (new); `build_brief` merges it into `BriefResult.attachments`.

### 4. Persistence — local

`session_dir/` layout grows two new entries:

```
session_dir/
├── brief.md
├── attachments.json          # NEW — list of all Attachment dicts
├── attachments/              # NEW — copies of local file attachments
│   └── <sha8>-<basename>...
└── ... (existing phase dirs, state.json, etc.)
```

### 5. Persistence — supabase

New migration `supabase/migrations/0003_attachment_blobs.sql`:

```sql
CREATE TABLE IF NOT EXISTS attachment_blobs (
    run_id      TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    rel_path    TEXT NOT NULL,           -- matches Attachment.rel_path; "attachments/<sha8>-<basename>"
    mime        TEXT NOT NULL,
    size_bytes  INT NOT NULL,
    content_b64 TEXT NOT NULL,
    PRIMARY KEY (run_id, rel_path)
);
```

`attachments.json` flows through the existing `session_files` table
(it's a `.json` file under `session_dir`, so the existing iterator
picks it up — but we add `.json` is already in `SESSION_FILE_GLOBS`).

`RemoteSession.push_session_dir` gains a fourth step: iterate
`session_dir/attachments/` (if it exists), read each file as bytes,
base64-encode, upsert into `attachment_blobs` keyed on `(run_id,
rel_path)` where `rel_path = "attachments/<basename>"`. Batched at 20
rows per upsert (binary blobs are heavier than markdown).

`PushSummary` grows a `blobs_upserted: int` field.

`SupabaseSessionData.materialize` gains a counterpart `_write_blobs`
that pages through `attachment_blobs`, base64-decodes, and writes the
files under the tmp dir's `attachments/` subdir.

### 6. UI server endpoints

In both `_make_app` and `_make_supabase_app`:

- `GET /api/runs/{run_id}/attachments` — returns the parsed
  `attachments.json` body (an `{"attachments": [...]}` object). 404
  with empty `{"attachments": []}` if missing — the UI treats absence
  identically.
- `GET /api/runs/{run_id}/attachment-blobs/{rel_path:path}` —
  serves binary content with the recorded mime type. fs mode reads
  from `session_dir/attachments/<basename>`. Supabase mode queries
  `attachment_blobs`, base64-decodes, returns the bytes with the
  recorded mime as `Content-Type`. Path-traversal-guarded.

### 7. Summary extraction

`src/dual_research/protocol/parse.py` gains a helper:

```python
def extract_summary(text: str) -> str | None:
    """Return the body of the first ## Summary / ## Summary of position
    section, stripped, or None."""
```

Recognises:
- `## Summary`
- `## Summary of my position`
- `## Summary` followed by any sub-line

Body ends at the next `## ` heading or EOF.

`aggregator.py::_populate_current_bodies` is extended to also walk
**completed** turn files (not just the current one) and populate
`Turn.summary` for past turns. A new helper `_summaries_from_disk` is
called from `load_run_snapshot` after `_populate_current_bodies` and
fills `agents[ag].last_turn.summary` and a new
`Run.phase_summaries: dict[str, dict[str, str]]` keyed on
`phase{N}_round{R}_{ag}` → summary string. The UI consumes this
through `phaseSummaries` (camelCase at the wire boundary).

The preflight critique files (`phase0/preflight-{agent}.md`) and
phase-1 drafts also get their `## Summary` parsed; the input card and
plan-draft cards consume these for the collapsed TL;DR.

### 8. Frontend — hash-stable block ids

`src/dual_research/ui/static/shared.jsx`, the `Markdown` component
swaps to a `marked` custom renderer that hashes the text content of
every block-level element and emits `id="b-<8-char-hex>"`:

```js
const hashBlock = s => {
  // FNV-1a 32-bit → base36
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(36).padStart(7, '0').slice(0, 8);
};
```

Applied to `paragraph`, `heading`, `list_item`, `code`, and
`blockquote` block renderers. The renderer is built once per `<Markdown>`
mount and shared via the existing `window.marked.parse` call (a
`marked.use(...)` install once-only at module load). Future specs use
these stable ids as anchors.

The hash is deterministic across re-renders for the same text — same
paragraph in two different rendered copies gets the same id. Allowed
to collide for now (probability is vanishingly small at the scale we
work with). A future spec can extend to W3C TextQuoteSelector fallback.

### 9. Frontend — Modal component

New in `shared.jsx`:

```jsx
function Modal({ open, onClose, title, tabs, children, width = 1200 }) { ... }
```

- Renders a fixed-position overlay (full viewport, rgba black 0.55
  background, click-outside closes), a centred surface
  (`max-width: 1200px`, height up to 90vh, rounded, themed bg-0/1),
  and an optional tab strip across the top.
- `Esc` closes. Focus trap is light — first focusable child auto-
  focuses, nothing more advanced.
- `tabs` is an optional `[{id, label, content}]` array; when present
  the surface body renders `tabs.find(...).content`.
- Exposed on `window` like other shared primitives.

### 10. Frontend — Summary cards + view-full button

`src/dual_research/ui/static/run-detail.jsx`:

- `ArtifactCard` no longer inline-expands on click. Instead the
  collapsed state is the **only** static state; clicking the card (or
  the new "View full" button on its trailing edge) opens the modal.
- Below the header row, every artifact card gains a **second row**
  rendering its summary (TL;DR) when one is available:
  - `input` (preflight): a synthesised 2-sentence TL;DR from
    `Run.brief_summary` — generated by truncating the brief text
    and joining the first two non-heading sentences. (Not LLM-
    generated; cheap heuristic. Future spec can add an LLM TL;DR.)
  - `plan` / `plan-live`: agent's `## Summary` from the draft (via
    `phaseSummaries.phase1_<agent>`).
  - `turn` / `turn-live`: agent's `## Summary of position` for the
    round (via `phaseSummaries.phase2_round{R}_<agent>`). For phase 2
    turns we also show a one-line "N open questions · M
    disagreements" stat row, repurposed from existing `StatsChips`
    data.
  - `doc`: a one-line "Converged document drafted by <agent>" stub
    (already exists). v1 doesn't synthesise a TL;DR for the final
    doc; spec 0027 may.

The summary row is muted (`fg-2`, 2-line clamp) and reads like a
sub-header. To the right of the summary row, an icon button "View
full" opens the modal. The chevron + inline-body code goes away
entirely.

`ArtifactBody`, `LazyMarkdownBody`, `Body` removed (replaced by
modal content).

### 11. Frontend — preflight modal (tabbed)

When the preflight `input` card is opened, the modal renders three
tabs:

- **Content** — the brief text rendered through `<Markdown>`.
- **Sources** — list of `kind == "link"` attachments (and any
  Notion source pages from `NotionIngestResult.sections` —
  serialised into attachments at ingest time). Each entry shows
  title, host, optional caption, and links externally.
- **Files** — list of `kind ∈ {image, pdf, file}` attachments. Images
  render as `<img>` thumbnails (180px max width), clickable to open
  full size in a new tab. PDFs and other files render with an icon,
  filename, size, and a "Download" link to
  `/api/runs/{id}/attachment-blobs/{rel_path}`. Hover shows the
  caption.

If a tab has zero items, it renders an empty-state ("No links
extracted from this brief.").

### 12. Frontend — drafts / turns / final modals

Single-pane modals showing the full markdown via `<Markdown>`. No
side-by-side, no comment cards — those land in spec 0026. The modal
title is the card's header (agent name + kind label).

### 13. Wire format

`Run` (camelCase at the boundary):
- `briefSummary: string | null` — synthesised TL;DR for the input
  card.
- `phaseSummaries: { [key]: string }` — per-turn summaries keyed by
  `phase0_<agent>`, `phase1_<agent>`, `phase2_round{R}_<agent>`,
  `phase4_round{R}_<agent>` (no entry when the agent didn't write
  a `## Summary`).

### 14. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.22.1 → 0.23.0.
- CHANGELOG: `## [0.23.0] — 2026-05-16`.
- `VERSION_NOTES` array: new entry at the top.

## Out of scope

- **Side-by-side inline comments** for phase 2 / 3 / 4 modals — spec
  0026 + 0027. The v1 modal shows full markdown without inline
  annotations.
- **Prompt changes** to require quoted spans in questions/remarks —
  spec 0026.
- **LLM-generated TL;DR** for the input card or final doc. v1 uses a
  heuristic (truncate + join first two sentences) for the input;
  drafts / turns use the agents' own `## Summary` section, which
  protocol already requires.
- **Editing / removing attachments** after the run starts. Attachments
  are ingest-time only.
- **Supabase Storage** for binary attachments. We base64-encode into
  a Postgres table; if attachment sizes balloon a future spec can
  swap to Storage.
- **Live attachment refresh** for hosted runs. Notion image URLs are
  time-limited; this spec captures them at ingest. Re-running the
  ingest is a manual `--push` re-run.
- **Mobile layout.** Desktop-first.
- **Focus trap** beyond auto-focus inside the modal. Accessible-modal
  semantics are minimal in v1.

## Test plan

- [ ] `tests/ingest/test_attachments.py` — markdown scanner happy path
      (images, PDFs, links), `attach_local_file` hashing + copy,
      `attach_url` shape, kind-from-extension table.
- [ ] `tests/ingest/test_notion_attachments.py` — Notion block
      renderer emits attachments for image / pdf / file / bookmark /
      embed / link_preview, dedupes inline links by URL.
- [ ] `tests/protocol/test_parse_summary.py` — `extract_summary`
      finds `## Summary`, `## Summary of position`, empty-section
      returns None, body ends at next `## `.
- [ ] `tests/persistence/test_remote.py` — new test class for the
      attachments table: blobs upsert by rel_path, `attachments.json`
      goes through the session_files pipeline, PushSummary surfaces
      the count.
- [ ] `tests/ui/test_datasource_supabase.py` — materialize round-trips
      a binary blob byte-for-byte.
- [ ] `tests/ui/test_server.py` — fs-mode `/api/runs/{id}/attachments`
      returns the JSON, `/attachment-blobs/{rel}` serves bytes with
      the right Content-Type, traversal returns 404.
- [ ] `tests/ui/test_server_supabase_mode.py` — same as above against
      the supabase backend.
- [ ] `tests/ui/test_aggregator.py` — `Run.brief_summary` populated
      from a brief.md fixture, `Run.phase_summaries` populated from
      phase1/phase2 fixtures.
- [ ] Manual: open a local run, click a card — modal opens with
      summary visible. Open preflight — tabs render. Drop a markdown
      brief with `![alt](https://example.com/foo.png)` →
      Files tab shows it. Add `--attach ./diagram.pdf` →
      `attachments/` populated and the file is downloadable.
- [ ] All existing 277 tests stay green.

## Risks

- **Attachment size on hosted.** Base64-encoded PDFs can be megabytes.
  Postgres TEXT in supabase handles it but the per-request payload
  for the materialize path is heavier. Mitigation: paginate
  `attachment_blobs` writes at batch size 20. Decode only on the
  per-blob serve endpoint, never inside `materialize`. The hosted
  page-load already lazy-fetches files; attachments follow the same
  pattern.
- **Notion image URL expiry.** Notion's image URLs are signed and
  time-limited (~1h). For hosted runs where the user is viewing
  hours/days after ingest, the URLs will 404. v1 accepts this — the
  Files tab shows a placeholder if `<img>` fails to load. A future
  spec can mirror Notion images into `attachment_blobs` at ingest
  time.
- **Hash-stable ids collision.** FNV-1a 32-bit has ~50% collision odds
  at ~77k blocks (birthday paradox). Real documents have hundreds, so
  collision risk is negligible — but possible in pathological repeats
  ("OK", "OK", "OK"). 0026's anchoring layers TextQuoteSelector
  fallback for robustness.
- **Modal stealing keyboard focus.** First-element auto-focus is
  enough for now; `Esc` works. Light user testing pre-merge will
  surface anything broken.
- **Bigger spec than usual.** Combined ingest + persistence + server +
  frontend touches more files than recent specs. The split into 0025
  / 0026 / 0027 keeps each PR reviewable; if 0025 grows past ~1500
  changed lines we split off the ingest piece as 0025b.

## Open questions

- Whether to surface `brief_summary` as a separate piece of data or
  derive it client-side from the brief body. Going server-side here
  so the same heuristic applies in fs + supabase mode and the wire
  format owns the contract.
