// how-it-works.jsx — user-facing explainer of the Dual Research protocol
// plus the in-app changelog (Spec 0121 rewrite; Spec 0220 fetch-rewire).
//
// IA: 11 collapsible sections in the "How it works" tab + a tabbed Changelog
// view. Every diagram embeds via theme-aware <img> swap (MutationObserver on
// body.classList) from /diagrams/how-it-works/. Every chip uses the spec-0119
// canonical Chip CSS classes (the .chip / .cat-bubble vocabulary in
// components.css); no bespoke chip variants are introduced here. Layout / list
// / table classes live under the `/* spec-0121` block in components.css.
//
// Changelog entries are no longer hand-maintained here. They live as
// /static/version-notes.json, generated at build time from CHANGELOG.md by
// scripts/build_version_notes.py and merged with per-entry overrides in
// version-notes-overrides.json. ChangelogList fetches the sidecar on mount.

(function () {
  'use strict';

  // ─── Version notes fetcher (Spec 0220) ────────────────────────
  // Single shared fetch — both ChangelogList and HowItWorksBody's menu
  // consume the same JSON sidecar.
  let _versionNotesPromise = null;
  function _loadVersionNotes() {
    if (_versionNotesPromise) return _versionNotesPromise;
    _versionNotesPromise = fetch('/version-notes.json?v=0220c')
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .catch((e) => { _versionNotesPromise = null; throw e; });
    return _versionNotesPromise;
  }
  function useVersionNotes() {
    const [entries, setEntries] = React.useState(null);
    const [err, setErr] = React.useState(null);
    React.useEffect(() => {
      let cancelled = false;
      _loadVersionNotes()
        .then((data) => { if (!cancelled) setEntries(data); })
        .catch((e) => { if (!cancelled) setErr(String(e.message || e)); });
      return () => { cancelled = true; };
    }, []);
    return { entries, err };
  }

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
    const src = `/diagrams/how-it-works/${name}.${variant}.svg?v=0133a`;
    const [open, setOpen] = React.useState(false);
    return (
      <React.Fragment>
        <button
          type="button"
          className="hiw-diagram hiw-diagram--clickable"
          onClick={() => setOpen(true)}
          aria-label={`Enlarge: ${alt}`}
        >
          <img src={src} alt={alt} loading="lazy" />
          <span className="hiw-diagram__hint" aria-hidden="true">⤢ click to enlarge</span>
        </button>
        {open && <DiagramViewer src={src} alt={alt} onClose={() => setOpen(false)} />}
      </React.Fragment>
    );
  }

  // ─── DiagramViewer — full-viewport SVG enlarger ──────────────
  // Spec 0123: click any embedded HiwDiagram → shows the SVG at
  // near-fullscreen size in a scrim-backed modal. Esc / scrim-click
  // / close-button dismisses.

  function DiagramViewer({ src, alt, onClose }) {
    React.useEffect(() => {
      function onKey(e) {
        if (e.key === 'Escape') { e.stopPropagation(); onClose(); }
      }
      window.addEventListener('keydown', onKey, true);
      return () => window.removeEventListener('keydown', onKey, true);
    }, [onClose]);

    function onScrimClick(e) {
      if (e.target === e.currentTarget) onClose();
    }

    return (
      <div
        className="diagram-viewer__scrim"
        onClick={onScrimClick}
        role="dialog"
        aria-modal="true"
        aria-label={alt}
      >
        <button
          type="button"
          className="diagram-viewer__close"
          onClick={onClose}
          aria-label="Close diagram viewer"
        >×</button>
        <img className="diagram-viewer__img" src={src} alt={alt} />
      </div>
    );
  }

  // ─── Collapsible section with localStorage persistence ────────

  function CollapsibleSection({ id, persistKey, defaultOpen, forceOpen, renderTitle, title, children }) {
    const storageKey = persistKey ? `hiw:cs:${persistKey}` : null;
    const [open, setOpen] = React.useState(() => {
      // Spec 0220 — `forceOpen` overrides defaultOpen + any persisted state
      // on initial render. After mount, the user can collapse normally and
      // the toggle persists per storageKey.
      if (forceOpen) return true;
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
        className={'hiw-sec hiw-cs-section' + (open ? ' is-open' : '')}
      >
        <div
          className="hiw-cs-header"
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
          <span className="hiw-cs-chevron" aria-hidden="true">▶</span>
          <span className="hiw-cs-title">
            {renderTitle ? renderTitle() : title}
          </span>
        </div>
        <div className="hiw-cs-body">{open ? children : null}</div>
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
      diagramName: 'deep-research-pipeline',
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
      diagramName: 'deep-research-pipeline',
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
      diagramName: 'deep-research-pipeline',
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

  // ─── SpecModal — Spec 0126 ──────────────────────────────────
  // Renders a spec's markdown inside the same M3 <Modal variant="rich">
  // the timeline cards use for full-view turn/draft modals. The body
  // is fetched via GET /api/specs/{spec_id} (server.py strips YAML
  // frontmatter before returning).

  function SpecModal({ specId, version, date, summary, onClose }) {
    const [body, setBody] = React.useState(null);
    const [err, setErr] = React.useState(null);

    React.useEffect(() => {
      let cancelled = false;
      setBody(null);
      setErr(null);
      const fetcher = typeof window.authedFetch === 'function' ? window.authedFetch : window.fetch;
      fetcher(`/api/specs/${encodeURIComponent(specId)}`)
        .then((r) => r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`)))
        .then((text) => { if (!cancelled) setBody(text); })
        .catch((e) => { if (!cancelled) setErr(String(e.message || e)); });
      return () => { cancelled = true; };
    }, [specId]);

    const title = `Spec ${specId}`;
    const subtitle = `v${version} · ${date}${summary ? ' · ' + summary : ''}`;

    return (
      <window.Modal
        open={true}
        onClose={onClose}
        title={title}
        subtitle={subtitle}
        variant="rich"
      >
        <div className="spec-modal__body">
          {body === null && !err && (
            <window.LoadingState size="inline" label="Loading spec…" />
          )}
          {err && (
            <div className="spec-modal__error">
              Couldn't load spec: {err}
            </div>
          )}
          {body && <window.Markdown text={body} />}
        </div>
      </window.Modal>
    );
  }

  function ChangelogEntry({ entry, defaultOpen, forceOpen, onOpenSpec }) {
    const bumpTone = entry.bump === 'MAJOR' ? 'err' : entry.bump === 'MINOR' ? 'info' : 'ok';
    return (
      <CollapsibleSection
        id={`cl-${entry.version.replace(/\./g, '')}`}
        persistKey={`changelog:${entry.version}`}
        defaultOpen={defaultOpen}
        forceOpen={forceOpen}
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
                    {/* Spec 0126: hide the figure if the image 404s so we
                        never render a broken-image icon. */}
                    <img
                      src={s.path}
                      alt={s.alt}
                      loading="lazy"
                      onError={(e) => {
                        const fig = e.target.closest('figure');
                        if (fig) fig.style.display = 'none';
                      }}
                    />
                    <figcaption>{s.caption}</figcaption>
                  </figure>
                )}
              </div>
            </React.Fragment>
          )}
          {entry.specs && entry.specs.length > 0 && (
            <div className="changelog-spec-link">
              {entry.specs.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="md-btn md-btn--text md-btn--sm"
                  onClick={() => onOpenSpec({
                    specId: s,
                    version: entry.version,
                    date: entry.date,
                    summary: entry.summary,
                  })}
                >Open spec {s} ↗</button>
              ))}
            </div>
          )}
        </div></div>
      </CollapsibleSection>
    );
  }

  // Spec 0220 — flat one-row presentation for entries classified
  // `user_facing: false` by scripts/build_version_notes.py. No expand
  // affordance, no body — the summary IS the payload.
  function ChangelogInternalRow({ entry, onOpenSpec }) {
    const bumpTone = entry.bump === 'MAJOR' ? 'err' : entry.bump === 'MINOR' ? 'info' : 'ok';
    return (
      <div
        className="changelog-internal-row"
        id={`cl-${entry.version.replace(/\./g, '')}`}
      >
        <span className="chip mono tone-neutral no-dot">v{entry.version}</span>
        <span className="changelog-date">{entry.date}</span>
        <span className="changelog-summary changelog-internal-summary">
          Internal — {entry.summary}
        </span>
        {entry.specs && entry.specs.map((s) => (
          <button
            key={s}
            type="button"
            className="chip mono chip-square tone-neutral no-dot changelog-internal-spec"
            onClick={() => onOpenSpec({
              specId: s,
              version: entry.version,
              date: entry.date,
              summary: entry.summary,
            })}
          >spec {s}</button>
        ))}
        {entry.bump && <span className={`chip tone-${bumpTone}`}>{entry.bump}</span>}
      </div>
    );
  }

  function ChangelogList() {
    const { entries, err } = useVersionNotes();
    const [q, setQ] = React.useState('');
    const [bumpFilter, setBumpFilter] = React.useState(null);
    const [showInternal, setShowInternal] = React.useState(false);
    const [openSpec, setOpenSpec] = React.useState(null);

    // Spec 0220 — hash routing. If the URL hash matches
    // `#how-it-works#cl-<digits>`, that entry is forced open on first
    // render regardless of any persisted collapse state.
    const forceOpenAnchor = React.useMemo(() => {
      try {
        const h = window.location.hash || '';
        const m = h.match(/#cl-(\d+)/);
        return m ? m[1] : null;
      } catch (e) { return null; }
    }, []);

    const counts = React.useMemo(() => {
      const c = { MAJOR: 0, MINOR: 0, PATCH: 0, INTERNAL: 0 };
      (entries || []).forEach((e) => {
        if (e.bump && c[e.bump] !== undefined) c[e.bump]++;
        if (e.user_facing === false) c.INTERNAL++;
      });
      return c;
    }, [entries]);

    if (err) {
      return (
        <div className="hiw-note hiw-note-err">
          Couldn't load the changelog — try refreshing.
        </div>
      );
    }
    if (entries === null) {
      return <window.LoadingState size="inline" label="Loading changelog…" />;
    }

    const filtered = entries.filter((e) => {
      if (!showInternal && e.user_facing === false) return false;
      if (bumpFilter && e.bump !== bumpFilter) return false;
      if (!q) return true;
      const blob = `${e.version} ${e.date} ${e.summary || ''} ${(e.specs || []).join(' ')} ${(e.items || []).join(' ')}`.toLowerCase();
      return blob.includes(q.toLowerCase());
    });

    // Track whether the autoOpen (first user-facing entry without a search
    // / filter active) has already been assigned, so chronologically-later
    // user-facing entries don't all default open.
    let autoOpenAssigned = false;

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
            <span className="chip-value">{entries.length}</span>
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
          <span
            className={`chip tone-neutral ${counts.INTERNAL === 0 ? 'dim' : ''}`}
            data-active={showInternal ? 'true' : 'false'}
            role="button"
            tabIndex={0}
            onClick={() => setShowInternal((v) => !v)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') setShowInternal((v) => !v);
            }}
            title={showInternal ? 'Hide internal entries' : 'Show internal entries'}
          >
            <span className="chip-label">Internal</span>
            <span className="chip-value">{counts.INTERNAL}</span>
          </span>
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
          {filtered.map((e) => {
            const anchor = e.version.replace(/\./g, '');
            const forceOpen = forceOpenAnchor === anchor;
            if (e.user_facing === false) {
              return (
                <ChangelogInternalRow
                  key={e.version}
                  entry={e}
                  onOpenSpec={setOpenSpec}
                />
              );
            }
            const isAuto = !autoOpenAssigned && !q && !bumpFilter && !forceOpenAnchor;
            if (isAuto) autoOpenAssigned = true;
            return (
              <ChangelogEntry
                key={e.version}
                entry={e}
                defaultOpen={isAuto}
                forceOpen={forceOpen}
                onOpenSpec={setOpenSpec}
              />
            );
          })}
        </div>
        {openSpec && (
          <SpecModal
            specId={openSpec.specId}
            version={openSpec.version}
            date={openSpec.date}
            summary={openSpec.summary}
            onClose={() => setOpenSpec(null)}
          />
        )}
      </React.Fragment>
    );
  }

  // ─── HowItWorksBody — the section/changelog/menu/tabs payload ─
  // Same content as the pre-0123 modal, minus the modal scrim and
  // chrome. Rendered inside HowItWorksPage for the full-page route.

  function HowItWorksBody() {
    // Default to "how" view; switch to "changelog" if the URL hash
    // points at a changelog anchor (e.g. /#how-it-works#cl-150).
    const initialView = (() => {
      try {
        const h = window.location.hash || '';
        return h.includes('#cl-') ? 'changelog' : 'how';
      } catch (e) { return 'how'; }
    })();
    const [view, setView] = React.useState(initialView);
    // Spec 0220 — the side-menu Changelog list reads from the shared
    // version-notes fetch; entries are null while loading or on error.
    const { entries: changelogEntries } = useVersionNotes();

    // Reflect view in <title>.
    React.useEffect(() => {
      const prev = document.title;
      document.title = (view === 'how' ? 'How it works' : 'Changelog') + ' · Dual Research';
      return () => { document.title = prev; };
    }, [view]);

    return (
      <div className="hiw-page__inner">
        <header className="hiw-page__header">
          <h1 className="hiw-page__title">
            {view === 'how' ? 'How it works' : 'Changelog'}
          </h1>
          <span className="hiw-page__spacer" />
          <div className="hiw-page__tabs" role="tablist">
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
        </header>

        <div className="hiw-page__layout">
          <nav className="hiw-page__menu" aria-label="Section navigation">
            <ul className="hiw-overlay__menu-list">
              {view === 'how'
                ? HIW_SECTIONS.map((s, i) =>
                    <li key={s.id}>
                      <a href={`#${s.id}`}>
                        <span className="menu-section-num">{i + 1}</span>{s.label}
                      </a>
                    </li>
                  )
                : (changelogEntries || []).slice(0, 12).map((e) =>
                    <li key={e.version}>
                      <a href={`#cl-${e.version.replace(/\./g, '')}`}>
                        <span className="menu-section-num">{e.version}</span>{(e.summary || '').slice(0, 30)}
                      </a>
                    </li>
                  )
              }
            </ul>
          </nav>

          <div className="hiw-page__content">
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
    );
  }

  // ─── HowItWorksPage — full-page route mount ───────────────────
  // Mounted at route.view === 'how-it-works' in app.jsx. No modal
  // scrim, no max-width cap below --md-content-max. The old modal
  // wrapper (HowItWorks) was retired in spec 0123.

  function HowItWorksPage() {
    return (
      <div className="hiw-page">
        <HowItWorksBody />
      </div>
    );
  }

  window.HowItWorksPage = HowItWorksPage;
})();
