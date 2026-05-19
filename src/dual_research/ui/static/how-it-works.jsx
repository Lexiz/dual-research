// how-it-works.jsx — user-facing explanation of the dual-research protocol
// plus release notes (specs 0023 + 0026).
//
// Spec 0026 restructured this page around a chat-lifecycle section that
// answers "when do we create new chats?", a context-growth visual, phase
// accordions, and a v3.5 protocol overview fold-out (cream-and-indigo
// reference diagram authored via the diagram skill). The original page is
// preserved in spirit — same facts, same data — but split into denser,
// more navigable cards. Inline visuals use the existing theme tokens; the
// fold-out reference map is a separate static look.
//
// VERSION_NOTES at the top is the in-app changelog; CONTRIBUTING.md asks
// that future specs touching user-visible behaviour append a new entry.

(function () {
  const VERSION_NOTES = [
    {
      version: '0.69.1',
      date: '2026-05-18',
      summary: 'Hotfix -- run-detail page white-screen regression fixed.',
      items: [
        'Fixed Babel parse error in run-detail.jsx that caused every run-detail page to white-screen (regression from v0.63.0).',
        'Root cause: JSX comment placed inside a prop expression slot -- Babel interprets this as a nested object literal.',
        'Added JSX syntax regression test to catch the same class of bug in all JSX files going forward.',
      ],
    },
    {
      version: '0.68.0',
      date: '2026-05-18',
      summary: 'Consumption tab agent-card restructure -- data at top, bars at bottom, wider bars, equal-height cards.',
      items: [
        'Expanded agent cards reorganized: metrics + costs grouped at top, bars zone (total + breakdown) at bottom with divider.',
        'Cards grow downward on expand; total bar stays put as visual anchor, breakdown bars cascade below.',
        'Phase-label column narrowed from 160px to 100px; bar-label columns narrowed from 140px to 100px for wider bars.',
        'New --consumption-label-w token and .consumption-card CSS class codified in the design system.',
        'Consumption card spotlight added to Design Language page.',
      ],
    },
    {
      version: '0.67.0',
      date: '2026-05-18',
      summary: 'Agent Input tab rework -- renamed, reordered to first position, structural improvements with CollapsibleSection and Markdown rendering.',
      items: [
        '"Input" tab renamed to "Agent Input" across all modal contexts (top-level tabs and left-pane sub-tabs).',
        'Agent Input now appears first in modal tab order, before Content.',
        'Entry ordering: System Prompt first (collapsed), User Prompt second (expanded), then remaining entries.',
        'Input entries now use the CollapsibleSection primitive for consistent disclosure UX.',
        'Input piece bodies render via Markdown instead of raw preformatted text.',
        'Improved empty state messaging when input bundles are unavailable.',
      ],
    },
    {
      version: '0.66.0',
      date: '2026-05-18',
      summary: 'Critique detail unification -- disagreement cards now use QuestionThread-style turns, Issue/Comment bodies render Markdown, new QuoteCallout primitive.',
      items: [
        'Disagreement detail rebuilt: progression entries now render as agent turn cards with action chips (raised/conceded/aligned) instead of vertical rail.',
        'QuestionThread extended with kind="disagreement" for unified turn-card rendering across questions and disagreements.',
        'Issue and Comment bodies now render via Markdown -- bold, italic, blockquotes, and code display correctly.',
        'New QuoteCallout primitive for styled quote fields on critique cards (left border + italic + muted background).',
        'Disagreement step notes and question bodies now render through Markdown for consistent formatting.',
      ],
    },
    {
      version: '0.65.0',
      date: '2026-05-18',
      summary: 'Critique pane structural pass -- filter strip overflow fix, Phase 4 Issues/Comments split, three-sentence summary, disabled-Drift UX.',
      items: [
        'Filter strip no longer clips the last tab: PaneToolbar expands to fit multi-row filter strips.',
        'Kind-axis filter row anchored left, agent+status row centered with tighter spacing.',
        'Every filter chip now shows a tooltip on hover explaining what it filters.',
        'Phase 4 Issues and Comments render in their own collapsible sections instead of mixing into DRIFT/OPEN/RESOLVED.',
        'Summary tab opens with a generated three-sentence verdict: sentiment, qualitative breakdown, and drift note.',
        'Drift status chip visually disables when Questions is the active kind filter.',
      ],
    },
    {
      version: '0.64.0',
      date: '2026-05-18',
      summary: 'Timeline structural pass -- collapsible phases, denser cards, improved PhaseRail contrast, collapsible critique sections.',
      items: [
        'New CollapsibleSection primitive: generic disclosure with chevron, localStorage persistence, and reduced-motion respect.',
        'Timeline phase headers are now clickable: collapse/expand cards under each phase. State preserved across reloads.',
        'Card vertical padding reduced for a denser, more scannable timeline.',
        'PhaseRail completed-phase labels now render in green (--ok) instead of dim gray for better readability.',
        'Critique pane DRIFT/OPEN/RESOLVED sections are now collapsible with the same disclosure pattern.',
        'Small inline badges (ok, issues) unified to consistent size and style across all card types.',
      ],
    },
    {
      version: '0.63.0',
      date: '2026-05-18',
      summary: 'Run-detail header restructure -- equal-width agent strips, blocking banner removed, phase tabs with structured chip clusters.',
      items: [
        'AgentStrip pills now share width equally via flex: 1 1 0 -- no more lopsided pills from differing model string lengths.',
        'Vertical padding reduced from var(--s-2) to 4px for a denser agent strip.',
        'Blocking-item callout banner removed -- the "N open . M ghosted . click to jump" bar is gone. Same info available in critique pane.',
        'Phase tabs restructured: each tab shows P2 Negotiate 26 questions 10 disagreements instead of cramped "PHASE 2 Negotiate . 26 Q . 10 D".',
        'Count chips use full words (questions, disagreements) and show 0 explicitly. Active tab chips at full opacity, inactive muted.',
      ],
    },
    {
      version: '0.62.0',
      date: '2026-05-18',
      summary: 'Run-list & chrome polish -- uniform status pills, structured info chips, cohesive chrome controls.',
      items: [
        'Status pills now have a fixed 88px min-width with centered text -- all statuses (running, deadlocked, completed, errored, converged) render at the same width.',
        'Run-list header info line replaced with structured Chip instances: run count, running count (info tone), and total cost.',
        'Chrome tabs (All runs, Compare, Search) now use consistent size="sm" for uniform visual weight.',
        'ConnectionPill flattened from two-line indicator to a single-line chip showing just the connection state.',
        'AppVersionChip restyled to use the Chip primitive. DesignLanguageButton restyled to use Tab primitive.',
        'StatusBadge spotlight added to the Design Language DNA page.',
      ],
    },
    {
      version: '0.61.0',
      date: '2026-05-18',
      summary: 'Brand-icon system + Design-page DNA reskin -- official brand marks everywhere agents are identified.',
      items: [
        'New BrandMark primitive renders official Anthropic sunburst (Claude) and OpenAI hexagonal rosette (GPT) at any size with solid or ghost variants.',
        'Agent-icon migration: AgentIcon, AgentStrip, and CodeCluster agent chips now use the brand SVG paths from a single BRAND_SVGS dictionary.',
        'Run-list dual-color gradient square replaced with two composed BrandMark glyphs.',
        'Design Language page restructured as a curated DNA one-pager (Hero, Palette, Brand marks, Component spotlights, Construction). Full reference at ?full=1.',
        'Component spotlight scaffolding: four live showcases with a marked block for future specs to add their primitives.',
      ],
    },
    {
      version: '0.60.0',
      date: '2026-05-18',
      summary: 'Chip vocabulary + code-cluster expansion -- full-word labels replace cryptic codes.',
      items: [
        'New parseCodeId utility + CodeCluster primitive. Critique public IDs (Q-c-r1-04, d-04, etc.) now render as structured chip clusters showing kind, agent, and round.',
        'Stats chips expanded: "+6 Cl" becomes "+6 claims", "+1 I -1" becomes "+1 issue -1". All timeline card chips use full words.',
        'Disagreement status labels: arrow notation ("-> claude") replaced with "conceded by Claude" / "conceded by GPT". Round ranges use "opened R2 / closed R5".',
        'Ghosted chips: "ghosted 4r" becomes "ghosted 4 rounds". Reuse chip: "x 3.8 reuse" becomes "x 3.8 token reuse".',
        'Output bar labels: slot codes removed ("-> d1") replaced with descriptive "feeds Claude\'s Phase 1 draft".',
      ],
    },
    {
      version: '0.59.0',
      date: '2026-05-17',
      summary: 'Onboarding flow + landing demo capsule -- final design-system arc spec.',
      items: [
        'Ship 4 spec #2 (final). 3-screen onboarding carousel for first-time users: what dual-research is, how a run works, and how to start exploring.',
        'Auth-free landing page now shows a read-only demo capsule of a real research run (partner-vetting). Topic, cost, phases, timeline entries, and critique items visible before sign-in.',
        'Onboarding completion persisted to localStorage. Skip or complete to dismiss. Reset with ?reset_onboarding=1 for testing.',
        'Demo run fixture committed as demo-run.json -- curated subset of partner-vetting data, no PII.',
        'Design-system migration arc complete (SPEC-0050 through SPEC-0061).',
      ],
    },
    {
      version: '0.58.0',
      date: '2026-05-17',
      summary: 'Cross-run dashboards -- /compare + /search.',
      items: [
        'Ship 4 spec #1. Two new surfaces: a cross-run search dashboard and a two-run side-by-side comparison view.',
        'Cross-run search (#/search): type to search across all runs by topic, brief content, and final documents. Results grouped by run with match-type chips and snippets. Click any result to jump to that run.',
        'Compare runs (#/compare): select any two runs from dropdown pickers. Synced-scroll side-by-side panels show each run\'s phases and turns. A delta column highlights differences in drafter, phase count, status, cost, and per-phase turn counts.',
        'New /api/search server endpoint with substring matching (both local fs and Supabase hosted modes). Results capped at 50.',
        'Chrome bar gains Compare and Search tabs. SearchPalette and ShortcutsOverlay updated with the new navigation targets.',
      ],
    },
    {
      version: '0.57.0',
      date: '2026-05-17',
      summary: 'Keyboard contract + shortcuts overlay + search palette.',
      items: [
        'Ship 3 spec #2. Global keyboard contract wired at the document level. Input/textarea exempt from single-key bindings; modifier chords (Cmd+K) fire everywhere.',
        'Press ? to open a shortcuts overlay listing every keyboard binding by context (global shortcuts, negotiate review modal). Built on the Modal primitive from SPEC-0058.',
        'Press Cmd+K (or Ctrl+K) to open a search palette. Type to filter runs by topic, ID, status, or phase. Arrow keys walk results, Enter navigates, Esc closes. Also surfaces navigation targets like All runs, How it works, and Design language.',
        'Existing / shortcut for focusing run-list search (SPEC-0055) preserved and documented in the overlay.',
      ],
    },
    {
      version: '0.56.0',
      date: '2026-05-17',
      summary: 'Modal primitive + RoundScrubber + provider-symmetric SourceCard + sub-tab migration.',
      items: [
        'Ship 3 spec #1. CSS-class-backed Modal replaces the inline-styled modal. Two variants: single (standard) and split (side-by-side). Agent-color left border (sable for Claude, sage for GPT). Theme-aware backdrop with focus trap.',
        'RoundScrubber at the bottom of split modals. Walk through negotiation rounds without closing the modal -- click round pills or prev/next arrows to switch content in place.',
        'Provider-symmetric SourceCard: Anthropic and OpenAI web search results now render identically. Title, host chip, page age chip, cited text blocks, and [cited] tags show for both providers. Missing data renders as muted placeholders instead of hiding rows.',
        'All modal sub-tabs migrated from inline-styled button rows to the TabGroup line variant (underline stripe). Consistent typography and interaction across all modal contexts.',
        'Source cards and citation cards now use Chip primitives for host, page age, cited, and citation badges.',
      ],
    },
    {
      version: '0.55.0',
      date: '2026-05-17',
      summary: 'Timeline + critique restructure -- PhaseRail, ChipCluster, 3-axis filter, DriftCluster, Summary enhancement, CardHeadline migration.',
      items: [
        'Ship 2 surface spec #3. Sticky PhaseRail down the timeline pane left edge shows phase progress with click-to-scroll navigation. Completed phases show green dots, current phase pulses blue.',
        'ChipCluster discipline: chip rows that exceed 5 items collapse into a +N overflow button. Prevents long unreadable chip clusters on dense turns.',
        'Three-axis critique filter: filter by kind (Questions/Disagreements/etc.), agent (Claude/GPT), and status (Open/Resolved/Drift). All axes combine with AND logic for precise drill-down.',
        'DriftCluster: ghosted items that went unanswered for multiple rounds now render in a dedicated Drift group above Open and Resolved, surfacing neglected items at scan distance.',
        'Summary tab now opens with the highest-leverage open item (most ghosted rounds) as a full QuestionThread. Immediate deadlock visibility on the post-mortem view.',
        'CardHeadline badges migrated from inline styles to Chip primitives. PaneButton/PaneButtonGroup dead code removed.',
      ],
    },
    {
      version: '0.54.0',
      date: '2026-05-17',
      summary: 'Run detail header restructure + chrome unification + ActiveRunChip + blocking callout.',
      items: [
        'Ship 2 surface spec #2. Chrome bar right cluster unified: HowItWorksLink migrated to Tab primitive, ActiveRunChip shows the short run ID when viewing a run detail for single-click back navigation.',
        'Run-detail header restructured with equal-row padding. Drafter callout pill with agent-tinted Chip + icon replaces the inline metadata text. Claude drafter shows sable, GPT shows sage.',
        'Blocking-item callout bar between header and content. Shows open + ghosted item counts from phases 2 and 4. Click jumps to the first open item in the critique pane.',
        'Timeline agent pills (Claude/GPT) migrated from bespoke inline styles to the design-system AgentStrip primitive. Activity phrase preserved via custom right prop.',
      ],
    },
    {
      version: '0.53.0',
      date: '2026-05-17',
      summary: 'Run list rework -- sortable columns, attention promotion, search, URL state.',
      items: [
        'Ship 2 surface spec #1. Sortable columns: click any column header to toggle ascending/descending sort with arrow indicator. Default sort is newest-first. Sort state persists in the URL so bookmarks and page reloads preserve your view.',
        'Attention-first section: errored and deadlocked runs surface at the top of the list in a dedicated "Needs attention" group with an inline summary (phase, rounds, status). No more scanning the full list to find broken runs.',
        'Search input in the header bar. Press / from anywhere on the page to jump to search. Filters runs by ID, topic, status, or phase. Search term persists in the URL.',
        'Visual attention borders: errored runs get a red left border, deadlocked runs get a warning-amber left border. Visible at scan distance in both themes.',
        'Filter tabs now wrapped in the design-system TabGroup primitive. URL filter state persists across page loads.',
      ],
    },
    {
      version: '0.52.0',
      date: '2026-05-17',
      summary: 'QuestionThread + QuestionRef primitives — AP-01 enforcement.',
      items: [
        'Ship 2 spec #3. QuestionThread: vertical turn-by-turn conversation timeline for critique items. Shows who raised the question, who responded in which round, with what verdict. Dashed-rail timeline with agent-tinted pills, serif quote blocks, drift/resolved footer banners.',
        'QuestionRef: decoded reference replaces legacy cryptic Q-g-r1-04 database keys. Compact format (Q . 04) inside threads; full format (Q . 04 . [GPT] . r1) for standalone references. AP-01 anti-pattern enforcement — no database shape leaks into the UI chrome.',
        'Question cards now expand into full QuestionThread views with origin + response turns derived from the existing question data. Ghosted questions show drift status with warning banner.',
        'CardHeadline for questions shows decoded number (01) instead of raw database key (Q-c-r1-01).',
      ],
    },
    {
      version: '0.51.0',
      date: '2026-05-17',
      summary: 'Tab system (3 variants) + table header distinction.',
      items: [
        "Ship 2 spec #2 of the design-system arc. Unified Tab primitive with three variants: default bordered pill (filter chips, chrome buttons), tabs-line (underline stripe for modal sub-tabs), tabs-solid (segmented control for pane switchers). One component subsumes four legacy inline-styled components.",
        "Critique pane phase buttons (Phase 2/4/Summary) and filter chips now render via the new tabs-solid segmented control. Conversation/Consumption toggle also migrated. Visually identical intent, class-backed instead of inline-styled.",
        "Run-list filter strip (all/running/converged/deadlocked/errored/completed) migrated to Tab with leading dot + filterTone color classes + count badges. Same data, new chrome.",
        "Table headers (CMP-11) now visually distinct from body rows: elevated background, stronger border, semibold weight, lifted text color. Applies to both the generic .tbl primitive and the bespoke run-list grid header.",
        "Dead PhaseTab function removed from run-detail.jsx (defined but never called since spec 0046).",
      ],
    },
    {
      version: '0.50.0',
      date: '2026-05-17',
      summary: 'Primitive vocabulary — Button, StatusBadge, Chip, RunIDChip, Card, AgentStrip, segmented ThemeToggle.',
      items: [
        "Ship 2 spec #1 of the design-system arc. New components.css lands the V1 component classes (.btn, .sb, .chip, .rid, .card, .as / .ai, .tt) on top of SPEC-0050's tokens + base. Class-only — no hex codes anywhere in components.",
        "Five legacy primitives → three: StatusBadge (state), Chip (data), RunIDChip (identity). The Tab primitive that subsumes the rest (PaneButton / PhaseTab / FilterChip / ViewSwitcher) arrives in SPEC-0053. Legacy Pill + StatusBadge stay unchanged in shared.jsx; surface specs sweep call sites onto the new primitives one by one.",
        "ThemeToggle restored to segmented with sliding thumb. Same sun/moon two-cell shape you already had, plus a small thumb element that animates between cells in 180 ms ease-out (the prior implementation had the segmented shape but the thumb was just an active-cell background flip).",
        "Today's-component migration — four of the components introduced in specs 0046-0048 (ReconcileChip, RepairChip, GhostedAnnotation, GhostedRoundsBadge) now consume the new primitives. ReconcileChip is the load-bearing one: all 5 visual states preserved (verified / drift / partial / unverified / awaiting_provider_data); body composition stays bespoke; tone classes drive color. CardHeadline + ProviderBilledLine defer to later specs (see CHANGELOG for reasons).",
        "AgentStrip min-width 480 → 320 (CMP-07). The strip no longer dominates the header after the upcoming chrome restructure (SPEC-0056).",
        "Cache-bust query strings (`?v=NNNN`) added to every local stylesheet and JSX script in index.html. Bumps each spec so browsers refetch fresh code after deploy — addresses a real verification pain point where stale CSS/JSX masked the new behaviour locally.",
      ],
    },
    {
      version: '0.49.0',
      date: '2026-05-17',
      summary: 'Consumption tab — content-vs-billing split, output bar, cross-turn slot naming.',
      items: [
        "Follow-up to the 0.47.1 cached-token fix. The fix made cache_read tokens visible but exposed two new problems: Claude's 'Brief' sub-bar was 3-4× GPT's in P1/P2 (because Anthropic's Messages API bills cache_read across every internal turn of a tool-use loop), and the expanded Consumption card had no output bar even though output is the more expensive rate.",
        "Card headline now reads `60kt seen · 411kt billed · 7.2kt out` with a `× 7 reuse` chip when there's measurable cache amplification. When there's no reuse, collapses to the simple `71kt in · 1.2kt out` form. Same split appears under the collapsed-row segmented bar.",
        "Per-piece sub-bars (`User prompt: Brief`, `Claude's Phase 1 draft`, etc.) sized to raw content heuristic counts instead of being renormalised to billed `tokensIn`. Sums to roughly content size now, matching distinct content the model saw.",
        "New `OutputBar` in the expanded card, colored by the **destination input slot** (`d1` / `d2` / `hist` / `draft` / `histp`) — not the agent color. So P1 Claude's output bar uses the same ochre as the `d1` segment on every later card's input. Scroll-trace an artifact through the run by color alone.",
        "Cost cluster gains the output split: `Input: $A · Output: $B · Web search: $C · Total: $T`. Output cost computed client-side from a small rate table mirroring `agents/pricing.py`. Models not in the table fall back to $10/MTok and the figure is marked with `~`.",
        "Pure frontend, no backend changes. 725 pytest baseline preserved.",
      ],
    },
    {
      version: '0.48.1',
      date: '2026-05-17',
      summary: 'CI fixture check-in — partner-vetting run committed so tests.yml passes on CI runners.',
      items: [
        "Hotfix between SPEC-0050 (design foundation) and SPEC-0052 (primitive vocabulary). Pure ops change; no UI behaviour change.",
      ],
    },
    {
      version: '0.48.0',
      date: '2026-05-17',
      summary: 'Design-system foundation — new fonts, retuned contrast, MDI icons, no emoji, focus ring, reduced-motion contract.',
      items: [
        "First spec of the 11-spec Claude Design migration arc. Invisible-but-everywhere refactor that underwrites Ship 2+. No surface restructure yet — fonts, colors, spacing, and icon system change; layout stays put.",
        "Typography swap. JetBrains Mono and Geist are gone. IBM Plex Sans handles UI chrome + data (tabular figures via `font-variant-numeric: tabular-nums` on the `.num`/`.mono` utilities). IBM Plex Serif handles agent-produced prose, hero, headings. Designed-together IBM pair — same x-height, blends without sacrificing distinction. 17 hardcoded SVG font-family attributes across how-it-works, auth, and design-language swept to the new families.",
        "Token & contrast retune. Foreground tier brightened in dark mode and darkened in light to clear WCAG-AA at 12 px (the small-label tier was the load-bearing fix). Status-background tokens land (`--ok-bg`, `--info-bg`, `--warn-bg`, `--err-bg` + matching borders); banners no longer inline rgba. 4-px spacing grid enforced; radii collapsed 10 → 4 named + pill; 3 elevation levels + 3 motion durations; agent-color rgba bumped in light mode for visibility on warm white.",
        "Accessibility. Global `:focus-visible` ring (2 px `--info` at 2 px offset) lands in `base.css` — no component opts out. `@media (prefers-reduced-motion: reduce)` forces all durations ≤1 ms and disables halos / caret blink / scroll-behavior.",
        "Material Design Icons. New `icons.jsx` (~60 MDI icons inlined as path data) exposes `<Mdi name size color />` on window. The legacy `Icon` object in `shared.jsx` becomes a thin shim — 14 keys (`Activity` / `List` / `Palette` / `Chevron` / `Dot` / `Check` / `X` / `Arrow` / `ArrowLeft` / `Spark` / `Warn` / `Gear` / `SignOut` / `Help`) forward to `<Mdi>` so call sites keep working through the migration. Future specs move call sites onto `<Mdi>` directly.",
        "Emoji eliminated. 13 emoji swept across 4 surfaces: 🔎 → `magnify`, ⚠ → `alert`, 🔗 stripped from DOM text, 📄/📎 → `file-document`, ⏳ → `timer`, ✓ → `check`. The 5-state ReconcileChip palette migrated from `{glyph: '✓'}` to `{icon: 'check'}` while preserving every visual state (verified / drift / partial / unverified / awaiting_provider_data). Three carve-outs deferred to later specs — see spec 0050 for rationale.",
        "File layout. New `tokens.css` (authoritative tokens), new `base.css` (body + reset + type utilities + focus + motion + markdown), new `icons.jsx`. `theme.css` slimmed from 383 → 109 lines (legacy component classes only — drains spec-by-spec in Ship 2). `index.html` swaps font links and adds the new stylesheets + icons script in load order.",
      ],
    },
    {
      version: '0.47.0',
      date: '2026-05-17',
      summary: 'Daily reconciliation cron, powered by Supabase-source run-cost data.',
      items: [
        "`reconcile-costs` learned a new flag: `--source supabase` queries the hosted `runs` table (where runs persist via spec 0020) instead of walking the local `runs/` directory. Same `LocalTotals` shape as the local source; same delta math downstream. Default stays `local` (no behaviour change for laptop use).",
        "GitHub Actions daily cron is back on (was disabled in 0.46.1). Runs at 02:00 UTC with `--source supabase --push`, so the CI runner's empty `runs/` directory no longer breaks anything — daily snapshots upsert into the `reconcile_results` Supabase table and the run-detail verification chip picks them up automatically.",
        "0.46.0 (a few hours earlier) shipped the rest of the always-on system: `ReconcileChip` in run-detail header (`✓ verified` / `⚠ drift` / `partial` / `unverified` / `awaiting`), Consumption-tab provider-billed annotation, `pricing_version` snapshot. With 0.47.0 the cron-driven path actually works end-to-end without manual intervention.",
        "Anthropic side stays graceful-degraded — admin keys are still unavailable in this org's Console UI. The cron will report `partial · ✓ OpenAI · ⚠ Anthropic missing` until that's resolved out-of-band.",
      ],
    },
    {
      version: '0.46.0',
      date: '2026-05-17',
      summary: 'Always-on cost verification against provider invoices.',
      items: [
        "New `dual-research reconcile-costs` CLI compares local `metrics.json` totals against the providers' billing APIs (OpenAI Organization Costs + Anthropic Admin Cost Report) at daily granularity. Five honest states: `verified` / `drift` / `partial` / `unverified` / `awaiting provider data`. CLI modes: `--day` · `--from/--to` · `--all` · `--run RUN_ID` · `--since-yesterday`. Exit code 0 within tolerance, 1 if any row exceeds — CI/cron friendly.",
        "Each provider's admin key is independently optional. Set `OPENAI_ADMIN_KEY` and/or `ANTHROPIC_ADMIN_KEY` (plus optional `OPENAI_PROJECT_ID` / `ANTHROPIC_WORKSPACE_ID` for scoping) in env or via Fly secrets. A missing key surfaces as `providers_skipped` on the report; the system reports honestly what was checked vs not. When a key is later added, restart and that side activates — zero code changes.",
        "New `<ReconcileChip>` in the run-detail header reads `/api/reconcile/<date>` and tells you, at a glance, whether the run's day was verified, drifted, partially-checked, unverified, or awaiting provider data. Tooltip shows local vs billed totals, which providers contributed, and which were skipped with why.",
        "Consumption-tab cards gain a `Provider-billed: $X · Δ $Y (Z%)` line under the costs cluster when the day's reconciliation has matched per-(provider, model) numbers. Flagged rows (delta exceeds tolerance, default 1.0%) get a warn-tinted ⚠.",
        "Daily reconciliation runs automatically via GitHub Actions at 02:00 UTC (manual `workflow_dispatch` also available); reports upsert into the new Supabase `reconcile_results` table so hosted-mode UI reads them. Local CLI invocations write `reconcile/<date>.json` snapshots beside the runs/ directory.",
        "`metrics.json` now records a `pricing_version` string (initial value `2026-05-17`, human-bumped when rates change). `recompute-costs` stamps the rewritten file with the live constant and surfaces the before/after transition on its per-run diff. A snapshot regression test ensures no rate-table edit can ship without a version bump.",
        "Anthropic side ships built but currently inactive: the Console's admin-keys page is no longer present in our account (Service Accounts only mint workspace-scoped `sk-ant-api03-` keys which 401 on `/v1/organizations/*`). Code path is complete + tested against a canonical docs-shape fixture; when an admin key becomes available the Anthropic half lights up automatically with zero changes.",
      ],
    },
    {
      version: '0.45.0',
      date: '2026-05-17',
      summary: 'Run-detail resilience + repair-turn visibility.',
      items: [
        "Run-detail page no longer crashes on historical runs that reached `completed` without a drafter (five local runs hit this — anything killed before Phase 3 but marked complete by an older orchestrator). `ArtifactHeader` now guards `meta` defensively in its `doc` / `doc-live` branches (matching the pattern already used in `DocumentModal`); `buildLiveTimeline` skips the `doc-final` push when there's no drafter, so the artifact strip just doesn't include a 'Final document by null' card for those runs.",
        "Finalize path hardened against the resume scenario where `phase2_outcome` is `None` on disk. The original spec-0036 guards on `confidence_tag` + `render_metadata_header` covered the APPROVED branch; spec 0047 adds the DEADLOCKED + None Phase 2 regression test so future regressions don't slip the guard.",
        "Phase 4 (and Phase 2) protocol-repair turns now appear as their own cards on the Consumption tab, adjacent to the original turn with a small `repair` chip and slightly muted background. Pre-spec the per-turn aggregator collapsed `phase4-r1-claude` + `phase4-r1-claude-repair` siblings onto one key (last-write-wins), so the Consumption tab under-reported repair cost. New behaviour: each LLM call is its own card. Agent-level totals are unchanged (still sum every event — matches the bill).",
        "Timeline turns whose parent has a repair sibling carry a small `+repair` discoverability chip on the `StatsChips` strip, so the user knows to look at the Consumption tab for the per-call breakdown.",
        "Per-turn key on the wire gains a `_repair` suffix for sibling labels (`phase4_round1_claude_repair`, `phase2_round4_gpt_repair`). Matches the suffix convention already used by the per-turn input bundles and search audit files. No transcript / on-disk schema changes.",
      ],
    },
    {
      version: '0.44.0',
      date: '2026-05-17',
      summary: 'Critique panel + Summary + Consumption rework + design unification.',
      items: [
        "Critique pane header restructured. The three buttons — `Phase 2 Negotiate`, `Phase 4 Review`, `∑ Summary` — are the primary navigation on the left; the count cluster (`introduced · open · resolved · ⚠ drift`) sits right-aligned. Pre-spec the header led with `Critique · N introduced` and the buttons sat as a secondary toolbar; now the navigation is at the visual anchor.",
        "Per-phase filter chips are context-aware. Phase 2 → `[All | Questions | Disagreements | Claims]`. Phase 4 → `[All | Issues | Comments | Disagreements]`. Kinds the phase doesn't emit don't render as zero-count chips. Switching phase auto-resets the filter if the previous selection isn't allowed in the new phase.",
        "Critique cards render human-readable headlines: `Issue C-1 · open · Mutation testing gate lacks a concrete enforcement mechanism…` instead of `**C-1** — open — Mutation testing gate…`. The round range + the cryptic internal IDs (`I-c-r1-01`) move into the expanded body — visible when you click the card, gone from the always-visible headline.",
        "Per-card ghosted-rounds annotation. When the system-derived ledger (spec 0043) shows a critique item was open for N rounds without an explicit addressing signal, the card headline carries a small `⚠ ghosted Nr` badge with a tooltip explaining what it means. Spec 0043 defined the component but didn't wire it; spec 0046 finishes the wiring.",
        "Summary tab redesigned as per-kind, per-model tables. Pre-spec was one 11-column table where most cells were `—`; spec 0046 splits it into one table per kind the phase emits (Phase 2 → Questions / Disagreements / Claims; Phase 4 → Issues / Comments). Columns are `Round | Claude raised | Claude {closed} | GPT raised | GPT {closed} | Open` — per-model surfaces who carried what. Empty kinds dropped entirely.",
        "Consumption tab rebuilt as single-row cards. Each phase-round is one card; expanding it now reveals the per-piece breakdowns INSIDE the same card. Pre-spec the expand opened a separate full-width grid row below the lanes; the eye kept reorienting left/right. The new card keeps the flow linear top-to-bottom.",
        "Consumption tab drops the 'not used in this turn: …' footer. Same rule as the input full-view (spec 0045 D3) — empty pieces simply don't render. Absence is the signal.",
        "Consumption tab web-search cluster cleaned up. Replaces the confusing `web searches: N · of which web search: $X` (there was no parent total for 'of which' to refer to) with a two-line `Tokens: $A · Web search: $B · Total: $T` + `Searches: N · Queries: M` cluster. The counts line only renders on turns that ran a search.",
        "All toggle / tab / filter buttons across the run-detail view use one shared `PaneButton` component. Pre-spec the Critique phase tabs, the Summary button, the filter chips, and the Conversation/Consumption pair each had their own border, padding, font, and hover/active styling. One design language now; differences are semantic (active / hover / disabled), not cosmetic.",
      ],
    },
    {
      version: '0.43.0',
      date: '2026-05-17',
      summary: 'Full-view shell standardisation + model pill layout.',
      items: [
        "Tabs on every full-view modal now render in a canonical order: `Content | Input | Web Search | Sources | Files`. Open two different modals back-to-back and the tabs stay in the same slot — no more re-finding `Input` next to the right edge in one modal and next to `Content` in another. Tabs whose content is empty are hidden entirely (Web Search isn't rendered on turns that ran no searches; Files isn't rendered on briefs that attached none); the hallucination ⚠ badge stays as a tab-label exception when there's real search data to flag.",
        "Input full-view drops the 'not used in this turn' rows. Only pieces the orchestrator actually inlined for THIS turn render — absence is the signal. The wire bundle still carries the full piece vocabulary (with empty strings for absent pieces), but the frontend filters them out, so a Phase 2 round-1 turn no longer renders 'Prior Phase 4 review turns (not used in this turn)' as visual noise.",
        "The brief is now labelled 'User prompt: Brief' and floats to the top of the input bundle. The brief IS the user-supplied research prompt for the run today (the CLI doesn't have a separate `--prompt` field yet), so the label tells the reader what role this section plays.",
        "Side-by-side modals (Phase 1 plan-draft, Phase 2 / Phase 4 turn modals) now use equal-width columns. `NegotiateReviewModal` was 1.5fr / 1fr (left-biased); `DraftReviewModal` was 1fr / 1.3fr (right-biased). Both move to 1fr / 1fr so the two panes read as parallel surfaces — neither is the 'primary'.",
        "Timeline-header model pills (Claude, GPT) are now equal-width with identity left-aligned (logo · provider · model) and metrics right-aligned (tokens · cost · ● status). The Claude pill grew ≈20% to give both pills room to breathe at the new alignment; GPT matches Claude. The metric strings sit at the right edge regardless of how long the model name is.",
      ],
    },
    {
      version: '0.42.0',
      date: '2026-05-17',
      summary: 'Turn-input semantics + per-turn badge redesign + side-by-side framing.',
      items: [
        "Per-turn count chips redesigned: explicit `+raised  −resolved` per kind instead of a single number with a cryptic `⤴` glyph. `+5 Q  −1` reads as `raised 5 questions, closed 1 prior` at a glance. Closed-only chips render as `−3 prior Q` in green. Zero-on-both chips are omitted so quiet turns stay sparse.",
        "The per-turn `negotiating` / `reviewing` status pill is gone — the phase-section header already labels the phase, the pill was noise. `✓ agreed` / `✓ approved` chips now appear only on the LAST turn of a phase whose system-derived ledger reports zero open blocking items (system view, not the agent's mid-loop self-claim). On runs where spec 0043's ledger surfaces ghosted items the pill correctly stays hidden.",
        "Side-by-side modal left pane gets phase-aware document tabs: Phase 2 R1 = `[Other's draft | Brief | Your draft]`, R2+ adds `[Other's prior turn]` (default), Phase 4 = `[Current draft | Other's prior turn | Brief]`. Click a tab to see what the agent had as input — no more guessing. Phase 1 plan-draft modal gets a `[Brief]` tab.",
        "Phase 1 plan-draft modal gains a structured-items strip above the draft body. Each Phase 1 claim or open question (extracted by spec 0042) renders as a clickable chip; clicking jumps the left brief pane to the referenced block — the click-to-highlight wiring spec 0034 added for Phase 2/4 is now active for Phase 1 too.",
        "Right-pane empty-state copy is action-specific: distinguishes 'no activity at all', 'only-closed' (closed N prior items but raised nothing new), and 'raised-but-unanchored' (items exist but lack quote/after markers). Previously all three read the same.",
        "Sentiment paragraph on Phase 2 / Phase 4 timeline cards now reads the ledger for phase-wide open counts. 'Standing across the phase:' line is system-derived, not agent-self-reported.",
      ],
    },
    {
      version: '0.41.0',
      date: '2026-05-17',
      summary: 'Cross-round ledger + standing-items input + conservative convergence.',
      items: [
        "The orchestrator now maintains an authoritative cross-round ledger of every claim / question / disagreement / issue / comment, derived from the existing parsed sections in each turn file. Built deterministically on every snapshot. Per-kind closure detection: questions via `## Answers to:` positional + verbatim-match; disagreements via D-N appearance in resolved or final-surfaced sections; claims via D-N escalation match against substantive disagreements; issues via latest-round body markers; comments terminal `noted`.",
        "Round-N (N≥2) prompts now include a `## Standing items from prior rounds` section built from the ledger. The agent sees structured prior-state as input — items raised by the other agent listed first ('still on them'), items they raised second ('still on you'). Soft instruction (no new mandatory output section); items left unaddressed surface as ghosted in the UI. Capped at 30 items / 3000 chars with a truncation footnote so prompt growth stays bounded.",
        "Convergence is now conservative: a phase terminates only when both the agent self-counters (OPEN_QUESTIONS / OPEN_ISSUES / BLOCKING_DISAGREEMENTS) AND the system-derived ledger agree the open-set is empty. If they disagree, the phase keeps running and the agent is told (via the standing-items input next round) which items they ghosted. Drift signal surfaces in the UI as a small `⚠ drift` badge on the Critique pane header.",
        "Kill-switch built in: set `DR_LEDGER_MODE=legacy` in the environment to roll back to self-counter-only convergence and omit the standing-items section, without a code revert. The ledger is still built (UI uses it) but doesn't affect orchestrator behaviour. Default mode is `enforce`.",
        "Backfill is automatic — the aggregator rebuilds the ledger on every page-load from existing on-disk turn files. Hosted runs see ledger data + drift signal on next refresh, no migration needed.",
      ],
    },
    {
      version: '0.40.0',
      date: '2026-05-17',
      summary: 'Critique data integrity — Phase 1 sections parsed, badges reconcile, markdown rendering fixed.',
      items: [
        "Phase 1 plan-draft cards now show real chip counts. The parser learned to recognise the protocol's Phase 1 sections — `## N. Claims I Expect the Other Agent Might Dispute` and `## N. Open Questions` — that previously slipped through unparsed. Cards now display `claims · questions` chips when the agent emits them, and the misleading `disagreements` tag never appears on a Phase 1 card again (Phase 1 doesn't emit disagreements; only Phase 2 R≥2's `## Substantive disagreements I'm holding` does).",
        "Phase 2 round-1 `## Diff vs … Phase 1` content re-categorised from `disagreement` to `claim`. Semantic correction — R1 enumerates contested points being *raised*, only R≥2 turns them into held disagreements. Claude turn 1 now reads `6 questions · 10 claims · r1` instead of `6 questions · negotiating · r1`. Side-by-side modal gains a Claims group on the right pane.",
        "Timeline chip counts no longer trust the agent's `OPEN_QUESTIONS:` / `OPEN_ISSUES:` / `BLOCKING_DISAGREEMENTS:` self-counters as the source of truth. They now read from `run.{questions,disagreements,claims,issues,comments}` filtered by `raisedTurnKey`. Self-counters become a sanity-check (logged at debug when mismatched). Per-phase chip allowlist: P0/P3/P5 = none; P1 = claims + questions; P2 = questions + disagreements + claims; P4 = issues + comments + disagreements.",
        "Phase 2 / Phase 4 side-by-side modal's right pane stopped silently dropping rounds with no items. Aggregator always creates the `phase{N}_round{R}_<agent>` bucket — an empty list means 'we looked and parsed nothing'; a missing key means 'the turn file doesn't exist.' Phase 4 modal's left pane reliably resolves `currentDraftPath` now that the aggregator surfaces it on `Run`.",
        "Critique header math reconciles. `99 introduced · 15 open · 21 resolved` was reading `introduced` as a cross-phase total while `open / resolved` were phase-filtered. Both are phase-scoped now — switch phase tab, the math adds up within the selected tab.",
        "Brief content's first paragraph no longer renders as a bold heading. The brief uses `---` as a section divider; CommonMark setext headings treat `---` immediately following a paragraph as an H2 underline, which silently wrapped the prior paragraph in `<h2>`. New pre-pass adds blank lines around bare `---` / `===` dividers so they render as `<hr>` thematic breaks. Headings (`## 1. Origin and Context`) stay headings; paragraphs stay paragraphs.",
        "Foundation for the next spec: the new `Run.claims` array, `kind=\"claim\"` wire type, and `current_draft_path` field are what the upcoming cross-round ledger (spec 0043) will build on. This release stops short of ledger semantics — closure between rounds is still agent-self-managed until 0043 lands.",
      ],
    },
    {
      version: '0.39.0',
      date: '2026-05-16',
      summary: 'Critique classification fix + load-time resilience + sentiment paragraph + tighter cards.',
      items: [
        "Phase 4 critique now distinguishes Issues, Questions, Disagreements, and Comments instead of bucketing them all as 'questions'. The protocol uses three different markdown sections (Issue ledger, Open questions for X, Comments on the current draft) with different closure semantics, but the parser previously classified all three as 'question' — which is why partner-vetting's Phase 4 read 'APPROVED with 0 open issues' on the timeline and '74 questions, 61 open' on the critique pane at the same time. Phase 4 now reports 30 I (30 resolved · 0 open) · 0 Q · 0 D · 33 C, reconciling with the timeline.",
        "Phase 4 issue status comes from the markers inside each ledger entry ('open' / 'resolved' / 'non-blocking') — matching the agent's own OPEN_ISSUES: N end-of-turn counter. No more cross-round positional-match heuristic that mis-classified resolved items as still-open.",
        "The 'Could not load run' flash on initial page load is gone. useLiveRun now retries the first poll at 1s, 2s, 4s before settling into 5s steady-state. A single transient 502 (Fly cold-start wake + Supabase materialise) silently retries until the second poll succeeds. Once we have run data, a transient failure NEVER replaces the page with the error screen — the connected indicator dims naturally.",
        "Question / disagreement / issue / comment card headlines truncate hard at ~70 characters before the ellipsis. Column reads as a scannable list; the full text is in the expanded body and on hover.",
        "Timeline plan/turn cards now lead with an overall-sentiment paragraph on every phase: Positive — / Mostly positive — / Cautious — / Critical — / Solid — / Done —. Pre-spec, Phase 0 / 1 / 3 / 5 produced no sentiment and Phase 2 / 4 were terse. Now: '**Cautious —** Claude's round-1 difference inventory. Raised 6 new questions. Standing: 6 open questions.'",
        "New IssueCard and CommentCard components in the critique pane mirror the QuestionCard shape. Type filter strip becomes All / Issues / Questions / Disagreements / Comments with per-kind pills. Phase tab counts show I/Q/D/C breakdown (zeros collapse). Summary tab table gains I raised / I resolved / I still open + C noted columns.",
      ],
    },
    {
      version: '0.38.0',
      date: '2026-05-16',
      summary: 'Critique rework — Phase 4 answer linkage fix, compact cards, Summary tab, Timeline tabs re-alignment.',
      items: [
        "Phase 4 question status now transitions to `answered` correctly. The protocol uses two different section headings — Phase 2 writes `## Answers to {other}'s open questions`, Phase 4 writes `## Answers to {other}'s prior comments` — but the reconstruction regex only matched the Phase 2 form. Every Phase 4 question silently stayed `open` regardless of the next round's response. Partner-vetting Phase 4 now correctly reports 13 answered + 61 open instead of 0 + 74.",
        "Question and disagreement cards collapsed to a single readable line by default. Type pill, round range, one-line truncated body, status pill, chevron. Click expands to the full body plus quote / after anchors and (for questions) the answer body or (for disagreements) the progression timeline + current positions + resolution. Disagreement cards shrink from ~70px collapsed height to ~38px.",
        "Clicking any critique card flashes BOTH timeline endpoints — the raising turn and the answering/closing turn — on the left pane. Was wired for disagreements since spec 0034; now works reliably for Phase 4 questions too (the linkage was blanked by the bug above).",
        "Timeline plan/turn chip row gains an explicit `↩ N` annotation when a turn closed prior-round questions or disagreements. The pre-spec `(-N)` delta was generic — the new glyph makes the answered-this-round count legible at a glance.",
        "New `∑ Summary` tab on the Critique pane, visible only when the run reaches a terminal state (completed / deadlocked / errored). Body: per-phase table with one row per round showing Q raised / Q answered / Q still open / D raised / D resolved / D still open. Click an existing phase tab to drill back into individual cards.",
        "Conversation / Consumption tabs moved from the right edge of the Timeline toolbar to the LEFT edge — directly under the `Timeline · N artifacts` title where a reviewer naturally looks. The GPT pill stays on the right, preserving the spec-0038 vertical column with Claude's pill on the row above.",
      ],
    },
    {
      version: '0.37.0',
      date: '2026-05-16',
      summary: 'Cost-pipeline integrity — resume preserves prior cost, 1h cache priced at the 1h rate, web-search fees fold into the headline.',
      items: [
        "Run totals will go UP for runs that used web search or 1h cache writes — search fees are now part of the headline cost (previously a side-channel hidden in the Consumption tab). The audit of the partner-vetting run showed metrics.json reported $2.45 against a recomputed ~$9.86; that gap is what the run list will now show for every existing run.",
        "Resume now preserves the pre-resume cost record. `Metrics.load_or_new(path)` rehydrates from disk on every session entry, so a `--resume` after a kill no longer overwrites the pre-resume call list with only the resume-window calls (the bug that drove this spec).",
        "Cache writes are now priced at the tier the agent actually requested. The Anthropic agent requests `cache_control: {ttl: \"1h\"}` (since spec 0017) but the pricing table hardcoded the 5-minute rate (1.25× input) instead of the 1h rate (2× input). New runs price each tier exactly from `usage.cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens` on the Anthropic response.",
        "Transcript is now the canonical truth path in the aggregator. metrics.json is the cold-start fallback for runs that haven't emitted any turn yet (previously the priority was inverted, which let a stale-on-resume metrics.json silently mask the transcript's correct numbers).",
        "Transcript dedup by label. A parse-error recovery replays the same `turn_ended` label twice — the later one is the canonical successful attempt. The aggregator now keeps only the last occurrence per label so the agent rollup doesn't double-count the failed retry's cost. Sibling labels with `-repair` suffixes are NOT deduped — they're distinct API calls billed separately.",
        "`dual-research recompute-costs --run RUN_ID | --all [--push] [--dry-run]` is the new backfill subcommand. Re-walks each run's transcript, recomputes every per-turn cost under the new pricing rules, and rewrites metrics.json. Backs up the original to `metrics.json.pre-0039.bak` on the first invocation; idempotent on re-run.",
        "CostBadge tooltip + CLI `[run]` summary both show the breakdown when search fees fired: `$9.8551 (tokens $8.7801 · web search $1.0750)`. The Consumption tab's per-turn card relabels its old \"tool cost\" line to \"of which web search\" — same number, clearer that it's part of the headline, not on top.",
      ],
    },
    {
      version: '0.35.0',
      date: '2026-05-16',
      summary: 'Web search audit UI + agent-pill alignment fix.',
      items: [
        'Every turn that fired web search now carries a search-count chip on its timeline card (next to the existing token + cost chips). Tooltip reports "N web searches · M URLs retrieved"; quiet on turns where search didn\'t happen.',
        'Expanding a card surfaces a one-line audit affordance below the sentiment paragraph: "Pulled M results across N queries · click to inspect →". Click opens the full-view modal pre-positioned to the Web Search tab. Provider-aware copy: OpenAI without sources gets "M citations · click to inspect →" instead.',
        'New Web Search tab on every full-view modal — joins Content / Input on one-pane modals (Phase 0 critique, Phase 3 doc, Phase 5 final), as a sub-tab on the Phase 2/4 side-by-side left pane (Original | Input | Web Search), and on the Phase 1 draft modal\'s right pane (Draft | Web Search). The tab renders a per-query accordion: each query group lists every retrieved URL, with Anthropic carrying title + host + page_age chip + monospace cited_text block per citation, OpenAI carrying URL-only. Results that the model actually cited get a [cited] tag.',
        'Hallucinated citations — a citation referencing a URL that wasn\'t in any retrieval set — surface in three places: a ⚠ badge on the Web Search tab strip, a ⚠ dot on the per-query group header (when relevant), and a banner inside the tab body listing every offending URL + title. Pre-existing validator data; the UI just reads Citation.matched_query_id.',
        'New run-header chip: total searches across all turns · total consulted URLs. When any turn has an unmatched citation, appends an unmatched-count flag; click jumps the timeline to the first flagged card. Hidden entirely on pre-0036 transcripts so older runs stay clean.',
        'Agent-pill alignment fix (spec-0035 follow-up): Claude\'s pill sits on the right of the Timeline header row; GPT\'s used to sit on the LEFT of the toolbar row below, breaking the visual column. They now both right-align — toolbar order is now [live-count] [flex] [Conversation | Consumption] [GPT pill]. Pure JSX reorder, no CSS changes.',
        'Server: /api/runs/<id>/searches/index gains an optional ?include=summary query param returning a per-key {queries, consulted, has_warning} map so the chip layer reads counts from one per-run fetch instead of fetching every bundle. Backward-compatible — default response shape unchanged.',
      ],
    },
    {
      version: '0.34.0',
      date: '2026-05-16',
      summary: 'Web search audit foundation + parser fixes + resume hardening + --notion repeatable.',
      items: [
        'Web search is now audited per turn — every query, every retrieved URL (Anthropic also captures titles + page_age), and every citation (Anthropic captures the actual cited_text snippet) is normalised into a provider-neutral schema and persisted to session_dir/searches/<turn-key>.json. The new audit layer is the data foundation for the Web Search tab the next spec will surface in the UI; today you can already `jq` the bundles per turn.',
        'OpenAI calls now force search_context_size=high + include=[web_search_call.action.sources], so the model receives more page content before generating and the full retrieval URL list comes back (not just cited URLs). Closes the bulk of the OpenAI community complaint that the API "ran search but hallucinated citations anyway".',
        'A validator stamps four flags on each audit: search_performed, cited_url_not_in_consulted_sources (strong hallucination signal — cited a URL that wasn\'t in any retrieval set, after stripping utm_source-style tracking params), citations_without_search_event, queries_missing_from_actions. The "URL not in consulted set" check skips itself when the consulted set is empty so it doesn\'t false-positive on OpenAI without include.',
        'Three CRITICAL parser fixes: ## Evidence checked this round and ## Disagreement carryover audit regexes use \\b word boundaries (so headings with trailing context like "(3 sources)" or ":" no longer get missed). extract_revised_draft strips horizontal-rule-only bodies (the old behaviour treated "----" as a valid draft and overwrote the converged document). New inclusive draft extractor absorbs stray "## Plan summary"-style sibling sub-sections the drafter sometimes emits instead of nested "### …" — Phase 4 uses it now.',
        'Three orchestrator-hardening fixes: emit_final no longer crashes on --resume when phase2_outcome is None (the metadata header renders a "replayed from prior run" note instead). Repair-turn max_output_tokens raised 6144 → 16384 so large repaired turns don\'t truncate (matches the regular turn budget). Phase 4 now skips rounds whose turn files already exist on disk during --resume — replays state without re-issuing API calls or duplicating events.',
        '--notion is now repeatable and combines with --brief / --prompt. Multi-source briefs are concatenated in CLI order with a "# Source: …" header between sources. --resume and --push remain exclusive with input sources but the CLI validates that explicitly in main() rather than relying on argparse mutex groups (so the error message tells you which combination is invalid).',
      ],
    },
    {
      version: '0.33.0',
      date: '2026-05-16',
      summary: 'Consumption rework + header-placement fix + app-version chip.',
      items: [
        'Consumption-tab bars are now sized to the actual data range (largest input × 1.15) instead of the full 1M-token cap. A vertical tick marker on each bar shows where the context-window cap sits — both signals visible without burying small consumption in a 1px sliver.',
        'Caption above the Consumption grid names the scale: "scale: 87K · cap 1M". Bars are comparable across rows because the denominator is grid-wide.',
        'Clicking a Consumption row now opens two side-by-side per-agent cards (Claude on the left, GPT on the right). Each card has the agent\'s total bar at top + one sub-bar per input piece below at the same scale. Sub-bars sort by descending size; toggle to canonical Tk order via the sort chip on each card.',
        'Sub-bar palette is neutral (indigo / ochre / sage / plum / rose / teal / slate-amber) — explicitly distinct from agent-amber / agent-green. The total bar stays in agent color so the aggregate-vs-component distinction reads at a glance.',
        'Pieces not used in a turn collapse to a single "not used: …" footnote with friendly labels.',
        'App version chip in the chrome bar (left of "How it works"). Click it to see the release notes for what landed.',
        'Header fix: per-agent activity pills moved out of the run header and into the Timeline pane — Claude on the right of "Timeline · N artifacts", GPT in the toolbar row below. The Conversation / Consumption tabs also moved back into the Timeline pane (prominent style preserved). Run header collapses to two rows.',
      ],
    },
    {
      version: '0.32.0',
      date: '2026-05-16',
      summary: 'Critique navigation — first-class Q+D, side-by-side rework, sentiment cards, click-to-highlight.',
      items: [
        'Questions are first-class now — parallel to Disagreements. IDs assigned at parse time (Q-c-r1-01 shape), answers linked positionally from the next-round "Answers to X" section with verbatim-match confidence tagging. They show in the new Critique explorer alongside disagreements, typed.',
        'The right-pane explorer is renamed Critique — phase tabs show "Phase 2 · 3 Q · 4 D"-shape counts, and a new filter strip toggles between All / Questions / Disagreements. Each card has a Q or D left-rail tag.',
        'Click any Q or D card in the explorer → the matching turn-cards in the timeline flash for 2s (blue ring for questions, amber for disagreements). Lets you walk a critique\'s history from the explorer side.',
        'Side-by-side viewer reliability fix. Block IDs are now assigned at parse time on the backend (protocol/blocks.py), embedded as HTML comments in served markdown, lifted onto rendered DOM nodes by the frontend, and pre-resolved by the parser against the prior content. NegotiateReviewModal\'s jumpToItem uses the resolved ID via getElementById — fastest + most reliable. Falls back to the legacy text-scan only when the agent paraphrased the quote.',
        'Phase 1 plan cards open a new DraftReviewModal with the brief on the left (carrying the spec-0033 Original | Input sub-tabs) and the draft on the right. Each draft section heading has a "brief" affordance that scans the brief for the closest matching block.',
        'Cards on the timeline now show a sentiment paragraph when unfolded — "Claude still negotiating in round 3. Raised 1 new question, answered 3 prior questions, resolved 1 disagreement. Standing: 2 open disagreements." Replaces the single-line gist.',
        'Card chips gain round-over-round deltas: 4 Q (-2) means "two answered since last round"; 5 D (+1, -2) means "one new this round, two resolved". The chip tooltip explains.',
      ],
    },
    {
      version: '0.31.0',
      date: '2026-05-16',
      summary: 'Inputs foundation — universal Input view, Phase 0 split, two-row live header.',
      items: [
        'Every full-view modal now has an Input tab showing exactly what the model saw — system prompt + brief + drafts + plan + history, one collapsible section per piece. The Phase 2/4 side-by-side modal\'s left pane gains an Original | Input sub-tab strip; same component everywhere.',
        'Phase 0 split into three timeline cards: shared `input` (brief + system) opens a brief-audit modal, plus per-agent `claude` / `gpt` critique cards opening their own modals. The previous single card conflated input with response.',
        'Run-detail header redesigned: row 1 carries topic + cost + status + Conversation/Consumption tabs, rows 2-3 are per-agent strips showing `[icon] [model] · [tokens·cost] │ [pulse dot + activity sentence]`, row 4 has phase dots with labels + metadata. The two tabs are now primary chrome — accent underline on the active tab.',
        'Activity sentences are deterministic — `drafting parallel plan`, `negotiating · round 3`, `waiting for Claude`. Greys out + falls to a waiting phrase when the agent isn\'t live.',
        'Per-turn input bundles travel through a new `TurnInputs` event → on-disk `inputs/<key>.json` → REST endpoint `/api/runs/<id>/inputs/<key>`. Bundles are byte-equal to what the prompt builder emitted (placeholder substitution, no drift). Pre-0033 runs synthesise their Phase 0 input on-demand from `brief.md`.',
        'Fixed a latent regex bug in `_round_index_from_label` — Phase 2/4 Consumption-tab keys had been collapsing across rounds in production because the regex didn\'t recognise the `r{N}-` label form the orchestrator actually emits.',
      ],
    },
    {
      version: '0.30.0',
      date: '2026-05-16',
      summary: 'Phase-2 hash-drift escape, P2 summaries, live-push flag, dual-research-run skill.',
      items: [
        'Fixed a Phase 2 convergence bug where both agents emitted STATUS: AGREED but their AGREED_PLAN hashes kept drifting (OpenAI paraphrasing instead of copying verbatim). The orchestrator now fires a force-verbatim repair turn on first detection; if drift persists, it promotes the drafter\'s plan as canonical and exits Phase 2.',
        'Phase 2 prompts now require a `## Summary` section — matching Phase 0 / 1 / 3 / 4. Timeline cards on the Conversation tab finally show a meaningful TL;DR when you unfold them.',
        'New `--push-while-running` CLI flag: the orchestrator pushes the session-dir to Supabase every 30s during the run, so the hosted UI updates as phases land. A final synchronous push fires on exit. Opt-in; requires the supabase env keys.',
        'New `dual-research-run` Claude Code skill captures the canonical recipe for firing a test run: source the env keys, ensure the local UI server is up, fire the run with the right flags, report both URLs. Versions with the code.',
      ],
    },
    {
      version: '0.29.0',
      date: '2026-05-16',
      summary: 'Consumption-tab follow-ups — tier-lookup window, click-to-expand bars, per-phase web-search count.',
      items: [
        'Existing runs now render at the right context window (1M for prod tier) — the aggregator derives the cap by looking up the run\'s `model_id` against `config.TIERS` when the run_started event didn\'t carry it explicitly. No data migration; just redeploy.',
        'Click any phase row on the Consumption tab to see the exact per-input numbers as a 3-column table — kind · Claude tokens · OpenAI tokens — plus summary rows for input total, output, web searches, and tool cost.',
        'Per-phase web-search count + cost. APIs don\'t expose tool-token attribution (search results fold into input_tokens), so we surface the next-best thing: number of web-search calls per turn and their per-request cost. $10/1k for Anthropic, $25/1k for OpenAI Responses-API web_search. Stays out of the headline cost chip — it\'s a separate side-channel.',
      ],
    },
    {
      version: '0.28.0',
      date: '2026-05-16',
      summary: 'Timeline UX pass — inline unfold, per-input consumption segments, real context windows, parser repairs.',
      items: [
        'Cards on the timeline now unfold inline on click — showing a synthesised gist, the TL;DR summary, and a "View in full mode" button. The modal is no longer the immediate destination.',
        'Disagreement cards finally render their contested point. The parser falls back to the first content line of the entry when the agent didn\'t use the explicit `(a) D-N: "…"` form; progression "raised" notes pick up the same text.',
        'Consumption bars now break down into per-input coloured segments — brief / d1 / d2 / plan / hist / draft / histp — matching the Tk palette on this page exactly. Each phase orchestrator computes piece sizes via a char÷3.5 heuristic and renormalises against the provider\'s reported input_tokens.',
        'Bars are now sized to the model\'s actual context window. Prod-tier runs (Claude Sonnet 4.6 + GPT-5.5) draw 1M-wide bars on both lanes; test-tier honours each model\'s real cap.',
        '`agents/context_windows.py` (spec 0029) is gone — the wire format carries context windows now, sourced from `ModelSpec.context_window`. No hand-maintained registry to drift.',
      ],
    },
    {
      version: '0.27.0',
      date: '2026-05-16',
      summary: 'Token-consumption tab — per-turn context-window visualisation.',
      items: [
        'New `Consumption` tab in the timeline pane sits alongside `Conversation`; the two per-agent total chips move to the right end of the toolbar.',
        'Each row is one API call — P0 / P1 / P3 give a single row, Phase 2 and Phase 4 give one row per round. Bars on each side show the chat\'s context-window utilisation; subsequent rounds visibly grow as the prompt history accumulates.',
        'Bar denominator = the model\'s actual context window (Claude 200K, GPT-5.5 200K, GPT-5-mini 128K). Asymmetric widths are honest — the percent number underneath each bar is the apples-to-apples comparison.',
        'Each bar shows three layers: cache-read portion (lighter shade), fresh input (full agent colour), and a thinner output tail. Hover for the full breakdown including model id and cost.',
        'Aggregator preserves per-turn token detail on `Run.phase_token_usage` (camelised inner keys at the wire, e.g. `phase2Round3Claude`); old runs from before this spec show an empty state on the Consumption tab and remain unaffected on the Conversation tab.',
      ],
    },
    {
      version: '0.26.0',
      date: '2026-05-16',
      summary: 'Cross-review inline comments — Phase 4 side-by-side modal.',
      items: [
        'Clicking a Phase 4 turn card now opens the same side-by-side modal as Phase 2: the current converged document on the left, the agent\'s issues / comments / disagreements as anchored cards on the right.',
        'Left pane uses the latest converged-document version available — the highest-numbered `phase4/draft-v*.md` if a drafter revision has landed, else `phase3/draft-v1.md`.',
        'Phase 4 prompts get the same `> quote:` / `> after:` marker hint as Phase 2, under Issue ledger / Comments on the current draft / Substantive disagreements.',
        'Phase 3 (single-shot drafting) and the final document still open the single-pane modal — there are no critique sections to anchor to.',
        'Wraps up the visualisation track (specs 0025 → 0027 → 0028). Every place where an agent critiques prior content now has a side-by-side review modal.',
      ],
    },
    {
      version: '0.25.0',
      date: '2026-05-16',
      summary: 'Negotiate inline comments — side-by-side modal with anchored critique cards.',
      items: [
        'Clicking a Phase 2 turn card opens a side-by-side modal: prior content on the left, the agent\'s questions and disagreements as inline-comment cards on the right.',
        'Clicking a card scrolls the left pane to the referenced span and flashes it amber for 1.5s.',
        '"Missing X" critiques use `> after: <heading>` and render a dashed-ghost "insert here" placeholder under the named section.',
        'Keyboard walk: `j` / `k` (or ↓ / ↑) move between cards, `Enter` re-jumps the active card, `Esc` closes the modal.',
        'Anchoring is opt-in via a one-paragraph prompt hint asking agents to emit `> quote: <verbatim span>` under each numbered question / D-N disagreement. Un-anchored items still render — they just don\'t auto-jump.',
        'Older Phase 2 runs predate the marker convention and render as un-anchored cards. Re-running gives them the full experience.',
      ],
    },
    {
      version: '0.24.0',
      date: '2026-05-16',
      summary: 'How-it-works restructure — chat-lifecycle diagram, phase accordions, v3.5 process map.',
      items: [
        'New "Chat lifecycle" section answers when fresh API calls happen across phases — every phase, every round, every agent, with the exact context bundle inlined into each call shown as colour-coded chips.',
        '"Context grows, but the prefix is cached" stacked-bar visual makes the CACHE_BREAKPOINT story concrete — shows P0/P1, P2 r1/r3/r6, and P3 with the cache split point marked.',
        'Phase walkthrough converted to expandable accordions; each phase carries an Inputs / Chats / Output / Gate / Caps meta block.',
        'FAQ entries collapsed into accordions — one tap to expand the answer.',
        'TL;DR strip of four cards at the top (models · transport · timing · exit) so the protocol read in one screen.',
        'New "View full process map" fold-out under the phase strip — embeds the v3.5 protocol landscape (Phase 0 → Phase 4 → Final Document) with source-verification, repair, and exit-code callouts. Authored via the diagram skill, cream-and-indigo, locked alongside the page as a static SVG asset.',
        'Stateless-vs-persistent comparison panel calls out what dual-research does NOT do (no thread_id, no Assistants API) versus what it actually does (re-inlining via filesystem state).',
      ],
    },
    {
      version: '0.23.0',
      date: '2026-05-16',
      summary: 'Visualisation foundations — summary cards, modal pattern, preflight tabs, attachment ingest.',
      items: [
        'Timeline cards no longer expand inline. Each card shows a one-line TL;DR + "View full" button; clicking opens a big centred modal over a dimmed overlay.',
        'Preflight (Input) opens a tabbed modal: Content · Sources · Files. Images render as thumbnails, links list with host + caption.',
        'Brief ingest now captures attachments: inline markdown images / links, Notion image / pdf / bookmark blocks, plus a new repeatable `--attach VALUE` CLI flag (local file or URL).',
        'Hosted runs get a new `attachment_blobs` table; `--push` uploads binary attachments alongside the existing transcript and session files.',
        'TL;DR cards come from each agent\'s existing `## Summary` section — no prompt changes; the UI just stopped ignoring it.',
        'Foundation for the upcoming side-by-side inline-comments view: markdown rendering now emits a stable `id="b-…"` on every block, so future specs can anchor critic comments to specific paragraphs.',
      ],
    },
    {
      version: '0.22.1',
      date: '2026-05-16',
      summary: 'Run-detail header pass 2 + compact theme toggle.',
      items: [
        'Run-detail header trimmed further: icon-only back arrow, no brand pill, no copy-id chip, no "PHASE N Done" or "converged in …" duplicates.',
        'Topic carries a "TOPIC" caps tag and reads as the visual centre.',
        'Status badge composes with the errors count when present — `completed | ⚠ 3 errors`, right half clickable to open the errors view.',
        'Cost and total tokens fold into one badge.',
        'Chrome bar light/dark segmented toggle replaced by a single compact pill with sun and moon icon buttons inside.',
      ],
    },
    {
      version: '0.22.0',
      date: '2026-05-16',
      summary: 'Compact run-detail header, "How it works" page, release notes.',
      items: [
        'Run-detail header collapsed from four rows into two — one card-height of timeline recovered.',
        'New "How it works" page in the chrome bar — explains the protocol end-to-end.',
        'Release notes (this list). New entries land here whenever a spec changes user-visible behaviour.',
      ],
    },
    {
      version: '0.21.0',
      date: '2026-05-15',
      summary: 'Admin allowlist UI, profile menu, landing-page redesign.',
      items: [
        'Top-right avatar menu with Design language, Settings (admin only), and Sign out — replaces the standalone "Design" link.',
        'New #/settings page for admins: table of allowlisted emails, inline add, remove. Protected against self-delete and removing the only admin.',
        'Landing page redesigned: centered hero, two-agent SVG visual, official-looking Google sign-in button.',
      ],
    },
    {
      version: '0.20.0',
      date: '2026-05-15',
      summary: 'Google OAuth + email allowlist.',
      items: [
        'Sign-in via Google through Supabase Auth replaces the HTTP Basic stopgap.',
        'New `approved_emails` table gates every /api/* request by signed-in email.',
        '/api/health and /api/config remain public so the bundle can bootstrap.',
      ],
    },
    {
      version: '0.19.0',
      date: '2026-05-15',
      summary: 'Fly.io deployment of the UI server.',
      items: [
        'Hosted UI at https://dual-research-alex.fly.dev/, single small machine, auto-stops when idle.',
        'New RUNS_BACKEND=fs|supabase toggle: hosted reads runs from Supabase, local still reads from `runs/`.',
        'Detail view materializes a tmp directory from Supabase per request, then hands it to the existing aggregator unchanged.',
      ],
    },
    {
      version: '0.18.0',
      date: '2026-05-15',
      summary: 'Supabase schema + `--push` CLI.',
      items: [
        'New Postgres tables (runs, events, session_files) mirror the on-disk session-dir layout.',
        '`dual-research --push runs/<session-dir>` bulk-uploads a completed run. Idempotent on re-run.',
        'Orchestrator behaviour unchanged — push is a manual step after a run finishes.',
      ],
    },
  ];

  // ─── Small SVG building blocks ─────────────────────────────────────────

  function AgentDisc({ cx, cy, r, letter, color, bg, border }) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={r} fill={bg} stroke={border} strokeWidth="1.25" />
        <text x={cx} y={cy + r * 0.32} textAnchor="middle"
              fontFamily="IBM Plex Sans, system-ui, sans-serif" fontWeight="600"
              fontSize={r * 0.95} fill={color}>{letter}</text>
      </g>
    );
  }

  function ClaudeDisc(props) {
    return <AgentDisc letter="C"
                      color="var(--agent-a)" bg="var(--agent-a-bg-strong)"
                      border="var(--agent-a-border)" {...props} />;
  }
  function GptDisc(props) {
    return <AgentDisc letter="G"
                      color="var(--agent-b)" bg="var(--agent-b-bg-strong)"
                      border="var(--agent-b-border)" {...props} />;
  }

  function Arrow({ x1, y1, x2, y2, dashed, color = 'var(--md-outline)' }) {
    return (
      <line x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={color} strokeWidth="1.5"
            strokeDasharray={dashed ? '4 6' : null}
            markerEnd="url(#arrowhead)" />
    );
  }

  function ArrowDefs() {
    return (
      <defs>
        <marker id="arrowhead" viewBox="0 0 10 10" refX="9" refY="5"
                markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--md-outline)" />
        </marker>
      </defs>
    );
  }

  // ─── Phase strip (kept, theme-coloured) ───────────────────────────────

  function PhaseStrip() {
    const cells = [
      { tag: 'turn-based',  color: 'var(--agent-a)', label: 'P0 · Preflight',  sub: 'agreed_interpretation' },
      { tag: 'parallel',    color: 'var(--agent-b)', label: 'P1 · Research',   sub: 'independent plans' },
      { tag: 'turn-based',  color: 'var(--agent-a)', label: 'P2 · Negotiate',  sub: 'agreed_plan + drafter' },
      { tag: 'single-shot', color: 'var(--md-on-surface-muted)',    label: 'P3 · Draft',      sub: 'drafter writes doc' },
      { tag: 'turn-based',  color: 'var(--agent-a)', label: 'P4 · Review',     sub: 'cross-review + revise' },
      { tag: 'output',      color: 'var(--ok)',      label: 'final.md',         sub: 'single document' },
    ];
    return (
      <div style={{
        display: 'flex', gap: 6, padding: '14px 16px',
        background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)',
        borderRadius: 8,
      }}>
        {cells.map((c, i) => (
          <div key={c.label} style={{
            flex: 1, minWidth: 0, position: 'relative',
            padding: '8px 10px', background: 'var(--md-surface-container-high)',
            border: '1px solid var(--md-outline-variant)', borderRadius: 6,
          }}>
            <div className="mono" style={{
              fontSize: 9.5, color: c.color, letterSpacing: '0.06em',
              textTransform: 'uppercase',
            }}>{c.tag}</div>
            <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--md-on-surface)', marginTop: 4 }}>
              {c.label}
            </div>
            <div className="mono" style={{ fontSize: 9.5, color: 'var(--md-on-surface-faint)', marginTop: 2 }}>{c.sub}</div>
            {i < cells.length - 1 && (
              <span style={{
                position: 'absolute', right: -8, top: '50%', transform: 'translateY(-50%)',
                color: 'var(--md-outline)', fontFamily: 'IBM Plex Sans, ui-monospace, monospace',
                fontSize: 14, zIndex: 1,
              }}>▶</span>
            )}
          </div>
        ))}
      </div>
    );
  }

  // ─── Diagram: one Phase 2 round (kept from spec 0023) ────────────────

  function NegotiationRoundDiagram() {
    // Spec 0117 step 4 — depicts the five operation blocks of one agent's
    // negotiation turn plus the status footer that gates convergence.
    const dn = (id) => (window.DrArtifacts ? window.DrArtifacts.displayName(id) : id);
    const ops = [
      { name: 'RAISE',       hint: 'new Q / D / I / C' },
      { name: 'ADDRESS',     hint: 'reply to other agent' },
      { name: 'RESOLVE',     hint: 'mark items resolved' },
      { name: 'ACKNOWLEDGE', hint: 'confirm closure' },
      { name: 'WITHDRAW',    hint: 'retract own item' },
    ];
    return (
      <svg viewBox="0 0 720 280" style={{ display: 'block', width: '100%', maxWidth: 720, margin: '0 auto' }}>
        <ArrowDefs />

        <text x={360} y={20} textAnchor="middle"
              fontFamily="IBM Plex Serif, system-ui, sans-serif" fontSize={13.5} fontWeight={600}
              fill="var(--md-on-surface)">One agent's negotiation turn</text>
        <text x={360} y={36} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={10}
              fill="var(--md-on-surface-faint)">{dn('phase2.claude.r3')} or {dn('phase2.openai.r3')} — same shape every round</text>

        {ops.map((op, i) => {
          const w = 130;
          const gap = 8;
          const x = 30 + i * (w + gap);
          return (
            <React.Fragment key={op.name}>
              <rect x={x} y={56} width={w} height={70} rx={8}
                    fill="var(--md-surface-container-high)" stroke="var(--md-outline-variant)" />
              <text x={x + w / 2} y={84} textAnchor="middle"
                    fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={11.5} fontWeight={600}
                    fill="var(--agent-a)" letterSpacing="0.06em">{op.name}</text>
              <text x={x + w / 2} y={104} textAnchor="middle"
                    fontFamily="IBM Plex Sans, system-ui, sans-serif" fontSize={10}
                    fill="var(--md-on-surface-variant)">{op.hint}</text>
              {i < ops.length - 1 && (
                <Arrow x1={x + w + 2} y1={91} x2={x + w + gap - 2} y2={91} />
              )}
            </React.Fragment>
          );
        })}

        <rect x={30} y={148} width={660} height={44} rx={8}
              fill="var(--md-surface-container-low)" stroke="var(--md-outline-variant)" />
        <text x={50} y={170} fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={11} fontWeight={600}
              fill="var(--md-on-surface-variant)" letterSpacing="0.06em">STATUS FOOTER</text>
        <text x={50} y={186} fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={9.5}
              fill="var(--md-on-surface-faint)">
          STATUS: NEGOTIATING | AGREED   ·   OPEN_QUESTIONS: N   ·   OPEN_DISAGREEMENTS: N   ·   STRONGEST_REMAINING_OBJECTION: …
        </text>

        <text x={30} y={220}
              fontFamily="IBM Plex Sans, system-ui, sans-serif" fontSize={11}
              fill="var(--md-on-surface-variant)">
          <tspan fontWeight={600}>Convergence gate:</tspan>{' '}
          both agents emit <tspan className="mono" fill="var(--md-on-surface)">STATUS: AGREED</tspan>{' '}
          and Agreed-plan blocks hash-match.
        </text>
        <text x={30} y={240}
              fontFamily="IBM Plex Sans, system-ui, sans-serif" fontSize={11}
              fill="var(--md-on-surface-variant)">
          <tspan fontWeight={600}>Closeout round:</tspan>{' '}
          if items linger after AGREED, only RESOLVE / ACKNOWLEDGE / WITHDRAW are allowed.
        </text>
        <text x={30} y={260}
              fontFamily="IBM Plex Sans, system-ui, sans-serif" fontSize={11}
              fill="var(--md-on-surface-faint)" fontStyle="italic">
          Both turns fire in parallel via asyncio.gather.
        </text>
      </svg>
    );
  }

  // ─── TL;DR strip ──────────────────────────────────────────────────────

  function TldrCards() {
    const cards = [
      { kicker: '01 / MODELS',   head: 'Two agents, one doc',     body: 'Claude Sonnet 4.6 + GPT-5.5 race the same brief and converge on one final.md.' },
      { kicker: '02 / TRANSPORT', head: 'Stateless per call',     body: 'Every API call is a fresh prompt with full prior history re-inlined. No session IDs.' },
      { kicker: '03 / TIMING',   head: 'Parallel where possible', body: 'P0, P1, P2, P4 fire both agents at once via asyncio.gather — no "speaker order".' },
      { kicker: '04 / EXIT',     head: 'Mechanical convergence',  body: 'SHA-256 plan-hash match + zero blocking disagreements ⇒ advance phase.' },
    ];
    return (
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10,
        margin: '18px 0 36px',
      }}>
        {cards.map(c => (
          <div key={c.kicker} style={{
            padding: '14px 14px 12px', background: 'var(--md-surface-container-low)',
            border: '1px solid var(--md-outline-hair)', borderRadius: 8,
          }}>
            <div className="mono" style={{
              fontSize: 11, color: 'var(--md-on-surface-faint)', letterSpacing: '0.08em',
            }}>{c.kicker}</div>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--md-on-surface)', margin: '6px 0 2px' }}>
              {c.head}
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--md-on-surface-muted)', lineHeight: 1.45 }}>{c.body}</div>
          </div>
        ))}
      </div>
    );
  }

  // ─── Chat lifecycle grid (the new main visual) ────────────────────────

  function Tk({ kind, children }) {
    const styles = {
      brief: { bg: 'rgba(107,156,240,0.12)', border: 'rgba(107,156,240,0.32)', fg: '#9ab6e8' },
      d1:    { bg: 'var(--agent-a-bg-strong)', border: 'var(--agent-a-border)', fg: 'var(--agent-a)' },
      d2:    { bg: 'var(--agent-b-bg-strong)', border: 'var(--agent-b-border)', fg: 'var(--agent-b)' },
      hist:  { bg: 'rgba(212,160,86,0.12)', border: 'rgba(212,160,86,0.32)', fg: 'var(--warn)' },
      plan:  { bg: 'rgba(111,179,128,0.12)', border: 'rgba(111,179,128,0.32)', fg: 'var(--ok)' },
      draft: { bg: 'rgba(217,106,106,0.10)', border: 'rgba(217,106,106,0.28)', fg: 'var(--err)' },
      histp: { bg: 'rgba(212,160,86,0.06)', border: 'rgba(212,160,86,0.20)', fg: 'var(--warn)' },
    };
    const s = styles[kind] || styles.brief;
    return (
      <span className="mono" style={{
        display: 'inline-block', padding: '0 5px', borderRadius: 3,
        fontSize: 10, border: `1px solid ${s.border}`,
        background: s.bg, color: s.fg,
      }}>{children}</span>
    );
  }

  function CallBox({ agent, fresh = true, lines, out, outId, silent, noteIf }) {
    if (silent) {
      return (
        <div style={{
          padding: '10px 12px', borderRadius: 6, border: '1px dashed var(--md-outline-variant)',
          color: 'var(--md-on-surface-faint)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontStyle: 'italic', fontSize: 11.5, minHeight: 86,
        }}>silent — other agent does not fire</div>
      );
    }
    const isClaude = agent === 'claude';
    const bg = isClaude ? 'var(--agent-a-bg)' : 'var(--agent-b-bg)';
    const border = isClaude ? 'var(--agent-a-border)' : 'var(--agent-b-border)';
    const letter = isClaude ? 'C' : 'G';
    const letterColor = isClaude ? 'var(--agent-a)' : 'var(--agent-b)';
    // Prefer the canonical artifact ID and resolve to a display name
    // via the registry mirror; fall back to the literal ``out`` prop
    // for legacy callers passing free-form text.
    const outLabel = outId && window.DrArtifacts
      ? window.DrArtifacts.displayName(outId)
      : out;
    return (
      <div style={{
        padding: '10px 12px', borderRadius: 6,
        background: bg, border: `1px solid ${border}`,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--md-on-surface)' }}>
            <span className="mono" style={{ color: letterColor, marginRight: 4 }}>{letter}</span>
            new chat
            {noteIf && (
              <em style={{ fontStyle: 'normal', color: 'var(--md-on-surface-faint)', fontSize: 10.5, marginLeft: 4 }}>
                ({noteIf})
              </em>
            )}
          </span>
          {fresh && (
            <span className="mono" style={{
              fontSize: 9.5, padding: '1px 6px', background: 'var(--md-surface-container-highest)',
              border: '1px solid var(--md-outline-variant)', borderRadius: 999,
              color: 'var(--md-on-surface-muted)',
            }}>fresh prompt</span>
          )}
        </div>
        <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: 'var(--md-on-surface-variant)', lineHeight: 1.55 }}>
          {lines.map((line, i) => <li key={i} style={{ listStyle: 'disc' }}>{line}</li>)}
        </ul>
        {outLabel && (
          <div style={{ marginTop: 8, fontSize: 10.5, color: 'var(--md-on-surface-muted)' }}>
            <span style={{ color: 'var(--md-on-surface-faint)' }}>→ </span>{outLabel}
          </div>
        )}
      </div>
    );
  }

  function LifecycleRow({ phase, tag, claude, openai, gather }) {
    return (
      <React.Fragment>
        <div style={{
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          padding: '12px 10px', background: 'var(--md-surface-container-high)',
          border: '1px solid var(--md-outline-variant)', borderRadius: 6,
        }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--md-on-surface)' }}>{phase}</div>
          <div className="mono" style={{
            fontSize: 9.5, color: 'var(--md-on-surface-faint)', letterSpacing: '0.06em',
            textTransform: 'uppercase', marginTop: 3,
          }}>{tag}</div>
        </div>
        {claude}
        {openai}
        {gather && (
          <div className="mono" style={{
            gridColumn: '2 / 4', textAlign: 'center', fontSize: 10,
            color: 'var(--md-on-surface-faint)', padding: '2px 0', letterSpacing: '0.04em',
          }}>{gather}</div>
        )}
      </React.Fragment>
    );
  }

  function ChatLifecycle() {
    const claudeCall = (lines, outId, noteIf) => <CallBox agent="claude" lines={lines} outId={outId} noteIf={noteIf} />;
    const openaiCall = (lines, outId, noteIf) => <CallBox agent="openai" lines={lines} outId={outId} noteIf={noteIf} />;
    const silent     = <CallBox silent />;
    // Tk labels resolve through the registry mirror — text matches
    // what the rest of the UI surfaces show.
    const dn = (id) => (window.DrArtifacts ? window.DrArtifacts.displayName(id) : id);
    const tkBrief    = <Tk kind="brief">{dn('user_prompt')}</Tk>;
    const tkD1       = <Tk kind="d1">{dn('phase1.claude')}</Tk>;
    const tkD2       = <Tk kind="d2">{dn('phase1.openai')}</Tk>;
    const tkInterp   = <Tk kind="plan">{dn('phase0.agreement.interpretation')}</Tk>;
    const tkP0Hist   = <Tk kind="hist">{dn('prior_turns.phase0')}</Tk>;
    const tkP2Hist   = <Tk kind="hist">{dn('prior_turns.phase2')}</Tk>;
    const tkPlan     = <Tk kind="plan">{dn('phase2.agreement.plan')}</Tk>;
    const tkDraft    = <Tk kind="draft">{dn('current_draft')}</Tk>;
    const tkP4Hist   = <Tk kind="histp">{dn('prior_turns.phase4')}</Tk>;
    const tkLedger   = <Tk kind="hist">{dn('ledger.standing_items')}</Tk>;

    return (
      <div style={{
        display: 'grid', gridTemplateColumns: '110px 1fr 1fr', gap: 10,
        padding: 14, background: 'var(--md-surface-container-low)',
        border: '1px solid var(--md-outline-hair)', borderRadius: 8,
      }}>
        <div className="mono" style={{
          fontSize: 10.5, color: 'transparent', letterSpacing: '0.08em',
          textTransform: 'uppercase', padding: '6px 0',
        }}>phase</div>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--agent-a)', letterSpacing: '0.08em',
          textTransform: 'uppercase', padding: '6px 0',
        }}>Claude lane</div>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--agent-b)', letterSpacing: '0.08em',
          textTransform: 'uppercase', padding: '6px 0',
        }}>GPT lane</div>

        <LifecycleRow
          phase="P0 Preflight" tag="Round 1"
          claude={claudeCall([tkBrief], 'phase0.claude.r1')}
          openai={openaiCall([tkBrief], 'phase0.openai.r1')}
          gather="⎯⎯  asyncio.gather  · both fire at once  ⎯⎯"
        />

        <LifecycleRow
          phase="P0 Preflight" tag="Round 2..N"
          claude={claudeCall([
            tkBrief,
            <span key="h">{tkP0Hist} (both agents, every round)</span>,
            <span key="l">{tkLedger} (per-agent)</span>,
          ], 'phase0.claude.r3')}
          openai={openaiCall([
            tkBrief,
            <span key="h">{tkP0Hist} (both agents, every round)</span>,
            <span key="l">{tkLedger} (per-agent)</span>,
          ], 'phase0.openai.r3')}
          gather={`⎯⎯  loop until ${dn('phase0.agreement.interpretation')} is hash-matched  ⎯⎯`}
        />

        <LifecycleRow
          phase="P1 Research" tag="1 call / agent"
          claude={claudeCall([tkBrief, tkInterp], 'phase1.claude')}
          openai={openaiCall([tkBrief, tkInterp], 'phase1.openai')}
          gather="⎯⎯  asyncio.gather  ⎯⎯"
        />

        <LifecycleRow
          phase="P2 Negotiate" tag="Round 1"
          claude={claudeCall([tkBrief, tkInterp, <span key="d">{tkD1} · {tkD2}</span>], 'phase2.claude.r1')}
          openai={openaiCall([tkBrief, tkInterp, <span key="d">{tkD1} · {tkD2}</span>], 'phase2.openai.r1')}
          gather="⎯⎯  asyncio.gather  ⎯⎯"
        />

        <LifecycleRow
          phase="P2 Negotiate" tag="Round 2..N"
          claude={claudeCall([
            tkBrief,
            tkInterp,
            <span key="d">{tkD1} · {tkD2}</span>,
            <span key="h">{tkP2Hist} (both agents, every round)</span>,
            <span key="l">{tkLedger} (per-agent)</span>,
          ], 'phase2.claude.r3')}
          openai={openaiCall([
            tkBrief,
            tkInterp,
            <span key="d">{tkD1} · {tkD2}</span>,
            <span key="h">{tkP2Hist} (both agents, every round)</span>,
            <span key="l">{tkLedger} (per-agent)</span>,
          ], 'phase2.openai.r3')}
          gather="⎯⎯  asyncio.gather · loop until convergence or hard-cap  ⎯⎯"
        />

        <LifecycleRow
          phase="P3 Drafting" tag="drafter only"
          claude={claudeCall([
            tkBrief,
            tkInterp,
            <span key="d">{tkD1} · {tkD2}</span>,
            <span key="p">{tkPlan} (hash-verified)</span>,
            <span key="h">{tkP2Hist} as context</span>,
          ], 'phase3.draft.v1', 'if drafter')}
          openai={silent}
          gather={`⎯⎯  single call · ${dn('phase2.agreement.drafter')} → drafter  ⎯⎯`}
        />

        <LifecycleRow
          phase="P4 Review" tag="Round 1..N"
          claude={claudeCall([tkBrief, tkInterp, tkDraft, tkP4Hist, tkLedger], 'phase4.claude.r2')}
          openai={openaiCall([tkBrief, tkInterp, tkDraft, tkP4Hist, tkLedger], 'phase4.openai.r2')}
          gather='⎯⎯  asyncio.gather · drafter may emit a "## Revised draft" → phase4.draft.v2  ⎯⎯'
        />
      </div>
    );
  }

  function Legend() {
    const dn = (id) => (window.DrArtifacts ? window.DrArtifacts.displayName(id) : id);
    const items = [
      { kind: 'brief', label: dn('user_prompt'),                       hint: 'chat message + each attached source — composite' },
      { kind: 'd1',    label: dn('phase1.claude'),                     hint: "Claude's Phase 1 research plan" },
      { kind: 'd2',    label: dn('phase1.openai'),                     hint: "GPT's Phase 1 research plan" },
      { kind: 'plan',  label: dn('phase0.agreement.interpretation'),   hint: 'hash-matched scope + approach from P0' },
      { kind: 'plan',  label: dn('phase2.agreement.plan'),             hint: 'hash-matched canonical plan from P2' },
      { kind: 'hist',  label: dn('prior_turns.phase2'),                hint: 'every prior P2 turn, both sides — re-inlined each round' },
      { kind: 'hist',  label: dn('ledger.standing_items'),             hint: 'per-agent open-item ledger, fed back next round' },
      { kind: 'draft', label: dn('current_draft'),                     hint: 'the latest P3/P4 document version' },
      { kind: 'histp', label: dn('prior_turns.phase4'),                hint: 'every prior P4 review turn' },
    ];
    return (
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '8px 14px',
        marginTop: 14, padding: '12px 14px', background: 'var(--md-surface-container-high)',
        border: '1px solid var(--md-outline-hair)', borderRadius: 6,
      }}>
        {items.map(i => (
          <div key={i.kind} style={{
            display: 'flex', gap: 6, alignItems: 'center', fontSize: 11.5, color: 'var(--md-on-surface-variant)',
          }}>
            <Tk kind={i.kind}>{i.label}</Tk>
            <span>{i.hint}</span>
          </div>
        ))}
      </div>
    );
  }

  function ComparePanel() {
    return (
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 18,
      }}>
        <div style={{
          padding: '14px 16px', borderRadius: 8,
          background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)',
        }}>
          <h3 style={{ margin: '0 0 6px', display: 'flex', alignItems: 'center', gap: 8,
                       fontSize: 13.5, fontWeight: 600, color: 'var(--md-on-surface)' }}>
            What we don't do
            <span className="mono" style={{
              fontSize: 10, padding: '1px 7px', borderRadius: 999,
              background: 'rgba(217,106,106,0.15)', color: 'var(--err)',
              border: '1px solid rgba(217,106,106,0.32)',
            }}>×</span>
          </h3>
          <p style={{ fontSize: 12, color: 'var(--md-on-surface-muted)', margin: '0 0 6px', lineHeight: 1.55 }}>
            A long-running ChatGPT-style thread per agent where each round appends a message.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.55 }}>
            <li>No <code style={codeS}>thread_id</code> or <code style={codeS}>conversation_id</code>.</li>
            <li>No OpenAI Assistants API. No Anthropic stateful messages.</li>
            <li>The provider holds no state for us between calls.</li>
          </ul>
        </div>
        <div style={{
          padding: '14px 16px', borderRadius: 8,
          background: 'var(--md-surface-container-low)', border: '1px solid var(--agent-b-border)',
          boxShadow: 'inset 0 0 0 1px var(--agent-b-border)',
        }}>
          <h3 style={{ margin: '0 0 6px', display: 'flex', alignItems: 'center', gap: 8,
                       fontSize: 13.5, fontWeight: 600, color: 'var(--md-on-surface)' }}>
            What we actually do
            <span className="mono" style={{
              display: 'inline-flex', alignItems: 'center',
              padding: '1px 7px', borderRadius: 999,
              background: 'var(--agent-b-bg-strong)', color: 'var(--agent-b)',
              border: '1px solid var(--agent-b-border)',
            }}><Mdi name="check" size={10} /></span>
          </h3>
          <p style={{ fontSize: 12, color: 'var(--md-on-surface-muted)', margin: '0 0 6px', lineHeight: 1.55 }}>
            Stateless re-inlining. Each turn rebuilds the entire prompt from disk + run state.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.55 }}>
            <li>Every call sends a single <code style={codeS}>user</code> message with the whole context.</li>
            <li>The orchestrator owns truth on the filesystem (and in Supabase).</li>
            <li>Anthropic prompt caching makes the repeated prefix cheap — see below.</li>
          </ul>
        </div>
      </div>
    );
  }

  // ─── Context-growth stacked bars ──────────────────────────────────────

  const codeS = {
    fontFamily: 'IBM Plex Sans, ui-monospace, monospace', fontSize: '0.88em',
    padding: '1px 5px', background: 'var(--md-surface-container-high)',
    border: '1px solid var(--md-outline-hair)', borderRadius: 4, color: 'var(--md-on-surface)',
  };

  function ContextGrowthBars() {
    const rows = [
      { label: 'P0 / P1',     segs: [{ kind: 'brief', w: 16 }],                                                                              total: '~1× brief' },
      { label: 'P2 r1',       segs: [{ kind: 'brief', w: 16 }, { kind: 'd1', w: 12 }, { kind: 'd2', w: 12 }],                                  total: '+ 2 drafts' },
      { label: 'P2 r3',       segs: [{ kind: 'brief', w: 16 }, { kind: 'd1', w: 12 }, { kind: 'd2', w: 12 }, { kind: 'hist', w: 20 }],         total: '+ 4 P2 turns' },
      { label: 'P2 r6',       segs: [{ kind: 'brief', w: 16 }, { kind: 'd1', w: 12 }, { kind: 'd2', w: 12 }, { kind: 'hist', w: 46 }],         total: '+ 10 P2 turns' },
      { label: 'P3 drafter',  segs: [{ kind: 'brief', w: 16 }, { kind: 'd1', w: 12 }, { kind: 'd2', w: 12 }, { kind: 'hist', w: 46 }],         total: 'full P2 history' },
    ];
    const colors = {
      brief: 'rgba(107,156,240,0.55)',
      d1:    'rgba(212,165,116,0.6)',
      d2:    'rgba(124,196,184,0.6)',
      hist:  'rgba(212,160,86,0.55)',
    };
    return (
      <div style={{
        padding: '16px 18px', background: 'var(--md-surface-container-low)',
        border: '1px solid var(--md-outline-hair)', borderRadius: 8,
      }}>
        {rows.map(r => (
          <div key={r.label} style={{
            display: 'grid', gridTemplateColumns: '90px 1fr 100px', gap: 10,
            alignItems: 'center', marginBottom: 6,
          }}>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-muted)' }}>{r.label}</div>
            <div style={{
              display: 'flex', height: 16, borderRadius: 3, overflow: 'hidden', background: 'var(--md-surface-container-high)',
            }}>
              {r.segs.map((s, i) => (
                <span key={i} style={{ display: 'block', height: '100%', width: `${s.w}%`, background: colors[s.kind] }} />
              ))}
            </div>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--md-on-surface-faint)', textAlign: 'right' }}>{r.total}</div>
          </div>
        ))}
        <div style={{
          display: 'grid', gridTemplateColumns: '90px 1fr 100px', gap: 10, marginTop: 10,
        }}>
          <div />
          <div style={{ position: 'relative', height: 8, borderTop: '1px solid var(--md-outline-variant)' }}>
            <span className="mono" style={tickS(0)}>0</span>
            <span className="mono" style={tickS(16)}>brief</span>
            <span className="mono" style={tickS(40)}>+drafts</span>
            <span className="mono" style={tickS(86)}>+history</span>
            <span className="mono" style={tickS(100)}>CACHE_BREAKPOINT ▏</span>
          </div>
          <div />
        </div>
        <div style={{
          marginTop: 14, padding: '10px 12px', background: 'var(--md-surface-container-high)',
          borderLeft: '2px solid var(--agent-b)', borderRadius: '0 6px 6px 0',
          fontSize: 11.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.55,
        }}>
          Anthropic cache hits return at ~25% of base cost; the volatile tail after the
          marker (round instructions, output schema) is the only piece billed at full rate every round.
        </div>
      </div>
    );
  }
  const tickS = leftPct => ({
    position: 'absolute', top: 0, left: `${leftPct}%`, transform: 'translateX(-50%)',
    paddingTop: 4, fontSize: 9.5, color: 'var(--md-on-surface-faint)',
  });

  // ─── Phase deep-dive accordions ───────────────────────────────────────

  function PhaseMeta({ rows }) {
    return (
      <dl style={{
        display: 'grid', gridTemplateColumns: '110px 1fr', gap: '4px 14px',
        fontSize: 11.5, padding: '10px 12px', background: 'var(--md-surface-container-high)',
        border: '1px solid var(--md-outline-hair)', borderRadius: 6, margin: '8px 0',
      }}>
        {rows.map(([k, v]) => (
          <React.Fragment key={k}>
            <dt className="mono" style={{
              color: 'var(--md-on-surface-faint)', fontSize: 10.5, letterSpacing: '0.06em',
              textTransform: 'uppercase', paddingTop: 2,
            }}>{k}</dt>
            <dd style={{ margin: 0, color: 'var(--md-on-surface-variant)' }}>{v}</dd>
          </React.Fragment>
        ))}
      </dl>
    );
  }

  function PhaseAccordion({ ph, name, tag, defaultOpen, children }) {
    const tagBg = tag === 'parallel'    ? { bg: 'var(--agent-b-bg-strong)', color: 'var(--agent-b)', border: 'var(--agent-b-border)' }
                : tag === 'turn-based'  ? { bg: 'var(--agent-a-bg-strong)', color: 'var(--agent-a)', border: 'var(--agent-a-border)' }
                : { bg: 'var(--md-surface-container-highest)', color: 'var(--md-on-surface-variant)', border: 'var(--md-outline-variant)' };
    return (
      <details open={defaultOpen} style={{
        background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)',
        borderRadius: 8, marginBottom: 10, overflow: 'hidden',
      }}>
        <summary style={{
          listStyle: 'none', cursor: 'pointer', padding: '14px 18px',
          display: 'flex', alignItems: 'center', gap: 14, userSelect: 'none',
        }}>
          <span className="mono" style={{
            fontSize: 10.5, color: 'var(--md-on-surface-faint)', letterSpacing: '0.08em', minWidth: 50,
          }}>PHASE {ph}</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--md-on-surface)' }}>{name}</span>
          <span className="mono" style={{
            fontSize: 10, padding: '2px 8px', borderRadius: 999,
            background: tagBg.bg, color: tagBg.color, border: `1px solid ${tagBg.border}`,
            marginLeft: 'auto',
          }}>{tag}</span>
          <span className="mono" style={{
            color: 'var(--md-on-surface-faint)', fontSize: 12,
          }}>▶</span>
        </summary>
        <div style={{
          padding: '4px 18px 18px', borderTop: '1px solid var(--md-outline-hair)',
          fontSize: 13, color: 'var(--md-on-surface-variant)', lineHeight: 1.65,
        }}>
          {children}
        </div>
      </details>
    );
  }

  // ─── FAQ accordion ────────────────────────────────────────────────────

  function Faq({ q, children }) {
    return (
      <details style={{
        background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)',
        borderRadius: 6, marginBottom: 6,
      }}>
        <summary style={{
          listStyle: 'none', cursor: 'pointer', padding: '10px 14px',
          fontSize: 13, color: 'var(--md-on-surface)', fontWeight: 500,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
        }}>
          <span>{q}</span>
          <span className="mono" style={{ color: 'var(--md-on-surface-faint)', fontSize: 11 }}>▶</span>
        </summary>
        <div style={{
          padding: '0 14px 12px', fontSize: 12.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.6,
        }}>{children}</div>
      </details>
    );
  }

  // ─── Section primitive ────────────────────────────────────────────────

  function Section({ kicker, title, lede, mutedLede, children }) {
    return (
      <section style={{ marginBottom: 44 }}>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--md-on-surface-faint)', letterSpacing: '0.08em',
          textTransform: 'uppercase', marginBottom: 6,
        }}>{kicker}</div>
        <h2 style={{
          fontSize: 17, fontWeight: 600, color: 'var(--md-on-surface)',
          margin: '0 0 14px', letterSpacing: '-0.005em',
        }}>{title}</h2>
        {lede && (
          <p style={{ fontSize: 13.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.65, margin: '0 0 12px' }}>{lede}</p>
        )}
        {mutedLede && (
          <p style={{ fontSize: 13.5, color: 'var(--md-on-surface-muted)', lineHeight: 1.65, margin: '0 0 12px' }}>{mutedLede}</p>
        )}
        {children}
      </section>
    );
  }

  // ─── Deep Research pipeline reference (spec 0117) ─────────────────────
  // Hand-authored SVG bundled under /diagrams/. The variant served
  // follows the app's theme toggle (light/dark). The legacy v3.5
  // inline-JSX overview lived here previously and is replaced by the
  // SVG embed below as part of spec 0117 step 3.

  function useThemeMode() {
    const [isDark, setIsDark] = React.useState(() => (
      typeof document !== 'undefined' && !document.body.classList.contains('light')
    ));
    React.useEffect(() => {
      if (typeof document === 'undefined' || typeof MutationObserver === 'undefined') return;
      const observer = new MutationObserver(() => {
        setIsDark(!document.body.classList.contains('light'));
      });
      observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
      return () => observer.disconnect();
    }, []);
    return isDark ? 'dark' : 'light';
  }

  function ProtocolOverviewMap() {
    const themeMode = useThemeMode();
    const src = themeMode === 'dark'
      ? '/diagrams/deep-research-pipeline.dark.svg?v=0117'
      : '/diagrams/deep-research-pipeline.light.svg?v=0117';
    return (
      <figure className="hiw-overview-figure" style={{ margin: 0 }}>
        <img
          src={src}
          alt="Deep Research pipeline · phase columns left to right; per-phase inputs stacked top to bottom in the order the orchestrator feeds them."
          className="hiw-overview-svg"
          loading="lazy"
          style={{ display: 'block', width: '100%', height: 'auto' }}
        />
      </figure>
    );
  }

  function ProtocolOverviewFold() {
    const themeMode = useThemeMode();
    const svgHref = themeMode === 'dark'
      ? '/diagrams/deep-research-pipeline.dark.svg?v=0117'
      : '/diagrams/deep-research-pipeline.light.svg?v=0117';
    return (
      <details style={{
        background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)',
        borderRadius: 8, overflow: 'hidden', marginTop: 14,
      }}>
        <summary style={{
          listStyle: 'none', cursor: 'pointer', padding: '14px 18px',
          display: 'flex', alignItems: 'center', gap: 12, userSelect: 'none',
        }}>
          <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--md-on-surface)' }}>View full process map</span>
          <span style={{ fontSize: 12, color: 'var(--md-on-surface-muted)' }}>
            — every phase, every input, every artifact passed forward
          </span>
          <span className="mono" style={{
            fontSize: 10, padding: '2px 8px', borderRadius: 999,
            background: 'var(--md-surface-container-highest)', color: 'var(--md-on-surface-muted)',
            border: '1px solid var(--md-outline-variant)', marginLeft: 'auto',
            letterSpacing: '0.04em',
          }}>deep research · landscape</span>
          <span className="mono" style={{ color: 'var(--md-on-surface-faint)', fontSize: 12 }}>▶</span>
        </summary>
        <div style={{
          padding: 0, borderTop: '1px solid var(--md-outline-hair)',
          background: 'var(--md-surface-container-lowest)',
        }}>
          <ProtocolOverviewMap />
        </div>
        <div style={{
          padding: '10px 18px', borderTop: '1px solid var(--md-outline-hair)',
          fontSize: 11.5, color: 'var(--md-on-surface-muted)',
          display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap',
        }}>
          <span>Reference diagram — light + dark variants, follows the theme toggle.</span>
          <a href={svgHref} target="_blank" rel="noopener"
             style={{ color: 'var(--info)' }}>Open SVG ↗</a>
          <span className="mono" style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--md-on-surface-faint)' }}>
            1660 × 1200 · IBM Plex · cream &amp; indigo design system
          </span>
        </div>
      </details>
    );
  }

  // ─── Release notes block ──────────────────────────────────────────────

  function ReleaseNote({ entry }) {
    return (
      <div style={{
        padding: '14px 16px', marginBottom: 10,
        background: 'var(--md-surface-container-low)', border: '1px solid var(--md-outline-hair)',
        borderRadius: 8,
      }}>
        <div style={{
          display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 6,
          flexWrap: 'wrap',
        }}>
          <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--md-on-surface)' }}>{entry.version}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--md-on-surface-faint)' }}>{entry.date}</span>
          <span style={{ fontSize: 12.5, color: 'var(--md-on-surface-muted)' }}>{entry.summary}</span>
        </div>
        <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12.5, color: 'var(--md-on-surface-variant)', lineHeight: 1.6 }}>
          {entry.items.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      </div>
    );
  }

  // ─── Canonical sub-section data for the right menu ──────────────────
  const HIW_SECTIONS = [
    { id: 'hiw-hero', label: 'Protocol overview' },
    { id: 'hiw-p0',   label: 'Preflight' },
    { id: 'hiw-p1',   label: 'Independent research' },
    { id: 'hiw-p2',   label: 'Plan negotiation' },
    { id: 'hiw-p3',   label: 'Drafting' },
    { id: 'hiw-p4',   label: 'Review loop' },
    { id: 'hiw-dis',  label: 'Disagreement & convergence' },
    { id: 'hiw-cost', label: 'Cost & consumption' },
    { id: 'hiw-vn',   label: 'Version notes' },
  ];

  // ─── Collapsible HIW sub-section wrapper ──────────────────────────
  function HiwSection({ id, label, title, lede, defaultOpen, children }) {
    const [collapsed, setCollapsed] = React.useState(!defaultOpen);
    return (
      <section className="hiw-sec" id={id} data-collapsed={String(collapsed)}>
        <div className="label">{label}</div>
        <h3>{title}</h3>
        <div className="lede">{lede}</div>
        <div className="hiw-sec__body">
          {children}
        </div>
        <button
          type="button"
          className="hiw-sec__toggle"
          onClick={() => setCollapsed(c => !c)}
          aria-expanded={!collapsed}
        >
          <span className="ms ms-20">{collapsed ? 'expand_more' : 'expand_less'}</span>
          {collapsed ? 'Read more' : 'Collapse'}
        </button>
      </section>
    );
  }

  // ─── Changelog entry with collapse ────────────────────────────────
  function ChangelogEntry({ entry, defaultOpen }) {
    const [collapsed, setCollapsed] = React.useState(!defaultOpen);
    return (
      <div className="changelog__entry" data-collapsed={String(collapsed)}>
        <div className="changelog__date">
          <div>v{entry.version}</div>
          <div style={{ marginTop: 4 }}>{entry.date}</div>
        </div>
        <div>
          <div className="changelog__body">
            <h4>{entry.summary}</h4>
            <ul>
              {entry.items.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </div>
          <button
            type="button"
            className="changelog__toggle"
            onClick={() => setCollapsed(c => !c)}
            aria-expanded={!collapsed}
          >
            <span className="ms ms-20">{collapsed ? 'expand_more' : 'expand_less'}</span>
            {collapsed ? 'Read more' : 'Collapse'}
          </button>
        </div>
      </div>
    );
  }

  // ─── Main overlay component ───────────────────────────────────────
  function HowItWorks({ open, onClose }) {
    const [view, setView] = React.useState('how');  // 'how' | 'changelog'
    const triggerRef = React.useRef(null);
    const contentRef = React.useRef(null);

    // Close on Escape
    React.useEffect(() => {
      if (!open) return;
      function onKey(e) {
        if (e.key === 'Escape') { e.stopPropagation(); onClose(); }
      }
      window.addEventListener('keydown', onKey, true);
      return () => window.removeEventListener('keydown', onKey, true);
    }, [open, onClose]);

    // Return focus to trigger on close
    React.useEffect(() => {
      if (!open && triggerRef.current) {
        triggerRef.current.focus();
        triggerRef.current = null;
      }
    }, [open]);

    // Capture the trigger element when opening
    React.useEffect(() => {
      if (open) {
        triggerRef.current = document.activeElement;
      }
    }, [open]);

    if (!open) return null;

    function onScrimClick(e) {
      if (e.target === e.currentTarget) onClose();
    }

    return (
      <div className="md-dialog__scrim" onClick={onScrimClick} role="dialog" aria-modal="true" aria-label="How it works">
        <div className="md-dialog md-dialog--rich" style={{ maxHeight: '92vh', overflow: 'hidden' }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--md-sp-4)', flexShrink: 0 }}>
            <div className="md-dialog__title" style={{ margin: 0 }}>
              {view === 'how' ? 'How it works' : 'Changelog'}
            </div>
            <button
              type="button"
              className="md-btn md-btn--text md-btn--sm"
              onClick={onClose}
              aria-label="Close"
            >
              <span className="ms ms-20">close</span>
            </button>
          </div>

          {/* Two-column layout */}
          <div className="hiw-overlay__layout">
            {/* Left: scrollable content */}
            <div className="hiw-overlay__content" ref={contentRef}>
              {view === 'how' ? (
                <div className="hiw">
                  {/* 1. Protocol overview (hero — open by default) */}
                  <HiwSection id="hiw-hero" label="Protocol" title="Protocol overview" defaultOpen
                    lede="Two language models start from the same brief, work independently, then negotiate until they agree on a single document. The orchestrator is deterministic; the agents are not.">
                    <TldrCards />
                    <div style={{ marginTop: 24 }}>
                      <PhaseStrip />
                    </div>
                    <div style={{ marginTop: 24 }}>
                      <ProtocolOverviewFold />
                    </div>
                  </HiwSection>

                  {/* 2. Preflight */}
                  <HiwSection id="hiw-p0" label="Phase 0" title="Preflight"
                    lede="Both agents read the brief and write a short critique. The two API calls fire in parallel; neither sees the other's critique.">
                    <PhaseAccordion ph={0} name="Preflight" tag="parallel" defaultOpen>
                      <p>
                        Both agents read the brief and write a short critique — what's
                        underspecified, what's ambiguous, what's missing. The two API
                        calls fire <code style={codeS}>asyncio.gather</code>-style at the same moment;
                        neither sees the other's critique. In autonomous mode their
                        feedback is logged but doesn't gate the run.
                      </p>
                      <PhaseMeta rows={[
                        ['input',  <Tk kind="brief">brief</Tk>],
                        ['chats',  '2 fresh API calls (one per agent), no history'],
                        ['output', <span><code style={codeS}>preflight-claude.md</code>, <code style={codeS}>preflight-openai.md</code></span>],
                        ['gate',   'none — informational'],
                      ]} />
                    </PhaseAccordion>
                  </HiwSection>

                  {/* 3. Independent research */}
                  <HiwSection id="hiw-p1" label="Phase 1" title="Independent research"
                    lede="Each agent writes a complete first-pass research draft alone. This is the only phase where you see how each model interprets the brief under zero negotiation pressure.">
                    <PhaseAccordion ph={1} name="Independent research" tag="parallel" defaultOpen>
                      <p>
                        Each agent writes a complete first-pass research draft, alone.
                        Same brief, same prompt structure — but the two drafts are written
                        without any cross-talk.
                      </p>
                      <PhaseMeta rows={[
                        ['input',  <Tk kind="brief">brief</Tk>],
                        ['chats',  '2 fresh API calls (one per agent), no history'],
                        ['output', <span><code style={codeS}>phase1/draft-claude.md</code>, <code style={codeS}>phase1/draft-openai.md</code></span>],
                        ['gate',   'both drafts present => advance'],
                      ]} />
                    </PhaseAccordion>
                  </HiwSection>

                  {/* 4. Plan negotiation */}
                  <HiwSection id="hiw-p2" label="Phase 2" title="Plan negotiation"
                    lede="The agents start reading each other's work. Each round, both agents fire in parallel. They exchange counter-proposals and try to converge on an agreed plan.">
                    <PhaseAccordion ph={2} name="Plan negotiation" tag="turn-based" defaultOpen>
                      <p>
                        Round 1 is structurally required to be a "first read" — neither
                        agent can mark AGREED yet. From round 2 on, they exchange
                        counter-proposals, mark disagreements with stable
                        {' '}<code style={codeS}>D-N</code> identifiers, and try to converge on an
                        {' '}<code style={codeS}>AGREED_PLAN</code> block whose SHA-256 hash matches the other agent's.
                      </p>
                      <PhaseMeta rows={[
                        ['r1 input', <span><Tk kind="brief">brief</Tk> <Tk kind="d1">P1 draft-claude</Tk> <Tk kind="d2">P1 draft-openai</Tk></span>],
                        ['rN input', <span><Tk kind="brief">brief</Tk> <Tk kind="d1">P1 draft-claude</Tk> <Tk kind="d2">P1 draft-openai</Tk> <Tk kind="hist">all prior P2 turns</Tk></span>],
                        ['chats',    '2 fresh API calls per round; full history re-inlined every time'],
                        ['output',   <span><code style={codeS}>phase2/round-NN-claude.md</code>, <code style={codeS}>phase2/round-NN-openai.md</code></span>],
                        ['caps',     'soft 6 rounds (warn), hard 12 rounds (exit 51)'],
                        ['gate',     'same-round plan-hash match + zero blocking disagreements'],
                      ]} />
                    </PhaseAccordion>
                  </HiwSection>

                  {/* 5. Drafting */}
                  <HiwSection id="hiw-p3" label="Phase 3" title="Drafting"
                    lede="One agent — the drafter — writes the converged document in a single call. The other agent is silent in this phase.">
                    <PhaseAccordion ph={3} name="Drafting" tag="single-shot" defaultOpen>
                      <p>
                        One agent — the drafter, picked by <code style={codeS}>tiebreak.pick_drafter</code> —
                        writes the converged document in a single call.
                      </p>
                      <PhaseMeta rows={[
                        ['input',  <span><Tk kind="brief">brief</Tk> <Tk kind="d1">P1 draft-claude</Tk> <Tk kind="d2">P1 draft-openai</Tk> <Tk kind="plan">agreed plan</Tk> <Tk kind="hist">all P2 turns</Tk></span>],
                        ['chats',  '1 fresh API call (drafter only)'],
                        ['output', <code style={codeS}>phase3/draft-v1.md</code>],
                        ['gate',   'draft written => advance'],
                      ]} />
                    </PhaseAccordion>
                  </HiwSection>

                  {/* 6. Review loop */}
                  <HiwSection id="hiw-p4" label="Phase 4" title="Review loop"
                    lede="Same shape as Phase 2: both agents fire in parallel each round. The drafter can include a revised draft, the reviewer comments. Convergence means both agents approve with zero open issues.">
                    <PhaseAccordion ph={4} name="Cross-review" tag="turn-based" defaultOpen>
                      <p>
                        Same shape as Phase&nbsp;2: both agents fire in parallel each
                        round. The drafter can include a <code style={codeS}>## Revised draft</code>{' '}
                        section in their turn. Convergence means both agents emit{' '}
                        <code style={codeS}>STATUS: APPROVED</code> with zero open issues.
                      </p>
                      <PhaseMeta rows={[
                        ['input',  <span><Tk kind="brief">brief</Tk> <Tk kind="draft">current draft-vK</Tk> <Tk kind="histp">all prior P4 turns</Tk></span>],
                        ['chats',  '2 fresh API calls per round; full history re-inlined every time'],
                        ['output', <span><code style={codeS}>phase4/round-NN-&#123;agent&#125;.md</code>, plus <code style={codeS}>draft-vK+1.md</code> if revised</span>],
                        ['gate',   <span>both agents <code style={codeS}>STATUS: APPROVED</code>, zero open issues, same round</span>],
                      ]} />
                    </PhaseAccordion>
                  </HiwSection>

                  {/* 7. Disagreement & convergence */}
                  <HiwSection id="hiw-dis" label="Convergence" title="Disagreement & convergence"
                    lede="A round, up close: how the orchestrator checks convergence, what happens when agents don't agree, and the FAQ.">
                    <div style={{
                      padding: '16px 18px', background: 'var(--md-surface-container-low)',
                      border: '1px solid var(--md-outline-hair)', borderRadius: 'var(--md-shape-md)',
                      marginBottom: 24,
                    }}>
                      <NegotiationRoundDiagram />
                      <div style={{
                        fontSize: 11.5, color: 'var(--md-on-surface-variant)', fontStyle: 'italic', marginTop: 6,
                      }}>
                        If yes, advance phase. If no, append both turns to disk and run the next round.
                      </div>
                    </div>
                    <Faq q="Do they read each other's work?">
                      Not in Phases 0 and 1. From Phase&nbsp;2 onward yes — each agent's prompt inlines the brief, both Phase&nbsp;1 drafts, and every prior round's turn from both sides.
                    </Faq>
                    <Faq q="Who goes first in a round?">
                      Neither. <strong>Both agents fire at the same moment</strong> via <code style={codeS}>asyncio.gather</code>. Each agent independently produces a turn that references all prior history.
                    </Faq>
                    <Faq q="What if they never converge?">
                      Two caps. <strong>Soft cap</strong> (default 6 rounds) logs a warning. <strong>Hard cap</strong> (default 12 rounds) stops the run with exit code 51.
                    </Faq>
                    <Faq q="What if an agent emits something the parser can't read?">
                      Each agent has one repair attempt per phase. Two consecutive parse failures kill the run (exit 52).
                    </Faq>
                  </HiwSection>

                  {/* 8. Cost & consumption */}
                  <HiwSection id="hiw-cost" label="Cost" title="Cost & consumption"
                    lede="Because we re-inline everything, the prompt gets longer each round. The orchestrator places a CACHE_BREAKPOINT between the stable prefix and the volatile suffix.">
                    <ContextGrowthBars />
                    <div style={{ marginTop: 24 }}>
                      <ChatLifecycle />
                    </div>
                    <div style={{ marginTop: 16 }}>
                      <Legend />
                    </div>
                    <Faq q="Which models are used?">
                      By default: Claude Sonnet 4.6 (1M-context beta) + GPT-5.5. Faster <code style={codeS}>test</code> tier: Haiku 4.5 + GPT-5-mini.
                    </Faq>
                    <Faq q="Where does the cost come from?">
                      Every call records token usage and per-call USD cost. Anthropic prompt caching gives ~75% off cached prefix reads.
                    </Faq>
                  </HiwSection>

                  {/* 9. Version notes */}
                  <HiwSection id="hiw-vn" label="Changelog" title="Version notes"
                    lede="Each entry corresponds to a merged spec. Newest first.">
                    {VERSION_NOTES.slice(0, 5).map(entry => <ReleaseNote key={entry.version} entry={entry} />)}
                  </HiwSection>
                </div>
              ) : (
                /* Changelog view */
                <div className="changelog">
                  {VERSION_NOTES.map((entry, i) => (
                    <ChangelogEntry key={entry.version} entry={entry} defaultOpen={i === 0} />
                  ))}
                </div>
              )}
            </div>

            {/* Right: sticky menu */}
            <div className="hiw-overlay__menu">
              <div className="tab-group-solid hiw-overlay__menu-toggle">
                <button type="button" className={'tab-solid' + (view === 'how' ? ' is-active' : '')}
                        onClick={() => setView('how')}>How It Works</button>
                <button type="button" className={'tab-solid' + (view === 'changelog' ? ' is-active' : '')}
                        onClick={() => setView('changelog')}>Changelog</button>
              </div>
              {view === 'how' && (
                <ol className="hiw-overlay__menu-list">
                  {HIW_SECTIONS.map(sec => (
                    <li key={sec.id}>
                      <a href={'#' + sec.id} onClick={(e) => {
                        e.preventDefault();
                        const el = contentRef.current?.querySelector('#' + sec.id);
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      }}>{sec.label}</a>
                    </li>
                  ))}
                </ol>
              )}
              {view === 'changelog' && (
                <ol className="hiw-overlay__menu-list">
                  {VERSION_NOTES.map(entry => (
                    <li key={entry.version}>
                      <a href="#" onClick={(e) => { e.preventDefault(); }}
                        style={{ fontFamily: 'var(--md-font-data)', fontSize: 11 }}>
                        v{entry.version} — {entry.date}
                      </a>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Keep legacy page-based HowItWorks as a redirect wrapper
  function HowItWorksPage() {
    return (
      <div style={{
        height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--md-surface)', color: 'var(--md-on-surface)',
      }}>
        <p style={{ color: 'var(--md-on-surface-muted)' }}>
          Use the "How it works" button in the top bar to open the overlay.
        </p>
      </div>
    );
  }

  window.HowItWorks = HowItWorks;
  window.HowItWorksPage = HowItWorksPage;
})();
