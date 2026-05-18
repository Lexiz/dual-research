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

  function Arrow({ x1, y1, x2, y2, dashed, color = 'var(--border-3)' }) {
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
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--border-3)" />
        </marker>
      </defs>
    );
  }

  // ─── Phase strip (kept, theme-coloured) ───────────────────────────────

  function PhaseStrip() {
    const cells = [
      { tag: 'parallel',    color: 'var(--agent-b)', label: 'P0 · Preflight',  sub: 'brief critique' },
      { tag: 'parallel',    color: 'var(--agent-b)', label: 'P1 · Research',   sub: 'independent drafts' },
      { tag: 'turn-based',  color: 'var(--agent-a)', label: 'P2 · Negotiate',  sub: 'plan convergence' },
      { tag: 'single-shot', color: 'var(--fg-2)',    label: 'P3 · Draft',      sub: 'drafter writes doc' },
      { tag: 'turn-based',  color: 'var(--agent-a)', label: 'P4 · Review',     sub: 'cross-review + revise' },
      { tag: 'output',      color: 'var(--ok)',      label: 'final.md',         sub: 'single document' },
    ];
    return (
      <div style={{
        display: 'flex', gap: 6, padding: '14px 16px',
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        borderRadius: 8,
      }}>
        {cells.map((c, i) => (
          <div key={c.label} style={{
            flex: 1, minWidth: 0, position: 'relative',
            padding: '8px 10px', background: 'var(--bg-2)',
            border: '1px solid var(--border-2)', borderRadius: 6,
          }}>
            <div className="mono" style={{
              fontSize: 9.5, color: c.color, letterSpacing: '0.06em',
              textTransform: 'uppercase',
            }}>{c.tag}</div>
            <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--fg-0)', marginTop: 4 }}>
              {c.label}
            </div>
            <div className="mono" style={{ fontSize: 9.5, color: 'var(--fg-3)', marginTop: 2 }}>{c.sub}</div>
            {i < cells.length - 1 && (
              <span style={{
                position: 'absolute', right: -8, top: '50%', transform: 'translateY(-50%)',
                color: 'var(--border-3)', fontFamily: 'IBM Plex Sans, ui-monospace, monospace',
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
    return (
      <svg viewBox="0 0 720 320" style={{ display: 'block', width: '100%', maxWidth: 720, margin: '0 auto' }}>
        <ArrowDefs />
        <rect x={30} y={20} width={200} height={80} rx={8}
              fill="var(--bg-2)" stroke="var(--border-2)" />
        <text x={130} y={44} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={11}
              fill="var(--fg-1)">disk: prior turns inlined</text>
        <text x={130} y={62} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={9.5}
              fill="var(--fg-3)">round 1..N-1, both agents</text>
        <text x={130} y={76} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={9.5}
              fill="var(--fg-3)">+ brief + phase-1 drafts</text>
        <text x={130} y={92} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={9.5}
              fill="var(--fg-3)">+ CACHE_BREAKPOINT</text>

        <text x={370} y={50} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={11}
              fill="var(--fg-1)">orchestrator assembles</text>
        <text x={370} y={66} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={10}
              fill="var(--fg-3)">a fresh prompt</text>

        <Arrow x1={230} y1={60} x2={510} y2={60} />

        <rect x={510} y={20} width={180} height={80} rx={8}
              fill="var(--bg-2)" stroke="var(--border-2)" />
        <text x={600} y={44} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={11}
              fill="var(--fg-1)">round N prompt</text>
        <text x={600} y={62} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={9.5}
              fill="var(--fg-3)">identical to both, except</text>
        <text x={600} y={78} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={9.5}
              fill="var(--fg-3)">agent_name substitution</text>

        <Arrow x1={560} y1={108} x2={180} y2={170} />
        <Arrow x1={640} y1={108} x2={550} y2={170} />

        <ClaudeDisc cx={150} cy={195} r={30} />
        <GptDisc    cx={580} cy={195} r={30} />

        <text x={365} y={200} textAnchor="middle"
              fontSize={11} fill="var(--fg-3)" fontFamily="IBM Plex Sans, ui-monospace, monospace">
          asyncio.gather
        </text>

        <Arrow x1={150} y1={225} x2={150} y2={258} />
        <Arrow x1={580} y1={225} x2={580} y2={258} />

        <rect x={50} y={258} width={200} height={28} rx={6}
              fill="var(--agent-a-bg)" stroke="var(--agent-a-border)" />
        <text x={150} y={276} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={10.5}
              fill="var(--agent-a)">phase2/round-NN-claude.md</text>

        <rect x={480} y={258} width={200} height={28} rx={6}
              fill="var(--agent-b-bg)" stroke="var(--agent-b-border)" />
        <text x={580} y={276} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={10.5}
              fill="var(--agent-b)">phase2/round-NN-openai.md</text>

        <rect x={260} y={294} width={200} height={22} rx={6}
              fill="var(--bg-1)" stroke="var(--border-2)" />
        <text x={360} y={309} textAnchor="middle"
              fontFamily="IBM Plex Sans, ui-monospace, monospace" fontSize={10}
              fill="var(--fg-1)">both AGREED + plan-hash match?</text>
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
            padding: '14px 14px 12px', background: 'var(--bg-1)',
            border: '1px solid var(--border-1)', borderRadius: 8,
          }}>
            <div className="mono" style={{
              fontSize: 11, color: 'var(--fg-3)', letterSpacing: '0.08em',
            }}>{c.kicker}</div>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--fg-0)', margin: '6px 0 2px' }}>
              {c.head}
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--fg-2)', lineHeight: 1.45 }}>{c.body}</div>
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

  function CallBox({ agent, fresh = true, lines, out, silent, noteIf }) {
    if (silent) {
      return (
        <div style={{
          padding: '10px 12px', borderRadius: 6, border: '1px dashed var(--border-2)',
          color: 'var(--fg-3)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontStyle: 'italic', fontSize: 11.5, minHeight: 86,
        }}>silent — other agent does not fire</div>
      );
    }
    const isClaude = agent === 'claude';
    const bg = isClaude ? 'var(--agent-a-bg)' : 'var(--agent-b-bg)';
    const border = isClaude ? 'var(--agent-a-border)' : 'var(--agent-b-border)';
    const letter = isClaude ? 'C' : 'G';
    const letterColor = isClaude ? 'var(--agent-a)' : 'var(--agent-b)';
    return (
      <div style={{
        padding: '10px 12px', borderRadius: 6,
        background: bg, border: `1px solid ${border}`,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-0)' }}>
            <span className="mono" style={{ color: letterColor, marginRight: 4 }}>{letter}</span>
            new chat
            {noteIf && (
              <em style={{ fontStyle: 'normal', color: 'var(--fg-3)', fontSize: 10.5, marginLeft: 4 }}>
                ({noteIf})
              </em>
            )}
          </span>
          {fresh && (
            <span className="mono" style={{
              fontSize: 9.5, padding: '1px 6px', background: 'var(--bg-3)',
              border: '1px solid var(--border-2)', borderRadius: 999,
              color: 'var(--fg-2)',
            }}>fresh prompt</span>
          )}
        </div>
        <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: 'var(--fg-1)', lineHeight: 1.55 }}>
          {lines.map((line, i) => <li key={i} style={{ listStyle: 'disc' }}>{line}</li>)}
        </ul>
        {out && (
          <div className="mono" style={{ marginTop: 8, fontSize: 10, color: 'var(--fg-2)' }}>
            <span style={{ color: 'var(--fg-3)' }}>→ </span>{out}
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
          padding: '12px 10px', background: 'var(--bg-2)',
          border: '1px solid var(--border-2)', borderRadius: 6,
        }}>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--fg-0)' }}>{phase}</div>
          <div className="mono" style={{
            fontSize: 9.5, color: 'var(--fg-3)', letterSpacing: '0.06em',
            textTransform: 'uppercase', marginTop: 3,
          }}>{tag}</div>
        </div>
        {claude}
        {openai}
        {gather && (
          <div className="mono" style={{
            gridColumn: '2 / 4', textAlign: 'center', fontSize: 10,
            color: 'var(--fg-3)', padding: '2px 0', letterSpacing: '0.04em',
          }}>{gather}</div>
        )}
      </React.Fragment>
    );
  }

  function ChatLifecycle() {
    const claudeCall = (lines, out, noteIf) => <CallBox agent="claude" lines={lines} out={out} noteIf={noteIf} />;
    const openaiCall = (lines, out, noteIf) => <CallBox agent="openai" lines={lines} out={out} noteIf={noteIf} />;
    const silent     = <CallBox silent />;
    const tkBrief  = <Tk kind="brief">brief</Tk>;
    const tkD1     = <Tk kind="d1">P1 draft-claude</Tk>;
    const tkD2     = <Tk kind="d2">P1 draft-openai</Tk>;
    const tkHist   = <Tk kind="hist">all prior P2 turns</Tk>;
    const tkPlan   = <Tk kind="plan">agreed plan</Tk>;
    const tkDraft  = <Tk kind="draft">current draft-vK.md</Tk>;
    const tkHistP  = <Tk kind="histp">all prior P4 turns</Tk>;

    return (
      <div style={{
        display: 'grid', gridTemplateColumns: '110px 1fr 1fr', gap: 10,
        padding: 14, background: 'var(--bg-1)',
        border: '1px solid var(--border-1)', borderRadius: 8,
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
        }}>OpenAI lane</div>

        <LifecycleRow
          phase="P0 Preflight" tag="1 call / agent"
          claude={claudeCall([tkBrief], 'preflight-claude.md')}
          openai={openaiCall([tkBrief], 'preflight-openai.md')}
          gather="⎯⎯  asyncio.gather  · both fire at once  ⎯⎯"
        />

        <LifecycleRow
          phase="P1 Research" tag="1 call / agent"
          claude={claudeCall([tkBrief], 'phase1/draft-claude.md')}
          openai={openaiCall([tkBrief], 'phase1/draft-openai.md')}
          gather="⎯⎯  asyncio.gather  ⎯⎯"
        />

        <LifecycleRow
          phase="P2 Negotiate" tag="Round 1"
          claude={claudeCall([tkBrief, <span key="d">{tkD1} · {tkD2}</span>], 'phase2/round-01-claude.md')}
          openai={openaiCall([tkBrief, <span key="d">{tkD1} · {tkD2}</span>], 'phase2/round-01-openai.md')}
          gather="⎯⎯  asyncio.gather  ⎯⎯"
        />

        <LifecycleRow
          phase="P2 Negotiate" tag="Round 2..N"
          claude={claudeCall([
            tkBrief,
            <span key="d">{tkD1} · {tkD2}</span>,
            <span key="h">{tkHist} (both agents, every round)</span>,
          ], 'phase2/round-NN-claude.md')}
          openai={openaiCall([
            tkBrief,
            <span key="d">{tkD1} · {tkD2}</span>,
            <span key="h">{tkHist} (both agents, every round)</span>,
          ], 'phase2/round-NN-openai.md')}
          gather="⎯⎯  asyncio.gather · loop until convergence or hard-cap  ⎯⎯"
        />

        <LifecycleRow
          phase="P3 Drafting" tag="drafter only"
          claude={claudeCall([
            tkBrief,
            <span key="d">{tkD1} · {tkD2}</span>,
            <span key="p">{tkPlan} (hash-verified)</span>,
            <span key="h">{tkHist} as context</span>,
          ], 'phase3/draft-v1.md', 'if drafter')}
          openai={silent}
          gather="⎯⎯  single call · drafter chosen by tiebreak.pick_drafter  ⎯⎯"
        />

        <LifecycleRow
          phase="P4 Review" tag="Round 1..N"
          claude={claudeCall([tkBrief, tkDraft, tkHistP], 'phase4/round-NN-claude.md')}
          openai={openaiCall([tkBrief, tkDraft, tkHistP], 'phase4/round-NN-openai.md')}
          gather='⎯⎯  asyncio.gather · drafter may emit a "## Revised draft" → draft-vK+1.md  ⎯⎯'
        />
      </div>
    );
  }

  function Legend() {
    const items = [
      { kind: 'brief', label: 'brief',           hint: 'the ingested brief.md, identical for both agents' },
      { kind: 'd1',    label: 'P1 draft-claude', hint: "Claude's Phase 1 research" },
      { kind: 'd2',    label: 'P1 draft-openai', hint: "OpenAI's Phase 1 research" },
      { kind: 'hist',  label: 'P2 turns',        hint: 'every prior negotiation turn, both sides' },
      { kind: 'plan',  label: 'agreed plan',     hint: 'the SHA-256-matched canonical plan from P2' },
      { kind: 'draft', label: 'current draft',   hint: 'the latest P3/P4 doc version' },
      { kind: 'histp', label: 'P4 turns',        hint: 'every prior review turn' },
    ];
    return (
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '8px 14px',
        marginTop: 14, padding: '12px 14px', background: 'var(--bg-2)',
        border: '1px solid var(--border-1)', borderRadius: 6,
      }}>
        {items.map(i => (
          <div key={i.kind} style={{
            display: 'flex', gap: 6, alignItems: 'center', fontSize: 11.5, color: 'var(--fg-1)',
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
          background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        }}>
          <h3 style={{ margin: '0 0 6px', display: 'flex', alignItems: 'center', gap: 8,
                       fontSize: 13.5, fontWeight: 600, color: 'var(--fg-0)' }}>
            What we don't do
            <span className="mono" style={{
              fontSize: 10, padding: '1px 7px', borderRadius: 999,
              background: 'rgba(217,106,106,0.15)', color: 'var(--err)',
              border: '1px solid rgba(217,106,106,0.32)',
            }}>×</span>
          </h3>
          <p style={{ fontSize: 12, color: 'var(--fg-2)', margin: '0 0 6px', lineHeight: 1.55 }}>
            A long-running ChatGPT-style thread per agent where each round appends a message.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11.5, color: 'var(--fg-1)', lineHeight: 1.55 }}>
            <li>No <code style={codeS}>thread_id</code> or <code style={codeS}>conversation_id</code>.</li>
            <li>No OpenAI Assistants API. No Anthropic stateful messages.</li>
            <li>The provider holds no state for us between calls.</li>
          </ul>
        </div>
        <div style={{
          padding: '14px 16px', borderRadius: 8,
          background: 'var(--bg-1)', border: '1px solid var(--agent-b-border)',
          boxShadow: 'inset 0 0 0 1px var(--agent-b-border)',
        }}>
          <h3 style={{ margin: '0 0 6px', display: 'flex', alignItems: 'center', gap: 8,
                       fontSize: 13.5, fontWeight: 600, color: 'var(--fg-0)' }}>
            What we actually do
            <span className="mono" style={{
              display: 'inline-flex', alignItems: 'center',
              padding: '1px 7px', borderRadius: 999,
              background: 'var(--agent-b-bg-strong)', color: 'var(--agent-b)',
              border: '1px solid var(--agent-b-border)',
            }}><Mdi name="check" size={10} /></span>
          </h3>
          <p style={{ fontSize: 12, color: 'var(--fg-2)', margin: '0 0 6px', lineHeight: 1.55 }}>
            Stateless re-inlining. Each turn rebuilds the entire prompt from disk + run state.
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11.5, color: 'var(--fg-1)', lineHeight: 1.55 }}>
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
    padding: '1px 5px', background: 'var(--bg-2)',
    border: '1px solid var(--border-1)', borderRadius: 4, color: 'var(--fg-0)',
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
        padding: '16px 18px', background: 'var(--bg-1)',
        border: '1px solid var(--border-1)', borderRadius: 8,
      }}>
        {rows.map(r => (
          <div key={r.label} style={{
            display: 'grid', gridTemplateColumns: '90px 1fr 100px', gap: 10,
            alignItems: 'center', marginBottom: 6,
          }}>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--fg-2)' }}>{r.label}</div>
            <div style={{
              display: 'flex', height: 16, borderRadius: 3, overflow: 'hidden', background: 'var(--bg-2)',
            }}>
              {r.segs.map((s, i) => (
                <span key={i} style={{ display: 'block', height: '100%', width: `${s.w}%`, background: colors[s.kind] }} />
              ))}
            </div>
            <div className="mono" style={{ fontSize: 10.5, color: 'var(--fg-3)', textAlign: 'right' }}>{r.total}</div>
          </div>
        ))}
        <div style={{
          display: 'grid', gridTemplateColumns: '90px 1fr 100px', gap: 10, marginTop: 10,
        }}>
          <div />
          <div style={{ position: 'relative', height: 8, borderTop: '1px solid var(--border-2)' }}>
            <span className="mono" style={tickS(0)}>0</span>
            <span className="mono" style={tickS(16)}>brief</span>
            <span className="mono" style={tickS(40)}>+drafts</span>
            <span className="mono" style={tickS(86)}>+history</span>
            <span className="mono" style={tickS(100)}>CACHE_BREAKPOINT ▏</span>
          </div>
          <div />
        </div>
        <div style={{
          marginTop: 14, padding: '10px 12px', background: 'var(--bg-2)',
          borderLeft: '2px solid var(--agent-b)', borderRadius: '0 6px 6px 0',
          fontSize: 11.5, color: 'var(--fg-1)', lineHeight: 1.55,
        }}>
          Anthropic cache hits return at ~25% of base cost; the volatile tail after the
          marker (round instructions, output schema) is the only piece billed at full rate every round.
        </div>
      </div>
    );
  }
  const tickS = leftPct => ({
    position: 'absolute', top: 0, left: `${leftPct}%`, transform: 'translateX(-50%)',
    paddingTop: 4, fontSize: 9.5, color: 'var(--fg-3)',
  });

  // ─── Phase deep-dive accordions ───────────────────────────────────────

  function PhaseMeta({ rows }) {
    return (
      <dl style={{
        display: 'grid', gridTemplateColumns: '110px 1fr', gap: '4px 14px',
        fontSize: 11.5, padding: '10px 12px', background: 'var(--bg-2)',
        border: '1px solid var(--border-1)', borderRadius: 6, margin: '8px 0',
      }}>
        {rows.map(([k, v]) => (
          <React.Fragment key={k}>
            <dt className="mono" style={{
              color: 'var(--fg-3)', fontSize: 10.5, letterSpacing: '0.06em',
              textTransform: 'uppercase', paddingTop: 2,
            }}>{k}</dt>
            <dd style={{ margin: 0, color: 'var(--fg-1)' }}>{v}</dd>
          </React.Fragment>
        ))}
      </dl>
    );
  }

  function PhaseAccordion({ ph, name, tag, defaultOpen, children }) {
    const tagBg = tag === 'parallel'    ? { bg: 'var(--agent-b-bg-strong)', color: 'var(--agent-b)', border: 'var(--agent-b-border)' }
                : tag === 'turn-based'  ? { bg: 'var(--agent-a-bg-strong)', color: 'var(--agent-a)', border: 'var(--agent-a-border)' }
                : { bg: 'var(--bg-3)', color: 'var(--fg-1)', border: 'var(--border-2)' };
    return (
      <details open={defaultOpen} style={{
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        borderRadius: 8, marginBottom: 10, overflow: 'hidden',
      }}>
        <summary style={{
          listStyle: 'none', cursor: 'pointer', padding: '14px 18px',
          display: 'flex', alignItems: 'center', gap: 14, userSelect: 'none',
        }}>
          <span className="mono" style={{
            fontSize: 10.5, color: 'var(--fg-3)', letterSpacing: '0.08em', minWidth: 50,
          }}>PHASE {ph}</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg-0)' }}>{name}</span>
          <span className="mono" style={{
            fontSize: 10, padding: '2px 8px', borderRadius: 999,
            background: tagBg.bg, color: tagBg.color, border: `1px solid ${tagBg.border}`,
            marginLeft: 'auto',
          }}>{tag}</span>
          <span className="mono" style={{
            color: 'var(--fg-3)', fontSize: 12,
          }}>▶</span>
        </summary>
        <div style={{
          padding: '4px 18px 18px', borderTop: '1px solid var(--border-1)',
          fontSize: 13, color: 'var(--fg-1)', lineHeight: 1.65,
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
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        borderRadius: 6, marginBottom: 6,
      }}>
        <summary style={{
          listStyle: 'none', cursor: 'pointer', padding: '10px 14px',
          fontSize: 13, color: 'var(--fg-0)', fontWeight: 500,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
        }}>
          <span>{q}</span>
          <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 11 }}>▶</span>
        </summary>
        <div style={{
          padding: '0 14px 12px', fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.6,
        }}>{children}</div>
      </details>
    );
  }

  // ─── Section primitive ────────────────────────────────────────────────

  function Section({ kicker, title, lede, mutedLede, children }) {
    return (
      <section style={{ marginBottom: 44 }}>
        <div className="mono" style={{
          fontSize: 10.5, color: 'var(--fg-3)', letterSpacing: '0.08em',
          textTransform: 'uppercase', marginBottom: 6,
        }}>{kicker}</div>
        <h2 style={{
          fontSize: 17, fontWeight: 600, color: 'var(--fg-0)',
          margin: '0 0 14px', letterSpacing: '-0.005em',
        }}>{title}</h2>
        {lede && (
          <p style={{ fontSize: 13.5, color: 'var(--fg-1)', lineHeight: 1.65, margin: '0 0 12px' }}>{lede}</p>
        )}
        {mutedLede && (
          <p style={{ fontSize: 13.5, color: 'var(--fg-2)', lineHeight: 1.65, margin: '0 0 12px' }}>{mutedLede}</p>
        )}
        {children}
      </section>
    );
  }

  // ─── Full v3.5 protocol overview (cream-and-indigo reference) ─────────
  // Authored via the diagram skill (spec 0026). Inlined as JSX so it
  // doesn't depend on a static-asset fetch — the same file ships as
  // protocol-overview.svg in this directory for download.

  function ProtocolOverviewMap() {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1660 880"
           fontFamily="Inter, system-ui, -apple-system, sans-serif"
           style={{ display: 'block', width: '100%', height: 'auto' }}
           role="img"
           aria-label="Dual Research Protocol v3.5 — full landscape process map showing all five phases, agent cards, convergence and approval gates, source verification, repair mechanism, and exit codes.">
        <defs>
          <filter id="mapCardShadow" x="-4%" y="-4%" width="108%" height="116%">
            <feDropShadow dx="0" dy="2" stdDeviation="6" floodColor="#1a1a18" floodOpacity="0.10" />
          </filter>
          <filter id="mapCardShadowDark" x="-4%" y="-4%" width="108%" height="116%">
            <feDropShadow dx="0" dy="3" stdDeviation="8" floodColor="#1a1a18" floodOpacity="0.22" />
          </filter>
          <linearGradient id="mapBgGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#f5f1ea" />
            <stop offset="100%" stopColor="#ece8e0" />
          </linearGradient>
          <linearGradient id="mapSurfacePrimary" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#6573c9" />
            <stop offset="100%" stopColor="#3a4a8a" />
          </linearGradient>
          <linearGradient id="mapSurfaceNeutral" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#252521" />
            <stop offset="100%" stopColor="#1a1a18" />
          </linearGradient>
          <linearGradient id="mapSurfaceSlate" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#4a5568" />
            <stop offset="100%" stopColor="#2d3748" />
          </linearGradient>
          <linearGradient id="mapSurfaceSecure" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#2a5e40" />
            <stop offset="100%" stopColor="#1e4530" />
          </linearGradient>
          <linearGradient id="mapSurfaceStore" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#5e3f1c" />
            <stop offset="100%" stopColor="#3f2810" />
          </linearGradient>
          <marker id="mapArrowAccent" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#4f5fb8" />
          </marker>
          <marker id="mapArrowAccentSm" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
            <path d="M0,0 L0,6 L7,3 z" fill="#4f5fb8" />
          </marker>
          <marker id="mapArrowGreen" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#3d7f5b" />
          </marker>
        </defs>

        <rect width="1660" height="880" fill="url(#mapBgGrad)" />

        <text x="830" y="58" textAnchor="middle" fontSize="24" fontWeight="600" fill="#1a1a18" letterSpacing="-0.3">Dual Research Protocol v3.5</text>
        <text x="830" y="82" textAnchor="middle" fontSize="13" fill="#706e67">Two models research independently, negotiate a shared plan, one drafts, both review, single approved document.</text>

        <rect x="1346" y="42" width="138" height="24" rx="6" fill="url(#mapSurfacePrimary)" />
        <text x="1415" y="58" textAnchor="middle" fontSize="10" fontWeight="600" fill="white" letterSpacing="0.4">Claude Sonnet 4.6</text>
        <rect x="1494" y="42" width="110" height="24" rx="6" fill="url(#mapSurfaceSlate)" />
        <text x="1549" y="58" textAnchor="middle" fontSize="10" fontWeight="600" fill="white" letterSpacing="0.4">GPT-5.5</text>

        <text x="151"  y="116" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9e9b95" letterSpacing="2">PHASE 0</text>
        <text x="151"  y="132" textAnchor="middle" fontSize="12" fontWeight="600" fill="#1a1a18">Brief &amp; Preflight</text>
        <text x="381"  y="116" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9e9b95" letterSpacing="2">PHASE 1</text>
        <text x="381"  y="132" textAnchor="middle" fontSize="12" fontWeight="600" fill="#1a1a18">Independent Research</text>
        <text x="641"  y="116" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9e9b95" letterSpacing="2">PHASE 2</text>
        <text x="641"  y="132" textAnchor="middle" fontSize="12" fontWeight="600" fill="#1a1a18">Plan Negotiation</text>
        <text x="911"  y="116" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9e9b95" letterSpacing="2">PHASE 3</text>
        <text x="911"  y="132" textAnchor="middle" fontSize="12" fontWeight="600" fill="#1a1a18">Drafting</text>
        <text x="1181" y="116" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9e9b95" letterSpacing="2">PHASE 4</text>
        <text x="1181" y="132" textAnchor="middle" fontSize="12" fontWeight="600" fill="#1a1a18">Review Loop</text>
        <text x="1480" y="116" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9e9b95" letterSpacing="2">OUTPUT</text>
        <text x="1480" y="132" textAnchor="middle" fontSize="12" fontWeight="600" fill="#1a1a18">Approved Document</text>

        <rect x="56" y="148" width="190" height="84" rx="10" fill="white" stroke="#e8e2d8" strokeWidth="1" filter="url(#mapCardShadow)" />
        <circle cx="80" cy="178" r="13" fill="#1a1a18" />
        <text x="80" y="178" textAnchor="middle" dominantBaseline="central" fontSize="11" fontWeight="700" fill="white">B</text>
        <text x="104" y="174" fontSize="13" fontWeight="600" fill="#1a1a18">Research Brief</text>
        <text x="104" y="190" fontSize="10" fill="#4a4845">prompt · .md · Notion URL</text>
        <text x="74"  y="210" fontSize="9" fontStyle="italic" fill="#706e67">Notion pages pre-fetched</text>
        <text x="74"  y="223" fontSize="9" fontStyle="italic" fill="#706e67">captured to brief.md</text>

        <rect x="56" y="252" width="190" height="186" rx="10" fill="url(#mapSurfaceSecure)" filter="url(#mapCardShadowDark)" />
        <text x="151" y="276" textAnchor="middle" fontSize="13" fontWeight="600" fill="white">Preflight</text>
        <text x="151" y="292" textAnchor="middle" fontSize="9" fontWeight="600" fill="#6aad86" letterSpacing="1.4">BOTH AGENTS · PARALLEL</text>
        <line x1="74" y1="304" x2="228" y2="304" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
        <circle cx="78" cy="322" r="4" fill="#5aad80" />
        <text x="90" y="326" fontSize="10" fill="rgba(255,255,255,0.9)">Brief clarity</text>
        <circle cx="78" cy="342" r="4" fill="#5aad80" />
        <text x="90" y="346" fontSize="10" fill="rgba(255,255,255,0.9)">Missing inputs</text>
        <circle cx="78" cy="362" r="4" fill="#5aad80" />
        <text x="90" y="366" fontSize="10" fill="rgba(255,255,255,0.9)">Framing concerns</text>
        <line x1="74" y1="382" x2="228" y2="382" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <text x="151" y="400" textAnchor="middle" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.6)">BRIEF_OK → proceed</text>
        <text x="151" y="414" textAnchor="middle" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.6)">NEEDS_INPUT → pause</text>
        <text x="151" y="430" textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.45)" fontFamily="monospace">harness · python</text>

        <line x1="151" y1="232" x2="151" y2="252" stroke="#4f5fb8" strokeWidth="1.6" markerEnd="url(#mapArrowAccentSm)" />

        <rect x="286" y="148" width="190" height="156" rx="10" fill="url(#mapSurfacePrimary)" filter="url(#mapCardShadowDark)" />
        <circle cx="310" cy="178" r="14" fill="rgba(0,0,0,0.22)" />
        <text x="310" y="178" textAnchor="middle" dominantBaseline="central" fontSize="11" fontWeight="700" fill="white">C</text>
        <text x="334" y="175" fontSize="13" fontWeight="600" fill="white">Claude</text>
        <text x="334" y="190" fontSize="9" fill="rgba(255,255,255,0.7)">Sonnet 4.6 · thinking=med</text>
        <line x1="304" y1="204" x2="464" y2="204" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
        <text x="304" y="222" fontSize="10" fill="rgba(255,255,255,0.92)">· Summary + thesis</text>
        <text x="304" y="238" fontSize="10" fill="rgba(255,255,255,0.92)">· Findings  [V] / [U]</text>
        <text x="304" y="254" fontSize="10" fill="rgba(255,255,255,0.92)">· Disputable claims</text>
        <text x="304" y="270" fontSize="10" fill="rgba(255,255,255,0.92)">· Open questions + sources</text>
        <text x="381" y="292" textAnchor="middle" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.55)">web search · no hedging · commit</text>

        <text x="381" y="324" textAnchor="middle" fontSize="9" fontWeight="600" fill="#4f5fb8" letterSpacing="1.4">PARALLEL</text>
        <line x1="346" y1="330" x2="416" y2="330" stroke="#4f5fb8" strokeWidth="1" strokeDasharray="3,3" opacity="0.55" />

        <rect x="286" y="338" width="190" height="156" rx="10" fill="url(#mapSurfaceSlate)" filter="url(#mapCardShadowDark)" />
        <circle cx="310" cy="368" r="14" fill="rgba(255,255,255,0.14)" />
        <text x="310" y="368" textAnchor="middle" dominantBaseline="central" fontSize="11" fontWeight="700" fill="white">G</text>
        <text x="334" y="365" fontSize="13" fontWeight="600" fill="white">GPT</text>
        <text x="334" y="380" fontSize="9" fill="rgba(255,255,255,0.7)">GPT-5.5 · reasoning=med</text>
        <line x1="304" y1="394" x2="464" y2="394" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
        <text x="304" y="412" fontSize="10" fill="rgba(255,255,255,0.92)">· Summary + thesis</text>
        <text x="304" y="428" fontSize="10" fill="rgba(255,255,255,0.92)">· Findings  [V] / [U]</text>
        <text x="304" y="444" fontSize="10" fill="rgba(255,255,255,0.92)">· Disputable claims</text>
        <text x="304" y="460" fontSize="10" fill="rgba(255,255,255,0.92)">· Open questions + sources</text>
        <text x="381" y="482" textAnchor="middle" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.55)">asyncio.gather · fires at the same moment</text>

        <path d="M 246 282 Q 270 270 286 220" stroke="#4f5fb8" strokeWidth="1.8" fill="none" markerEnd="url(#mapArrowAccent)" />
        <text x="260" y="252" textAnchor="middle" fontSize="8" fontWeight="600" fill="#4f5fb8" letterSpacing="0.6">PASS</text>
        <path d="M 246 408 Q 270 420 286 414" stroke="#4f5fb8" strokeWidth="1.8" fill="none" markerEnd="url(#mapArrowAccent)" />

        <rect x="516" y="148" width="250" height="378" rx="14" fill="url(#mapSurfaceNeutral)" filter="url(#mapCardShadowDark)" />
        <text x="641" y="174" textAnchor="middle" fontSize="14" fontWeight="600" fill="white">Plan Negotiation</text>
        <text x="641" y="190" textAnchor="middle" fontSize="9" fontWeight="600" fill="#9aa3d4" letterSpacing="1.4">TURN-BASED · UP TO 12 ROUNDS</text>
        <line x1="536" y1="202" x2="746" y2="202" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />

        <rect x="536" y="214" width="210" height="58" rx="7" fill="rgba(79,95,184,0.22)" stroke="rgba(79,95,184,0.4)" strokeWidth="1" />
        <text x="548" y="233" fontSize="10" fontWeight="600" fill="#c5cdf0">Round 1 · Diff inventory</text>
        <text x="548" y="249" fontSize="9" fill="rgba(255,255,255,0.7)">diff vs other draft · gap research</text>
        <text x="548" y="263" fontSize="9" fill="rgba(255,255,255,0.5)" fontFamily="monospace">STATUS: NEGOTIATING (forced)</text>

        <rect x="536" y="282" width="210" height="82" rx="7" fill="rgba(255,255,255,0.06)" />
        <text x="548" y="301" fontSize="10" fontWeight="600" fill="rgba(255,255,255,0.92)">Rounds 2+ · Negotiation</text>
        <text x="548" y="316" fontSize="9" fill="rgba(255,255,255,0.7)">· corroborate [U] / central [V]</text>
        <text x="548" y="330" fontSize="9" fill="rgba(255,255,255,0.7)">· anti-sycophancy guard / turn</text>
        <text x="548" y="344" fontSize="9" fill="rgba(255,255,255,0.7)">· D-N IDs track disagreements</text>
        <text x="548" y="358" fontSize="9" fill="rgba(255,255,255,0.5)" fontFamily="monospace">BLOCKING / FINAL_SURFACED</text>

        <line x1="536" y1="378" x2="746" y2="378" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <text x="641" y="396" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9aa3d4" letterSpacing="1.4">CONVERGENCE GATE</text>
        <text x="536" y="412" fontSize="9" fill="rgba(255,255,255,0.78)">+ Both STATUS: AGREED</text>
        <text x="536" y="426" fontSize="9" fill="rgba(255,255,255,0.78)">+ AGREED_PLAN SHA-256 match</text>
        <text x="536" y="440" fontSize="9" fill="rgba(255,255,255,0.78)">+ BLOCKING_DISAGREEMENTS = 0</text>
        <text x="536" y="454" fontSize="9" fill="rgba(255,255,255,0.78)">+ OPEN_QUESTIONS = 0</text>
        <text x="536" y="468" fontSize="9" fill="rgba(255,255,255,0.78)">+ STRONGEST_REMAINING_OBJECTION</text>
        <text x="536" y="484" fontSize="9" fill="rgba(255,255,255,0.55)">FSD IDs aligned · pickDrafter() tiebreak</text>

        <line x1="536" y1="498" x2="746" y2="498" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <text x="641" y="514" textAnchor="middle" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.5)">soft cap 6 · hard cap 12 · resumable</text>

        <line x1="476" y1="220" x2="510" y2="290" stroke="#4f5fb8" strokeWidth="1.8" fill="none" markerEnd="url(#mapArrowAccentSm)" />
        <text x="488" y="248" fontSize="8" fontWeight="600" fill="#4f5fb8" letterSpacing="0.6">DRAFT-C</text>
        <line x1="476" y1="414" x2="510" y2="340" stroke="#4f5fb8" strokeWidth="1.8" fill="none" markerEnd="url(#mapArrowAccentSm)" />
        <text x="488" y="388" fontSize="8" fontWeight="600" fill="#4f5fb8" letterSpacing="0.6">DRAFT-G</text>

        <line x1="766" y1="337" x2="816" y2="337" stroke="#4f5fb8" strokeWidth="2" markerEnd="url(#mapArrowAccent)" />
        <text x="791" y="328" textAnchor="middle" fontSize="9" fontWeight="600" fill="#4f5fb8" letterSpacing="0.8">AGREED</text>

        <rect x="816" y="148" width="190" height="260" rx="10" fill="url(#mapSurfacePrimary)" filter="url(#mapCardShadowDark)" />
        <circle cx="840" cy="178" r="14" fill="rgba(255,255,255,0.18)" />
        <text x="840" y="178" textAnchor="middle" dominantBaseline="central" fontSize="11" fontWeight="700" fill="white">★</text>
        <text x="864" y="175" fontSize="13" fontWeight="600" fill="white">Drafter</text>
        <text x="864" y="190" fontSize="9" fill="rgba(255,255,255,0.7)">tiebreak winner · single-shot</text>
        <line x1="836" y1="204" x2="996" y2="204" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
        <text x="836" y="220" fontSize="9" fontWeight="600" fill="#c5cdf0" letterSpacing="1.4">INPUTS</text>
        <text x="836" y="236" fontSize="10" fill="rgba(255,255,255,0.92)">· hash-verified AGREED_PLAN</text>
        <text x="836" y="252" fontSize="10" fill="rgba(255,255,255,0.92)">· both Phase 1 drafts</text>
        <text x="836" y="268" fontSize="10" fill="rgba(255,255,255,0.92)">· full Phase 2 conversation</text>
        <text x="836" y="284" fontSize="10" fill="rgba(255,255,255,0.92)">· injected FSD array</text>
        <line x1="836" y1="298" x2="996" y2="298" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
        <text x="836" y="314" fontSize="9" fontWeight="600" fill="#c5cdf0" letterSpacing="1.4">OUTPUT SECTIONS</text>
        <text x="836" y="330" fontSize="10" fill="rgba(255,255,255,0.92)">· Summary · Findings · FSD</text>
        <text x="836" y="346" fontSize="10" fill="rgba(255,255,255,0.92)">· Open questions · Sources</text>
        <text x="836" y="362" fontSize="10" fill="rgba(255,255,255,0.92)">· Confidence ledger [V] / [U]</text>
        <text x="911" y="388" textAnchor="middle" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.55)" fontFamily="monospace">draft-v1.md</text>

        <line x1="1006" y1="337" x2="1056" y2="337" stroke="#4f5fb8" strokeWidth="2" markerEnd="url(#mapArrowAccent)" />
        <text x="1031" y="328" textAnchor="middle" fontSize="9" fontWeight="600" fill="#4f5fb8" letterSpacing="0.8">DRAFT V1</text>

        <rect x="1056" y="148" width="250" height="378" rx="14" fill="url(#mapSurfaceNeutral)" filter="url(#mapCardShadowDark)" />
        <text x="1181" y="174" textAnchor="middle" fontSize="14" fontWeight="600" fill="white">Review Loop</text>
        <text x="1181" y="190" textAnchor="middle" fontSize="9" fontWeight="600" fill="#9aa3d4" letterSpacing="1.4">TURN-BASED · DRAFTER vs REVIEWER</text>
        <line x1="1076" y1="202" x2="1286" y2="202" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />

        <rect x="1076" y="214" width="210" height="76" rx="7" fill="rgba(74,85,104,0.4)" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
        <text x="1088" y="232" fontSize="10" fontWeight="600" fill="rgba(255,255,255,0.92)">Reviewer · non-drafter</text>
        <text x="1088" y="248" fontSize="9" fill="rgba(255,255,255,0.7)">· evidence checked / round (req)</text>
        <text x="1088" y="262" fontSize="9" fill="rgba(255,255,255,0.7)">· issue ledger · stable IDs</text>
        <text x="1088" y="276" fontSize="9" fill="rgba(255,255,255,0.5)">corroborates [U] + central [V]</text>

        <rect x="1076" y="300" width="210" height="76" rx="7" fill="rgba(79,95,184,0.22)" stroke="rgba(79,95,184,0.4)" strokeWidth="1" />
        <text x="1088" y="318" fontSize="10" fontWeight="600" fill="#c5cdf0">Drafter · revision note</text>
        <text x="1088" y="334" fontSize="9" fill="rgba(255,255,255,0.7)">· answers every open issue</text>
        <text x="1088" y="348" fontSize="9" fill="rgba(255,255,255,0.7)">· writes draft-v(N+1).md</text>
        <text x="1088" y="362" fontSize="9" fill="rgba(255,255,255,0.5)">updates Confidence on each rev</text>

        <line x1="1076" y1="390" x2="1286" y2="390" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <text x="1181" y="408" textAnchor="middle" fontSize="10" fontWeight="600" fill="#9aa3d4" letterSpacing="1.4">APPROVAL GATE</text>
        <text x="1076" y="424" fontSize="9" fill="rgba(255,255,255,0.78)">+ Both STATUS: APPROVED</text>
        <text x="1076" y="438" fontSize="9" fill="rgba(255,255,255,0.78)">+ OPEN_ISSUES = 0</text>
        <text x="1076" y="452" fontSize="9" fill="rgba(255,255,255,0.78)">+ ENDORSEMENT + NON-BLOCKING</text>
        <text x="1076" y="466" fontSize="9" fill="rgba(255,255,255,0.78)">+ STRONGEST_REMAINING_OBJECTION</text>
        <text x="1076" y="480" fontSize="9" fill="rgba(255,255,255,0.55)">carryover audit: FSD-N verified in draft</text>

        <line x1="1076" y1="498" x2="1286" y2="498" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        <text x="1181" y="514" textAnchor="middle" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.5)">soft cap 6 · hard cap 12 · deadlock = 51</text>

        <line x1="1306" y1="337" x2="1356" y2="337" stroke="#3d7f5b" strokeWidth="2" markerEnd="url(#mapArrowGreen)" />
        <text x="1331" y="328" textAnchor="middle" fontSize="9" fontWeight="600" fill="#3d7f5b" letterSpacing="0.8">APPROVED</text>

        <rect x="1356" y="148" width="248" height="280" rx="10" fill="url(#mapSurfaceStore)" filter="url(#mapCardShadowDark)" />
        <text x="1480" y="174" textAnchor="middle" fontSize="14" fontWeight="600" fill="white">Final Document</text>
        <text x="1480" y="190" textAnchor="middle" fontSize="9" fontWeight="600" fill="#cba075" letterSpacing="1.4">BOTH MODELS ENDORSED</text>
        <circle cx="1592" cy="166" r="5" fill="#3d7f5b" />
        <line x1="1376" y1="202" x2="1584" y2="202" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />

        <rect x="1376" y="212" width="208" height="40" rx="6" fill="rgba(0,0,0,0.22)" />
        <text x="1388" y="230" fontSize="10" fill="#cba075" fontFamily="monospace">## How this document</text>
        <text x="1388" y="244" fontSize="10" fill="#cba075" fontFamily="monospace">##   was produced</text>

        <text x="1376" y="270" fontSize="10" fill="rgba(255,255,255,0.88)">· Outcome: APPROVED</text>
        <text x="1376" y="286" fontSize="10" fill="rgba(255,255,255,0.88)">· Plan rounds · drafter · review rounds</text>
        <text x="1376" y="302" fontSize="10" fill="rgba(255,255,255,0.88)">· Confidence: HIGH / MOD / LOW</text>
        <text x="1376" y="318" fontSize="10" fill="rgba(255,255,255,0.88)">· Token cost estimate</text>

        <line x1="1376" y1="334" x2="1584" y2="334" stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
        <text x="1376" y="352" fontSize="9" fontWeight="600" fill="#cba075" letterSpacing="1.4">CONFIDENCE LEDGER</text>
        <text x="1376" y="370" fontSize="10" fill="rgba(255,255,255,0.78)">claim · [V] / [U] · CORROBORATED</text>
        <text x="1376" y="386" fontSize="10" fill="rgba(255,255,255,0.78)">material claims only · body prose clean</text>
        <text x="1376" y="412" fontSize="9" fontStyle="italic" fill="rgba(255,255,255,0.5)">final.md · written once, both models endorse</text>

        <text x="56" y="562" fontSize="10" fontWeight="600" fill="#9e9b95" letterSpacing="2">PROTOCOL DETAILS</text>
        <line x1="56" y1="572" x2="200" y2="572" stroke="#9e9b95" strokeWidth="0.5" />

        <rect x="56" y="588" width="496" height="124" rx="10" fill="white" stroke="#e8e2d8" strokeWidth="1" filter="url(#mapCardShadow)" />
        <text x="76" y="610" fontSize="10" fontWeight="600" fill="#1a1a18" letterSpacing="1.4">SOURCE VERIFICATION  ·  v3.1</text>
        <line x1="76" y1="620" x2="532" y2="620" stroke="#e8e2d8" strokeWidth="1" />
        <rect x="76" y="632" width="40" height="20" rx="4" fill="#4f5fb8" />
        <text x="96" y="646" textAnchor="middle" fontSize="10" fontWeight="700" fill="white">[V]</text>
        <text x="124" y="646" fontSize="11" fill="#4a4845">verified this run — tool retrieved a source</text>
        <rect x="76" y="660" width="40" height="20" rx="4" fill="#9e9b95" />
        <text x="96" y="674" textAnchor="middle" fontSize="10" fontWeight="700" fill="white">[U]</text>
        <text x="124" y="674" fontSize="11" fill="#4a4845">unverified — from training weights, must be corroborated</text>
        <text x="76" y="698" fontSize="9" fontStyle="italic" fill="#706e67">CORROBORATED  ·  UNCORROBORATED  ·  CONTRADICTED</text>

        <rect x="572" y="588" width="496" height="124" rx="10" fill="white" stroke="#e8e2d8" strokeWidth="1" filter="url(#mapCardShadow)" />
        <text x="592" y="610" fontSize="10" fontWeight="600" fill="#1a1a18" letterSpacing="1.4">REPAIR MECHANISM</text>
        <line x1="592" y1="620" x2="1048" y2="620" stroke="#e8e2d8" strokeWidth="1" />
        <text x="592" y="640" fontSize="11" fill="#4a4845">1.  malformed turn  →  rename to <tspan fontFamily="monospace" fill="#3a4a8a">.malformed-N.md</tspan></text>
        <text x="592" y="660" fontSize="11" fill="#4a4845">2.  repair prompt  →  re-check well-formedness</text>
        <text x="592" y="680" fontSize="11" fill="#4a4845">3.  2 consecutive failures  →  <tspan fontWeight="600" fill="#cc6e55">exit 52</tspan></text>
        <text x="592" y="700" fontSize="9" fontStyle="italic" fill="#706e67">repair events logged · invisible to the other agent</text>

        <rect x="1088" y="588" width="516" height="124" rx="10" fill="white" stroke="#e8e2d8" strokeWidth="1" filter="url(#mapCardShadow)" />
        <text x="1108" y="610" fontSize="10" fontWeight="600" fill="#1a1a18" letterSpacing="1.4">EXIT CODES</text>
        <line x1="1108" y1="620" x2="1584" y2="620" stroke="#e8e2d8" strokeWidth="1" />
        <text x="1108" y="640" fontSize="11" fill="#4a4845">
          <tspan fontWeight="700" fill="#3d7f5b" fontFamily="monospace">0</tspan>
          <tspan>  approved</tspan>
          <tspan fontWeight="700" fill="#cc6e55" fontFamily="monospace" dx="20">1</tspan>
          <tspan>  preflight failure</tspan>
          <tspan fontWeight="700" fill="#cc6e55" fontFamily="monospace" dx="20">2</tspan>
          <tspan>  runtime error</tspan>
        </text>
        <text x="1108" y="660" fontSize="11" fill="#4a4845">
          <tspan fontWeight="700" fill="#4a9eca" fontFamily="monospace">50</tspan>
          <tspan>  soft cap (resumable)</tspan>
          <tspan fontWeight="700" fill="#cc6e55" fontFamily="monospace" dx="20">51</tspan>
          <tspan>  hard cap / deadlock</tspan>
        </text>
        <text x="1108" y="680" fontSize="11" fill="#4a4845">
          <tspan fontWeight="700" fill="#cc6e55" fontFamily="monospace">52</tspan>
          <tspan>  protocol parse failure (2 consecutive malformed turns)</tspan>
        </text>
        <text x="1108" y="700" fontSize="9" fontStyle="italic" fill="#706e67"><tspan fontFamily="monospace">state.json</tspan> persisted  ·  resume with <tspan fontFamily="monospace">--resume</tspan></text>

        <line x1="56" y1="752" x2="1604" y2="752" stroke="#d8d4cc" strokeWidth="1" opacity="0.7" />
        <text x="56" y="778" fontSize="11" fill="#4a4845">
          <tspan fontWeight="600" fill="#1a1a18">Agreement is valuable only when it improves the final answer.</tspan>
          <tspan>  Do not agree for politeness, speed, symmetry, or fatigue · do not disagree for performance or to appear rigorous.</tspan>
        </text>
        <text x="56" y="800" fontSize="11" fill="#4a4845">
          <tspan fontWeight="600" fill="#1a1a18">Phase 2 and Phase 4 each run internally until convergence.</tspan>
          <tspan>  No cross-phase back-propagation occurs in a single run.</tspan>
        </text>

        <text x="1604" y="836" textAnchor="end" fontSize="9" fontStyle="italic" fill="#9e9b95">Dual Research Protocol v3.5  ·  Claude Sonnet 4.6 + GPT-5.5  ·  Python orchestrator</text>
      </svg>
    );
  }

  function ProtocolOverviewFold() {
    return (
      <details style={{
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        borderRadius: 8, overflow: 'hidden', marginTop: 14,
      }}>
        <summary style={{
          listStyle: 'none', cursor: 'pointer', padding: '14px 18px',
          display: 'flex', alignItems: 'center', gap: 12, userSelect: 'none',
        }}>
          <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--fg-0)' }}>View full process map</span>
          <span style={{ fontSize: 12, color: 'var(--fg-2)' }}>
            — every phase, sub-card, gate, callout and exit code in one page
          </span>
          <span className="mono" style={{
            fontSize: 10, padding: '2px 8px', borderRadius: 999,
            background: 'var(--bg-3)', color: 'var(--fg-2)',
            border: '1px solid var(--border-2)', marginLeft: 'auto',
            letterSpacing: '0.04em',
          }}>v3.5 · landscape</span>
          <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 12 }}>▶</span>
        </summary>
        <div style={{
          padding: 0, borderTop: '1px solid var(--border-1)', background: '#f5f1ea',
        }}>
          <ProtocolOverviewMap />
        </div>
        <div style={{
          padding: '10px 18px', borderTop: '1px solid var(--border-1)',
          fontSize: 11.5, color: 'var(--fg-2)',
          display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap',
        }}>
          <span>Reference diagram — light surface, doesn't follow theme toggle.</span>
          <a href="protocol-overview.svg" target="_blank" rel="noopener"
             style={{ color: 'var(--info)' }}>Open SVG ↗</a>
          <span className="mono" style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--fg-3)' }}>
            1660 × 880 · Inter · cream &amp; indigo design system
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
        background: 'var(--bg-1)', border: '1px solid var(--border-1)',
        borderRadius: 8,
      }}>
        <div style={{
          display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 6,
          flexWrap: 'wrap',
        }}>
          <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg-0)' }}>{entry.version}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--fg-3)' }}>{entry.date}</span>
          <span style={{ fontSize: 12.5, color: 'var(--fg-2)' }}>{entry.summary}</span>
        </div>
        <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12.5, color: 'var(--fg-1)', lineHeight: 1.6 }}>
          {entry.items.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      </div>
    );
  }

  // ─── Main page ────────────────────────────────────────────────────────

  function HowItWorks() {
    return (
      <div style={{
        height: '100%', overflow: 'auto', padding: '28px 32px 96px',
        background: 'var(--bg-0)', color: 'var(--fg-0)',
      }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>

          {/* Hero */}
          <header style={{ marginBottom: 36 }}>
            <div className="mono" style={{
              fontSize: 10.5, color: 'var(--fg-3)', letterSpacing: '0.08em',
              textTransform: 'uppercase', marginBottom: 8,
            }}>PROTOCOL · v3.5</div>
            <h1 style={{
              fontSize: 30, fontWeight: 600, margin: 0,
              letterSpacing: '-0.02em', color: 'var(--fg-0)',
            }}>How dual-research works</h1>
            <p style={{
              fontSize: 14.5, color: 'var(--fg-2)', maxWidth: 640,
              marginTop: 10, marginBottom: 0, lineHeight: 1.6,
            }}>
              Two language models start from the same brief, work independently,
              then negotiate until they agree on a single document. The
              orchestrator is deterministic; the agents are not. This page is
              what they actually do, in order.
            </p>
            <TldrCards />
          </header>

          {/* Five phases at a glance */}
          <Section
            kicker="Overview"
            title="The five phases"
            lede={
              <span>
                A run walks a fixed phase machine. Some phases fire both agents in
                parallel, some are turn-based with multiple rounds, one is a
                single-shot draft. The orchestrator never lets an agent advance
                the phase — it watches the outputs and decides.
              </span>
            }
          >
            <PhaseStrip />
            <ProtocolOverviewFold />
          </Section>

          {/* Chat lifecycle (main new section) */}
          <Section
            kicker="Chat lifecycle"
            title="When do we start new chats?"
            lede={
              <span>
                <strong>Every API call is a new "chat".</strong> The orchestrator
                never holds a conversation handle, never sends a thread ID, never
                appends to a stored message list. For each phase and each round,
                it assembles a fresh prompt from scratch — re-inlining the brief,
                the Phase&nbsp;1 drafts, any prior turns, the agreed plan, and so
                on. The two agents do not share an API session and they have no
                memory of previous calls beyond what the orchestrator quotes back
                at them.
              </span>
            }
            mutedLede="Below: every box is one HTTP request to one provider. The contents of each box are exactly the inputs that request carries."
          >
            <ChatLifecycle />
            <Legend />
            <ComparePanel />
            <div className="mono" style={{
              marginTop: 14, padding: '8px 12px',
              background: 'var(--bg-1)', border: '1px solid var(--border-1)',
              borderRadius: 6, fontSize: 10.5, color: 'var(--fg-3)',
              lineHeight: 1.55,
            }}>
              Want the same lanes filled with real numbers from a run? Open
              any run and switch the timeline pane to its
              <span style={{ color: 'var(--fg-1)' }}>&nbsp;Consumption&nbsp;</span>
              tab — each row is one chat above, with a bar showing how much
              of that model's context window the call consumed.
            </div>
          </Section>

          {/* Context grows, prefix is cached */}
          <Section
            kicker="Cost shape"
            title="Context grows, but the prefix is cached"
            lede={
              <span>
                Because we re-inline everything, the prompt gets longer each
                round. The orchestrator places a <code style={codeS}>CACHE_BREAKPOINT</code> marker
                between the stable prefix (brief + Phase&nbsp;1 drafts + earlier
                turns) and the volatile suffix (the round's instructions).
                Anthropic caches the prefix with a 1h TTL; OpenAI auto-caches any
                shared prefix ≥1024 tokens. Long runs end up paying full price
                only for the small variable tail.
              </span>
            }
          >
            <ContextGrowthBars />
          </Section>

          {/* Phase deep-dive */}
          <Section
            kicker="Deep-dive"
            title="Phase by phase"
            mutedLede="Expand any phase for the full mechanics, inputs, and outputs."
          >
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

            <PhaseAccordion ph={1} name="Independent research" tag="parallel">
              <p>
                Each agent writes a complete first-pass research draft, alone.
                Same brief, same prompt structure — but the two drafts are written
                without any cross-talk. This is the only phase where you see how
                each model interprets the brief under zero negotiation pressure.
              </p>
              <PhaseMeta rows={[
                ['input',  <Tk kind="brief">brief</Tk>],
                ['chats',  '2 fresh API calls (one per agent), no history'],
                ['output', <span><code style={codeS}>phase1/draft-claude.md</code>, <code style={codeS}>phase1/draft-openai.md</code></span>],
                ['gate',   'both drafts present ⇒ advance'],
              ]} />
            </PhaseAccordion>

            <PhaseAccordion ph={2} name="Plan negotiation" tag="turn-based">
              <p>
                The agents start reading each other's work. Each round, both
                agents fire <em>in parallel</em> with the brief, both Phase&nbsp;1
                drafts, and every prior negotiation turn from both sides as input.
                Round 1 is structurally required to be a "first read" — neither
                agent can mark AGREED yet. From round 2 on, they exchange
                counter-proposals, mark disagreements with stable
                {' '}<code style={codeS}>D-N</code> identifiers, and try to converge on an
                {' '}<code style={codeS}>AGREED_PLAN</code> block whose SHA-256 hash matches the other agent's.
              </p>
              <p>
                Convergence detection is mechanical: same{' '}
                <code style={codeS}>STATUS: AGREED</code>, same drafter choice, same plan hash,
                zero open questions, zero blocking disagreements, matching
                final-surfaced disagreements — all in the same round.
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

            <PhaseAccordion ph={3} name="Drafting" tag="single-shot">
              <p>
                One agent — the drafter, picked by <code style={codeS}>tiebreak.pick_drafter</code> —
                writes the converged document in a single call. They receive: the
                brief, both Phase&nbsp;1 drafts, the hash-verified canonical agreed
                plan, the final-surfaced disagreements, and the entire Phase&nbsp;2
                conversation as context. The other agent is silent in this phase.
              </p>
              <PhaseMeta rows={[
                ['input',  <span><Tk kind="brief">brief</Tk> <Tk kind="d1">P1 draft-claude</Tk> <Tk kind="d2">P1 draft-openai</Tk> <Tk kind="plan">agreed plan</Tk> <Tk kind="hist">all P2 turns</Tk></span>],
                ['chats',  '1 fresh API call (drafter only)'],
                ['output', <code style={codeS}>phase3/draft-v1.md</code>],
                ['gate',   'draft written ⇒ advance'],
              ]} />
            </PhaseAccordion>

            <PhaseAccordion ph={4} name="Cross-review" tag="turn-based">
              <p>
                Same shape as Phase&nbsp;2: both agents fire in parallel each
                round. The drafter can include a <code style={codeS}>## Revised draft</code>{' '}
                section in their turn, which the orchestrator detects, writes as{' '}
                <code style={codeS}>phase4/draft-vN+1.md</code>, and shows to both agents in the
                next round. The reviewer can comment but not edit. Convergence
                here means both agents emit <code style={codeS}>STATUS: APPROVED</code> with
                zero open issues in the same round.
              </p>
              <PhaseMeta rows={[
                ['input',  <span><Tk kind="brief">brief</Tk> <Tk kind="draft">current draft-vK</Tk> <Tk kind="histp">all prior P4 turns</Tk></span>],
                ['chats',  '2 fresh API calls per round; full history re-inlined every time'],
                ['output', <span><code style={codeS}>phase4/round-NN-&#123;agent&#125;.md</code>, plus <code style={codeS}>draft-vK+1.md</code> if revised</span>],
                ['gate',   <span>both agents <code style={codeS}>STATUS: APPROVED</code>, zero open issues, same round</span>],
              ]} />
            </PhaseAccordion>
          </Section>

          {/* Round up close */}
          <Section
            kicker="Zoom in"
            title="A round, up close"
            lede={
              <span>
                In each Phase&nbsp;2 (and Phase&nbsp;4) round, the orchestrator
                builds one prompt per agent that bundles all the prior history,
                fires both calls in parallel, writes the two responses to disk,
                then checks whether the convergence criteria are met. If yes,
                advance phase. If no, repeat with the new turn files appended to
                the history.
              </span>
            }
          >
            <div style={{
              padding: '16px 18px', background: 'var(--bg-1)',
              border: '1px solid var(--border-1)', borderRadius: 8,
            }}>
              <NegotiationRoundDiagram />
              <div style={{
                fontSize: 11.5, color: 'var(--fg-3)', fontStyle: 'italic', marginTop: 6,
              }}>
                If yes, advance phase. If no, append both turns to disk and run
                the next round.
              </div>
            </div>
          </Section>

          {/* FAQ */}
          <Section kicker="FAQ" title="What gets decided when">
            <Faq q="Do they read each other's work?">
              Not in Phases 0 and 1. From Phase&nbsp;2 onward yes — each agent's
              prompt inlines the brief, both Phase&nbsp;1 drafts, and every prior
              round's turn from both sides. They build context fully transparently.
            </Faq>
            <Faq q="Who goes first in a round? Random? Fixed?">
              Neither. <strong>Both agents fire at the same moment</strong> via
              {' '}<code style={codeS}>asyncio.gather</code>. There's no "speaker" in the way humans
              would imagine. Each agent independently produces a turn that
              references all prior history — they aren't reading the round-N
              turn of the other agent while they're writing round N.
            </Faq>
            <Faq q="Fresh chats per turn, or one long chat?">
              <strong>Fresh API call every turn.</strong> The agents have no
              persistent conversation handle; the orchestrator re-inlines the
              full prior-turn history into every new prompt. The{' '}
              <code style={codeS}>CACHE_BREAKPOINT</code> marker lets Anthropic cache the
              stable prefix (brief + Phase&nbsp;1 drafts + earlier turns) so the
              marginal cost of long history is small, but that's prefix caching —
              not a session. From the agent's perspective every turn is a single
              question with all context provided up front. See "Chat lifecycle"
              above for the per-phase picture.
            </Faq>
            <Faq q="How is the drafter picked?">
              A four-step cascade in <code style={codeS}>tiebreak.pick_drafter</code>:
              <ol style={{ paddingLeft: 22, margin: '6px 0' }}>
                <li>If both agents independently recommend the same drafter in their AGREED turns — that wins.</li>
                <li>Otherwise, sum each agent's self-rated <code style={codeS}>DOMAIN_FIT_SELF</code> plus the other's rating of them. Higher total drafts.</li>
                <li>Tiebreak by plan-alignment: word-set overlap between the agreed plan and each agent's Phase 1 draft.</li>
                <li>Last-resort: <code style={codeS}>SHA-256(brief)</code>'s first byte parity. Even = claude, odd = openai. Deterministic, no concession asymmetry.</li>
              </ol>
            </Faq>
            <Faq q="What if they never converge?">
              Two caps. <strong>Soft cap</strong> (default 6 rounds) logs a
              warning and keeps going. <strong>Hard cap</strong> (default 12
              rounds) stops the run, exits with code&nbsp;51, and emits a
              {' '}<code style={codeS}>final.md</code> containing the last draft plus both agents'
              last review turns as an "unresolved disagreements" appendix.
              Confidence tag is forced to <code style={codeS}>LOW</code>.
            </Faq>
            <Faq q="What if an agent emits something the parser can't read?">
              Each agent has one repair attempt per phase. The orchestrator saves
              the malformed turn (as <code style={codeS}>round-NN-agent.malformed-N.md</code>),
              spends the budget, and re-prompts the agent with the specific
              missing fields surfaced. If the agent fails again on the next
              round, the run exits with code&nbsp;52. Two consecutive parse
              failures kill it.
            </Faq>
            <Faq q="Which models are used?">
              By default the production tier: Claude Sonnet 4.6 (with the
              1M-context beta) + GPT-5.5. There's a faster <code style={codeS}>test</code>{' '}
              tier (Haiku 4.5 + GPT-5-mini) for verifying changes without
              spending much. The agent labels stay <code style={codeS}>claude</code> and{' '}
              <code style={codeS}>openai</code>; the actual model id is recorded in the
              run's metrics file.
            </Faq>
            <Faq q="Where does the cost come from?">
              Every call records its token usage and a per-call USD cost computed
              from the model's published pricing. The number you see in the
              header is the sum of every call in the run. Anthropic prompt
              caching gives ~75% off cached prefix reads — long Phase&nbsp;2 runs
              are cheaper than their input-token count suggests.
            </Faq>
          </Section>

          {/* Release notes */}
          <Section kicker="Changelog" title="Release notes" mutedLede="Each entry corresponds to a merged spec. Newest first.">
            {VERSION_NOTES.map(entry => <ReleaseNote key={entry.version} entry={entry} />)}
          </Section>

        </div>
      </div>
    );
  }

  window.HowItWorks = HowItWorks;
})();
