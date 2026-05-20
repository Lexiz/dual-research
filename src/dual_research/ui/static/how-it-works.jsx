// how-it-works.jsx — user-facing explainer of the Dual Research protocol
// plus the in-app changelog (Spec 0121 rewrite).
//
// IA: 11 collapsible sections in the "How it works" tab + a tabbed Changelog
// view. Every diagram embeds via theme-aware <img> swap (MutationObserver on
// body.classList) from /diagrams/how-it-works/. Every chip uses the spec-0119
// canonical Chip CSS classes (the .chip / .cat-bubble vocabulary in
// components.css); no bespoke chip variants are introduced here. Layout / list
// / table classes live under the `/* spec-0121` block in components.css.
//
// VERSION_NOTES is the source of the in-app changelog. Future specs touching
// user-visible behaviour append a new entry per CONTRIBUTING.md. New entries
// (v1.3.0 onward) carry richer metadata — bump, specs, specPath, screenshots
// — which the ChangelogEntry renderer handles. Older entries keep their
// minimal {version, date, summary, items} shape; absent fields render as
// suppressed chrome.

(function () {
  'use strict';

  // ─── In-app release notes ─────────────────────────────────────
  const VERSION_NOTES = [
    {
      version: '1.5.0',
      date: '2026-05-20',
      bump: 'MINOR',
      specs: ['0121'],
      specPath: '/specs/0121-how-it-works-and-changelog-rework.md',
      summary: 'How-It-Works overlay + Changelog tab — full content & component rewrite.',
      items: [
        '<strong>Rewrote 100% of the in-overlay prose</strong> to match the live Deep Research protocol (specs 0114 → 0120). Phase vocabulary updated (input / research-plan / negotiate-plan / draft / review-draft). The legacy <code>claim</code> kind, pre-0114 D-N identifiers, and pre-0118 cost terminology are gone from the prose.',
        '<strong>Redrew every diagram from scratch.</strong> Seven new diagrams via the diagram skill, light + dark each (14 SVGs under <code>/diagrams/how-it-works/</code>): full protocol pipeline, per-phase input composition, item lifecycle state machine, category taxonomy + chip composition, cost calculation flow, convergence + escape hatches, turn-modal anatomy.',
        '<strong>New 11-section IA</strong>: Protocol overview → Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → How turns are reviewed → Item taxonomy & categories → Item lifecycle → Convergence & escape hatches → Cost & consumption. Each section is a CollapsibleSection with localStorage persistence; first section open by default.',
        '<strong>Every chip on the overlay uses the spec-0119 vocabulary.</strong> Category bubbles (Q/D/I/C) render with their canonical tones (info/warn/err/idle); provider chips use Claude (sable) / GPT (sage); status chips never bare.',
        '<strong>Changelog tab rewritten</strong> with per-entry CollapsibleSection + Card, bump chip (MAJOR/MINOR/PATCH), spec-link button, and a screenshot grid (the three newest entries embed before/after PNGs of the surface each spec affected).',
        '<strong>Backfilled the three missing changelog entries</strong>: v1.3.0 (spec 0118 — consumption + cost), v1.4.0 (spec 0119 — badge governance), v1.4.1 (spec 0120 — turn-modal items panel).',
        '<strong>Retired ~1,500 lines of dead-code JSX</strong> from how-it-works.jsx: <code>PhaseStrip</code>, <code>NegotiationRoundDiagram</code>, <code>ContextGrowthBars</code>, <code>ChatLifecycle</code>, <code>LifecycleRow</code>, <code>CallBox</code>, <code>TldrCards</code>, <code>ComparePanel</code>, <code>Section</code>, <code>Legend</code>, <code>Tk</code>, <code>AgentDisc</code>, <code>ProtocolOverviewMap</code>, <code>ProtocolOverviewFold</code>, the old <code>ReleaseNote</code> and <code>ChangelogEntry</code>. The legacy <code>deep-research-pipeline.{light,dark}.svg</code> remains in <code>/diagrams/</code> but is no longer referenced.',
        '<strong>Three new CSS utilities</strong> in components.css under a spec-0121 block: <code>.hiw-note</code> (info/warn/err/ok-toned callout), <code>.hiw-table</code> (styled prose table), <code>.hiw-code</code> (block code), plus the structural <code>.hiw-*</code> / <code>.changelog-*</code> / <code>.cs-section</code> / <code>.cl-filter-row</code> classes.',
        '<strong>Backend untouched.</strong> Pure frontend documentation surface; no edits to <code>contract/</code>, <code>orchestrator/</code>, <code>protocol/</code>, <code>events/</code>, or any other JSX file. Cache-bust <code>?v=0120b → ?v=0121a</code>.',
      ],
      screenshots: [
        { path: '/changelog-shots/1.5.0/overview-section-overview.dark.png',
          alt: 'How-it-works overlay — Protocol overview',
          caption: 'Protocol overview section (default-open)' },
        { path: '/changelog-shots/1.5.0/overlay-section-categories.dark.png',
          alt: 'How-it-works overlay — Item taxonomy & categories',
          caption: 'Category taxonomy & chip composition' },
      ],
    },
    {
      version: '1.4.1',
      date: '2026-05-20',
      bump: 'PATCH',
      specs: ['0120'],
      specPath: '/specs/0120-turn-modal-items-panel-rework.md',
      summary: 'Turn-modal items panel rework — provider chip + Anchor/Title/Rationale split + Claims panel removed.',
      items: [
        '<strong>Provider chip on every item card.</strong> Each card in the turn-modal right pane now begins with a <span class="chip tone-claude no-dot"><span class="chip-label">Claude</span></span> or <span class="chip tone-gpt no-dot"><span class="chip-label">GPT</span></span> chip so you can see at a glance who raised the item.',
        '<strong>Three labelled body segments.</strong> Each card body splits into <strong>Anchored to &lt;agent&gt;\'s draft</strong> (the quoted reference), <strong>Title</strong> (the one-line bold summary), and <strong>Rationale</strong> (the elaborating paragraph). Labels are small caps so the body stays visually quiet.',
        '<strong>Claims panel removed</strong> from new-protocol render paths. Legacy renderer (for pre-0114 runs) unchanged.',
        '<strong>Panel headers use spec-0119 category chips.</strong> "Questions 5" panel header is now <span class="chip tone-info no-dot"><span class="cat-bubble">Q</span><span class="chip-label">Questions</span><span class="chip-value">5</span></span> — identical to the critique pane\'s filter legend.',
        '<strong>Sources widget unchanged.</strong> When an item carries evidence, the existing SourceRow renders verbatim.',
      ],
      screenshots: [
        { path: '/changelog-shots/1.4.1/turn-modal-right-pane-before.dark.png',
          alt: 'pre-0120 raw-markdown turn-modal card',
          caption: 'before: raw markdown body' },
        { path: '/changelog-shots/1.4.1/turn-modal-right-pane-after.dark.png',
          alt: 'post-0120 labelled-segment turn-modal card',
          caption: 'after: Anchor / Title / Rationale labelled' },
      ],
    },
    {
      version: '1.4.0',
      date: '2026-05-20',
      bump: 'MINOR',
      specs: ['0119'],
      specPath: '/specs/0119-badge-governance.md',
      summary: 'Badge governance — unified Chip primitive + canonical vocabulary (Q/D/I/C bubbles, lifecycle verb chips, never-bare status).',
      items: [
        '<strong>One Chip primitive.</strong> Eight pre-0119 chip-like JSX patterns and their CSS rules deleted. shared.jsx\'s &lt;Chip&gt; gains a slot API: leadingDot / leadingIcon / categoryBubble, then label / value / +add / −sub / trailingSuffix, plus iconOnly / dim / mono / shape / size modifiers.',
        '<strong>Category bubble icon glyph.</strong> Q / D / I / C render as a 14 px filled circle with a knockout-white letter (designed icon, not a raw abbreviation). Fixed color map (Q=info, D=warn, I=err, C=idle) and fixed order (Q→D→I→C). The critique-pane filter row is the canonical legend.',
        '<strong>Never-bare status.</strong> Every completed timeline card carries a right-aligned status chip — running / ✓ agreed / ✓ / queued.',
        '<strong>Provider + activity split.</strong> The combined <code>.qref qref-full</code> span is replaced by two adjacent chips — <span class="chip tone-claude no-dot"><span class="chip-label">Claude</span></span> and <span class="chip mono tone-neutral no-dot">turn 1</span>.',
        '<strong>Cross-pane chip jumps.</strong> Clicking a category chip on a timeline turn card fires a <code>dr-critique-jump</code> event; the critique pane applies the matching filter and scrolls into view.',
        '<strong>Phase-header chip cluster.</strong> Each visible phase header carries a right-aligned aggregate-across-both-agents category-summary chip cluster.',
        '<strong>Vocabulary cleanup.</strong> Strict per-spec removal of the legacy <code>claim</code> data path. <code>\'conceded\'</code>, <code>\'answered\'</code>, <code>\'noted\'</code>, <code>\'ghosted\'</code>, <code>\'repair\'</code>, legacy abbreviations <code>QCR1</code> / <code>OQ</code> / <code>BD</code> / <code>OI</code> all gone.',  // spec-0119:vocab-ok
        '<strong>Lifecycle-verbs.js helper</strong> mirrors <code>contract/lifecycle.py:TRANSITIONS</code>; a cross-language sync test enforces it.',
        '<strong>Backend untouched.</strong> No edits to <code>contract/</code>, <code>orchestrator/</code>, <code>protocol/</code>, or <code>events/</code>.',
      ],
      screenshots: [
        { path: '/changelog-shots/1.4.0/critique-pane-filter-row.dark.png',
          alt: 'critique-pane chip-only filter legend',
          caption: 'chip-only filter legend (canonical category vocabulary)' },
        { path: '/changelog-shots/1.4.0/timeline-card-header.dark.png',
          alt: 'timeline turn card header',
          caption: 'provider + turn + status chips' },
        { path: '/changelog-shots/1.4.0/phase-header-chip-cluster.dark.png',
          alt: 'phase-header chip cluster',
          caption: 'aggregate Q/D/I/C across both agents' },
      ],
    },
    {
      version: '1.3.0',
      date: '2026-05-20',
      bump: 'MINOR',
      specs: ['0118'],
      specPath: '/specs/0118-deep-research-consumption-and-cost-tracking.md',
      summary: 'Consumption tab redesign + canonical-piece aggregation + per-piece proportional cost tracking.',
      items: [
        '<strong>Canonical-piece keys</strong> replace the legacy 7-key vocabulary (brief / d1 / d2 / plan / hist / draft / histp). Each per-turn TurnEnded event\'s promptPieces dictionary now keys by spec-0117 artifact registry IDs.',
        '<strong>Per-phase grouping rules (NORMATIVE).</strong> Always-separate rows: user_prompt + System prompt aggregate. Phase-specific separate rows include phase1.claude / phase1.openai (P2/P3), all_p2_turns (P3), current_draft + prior_turns.phase4 (P4).',
        '<strong>Total bar shows exact billed numbers.</strong> Tokens + cost = exact API-billed values. The cache-reuse stripe (45° overlay at 0.5 opacity) renders over the cache_read_tokens proportion.',
        '<strong>Per-piece cost is proportional.</strong> pieceCost = (pieceTokens / billedInputTokens) × totalInputCost. Tooltip annotates <code>(proportional)</code> to flag the heuristic.',
        '<strong>System prompt aggregate.</strong> Per-phase system.task.* + prior_turns.* + ledger.standing_items + closeout.request rolled into a single "System prompt" row with hover tooltip showing the per-sub-artifact breakdown.',
        '<strong>Collapsed vs unfolded card.</strong> Collapsed: single "Total tokens" bar with <code>&lt;tokens&gt;t · $&lt;cost&gt;</code>, cache-reuse meta line. Unfolded: 3-column grid per row (description · bar · tokens·cost).',
      ],
      screenshots: [
        { path: '/changelog-shots/1.3.0/cost-card-collapsed.dark.png',
          alt: 'collapsed cost card',
          caption: 'collapsed: total bar with cache-reuse stripe' },
        { path: '/changelog-shots/1.3.0/cost-card-unfolded.dark.png',
          alt: 'unfolded cost card',
          caption: 'unfolded: per-piece rows + System prompt tooltip' },
      ],
    },
    {
      version: '1.2.0',
      date: '2026-05-20',
      summary: 'Spec 0117 -- canonical artifact registry, Deep Research how-it-works diagram, and display-name propagation across the UI.',
      items: [
        'New artifact registry at contract/artifacts.py: ArtifactKind enum, ArtifactDef dataclass, 33-entry REGISTRY tuple, display_name() / is_known() / kind_of(). Single source of truth for every artifact name surfaced to the user.',
        'Hand-authored Deep Research pipeline SVGs bundled under /diagrams/ (light + dark variants). The how-it-works "View full process map" panel now embeds the variant matching the active theme; toggling the theme swaps the SVG via a MutationObserver on body.classList.',
        'JS-side registry mirror at static/artifacts.jsx (window.DrArtifacts.displayName / isKnown / truncateTitle). A pytest sync test parses both registries and fails CI if Python and JS drift apart.',
        'Display-name propagation: every modal header in run-detail.jsx resolves through the registry ("Negotiation turn · Claude · round 3", "Claude\'s research plan", "Current draft (latest version) · drafted by Claude").',
        'CI drift guard: a pytest scans src/dual_research/ for string literals matching the registry\'s ID prefixes and fails if any unregistered ID slips in.',
      ],
    },
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
      ],
    },
    {
      version: '0.67.0',
      date: '2026-05-18',
      summary: 'Agent Input tab rework -- renamed, reordered to first position, structural improvements with CollapsibleSection and Markdown rendering.',
      items: [
        '"Input" tab renamed to "Agent Input" across all modal contexts.',
        'Agent Input now appears first in modal tab order, before Content.',
        'Entry ordering: System Prompt first (collapsed), User Prompt second (expanded), then remaining entries.',
        'Input entries now use the CollapsibleSection primitive for consistent disclosure UX.',
        'Input piece bodies render via Markdown instead of raw preformatted text.',
      ],
    },
    {
      version: '0.66.0',
      date: '2026-05-18',
      summary: 'Critique detail unification -- disagreement cards now use QuestionThread-style turns, Issue/Comment bodies render Markdown, new QuoteCallout primitive.',
      items: [
        'Disagreement detail rebuilt: progression entries now render as agent turn cards with action chips instead of vertical rail.',
        'QuestionThread extended with kind="disagreement" for unified turn-card rendering across questions and disagreements.',
        'Issue and Comment bodies now render via Markdown -- bold, italic, blockquotes, and code display correctly.',
        'New QuoteCallout primitive for styled quote fields on critique cards (left border + italic + muted background).',
      ],
    },
    {
      version: '0.65.0',
      date: '2026-05-18',
      summary: 'Critique pane structural pass -- filter strip overflow fix, Phase 4 Issues/Comments split, three-sentence summary, disabled-Drift UX.',
      items: [
        'Filter strip no longer clips the last tab: PaneToolbar expands to fit multi-row filter strips.',
        'Kind-axis filter row anchored left, agent+status row centered with tighter spacing.',
        'Phase 4 Issues and Comments render in their own collapsible sections instead of mixing into DRIFT/OPEN/RESOLVED.',
        'Summary tab opens with a generated three-sentence verdict: sentiment, qualitative breakdown, and drift note.',
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
        'PhaseRail completed-phase labels now render in green (--ok) instead of dim gray.',
        'Critique pane DRIFT/OPEN/RESOLVED sections are now collapsible with the same disclosure pattern.',
      ],
    },
    {
      version: '0.63.0',
      date: '2026-05-18',
      summary: 'Run-detail header restructure -- equal-width agent strips, blocking banner removed, phase tabs with structured chip clusters.',
      items: [
        'AgentStrip pills now share width equally via flex: 1 1 0 -- no more lopsided pills.',
        'Vertical padding reduced from var(--s-2) to 4px for a denser agent strip.',
        'Blocking-item callout banner removed -- the "N open . M ghosted" bar is gone. Same info available in critique pane.',
        'Phase tabs restructured: each tab shows P2 Negotiate 26 questions 10 disagreements instead of cramped notation.',
      ],
    },
    {
      version: '0.62.0',
      date: '2026-05-18',
      summary: 'Run-list & chrome polish -- uniform status pills, structured info chips, cohesive chrome controls.',
      items: [
        'Status pills now have a fixed 88px min-width with centered text -- all statuses render at the same width.',
        'Run-list header info line replaced with structured Chip instances.',
        'Chrome tabs (All runs, Compare, Search) now use consistent size="sm" for uniform visual weight.',
        'ConnectionPill flattened from two-line indicator to a single-line chip.',
        'AppVersionChip restyled to use the Chip primitive. DesignLanguageButton restyled to use Tab primitive.',
      ],
    },
    {
      version: '0.61.0',
      date: '2026-05-18',
      summary: 'Brand-icon system + Design-page DNA reskin -- official brand marks everywhere agents are identified.',
      items: [
        'New BrandMark primitive renders official Anthropic sunburst (Claude) and OpenAI hexagonal rosette (GPT).',
        'Agent-icon migration: AgentIcon, AgentStrip, and CodeCluster agent chips now use the brand SVG paths.',
        'Run-list dual-color gradient square replaced with two composed BrandMark glyphs.',
        'Design Language page restructured as a curated DNA one-pager.',
      ],
    },
    {
      version: '0.60.0',
      date: '2026-05-18',
      summary: 'Chip vocabulary + code-cluster expansion -- full-word labels replace cryptic codes.',
      items: [
        'New parseCodeId utility + CodeCluster primitive. Critique public IDs now render as structured chip clusters.',
        'Stats chips expanded: "+6 Cl" becomes "+6 claims", "+1 I -1" becomes "+1 issue -1".',
        'Disagreement status labels: arrow notation replaced with "conceded by Claude" / "conceded by GPT".',
        'Output bar labels: slot codes removed, replaced with descriptive "feeds Claude\'s Phase 1 draft".',
      ],
    },
    {
      version: '0.59.0',
      date: '2026-05-17',
      summary: 'Onboarding flow + landing demo capsule -- final design-system arc spec.',
      items: [
        '3-screen onboarding carousel for first-time users.',
        'Auth-free landing page now shows a read-only demo capsule of a real research run.',
        'Onboarding completion persisted to localStorage. Skip or complete to dismiss.',
        'Design-system migration arc complete (SPEC-0050 through SPEC-0061).',
      ],
    },
    {
      version: '0.58.0',
      date: '2026-05-17',
      summary: 'Cross-run dashboards -- /compare + /search.',
      items: [
        'Two new surfaces: a cross-run search dashboard and a two-run side-by-side comparison view.',
        'Cross-run search (#/search): type to search across all runs by topic, brief content, and final documents.',
        'Compare runs (#/compare): select any two runs from dropdown pickers. Synced-scroll side-by-side panels.',
        'Chrome bar gains Compare and Search tabs.',
      ],
    },
    {
      version: '0.57.0',
      date: '2026-05-17',
      summary: 'Keyboard contract + shortcuts overlay + search palette.',
      items: [
        'Global keyboard contract wired at the document level.',
        'Press ? to open a shortcuts overlay listing every keyboard binding by context.',
        'Press Cmd+K (or Ctrl+K) to open a search palette.',
        'Existing / shortcut for focusing run-list search preserved.',
      ],
    },
    {
      version: '0.56.0',
      date: '2026-05-17',
      summary: 'Modal primitive + RoundScrubber + provider-symmetric SourceCard + sub-tab migration.',
      items: [
        'CSS-class-backed Modal replaces the inline-styled modal. Agent-color left border, theme-aware backdrop, focus trap.',
        'RoundScrubber at the bottom of split modals. Walk through negotiation rounds without closing the modal.',
        'Provider-symmetric SourceCard: Anthropic and OpenAI web search results now render identically.',
        'All modal sub-tabs migrated to the TabGroup line variant.',
      ],
    },
    {
      version: '0.55.0',
      date: '2026-05-17',
      summary: 'Timeline + critique restructure -- PhaseRail, ChipCluster, 3-axis filter, DriftCluster, Summary enhancement, CardHeadline migration.',
      items: [
        'Sticky PhaseRail down the timeline pane left edge with click-to-scroll navigation.',
        'ChipCluster discipline: chip rows that exceed 5 items collapse into a +N overflow button.',
        'Three-axis critique filter: filter by kind, agent, and status with AND logic for precise drill-down.',
        'DriftCluster: ghosted items now render in a dedicated Drift group above Open and Resolved.',
      ],
    },
    {
      version: '0.54.0',
      date: '2026-05-17',
      summary: 'Run detail header restructure + chrome unification + ActiveRunChip + blocking callout.',
      items: [
        'Chrome bar right cluster unified: HowItWorksLink migrated to Tab primitive.',
        'Run-detail header restructured with equal-row padding. Drafter callout pill with agent-tinted Chip + icon.',
        'Blocking-item callout bar between header and content.',
        'Timeline agent pills migrated to the design-system AgentStrip primitive.',
      ],
    },
    {
      version: '0.53.0',
      date: '2026-05-17',
      summary: 'Run list rework -- sortable columns, attention promotion, search, URL state.',
      items: [
        'Sortable columns: click any column header to toggle ascending/descending sort.',
        'Attention-first section: errored and deadlocked runs surface at the top of the list.',
        'Search input in the header bar. Press / from anywhere on the page to jump to search.',
        'Visual attention borders: errored runs get a red left border, deadlocked runs amber.',
      ],
    },
    {
      version: '0.52.0',
      date: '2026-05-17',
      summary: 'QuestionThread + QuestionRef primitives — AP-01 enforcement.',
      items: [
        'QuestionThread: vertical turn-by-turn conversation timeline for critique items.',
        'QuestionRef: decoded reference replaces legacy cryptic Q-g-r1-04 database keys.',
        'Question cards now expand into full QuestionThread views.',
        'CardHeadline for questions shows decoded number (01) instead of raw database key.',
      ],
    },
    {
      version: '0.51.0',
      date: '2026-05-17',
      summary: 'Tab system (3 variants) + table header distinction.',
      items: [
        'Unified Tab primitive with three variants: default bordered pill, tabs-line, tabs-solid.',
        'Critique pane phase buttons and filter chips now render via the new tabs-solid segmented control.',
        'Run-list filter strip migrated to Tab with leading dot + filterTone color classes + count badges.',
        'Table headers now visually distinct from body rows.',
      ],
    },
    {
      version: '0.50.0',
      date: '2026-05-17',
      summary: 'Primitive vocabulary — Button, StatusBadge, Chip, RunIDChip, Card, AgentStrip, segmented ThemeToggle.',
      items: [
        'New components.css lands the V1 component classes on top of SPEC-0050\'s tokens + base.',
        'Five legacy primitives → three: StatusBadge (state), Chip (data), RunIDChip (identity).',
        'ThemeToggle restored to segmented with sliding thumb.',
        'AgentStrip min-width 480 → 320.',
        'Cache-bust query strings added to every local stylesheet and JSX script in index.html.',
      ],
    },
    {
      version: '0.49.0',
      date: '2026-05-17',
      summary: 'Consumption tab — content-vs-billing split, output bar, cross-turn slot naming.',
      items: [
        'Card headline now reads "60kt seen · 411kt billed · 7.2kt out" with a "× 7 reuse" chip when there\'s measurable cache amplification.',
        'Per-piece sub-bars sized to raw content heuristic counts.',
        'New OutputBar in the expanded card, colored by the destination input slot.',
        'Cost cluster gains the output split: Input / Output / Web search / Total.',
      ],
    },
    {
      version: '0.48.1',
      date: '2026-05-17',
      summary: 'CI fixture check-in — partner-vetting run committed so tests.yml passes on CI runners.',
      items: ['Hotfix between SPEC-0050 and SPEC-0052. Pure ops change; no UI behaviour change.'],
    },
    {
      version: '0.48.0',
      date: '2026-05-17',
      summary: 'Design-system foundation — new fonts, retuned contrast, MDI icons, no emoji, focus ring, reduced-motion contract.',
      items: [
        'IBM Plex Sans handles UI chrome + data; IBM Plex Serif handles agent-produced prose.',
        'Foreground tier brightened in dark mode and darkened in light to clear WCAG-AA at 12 px.',
        'Global :focus-visible ring (2 px --info at 2 px offset) lands in base.css.',
        '@media (prefers-reduced-motion: reduce) forces all durations ≤ 1 ms.',
        'Material Design Icons via new icons.jsx (~60 MDI icons inlined as path data).',
        '13 emoji swept across 4 surfaces.',
      ],
    },
    {
      version: '0.47.0',
      date: '2026-05-17',
      summary: 'Daily reconciliation cron, powered by Supabase-source run-cost data.',
      items: [
        '`reconcile-costs` learned a `--source supabase` flag.',
        'GitHub Actions daily cron at 02:00 UTC.',
        'Anthropic side stays graceful-degraded — admin keys still unavailable in this org\'s Console UI.',
      ],
    },
    {
      version: '0.46.0',
      date: '2026-05-17',
      summary: 'Always-on cost verification against provider invoices.',
      items: [
        'New `dual-research reconcile-costs` CLI compares local metrics.json totals against the providers\' billing APIs.',
        'Each provider\'s admin key is independently optional.',
        'New `<ReconcileChip>` in the run-detail header.',
        'Consumption-tab cards gain a "Provider-billed" line when reconciled.',
        'metrics.json now records a pricing_version string.',
      ],
    },
    {
      version: '0.45.0',
      date: '2026-05-17',
      summary: 'Run-detail resilience + repair-turn visibility.',
      items: [
        'Run-detail page no longer crashes on historical runs that reached `completed` without a drafter.',
        'Finalize path hardened against the resume scenario where phase2_outcome is None on disk.',
        'Phase 4 protocol-repair turns now appear as their own cards on the Consumption tab.',
        'Per-turn key on the wire gains a _repair suffix for sibling labels.',
      ],
    },
    {
      version: '0.44.0',
      date: '2026-05-17',
      summary: 'Critique panel + Summary + Consumption rework + design unification.',
      items: [
        'Critique pane header restructured. Phase buttons primary navigation; count cluster right-aligned.',
        'Per-phase filter chips are context-aware (Phase 2 vs Phase 4 kinds differ).',
        'Critique cards render human-readable headlines instead of cryptic internal IDs.',
        'Summary tab redesigned as per-kind, per-model tables.',
        'Consumption tab rebuilt as single-row cards.',
      ],
    },
    {
      version: '0.43.0',
      date: '2026-05-17',
      summary: 'Full-view shell standardisation + model pill layout.',
      items: [
        'Tabs on every full-view modal now render in a canonical order: Content | Input | Web Search | Sources | Files.',
        'Input full-view drops the "not used in this turn" rows.',
        'Side-by-side modals now use equal-width columns.',
        'Timeline-header model pills (Claude, GPT) are now equal-width.',
      ],
    },
    {
      version: '0.42.0',
      date: '2026-05-17',
      summary: 'Turn-input semantics + per-turn badge redesign + side-by-side framing.',
      items: [
        'Per-turn count chips redesigned: explicit +raised / −resolved per kind.',
        'The per-turn `negotiating` / `reviewing` status pill is gone.',
        'Side-by-side modal left pane gets phase-aware document tabs.',
        'Phase 1 plan-draft modal gains a structured-items strip above the draft body.',
      ],
    },
    {
      version: '0.41.0',
      date: '2026-05-17',
      summary: 'Cross-round ledger + standing-items input + conservative convergence.',
      items: [
        'The orchestrator now maintains an authoritative cross-round ledger of every claim / question / disagreement / issue / comment.',
        'Round-N (N≥2) prompts now include a `## Standing items from prior rounds` section built from the ledger.',
        'Convergence is now conservative: a phase terminates only when both the agent self-counters AND the system-derived ledger agree the open-set is empty.',
        'Kill-switch built in: set DR_LEDGER_MODE=legacy in the environment to roll back.',
      ],
    },
    {
      version: '0.40.0',
      date: '2026-05-17',
      summary: 'Critique data integrity — Phase 1 sections parsed, badges reconcile, markdown rendering fixed.',
      items: [
        'Phase 1 plan-draft cards now show real chip counts. The parser learned to recognise Phase 1 sections.',
        'Phase 2 round-1 content re-categorised from `disagreement` to `claim`.',
        'Timeline chip counts no longer trust the agent\'s self-counters as source of truth.',
        'Critique header math reconciles.',
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

  // ─── Section list (drives the side menu) ──────────────────────
  const HIW_SECTIONS = [
    { id: 'hiw-overview',  label: 'Protocol overview' },
    { id: 'hiw-p0',        label: 'Phase 0 — Input' },
    { id: 'hiw-p1',        label: 'Phase 1 — Research plan' },
    { id: 'hiw-p2',        label: 'Phase 2 — Negotiate plan' },
    { id: 'hiw-p3',        label: 'Phase 3 — Draft' },
    { id: 'hiw-p4',        label: 'Phase 4 — Review draft' },
    { id: 'hiw-modal',     label: 'How turns are reviewed' },
    { id: 'hiw-items',     label: 'Item taxonomy & categories' },
    { id: 'hiw-lifecycle', label: 'Item lifecycle' },
    { id: 'hiw-converge',  label: 'Convergence & escape hatches' },
    { id: 'hiw-cost',      label: 'Cost & consumption' },
  ];

  // ─── Theme-aware diagram embed ────────────────────────────────

  function useThemeMode() {
    const [isLight, setIsLight] = React.useState(() =>
      typeof document !== 'undefined' && document.body.classList.contains('light')
    );
    React.useEffect(() => {
      if (typeof document === 'undefined') return;
      const obs = new MutationObserver(() => {
        setIsLight(document.body.classList.contains('light'));
      });
      obs.observe(document.body, { attributes: true, attributeFilter: ['class'] });
      return () => obs.disconnect();
    }, []);
    return isLight ? 'light' : 'dark';
  }

  function HiwDiagram({ name, alt }) {
    const variant = useThemeMode();
    return (
      <div className="hiw-diagram">
        <img
          src={`/diagrams/how-it-works/${name}.${variant}.svg?v=0121a`}
          alt={alt}
          loading="lazy"
        />
      </div>
    );
  }

  // ─── Collapsible section with localStorage persistence ────────

  function CollapsibleSection({ id, persistKey, defaultOpen, renderTitle, title, children }) {
    const storageKey = persistKey ? `hiw:cs:${persistKey}` : null;
    const [open, setOpen] = React.useState(() => {
      if (!storageKey) return !!defaultOpen;
      try {
        const stored = localStorage.getItem(storageKey);
        if (stored === '1') return true;
        if (stored === '0') return false;
      } catch (e) { /* ignore */ }
      return !!defaultOpen;
    });
    React.useEffect(() => {
      if (!storageKey) return;
      try { localStorage.setItem(storageKey, open ? '1' : '0'); } catch (e) { /* ignore */ }
    }, [open, storageKey]);

    return (
      <section
        id={id}
        className={'hiw-sec cs-section' + (open ? ' is-open' : '')}
      >
        <div
          className="cs-header"
          role="button"
          tabIndex={0}
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setOpen((o) => !o);
            }
          }}
        >
          <span className="cs-chevron" aria-hidden="true">▶</span>
          <span className="cs-title">
            {renderTitle ? renderTitle() : title}
          </span>
        </div>
        <div className="cs-body">{open ? children : null}</div>
      </section>
    );
  }

  // ─── Chip primitives (CSS-only — uses canonical spec-0119 classes) ─

  function BrandSwatch() {
    // currentColor-driven mark; the .chip.tone-claude / .tone-gpt
    // background + foreground tokens drive the actual color.
    return (
      <svg viewBox="0 0 16 16" fill="currentColor" width="12" height="12" aria-hidden="true">
        <circle cx="8" cy="8" r="6" />
      </svg>
    );
  }

  function CategoryChip({ letter, label, value }) {
    const tone = { Q: 'info', D: 'warn', I: 'err', C: 'idle' }[letter];
    return (
      <span className={`chip tone-${tone} no-dot`}>
        <span className="cat-bubble">{letter}</span>
        <span className="chip-label">{label}</span>
        {value != null && <span className="chip-value">{value}</span>}
      </span>
    );
  }

  function ProviderChip({ provider, label }) {
    const tone = provider === 'claude' ? 'claude' : 'gpt';
    const displayLabel = label || (provider === 'claude' ? 'Claude' : 'GPT');
    return (
      <span className={`chip tone-${tone} no-dot`}>
        <span className="chip-leading-icon"><BrandSwatch /></span>
        <span className="chip-label">{displayLabel}</span>
      </span>
    );
  }

  function ModChip({ text }) {
    return <span className="chip mono tone-neutral no-dot">{text}</span>;
  }

  // ─── Input / output list rows ─────────────────────────────────

  function InputRow({ id, tone, name, note }) {
    const toneClass =
      tone === 'ok'     ? 'tone-ok'     :
      tone === 'claude' ? 'tone-claude' :
      tone === 'gpt'    ? 'tone-gpt'    : 'tone-neutral';
    return (
      <li>
        <span className={`chip mono chip-square ${toneClass} no-dot`}>{id}</span>
        {name && <span className="hiw-input-name">{name}</span>}
        {!name && <span className="hiw-input-name" />}
        {note && <span className="hiw-input-note">{note}</span>}
      </li>
    );
  }

  // ─── Per-phase section template (sections 2–6) ────────────────

  function PhaseSection({ phase }) {
    return (
      <CollapsibleSection
        id={phase.anchor}
        persistKey={phase.anchor}
        renderTitle={() => (
          <span className="hiw-section-title">
            {phase.title}
            <ModChip text={phase.cap} />
            <ModChip text={phase.shape} />
          </span>
        )}
      >
        <p className="lede">{phase.lede}</p>

        <div className="crit-section-title">Inputs</div>
        <ul className="hiw-input-list">
          {phase.inputs.map((i, idx) => <InputRow key={idx} {...i} />)}
        </ul>

        <div className="crit-section-title">Allowed categories</div>
        <div className="chip-row">
          {phase.categories.length === 0
            ? <span className="hiw-muted">{phase.categoriesNote}</span>
            : phase.categories.map((c) =>
                <CategoryChip key={c.letter} letter={c.letter} label={c.label} />
              )}
        </div>

        <div className="crit-section-title">Convergence condition</div>
        <p>{phase.convergence}</p>

        {phase.diagramName && (
          <React.Fragment>
            <HiwDiagram name={phase.diagramName} alt={`${phase.title} — input composition`} />
            <p className="hiw-caption">{phase.diagramCaption}</p>
          </React.Fragment>
        )}

        <div className="crit-section-title">Outputs</div>
        <ul className="hiw-output-list">
          {phase.outputs.map((o, idx) => <InputRow key={idx} {...o} />)}
        </ul>

        {phase.footer}
      </CollapsibleSection>
    );
  }

  // ─── Per-phase data ───────────────────────────────────────────

  const PHASES = [
    {
      anchor: 'hiw-p0',
      title: 'Phase 0 — Input',
      cap: 'soft 2 / hard 4 rounds',
      shape: 'parallel',
      lede: "Both agents read the user's brief and raise questions or disagreements about scope, framing, missing inputs, or the intended audience. Round 1 is a first-look critique; round 2+ both addresses the counterpart's raised items and ratifies (or counter-argues) the responses. The phase converges on an agreed interpretation — scope, approach, and any items that should carry forward into later phases.",
      inputs: [
        { id: 'system.preamble',       tone: 'neutral', name: 'shared system preamble' },
        { id: 'system.task.input',     tone: 'neutral', name: 'phase-0 task instructions' },
        { id: 'user_prompt',           tone: 'neutral', name: "the user's brief (message + attachments)" },
        { id: 'prior_turns.phase0',    tone: 'neutral', name: "both agents' turns from prior rounds, perspective-flipped", note: 'round ≥ 2' },
        { id: 'ledger.standing_items', tone: 'neutral', name: 'open items raised so far', note: 'round ≥ 2' },
        { id: 'closeout.request',      tone: 'neutral', name: 'orchestrator-injected closeout instruction', note: 'closeout rounds only' },
      ],
      categories: [
        { letter: 'Q', label: 'Questions' },
        { letter: 'D', label: 'Disagreements' },
      ],
      convergence: 'Both agents emit STATUS: AGREED in the same round AND every raised item is in a terminal state (resolved, acknowledged, withdrawn, or capped) AND both agents emit the AGREED_INTERPRETATION block in matching form.',
      diagramName: '02-phase-inputs',
      diagramCaption: 'In Phase 0, system.task.input fills the system-task row; carry-forward inputs are absent in round 1. From round 2, prior_turns.phase0 + ledger.standing_items activate (dashed rows in the diagram).',
      outputs: [
        { id: 'phase0.<agent>.r<N>',             tone: 'neutral', name: 'per-round turn artifact (one per agent per round)' },
        { id: 'phase0.agreement.interpretation', tone: 'ok',      name: 'emitted on AGREED' },
      ],
    },
    {
      anchor: 'hiw-p1',
      title: 'Phase 1 — Research plan',
      cap: 'one-shot',
      shape: 'parallel',
      lede: "Each agent writes a complete research plan + thesis, independently. No operation blocks — agents don't raise items in this phase. Inline [V] / [U] source tagging is required on prose claims. The phase ends when both plans are present.",
      inputs: [
        { id: 'system.preamble',                  tone: 'neutral' },
        { id: 'system.task.research_plan',        tone: 'neutral', name: 'phase-1 task instructions' },
        { id: 'user_prompt',                      tone: 'neutral' },
        { id: 'phase0.agreement.interpretation',  tone: 'ok',      name: 'carry-forward from Phase 0' },
      ],
      categories: [],
      categoriesNote: '(none — this is a production phase, not a negotiation phase)',
      convergence: 'Both phase1.claude and phase1.openai artifacts present and well-formed.',
      diagramName: '02-phase-inputs',
      diagramCaption: 'Phase 1 has no round-conditional inputs (one-shot) and no agreement-emitted output — the dashed rows and ok-green output pill in the diagram are absent here.',
      outputs: [
        { id: 'phase1.claude',  tone: 'neutral', name: "Claude's research plan + thesis (Summary · Thesis · Detailed findings · Sources)" },
        { id: 'phase1.openai',  tone: 'neutral', name: "GPT's research plan + thesis (same shape)" },
      ],
    },
    {
      anchor: 'hiw-p2',
      title: 'Phase 2 — Negotiate plan',
      cap: 'soft 4 / hard 8 rounds',
      shape: 'parallel',
      lede: "Each agent reads both phase-1 plans (their own and the counterpart's). They raise questions and disagreements about scope, methodology, source quality, missing angles, and structure. The phase converges on an agreed plan — a section-by-section outline + the key claims each section will make — plus a drafter selection (which agent will write the unified document in Phase 3).",
      inputs: [
        { id: 'system.preamble',                  tone: 'neutral' },
        { id: 'system.task.plan_negotiation',     tone: 'neutral', name: 'phase-2 task instructions' },
        { id: 'user_prompt',                      tone: 'neutral' },
        { id: 'phase0.agreement.interpretation',  tone: 'ok',      name: 'carry-forward' },
        { id: 'phase1.claude',                    tone: 'claude',  name: "Claude's research plan" },
        { id: 'phase1.openai',                    tone: 'gpt',     name: "GPT's research plan" },
        { id: 'prior_turns.phase2',               tone: 'neutral', note: 'round ≥ 2' },
        { id: 'ledger.standing_items',            tone: 'neutral', note: 'round ≥ 2' },
        { id: 'closeout.request',                 tone: 'neutral', note: 'closeout rounds' },
      ],
      categories: [
        { letter: 'Q', label: 'Questions' },
        { letter: 'D', label: 'Disagreements' },
      ],
      convergence: 'Both AGREED + every raised item terminal + both emit the AGREED_PLAN block in matching form + both emit a matching DRAFTER: line (tiebreak resolves disagreements per tiebreak.pick_drafter).',
      diagramName: '02-phase-inputs',
      diagramCaption: 'Phase 2 is the densest-input phase: both research plans (in agent-tinted pills) plus the agreed-interpretation carry-forward plus round-conditional inputs from round 2 onward. Outputs include the agreement-emitted plan + drafter pair (ok-green) when convergence lands.',
      outputs: [
        { id: 'phase2.<agent>.r<N>',         tone: 'neutral', name: 'per-round turn artifact' },
        { id: 'phase2.agreement.plan',       tone: 'ok',      name: 'section-by-section outline + key claims' },
        { id: 'phase2.agreement.drafter',    tone: 'ok',      name: 'which agent drafts in Phase 3' },
      ],
    },
    {
      anchor: 'hiw-p3',
      title: 'Phase 3 — Draft',
      cap: 'one-shot',
      shape: 'single drafter',
      lede: 'The drafter chosen in Phase 2 writes the unified document, section-by-section, following the agreed plan. The non-drafter agent does NOT run in this phase. The draft emits a "## Disagreements left open" section listing every Phase-2 disagreement that ended in acknowledged or capped (i.e. known but unresolved); same for "## Open questions".',
      inputs: [
        { id: 'system.preamble',                  tone: 'neutral' },
        { id: 'system.task.drafting',             tone: 'neutral' },
        { id: 'user_prompt',                      tone: 'neutral' },
        { id: 'phase0.agreement.interpretation',  tone: 'ok' },
        { id: 'phase1.claude',                    tone: 'claude' },
        { id: 'phase1.openai',                    tone: 'gpt' },
        { id: 'phase2.agreement.plan',            tone: 'ok' },
        { id: 'carry_forward.phase2',             tone: 'neutral', name: 'acknowledged / capped Phase 2 items' },
        { id: 'all_p2_turns',                     tone: 'neutral', name: 'every Phase 2 turn (concatenated)' },
      ],
      categories: [],
      categoriesNote: '(none)',
      convergence: 'Drafter emits the phase3.draft.v1 artifact.',
      outputs: [
        { id: 'phase3.draft.v1', tone: 'neutral', name: 'initial unified draft' },
      ],
    },
    {
      anchor: 'hiw-p4',
      title: 'Phase 4 — Review draft',
      cap: 'soft 4 / hard 8 rounds',
      shape: 'parallel',
      lede: 'Both agents read the current draft. Either may raise questions (Q), disagreements (D), issues (I — defects in the draft), or comments (C — non-defect improvements). The drafter may mid-phase revise via a "## Revised draft" section, which advances the draft_version pointer (v1 → v2 → …). The phase converges on an agreed draft acceptance — draft_version + draft_hash + a mutual endorsement.',
      inputs: [
        { id: 'system.preamble',          tone: 'neutral' },
        { id: 'system.task.review',       tone: 'neutral' },
        { id: 'user_prompt',              tone: 'neutral' },
        { id: 'current_draft',            tone: 'neutral', name: 'latest phase{3,4}.draft.v<N>' },
        { id: 'prior_turns.phase4',       tone: 'neutral', note: 'round ≥ 2' },
        { id: 'ledger.standing_items',    tone: 'neutral', note: 'round ≥ 2' },
        { id: 'closeout.request',         tone: 'neutral', note: 'closeout rounds' },
      ],
      categories: [
        { letter: 'Q', label: 'Questions' },
        { letter: 'D', label: 'Disagreements' },
        { letter: 'I', label: 'Issues' },
        { letter: 'C', label: 'Comments' },
      ],
      convergence: 'Both AGREED on the SAME draft_version + every raised item terminal + both emit the AGREED_DRAFT_ACCEPTANCE block matching on (draft_version, draft_hash).',
      outputs: [
        { id: 'phase4.<agent>.r<N>',                  tone: 'neutral', name: 'per-round turn artifact' },
        { id: 'phase4.draft.v<N>',                    tone: 'neutral', name: 'versioned draft (when drafter revises)' },
        { id: 'phase4.agreement.draft_acceptance',    tone: 'ok' },
      ],
      footer: (
        <div className="hiw-note" data-tone="ok">
          <span className="hiw-note__label">Finalize</span>
          <span className="chip mono tone-neutral no-dot" style={{ marginRight: 8 }}>programmatic</span>
          When Phase 4 converges, the orchestrator assembles <code>final.document</code> from the latest draft version, plus an <code>## Appendix — Unresolved items</code> section listing every item across the run that ended in <code>acknowledged</code> or <code>capped</code>. No LLM call.
        </div>
      ),
    },
  ];

  // ─── Section 1: Protocol overview ─────────────────────────────

  function ProtocolOverviewSection() {
    return (
      <CollapsibleSection id="hiw-overview" persistKey="overview" defaultOpen
        renderTitle={() => 'Protocol overview'}
      >
        <p className="lede">
          Dual Research runs two large language models — <strong>Claude</strong> and <strong>GPT</strong> — through a six-phase protocol on a single brief, in parallel where possible and one-after-the-other where the next phase needs the previous phase's output. Both agents see the same brief, the same prior turns, and the same ledger of unresolved items. The orchestrator is deterministic; the agents are not. A run ends with a single approved document and an audit trail of every claim, disagreement, and source.
        </p>
        <div className="hiw-tldr">
          <div className="dr-card"><div className="dr-card-body">
            <h4>Two agents, one document</h4>
            <p>Two providers research the same brief. They negotiate a plan, one of them drafts, both review. The output is one document — not two.</p>
          </div></div>
          <div className="dr-card"><div className="dr-card-body">
            <h4>Every claim has a source</h4>
            <p>Each agent cites the URLs it consulted. Every cited URL is checked against a recorded web-search event; fabricated sources are flagged with <span className="chip mono tone-err no-dot">⚠ unverified</span>.</p>
          </div></div>
          <div className="dr-card"><div className="dr-card-body">
            <h4>Orchestrator owns convergence</h4>
            <p>Agents propose to converge; the orchestrator enforces caps and closeout. No agent can extend a phase past its hard cap.</p>
          </div></div>
        </div>
        <HiwDiagram name="01-pipeline" alt="Full Dual Research protocol pipeline" />
        <p className="hiw-caption">Six phases, left to right. Phases 0, 1, 2, 4 run both agents in parallel; phase 3 runs one drafter. Phases 0 / 2 / 4 are multi-round (each round = one turn per agent + an orchestrator update step). The "Agreed interpretation", "Agreed plan + drafter", "Agreed draft acceptance" capsules are the artifacts each multi-round phase emits when both agents reach AGREED with zero non-terminal items.</p>
      </CollapsibleSection>
    );
  }

  // ─── Section 7: How turns are reviewed ────────────────────────

  function ModalAnatomySection() {
    return (
      <CollapsibleSection id="hiw-modal" persistKey="modal"
        renderTitle={() => 'How turns are reviewed'}
      >
        <p className="lede">
          Click any phase row on the timeline to open the turn modal. The modal has two panes: on the left, the <strong>artifact you're reviewing</strong> (the counterpart's prior turn, the converged draft, etc.) with sub-tabs to switch between adjacent artifacts. On the right, the <strong>items extracted from this turn</strong> — grouped by category, each card shows who raised it, what part of the source it anchors to, its title, its rationale, and (if the agent cited any) its sources.
        </p>
        <HiwDiagram name="07-modal-anatomy" alt="Turn-review modal anatomy" />
        <p className="hiw-caption">
          Left pane: artifact + sub-tabs. Right pane: category-grouped item cards in canonical Q → D → I → C order. Each card header begins with the <strong>provider</strong> chip, then the <strong>category</strong> chip, then the <strong>raised-in-r&lt;N&gt;</strong> chip, then (optional) <strong>Sources &lt;count&gt;</strong> chip. Body: Anchor → Title → Rationale → Sources.
        </p>

        <div className="crit-section-title">The left pane</div>
        <p>Sub-tabs let you compare adjacent artifacts. <code>Original</code> is the default; <code>Input</code> is one click away. The "Original" default flips per phase:</p>
        <table className="hiw-table">
          <thead><tr><th>Phase</th><th>"Original" default</th></tr></thead>
          <tbody>
            <tr><td>Phase 4</td><td>Current draft</td></tr>
            <tr><td>Phase 2, round ≥ 2</td><td>Other agent's prior turn</td></tr>
            <tr><td>Phase 2, round 1</td><td>Other agent's draft</td></tr>
          </tbody>
        </table>

        <div className="crit-section-title">The right pane</div>
        <p>
          Category-grouped panels. Each panel header is a <CategoryChip letter="Q" label="Questions" value={5} /> — the same Chip primitive that renders the critique-pane filter legend. Pre-0114 legacy runs render an additional <code>Claims</code> panel via a separate code path; new-protocol runs do not.
        </p>

        <div className="hiw-note">
          <span className="hiw-note__label">Why "Anchored to &lt;agent&gt;'s draft" instead of "Anchored to text"?</span>
          The anchor identifies <em>which artifact and where in it</em> the item refers to. Naming the source agent makes it unambiguous which pane to scan when reading the anchor.
        </div>
      </CollapsibleSection>
    );
  }

  // ─── Section 8: Item taxonomy & categories ────────────────────

  function ItemTaxonomySection() {
    return (
      <CollapsibleSection id="hiw-items" persistKey="items"
        renderTitle={() => 'Item taxonomy & categories'}
      >
        <p className="lede">
          Every structured item raised in any negotiation phase has a <strong>kind</strong>. There are four kinds; together they are the entire vocabulary. The kind is fixed at raise-time and never changes.
        </p>
        <HiwDiagram name="04-categories" alt="Category taxonomy and chip composition reference" />

        <table className="hiw-table">
          <thead><tr><th>Chip</th><th>Kind</th><th>Raisable in</th><th>Meaning</th></tr></thead>
          <tbody>
            <tr>
              <td><CategoryChip letter="Q" label="Question" /></td>
              <td>question</td>
              <td>
                <ModChip text="P0" />{' '}
                <ModChip text="P2" />{' '}
                <ModChip text="P4" />
              </td>
              <td><em>"I don't know; the other agent does or should research."</em></td>
            </tr>
            <tr>
              <td><CategoryChip letter="D" label="Disagreement" /></td>
              <td>disagreement</td>
              <td>
                <ModChip text="P0" />{' '}
                <ModChip text="P2" />{' '}
                <ModChip text="P4" />
              </td>
              <td><em>"I hold X; they hold Y; we differ on substance."</em></td>
            </tr>
            <tr>
              <td><CategoryChip letter="I" label="Issue" /></td>
              <td>issue</td>
              <td><ModChip text="P4" /> <strong>only</strong></td>
              <td><em>"The drafted document is defective in a specific way."</em></td>
            </tr>
            <tr>
              <td><CategoryChip letter="C" label="Comment" /></td>
              <td>comment</td>
              <td><ModChip text="P4" /> <strong>only</strong></td>
              <td><em>"Could be improved in a non-defect way."</em></td>
            </tr>
          </tbody>
        </table>

        <div className="crit-section-title">Why no <code>claim</code>?</div>
        <div className="hiw-note" data-tone="warn">
          <span className="hiw-note__label">retired</span>
          The <code>claim</code> kind was removed in spec 0114 (Deep Research protocol). The old <code>## Claims I expect the other agent might dispute</code> section is gone — the new prompts never ask for it. Disagreements that used to be raised pre-emptively as such are now raised reactively as <span className="chip tone-warn no-dot"><span className="cat-bubble">D</span></span> items in Phase 2 or Phase 4 when an agent actually objects. Pre-0114 runs in the archive still show a Claims panel via the legacy renderer; new runs do not.
        </div>

        <div className="crit-section-title">Chip composition rule</div>
        <p>Every chip-bearing card header reads, left-to-right: <strong>Provider → Activity → Category → Modifier → Status</strong>. Provider always first; status always right-aligned (and never bare). Categories in canonical Q → D → I → C order.</p>

        <div className="crit-section-title">Example: a resolved Phase-2 question card header</div>
        <div className="chip-row">
          <ProviderChip provider="claude" />
          <ModChip text="turn 3" />
          <CategoryChip letter="Q" label="Question" />
          <ModChip text="raised in r2" />
          <span className="chip tone-neutral no-dot">
            <span className="chip-label">Sources</span>
            <span className="chip-value">4</span>
          </span>
          <span className="chip tone-ok"><span className="chip-label">✓ resolved in r4</span></span>
        </div>
      </CollapsibleSection>
    );
  }

  // ─── Section 9: Item lifecycle ────────────────────────────────

  function ItemLifecycleSection() {
    return (
      <CollapsibleSection id="hiw-lifecycle" persistKey="lifecycle"
        renderTitle={() => 'Item lifecycle'}
      >
        <p className="lede">
          Once raised, an item moves through a small state machine. Six states, with named transitions. The orchestrator (not the agents) decides which state an item is in at the end of each round; agents propose, the orchestrator ratifies.
        </p>
        <HiwDiagram name="03-item-lifecycle" alt="Item lifecycle state machine" />

        <table className="hiw-table">
          <thead><tr><th>From → To</th><th>Verb chip</th><th>Actor</th><th>Notes</th></tr></thead>
          <tbody>
            <tr><td><code>(new) → open</code></td><td><span className="chip tone-info no-dot"><span className="chip-label">raised</span></span></td><td>raiser</td><td>Item enters <code>open</code> with an ID stamped by the orchestrator.</td></tr>
            <tr><td><code>open → addressed</code></td><td><span className="chip tone-info no-dot"><span className="chip-label">addressed</span></span></td><td>addressee</td><td>The other agent responds with <code>### ADDRESS &lt;id&gt;</code>.</td></tr>
            <tr><td><code>addressed → resolved</code></td><td><span className="chip tone-ok no-dot"><span className="chip-label">resolved</span></span></td><td>raiser</td><td>Terminal. Raiser ratifies the response.</td></tr>
            <tr><td><code>addressed → acknowledged_proposed</code></td><td><span className="chip tone-warn no-dot"><span className="chip-label">acknowledged</span></span></td><td>raiser</td><td>Not yet terminal — needs mutual handshake.</td></tr>
            <tr><td><code>acknowledged_proposed → acknowledged</code></td><td><span className="chip tone-warn no-dot"><span className="chip-label">acknowledged</span></span></td><td>both</td><td>Terminal when both have ACK'd.</td></tr>
            <tr><td><code>open / addressed → withdrawn</code></td><td><span className="chip tone-idle no-dot"><span className="chip-label">withdrawn</span></span></td><td>raiser</td><td>Terminal. Raiser drops the item with a stated reason.</td></tr>
            <tr><td><code>addressed → open</code></td><td><span className="chip tone-info no-dot"><span className="chip-label">raised again</span></span></td><td>raiser</td><td>Raiser counter-argues; item flips back to <code>open</code>.</td></tr>
            <tr><td><code>any → capped</code></td><td><span className="chip tone-err no-dot"><span className="chip-label">capped</span></span></td><td><strong>orchestrator</strong></td><td>Terminal. Closeout budget exhausted or hard cap reached.</td></tr>
          </tbody>
        </table>

        <div className="hiw-note" data-tone="warn">
          <span className="hiw-note__label">important</span>
          <strong>Rationale is mandatory at every transition.</strong> Every operation block (<code>RAISE</code>, <code>ADDRESS</code>, <code>RESOLVE</code>, <code>ACKNOWLEDGE</code>, <code>WITHDRAW</code>, counter) requires a <code>reason:</code> field with non-empty content. The validator rejects operations without it.
        </div>

        <div className="crit-section-title">Anchors</div>
        <p>Each item carries an <strong>anchor</strong> — a pointer to the part of the source artifact it refers to. Three formats:</p>
        <ul>
          <li><code>quote</code> — a verbatim ≤25-word span from the source. Most common.</li>
          <li><code>after</code> — a section heading from the source (<code>anchor_text: "## Methodology"</code>).</li>
          <li><code>none</code> — the item refers to the artifact as a whole.</li>
        </ul>

        <div className="crit-section-title">Evidence</div>
        <p>When an item's resolution turns on a factual claim, the agent must attach <code>EvidenceRecord</code> entries (URL, page title, search query, fetched-at, content excerpt). The orchestrator validates every cited URL against the recorded web-search events for that turn; fabricated sources are flagged with <span className="chip mono tone-err no-dot">⚠ unverified</span>.</p>
      </CollapsibleSection>
    );
  }

  // ─── Section 10: Convergence & escape hatches ─────────────────

  function ConvergenceSection() {
    return (
      <CollapsibleSection id="hiw-converge" persistKey="converge"
        renderTitle={() => 'Convergence & escape hatches'}
      >
        <p className="lede">
          Multi-round phases (P0, P2, P4) need a deterministic way to end. The default is <strong>organic convergence</strong>: both agents simultaneously emit <code>STATUS: AGREED</code> with zero non-terminal items. When that doesn't happen, three escape hatches engage in sequence — <strong>closeout → ghost cap → hard cap</strong> — to ensure every run terminates.
        </p>
        <HiwDiagram name="06-convergence" alt="Convergence and escape hatches" />

        <div className="crit-section-title">Organic convergence</div>
        <p>Both AGREED in the same round + every item terminal + matching agreement-artifact block.</p>

        <div className="crit-section-title">Closeout</div>
        <p>Triggered when both AGREED but non-terminal items remain. The next round is a <strong>closeout round</strong>: <code>RAISE</code> is forbidden; only <code>RESOLVE</code>, <code>ACKNOWLEDGE</code>, <code>WITHDRAW</code>, or counter on listed items. Each agent has a closeout budget of <strong>2 per phase</strong>.</p>

        <div className="crit-section-title">Ghost cap</div>
        <p>When an agent exhausts their closeout budget with items still non-terminal, those items auto-flip to <code>capped</code> with an orchestrator-generated rationale (<code>"ghost-capped — closeout budget exhausted with item still non-terminal"</code>). The phase converges via <code>via_ghost_cap: true</code>.</p>

        <div className="crit-section-title">Hard cap</div>
        <p>Independent ceiling per phase (<strong>P0 = 4, P2 = 8, P4 = 8</strong>). When the round counter hits the hard cap, every remaining non-terminal item flips to <code>capped</code>. The phase converges via <code>via_hard_cap: true</code>.</p>

        <div className="crit-section-title">Mutual-acknowledge handshake</div>
        <p><code>ACKNOWLEDGE</code> proposed by the raiser doesn't terminalize the item; it requires the other agent to also <code>ACKNOWLEDGE</code> (in the same or next round) before transitioning to terminal <code>acknowledged</code>. Until then it stays in <code>acknowledged_proposed</code>.</p>

        <div className="hiw-note">
          <span className="hiw-note__label">spec 0114</span>
          <strong>No partial convergence, no canonical-FSD synthesis, no stuck-AGREED promotion.</strong> The closeout → ghost cap → hard cap sequence is the only convergence-failure path.
        </div>
      </CollapsibleSection>
    );
  }

  // ─── Section 11: Cost & consumption ───────────────────────────

  function CostSection() {
    return (
      <CollapsibleSection id="hiw-cost" persistKey="cost"
        renderTitle={() => 'Cost & consumption'}
      >
        <p className="lede">
          Every model call has a token cost. The Consumption tab on each run breaks that cost down per phase and per turn. This section explains where the numbers come from and how the per-piece costs are computed.
        </p>
        <HiwDiagram name="05-cost-flow" alt="Cost calculation flow" />

        <div className="crit-section-title">Where the totals come from</div>
        <p>The <strong>Total bar</strong> on every cost card shows <code>billedInputTokens + billedOutputTokens</code> and the exact API-billed cost. These come straight from the provider response (Anthropic / OpenAI), unmodified.</p>

        <div className="crit-section-title">Where the per-piece costs come from</div>
        <p>The per-canonical-piece rows are computed proportionally:</p>
        <div className="hiw-code">pieceCost = (pieceTokens / billedInputTokens) × totalInputCost</div>
        <p>This is a heuristic — the API doesn't tell us which tokens belonged to which prompt piece. The tooltip on every per-piece row says <code>(proportional)</code> to flag this.</p>

        <div className="crit-section-title">The <code>System prompt</code> aggregate</div>
        <p>Every per-phase <code>system.task.*</code> artifact, plus <code>prior_turns.*</code>, <code>ledger.standing_items</code>, and <code>closeout.request</code>, are rolled into a single <strong>System prompt</strong> row to keep the per-piece table readable. The tooltip on the row shows the per-sub-artifact breakdown.</p>

        <div className="crit-section-title">Cache savings</div>
        <p>Anthropic prompt caching reuses tokens across turns within the 5-minute cache window. The Total bar renders a 45° diagonal stripe over the <code>cache_read_tokens</code> proportion at 0.5 opacity. The per-turn meta line reads e.g. <code>"3.5kt seen · 1.0kt billed (× 3.5 token reuse) · 980t out"</code>.</p>

        <div className="crit-section-title">Which canonical pieces appear where</div>
        <table className="hiw-table">
          <thead><tr><th>Piece</th><th>Phases</th><th>Always-present?</th></tr></thead>
          <tbody>
            <tr><td><code>user_prompt</code></td><td>every phase</td><td>yes</td></tr>
            <tr><td><code>System prompt</code> aggregate</td><td>every phase</td><td>yes</td></tr>
            <tr><td><code>phase0.agreement.interpretation</code></td><td>P1, P2, P3</td><td>yes (carry-forward)</td></tr>
            <tr><td><code>phase1.claude</code>, <code>phase1.openai</code></td><td>P2, P3</td><td>yes (both shown)</td></tr>
            <tr><td><code>phase2.agreement.plan</code></td><td>P3</td><td>yes</td></tr>
            <tr><td><code>all_p2_turns</code></td><td>P3</td><td>yes</td></tr>
            <tr><td><code>current_draft</code></td><td>P4</td><td>yes</td></tr>
            <tr><td><code>prior_turns.phase{0,2,4}</code></td><td>round ≥ 2 of that phase</td><td>conditional</td></tr>
            <tr><td><code>ledger.standing_items</code></td><td>round ≥ 2 of multi-round phases</td><td>conditional</td></tr>
            <tr><td><code>closeout.request</code></td><td>closeout rounds only</td><td>conditional</td></tr>
          </tbody>
        </table>

        <div className="crit-section-title">Models used</div>
        <div className="chip-row">
          <ProviderChip provider="claude" label="Claude Sonnet 4.6" />
          <ModChip text="default" />
        </div>
        <div className="chip-row">
          <ProviderChip provider="gpt" label="GPT-5.5" />
          <ModChip text="default" />
        </div>

        <div className="hiw-note" data-tone="idle">
          <span className="hiw-note__label">test tier</span>
          Internal runs use Haiku 4.5 + GPT-5-mini for ~10× cost reduction during development; production runs use the chips above.
        </div>
      </CollapsibleSection>
    );
  }

  // ─── Changelog ────────────────────────────────────────────────

  function ChangelogEntry({ entry, defaultOpen }) {
    const bumpTone = entry.bump === 'MAJOR' ? 'err' : entry.bump === 'MINOR' ? 'info' : 'ok';
    return (
      <CollapsibleSection
        id={`cl-${entry.version.replace(/\./g, '')}`}
        persistKey={`changelog:${entry.version}`}
        defaultOpen={defaultOpen}
        renderTitle={() => (
          <div className="changelog-head">
            <span className="chip mono tone-neutral no-dot">v{entry.version}</span>
            <span className="changelog-date">{entry.date}</span>
            <span className="changelog-summary">{entry.summary}</span>
            {entry.specs && entry.specs.map((s) =>
              <span key={s} className="chip mono chip-square tone-neutral no-dot">spec {s}</span>
            )}
            {entry.bump && <span className={`chip tone-${bumpTone}`}>{entry.bump}</span>}
          </div>
        )}
      >
        <div className="dr-card"><div className="dr-card-body">
          <div className="crit-section-title">What changed</div>
          <ul className="changelog-bullets">
            {entry.items.map((b, i) =>
              <li key={i} dangerouslySetInnerHTML={{ __html: b }} />
            )}
          </ul>
          {entry.screenshots && entry.screenshots.length > 0 && (
            <React.Fragment>
              <div className="crit-section-title">Screenshots</div>
              <div className="changelog-shots">
                {entry.screenshots.map((s, i) =>
                  <figure key={i}>
                    <img src={s.path} alt={s.alt} loading="lazy" />
                    <figcaption>{s.caption}</figcaption>
                  </figure>
                )}
              </div>
            </React.Fragment>
          )}
          {entry.specPath && (
            <div className="changelog-spec-link">
              <button
                type="button"
                className="md-btn md-btn--text md-btn--sm"
                onClick={() => window.open(entry.specPath, '_blank')}
              >Open spec ↗</button>
            </div>
          )}
        </div></div>
      </CollapsibleSection>
    );
  }

  function ChangelogList() {
    const [q, setQ] = React.useState('');
    const [bumpFilter, setBumpFilter] = React.useState(null);
    const counts = React.useMemo(() => {
      const c = { MAJOR: 0, MINOR: 0, PATCH: 0 };
      VERSION_NOTES.forEach((e) => { if (e.bump && c[e.bump] !== undefined) c[e.bump]++; });
      return c;
    }, []);
    const filtered = VERSION_NOTES.filter((e) => {
      if (bumpFilter && e.bump !== bumpFilter) return false;
      if (!q) return true;
      const blob = `${e.version} ${e.date} ${e.summary} ${(e.specs || []).join(' ')} ${e.items.join(' ')}`.toLowerCase();
      return blob.includes(q.toLowerCase());
    });
    return (
      <React.Fragment>
        <div className="cl-filter-row">
          <span
            className={`chip tone-info ${bumpFilter ? 'dim' : ''}`}
            data-active={!bumpFilter}
            role="button"
            tabIndex={0}
            onClick={() => setBumpFilter(null)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setBumpFilter(null); }}
          >
            <span className="chip-label">All</span>
            <span className="chip-value">{VERSION_NOTES.length}</span>
          </span>
          {['MAJOR', 'MINOR', 'PATCH'].map((b) => {
            const tone = b === 'MAJOR' ? 'err' : b === 'MINOR' ? 'info' : 'ok';
            return (
              <span
                key={b}
                className={`chip tone-${tone} ${counts[b] === 0 ? 'dim' : ''}`}
                data-active={bumpFilter === b ? 'true' : 'false'}
                role="button"
                tabIndex={0}
                onClick={() => setBumpFilter(bumpFilter === b ? null : b)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    setBumpFilter(bumpFilter === b ? null : b);
                  }
                }}
              >
                <span className="chip-label">{b}</span>
                <span className="chip-value">{counts[b]}</span>
              </span>
            );
          })}
          <span className="spacer" />
          <input
            type="search"
            className="hiw-search"
            placeholder="search…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="cl-list">
          {filtered.map((e, i) =>
            <ChangelogEntry key={e.version} entry={e} defaultOpen={i === 0 && !q && !bumpFilter} />
          )}
        </div>
      </React.Fragment>
    );
  }

  // ─── Main overlay component ───────────────────────────────────

  function HowItWorks({ open, onClose }) {
    const [view, setView] = React.useState('how');
    const triggerRef = React.useRef(null);

    React.useEffect(() => {
      if (!open) return;
      function onKey(e) {
        if (e.key === 'Escape') {
          e.stopPropagation();
          onClose();
        }
      }
      window.addEventListener('keydown', onKey, true);
      return () => window.removeEventListener('keydown', onKey, true);
    }, [open, onClose]);

    React.useEffect(() => {
      if (open) {
        triggerRef.current = document.activeElement;
      } else if (triggerRef.current) {
        try { triggerRef.current.focus(); } catch (e) { /* ignore */ }
        triggerRef.current = null;
      }
    }, [open]);

    if (!open) return null;

    function onScrimClick(e) {
      if (e.target === e.currentTarget) onClose();
    }

    return (
      <div
        className="md-dialog__scrim"
        onClick={onScrimClick}
        role="dialog"
        aria-modal="true"
        aria-label="How it works"
      >
        <div className="md-dialog md-dialog--rich" style={{ maxHeight: '92vh', overflow: 'hidden' }}>
          {/* Header */}
          <div className="dr-modal-header">
            <h2>How it works</h2>
            <span className="spacer" />
            <div className="dr-modal-tabs" role="tablist">
              <button
                type="button"
                className={'tab' + (view === 'how' ? ' is-active' : '')}
                role="tab"
                aria-selected={view === 'how'}
                onClick={() => setView('how')}
              >How it works</button>
              <button
                type="button"
                className={'tab' + (view === 'changelog' ? ' is-active' : '')}
                role="tab"
                aria-selected={view === 'changelog'}
                onClick={() => setView('changelog')}
              >Changelog</button>
            </div>
            <button
              type="button"
              className="dr-modal-close"
              onClick={onClose}
              aria-label="Close"
            >×</button>
          </div>

          {/* Two-column layout: side menu + scrollable content */}
          <div className="hiw-overlay__layout">
            <nav className="hiw-overlay__menu" aria-label="Section navigation">
              <ul className="hiw-overlay__menu-list">
                {view === 'how'
                  ? HIW_SECTIONS.map((s, i) =>
                      <li key={s.id}>
                        <a href={`#${s.id}`}>
                          <span className="menu-section-num">{i + 1}</span>{s.label}
                        </a>
                      </li>
                    )
                  : VERSION_NOTES.slice(0, 12).map((e) =>
                      <li key={e.version}>
                        <a href={`#cl-${e.version.replace(/\./g, '')}`}>
                          <span className="menu-section-num">{e.version}</span>{e.summary.slice(0, 30)}
                        </a>
                      </li>
                    )
                }
              </ul>
            </nav>

            <div className="hiw-overlay__content">
              {view === 'how' ? (
                <div className="hiw">
                  <ProtocolOverviewSection />
                  {PHASES.map((p) => <PhaseSection key={p.anchor} phase={p} />)}
                  <ModalAnatomySection />
                  <ItemTaxonomySection />
                  <ItemLifecycleSection />
                  <ConvergenceSection />
                  <CostSection />
                </div>
              ) : (
                <ChangelogList />
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Vestigial — legacy onboarding tour and a few deep-links still hit
  // HowItWorksPage. Keep it as a no-op that dispatches an open event the
  // app shell catches to surface the overlay.
  function HowItWorksPage() {
    React.useEffect(() => {
      if (typeof window === 'undefined') return;
      window.dispatchEvent(new CustomEvent('dr-open-how-it-works'));
    }, []);
    return null;
  }

  window.HowItWorks = HowItWorks;
  window.HowItWorksPage = HowItWorksPage;
})();
