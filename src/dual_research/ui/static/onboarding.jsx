// onboarding.jsx — 8-step onboarding tour overlay (SPEC-0103).
//
// Mounts as a sibling of the app root via position:fixed. Does NOT
// re-render any underlying surface. Reads bounding boxes of
// [data-tour-anchor] nodes at step time.
//
// Steps 1, 4, 8 render M3 rich dialogs over a dimmed mask.
// Steps 2, 3, 5, 6, 7 render spotlight cutouts + callout.
// Completion sets localStorage 'dr_onboarded' = 'true'.
// Reset via ?reset_onboarding=1 query param for testing.

(function () {
  const TOTAL_STEPS = 8;

  const TOUR_STEPS = [
    { id: 1, type: 'modal', title: 'Welcome to dual-research', body: 'Two AI agents — one Claude, one GPT — hold a structured conversation to produce a single research document. They negotiate a plan, research independently, draft collaboratively, and review each other\'s work adversarially.\n\nThis tour will walk you through the key surfaces of the app.' },
    { id: 2, type: 'spotlight', anchor: 'run-row', stepLabel: 'RUN ROW', title: 'One row, the whole run', body: 'Each row carries the run ID, topic, current phase, round, status, duration, tokens, and cost. Eight columns, scannable in one glance.', route: 'list' },
    { id: 3, type: 'spotlight', anchor: 'run-detail-header', stepLabel: 'RUN DETAIL', title: 'The run header', body: 'The sticky header shows the topic, total cost, reconciliation status, phase dots, and run metadata. Everything you need to orient yourself in a run.', route: 'detail' },
    { id: 4, type: 'modal', title: 'How the five phases work', body: null },
    { id: 5, type: 'spotlight', anchor: 'timeline-phase-rail', stepLabel: 'PHASE RAIL', title: 'The timeline rail', body: 'The vertical rail on the left edge of the timeline marks which phase each turn belongs to. Segments light up as the run progresses through preflight, research, negotiation, drafting, and review.' },
    { id: 6, type: 'spotlight', anchor: 'critique-pane', stepLabel: 'CRITIQUE PANE', title: 'Critique items, tracked', body: 'Every question, disagreement, or concern raised during negotiation and review lives here. Items are tracked across rounds — opened, carried over, resolved, or drifted.' },
    { id: 7, type: 'spotlight', anchor: 'consumption-card', stepLabel: 'CONSUMPTION', title: 'Token consumption at a glance', body: 'Each card shows one agent\'s token usage for the current turn: input, output, cache hits, and cost. The bar chart makes it easy to spot which turns are expensive.' },
    { id: 8, type: 'modal', title: 'You\'re all set', body: 'You now know the key surfaces. Explore a run, check the critique pane, or start a new run from the CLI.\n\nYou can re-open this tour any time from the browser console or with ?reset_onboarding=1.' },
  ];

  function TourOverlay({ open, step, onClose, onAdvance, onBack, navigate }) {
    const [anchorRect, setAnchorRect] = React.useState(null);
    const calloutRef = React.useRef(null);
    const overlayRef = React.useRef(null);

    const stepDef = TOUR_STEPS[step - 1];
    if (!stepDef) return null;

    // Navigate to correct route when step changes
    React.useEffect(() => {
      if (!open) return;
      const def = TOUR_STEPS[step - 1];
      if (!def) return;
      if (def.route === 'list' && window.location.hash !== '#/') {
        navigate('list');
      }
      // For step 3 (detail), we need a run ID. Pick the first available.
      if (def.route === 'detail') {
        const firstRow = document.querySelector('.run-row, [data-tour-anchor="run-row"]');
        if (firstRow) {
          const runId = firstRow.getAttribute('data-run-id') || firstRow.title;
          if (runId && !window.location.hash.startsWith('#/runs/')) {
            navigate('detail', runId);
          }
        }
      }
    }, [open, step, navigate]);

    // Compute anchor bounding box for spotlight steps
    React.useEffect(() => {
      if (!open) return;
      const def = TOUR_STEPS[step - 1];
      if (!def || def.type !== 'spotlight') {
        setAnchorRect(null);
        return;
      }
      const computeRect = () => {
        const el = document.querySelector(`[data-tour-anchor="${def.anchor}"]`);
        if (el) {
          setAnchorRect(el.getBoundingClientRect());
        } else {
          setAnchorRect(null);
          // Anchor not found — skip to next step per spec § 10
          // (retry briefly in case of async render)
          const timer = setTimeout(() => {
            const el2 = document.querySelector(`[data-tour-anchor="${def.anchor}"]`);
            if (el2) {
              setAnchorRect(el2.getBoundingClientRect());
            }
          }, 500);
          return () => clearTimeout(timer);
        }
      };
      computeRect();
      window.addEventListener('resize', computeRect);
      window.addEventListener('scroll', computeRect, true);
      return () => {
        window.removeEventListener('resize', computeRect);
        window.removeEventListener('scroll', computeRect, true);
      };
    }, [open, step]);

    // Focus trap: Tab cycles within callout, Escape fires onClose
    React.useEffect(() => {
      if (!open) return;
      const onKey = (e) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          onClose();
          return;
        }
        if (e.key === 'Tab' && overlayRef.current) {
          const focusable = overlayRef.current.querySelectorAll('button, [tabindex]:not([tabindex="-1"])');
          if (focusable.length === 0) return;
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      };
      window.addEventListener('keydown', onKey);
      return () => window.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    if (!open) return null;

    const handleSkip = () => {
      onClose();
    };

    const handleDone = () => {
      onClose();
    };

    // Progress dots
    const progressDots = [];
    for (let i = 1; i <= TOTAL_STEPS; i++) {
      progressDots.push(
        <span key={i} className={i === step ? 'on' : ''} />
      );
    }

    // Action buttons
    const actions = (
      <div className="row" style={{ marginTop: 16 }}>
        <div className="callout__progress">
          {progressDots}
        </div>
        <div className="callout__spacer" />
        {step > 1 && (
          <button className="md-btn md-btn--text md-btn--sm" onClick={onBack}>Back</button>
        )}
        {step < TOTAL_STEPS ? (
          <>
            <button className="md-btn md-btn--text md-btn--sm" onClick={handleSkip}>Skip</button>
            <button className="md-btn md-btn--filled md-btn--sm" onClick={onAdvance}>Continue</button>
          </>
        ) : (
          <button className="md-btn md-btn--filled md-btn--sm" onClick={handleDone}>Done</button>
        )}
      </div>
    );

    // Modal steps (1, 4, 8)
    if (stepDef.type === 'modal') {
      return (
        <div className="tour-overlay" ref={overlayRef}>
          <div className="tour-overlay__mask" />
          <div style={{
            position: 'fixed', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1,
          }}>
            <div className="callout" style={{
              position: 'relative', width: stepDef.id === 4 ? 720 : 420,
              maxWidth: 'calc(100vw - 48px)',
              maxHeight: 'calc(100vh - 48px)',
              overflow: 'auto',
            }}>
              <div className="callout__step">STEP {stepDef.id} of {TOTAL_STEPS}</div>
              <div className="callout__title">{stepDef.title}</div>
              {stepDef.id === 4 ? (
                <div>
                  <div className="callout__body" style={{ marginBottom: 16 }}>
                    The dual-research pipeline progresses through five phases. Each phase has a distinct role in producing the final document.
                  </div>
                  <PhasesOverviewSVG />
                </div>
              ) : (
                <p className="callout__body">{stepDef.body}</p>
              )}
              {actions}
            </div>
          </div>
        </div>
      );
    }

    // Spotlight steps (2, 3, 5, 6, 7)
    const pad = 8;
    const clipPath = anchorRect
      ? buildClipPath(anchorRect, pad)
      : undefined;

    // Compute callout position with overflow-aware placement (spec 0121 § 16).
    // Earlier logic branched on viewport width alone — a full-width anchor (e.g. the
    // run-row at step 2) made `anchorRect.right + 16` land off-screen, and the
    // `maxWidth: calc(100vw - {anchorRect.right + 32}px)` term evaluated to a
    // non-positive number, collapsing the callout to zero width. Fix: pick the first
    // side with enough space among [right, below, left, above], then clamp inside
    // the viewport.
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const CW = 360;             // callout width
    const G = 16;               // gutter between anchor and callout
    const CH_EST = 220;         // rough callout height for the vertical clamp
    let calloutStyle = {};
    if (anchorRect) {
      const spaceRight = vw - anchorRect.right - G;
      const spaceBelow = vh - anchorRect.bottom - G;
      const spaceLeft  = anchorRect.left - G;
      const clampY = (y) => Math.max(G, Math.min(y, vh - CH_EST - G));
      const clampX = (x) => Math.max(G, Math.min(x, vw - CW - G));
      if (spaceRight >= CW + G) {
        // Right of the anchor — original >=1500px branch, now space-aware.
        calloutStyle = {
          position: 'fixed',
          top: clampY(anchorRect.top),
          left: anchorRect.right + G,
          width: CW,
        };
      } else if (spaceBelow >= CH_EST) {
        // Below the anchor, left-aligned, clamped to viewport.
        calloutStyle = {
          position: 'fixed',
          top: anchorRect.bottom + G,
          left: clampX(anchorRect.left),
          width: CW,
        };
      } else if (spaceLeft >= CW + G) {
        // Left of the anchor — fallback for tall anchors hugging the right edge.
        calloutStyle = {
          position: 'fixed',
          top: clampY(anchorRect.top),
          left: anchorRect.left - CW - G,
          width: CW,
        };
      } else {
        // Last resort: above the anchor.
        calloutStyle = {
          position: 'fixed',
          top: Math.max(G, anchorRect.top - CH_EST - G),
          left: clampX(anchorRect.left),
          width: CW,
        };
      }
    } else {
      calloutStyle = {
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 360,
      };
    }

    return (
      <div className="tour-overlay" ref={overlayRef}>
        <div className="tour-overlay__mask" style={clipPath ? { clipPath } : undefined} />
        {anchorRect && (
          <div className="tour-overlay__cutout" style={{
            top: anchorRect.top - pad,
            left: anchorRect.left - pad,
            width: anchorRect.width + pad * 2,
            height: anchorRect.height + pad * 2,
          }} />
        )}
        <div className="callout" ref={calloutRef} style={calloutStyle}>
          <div className="callout__step">STEP {stepDef.id} &middot; {stepDef.stepLabel}</div>
          <div className="callout__title">{stepDef.title}</div>
          <p className="callout__body">{stepDef.body}</p>
          {actions}
        </div>
      </div>
    );
  }

  function buildClipPath(rect, pad) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const t = rect.top - pad;
    const l = rect.left - pad;
    const r = rect.right + pad;
    const b = rect.bottom + pad;
    // Polygon: outer rect with a rectangular hole
    return `polygon(
      0% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%,
      ${l}px ${t}px, ${l}px ${b}px, ${r}px ${b}px, ${r}px ${t}px, ${l}px ${t}px
    )`;
  }

  // Phases overview SVG — inlined from Design System v2.html lines 1828-1927
  function PhasesOverviewSVG() {
    return (
      <div dangerouslySetInnerHTML={{ __html: PHASES_SVG }} style={{ margin: '0 0 16px' }} />
    );
  }

  const PHASES_SVG = `<svg viewBox="0 0 1100 480" style="width: 100%; height: auto; background: var(--md-surface-container); border-radius: 12px;" role="img" aria-label="Phases overview — five phases from brief to converged document">
  <defs>
    <linearGradient id="po-a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d4a574" stop-opacity="0.22"/><stop offset="1" stop-color="#d4a574" stop-opacity="0.06"/></linearGradient>
    <linearGradient id="po-b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7cc4b8" stop-opacity="0.22"/><stop offset="1" stop-color="#7cc4b8" stop-opacity="0.06"/></linearGradient>
    <marker id="poM"  viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#9aa0ac"/></marker>
    <marker id="poMI" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#6b9cf0"/></marker>
    <marker id="poMO" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#6fb380"/></marker>
  </defs>
  <rect x="60" y="142" width="980" height="72" rx="12" fill="#d4a574" fill-opacity="0.05"/>
  <rect x="60" y="276" width="980" height="72" rx="12" fill="#7cc4b8" fill-opacity="0.05"/>
  <text x="34" y="186" fill="#9aa0ac" font-family="Roboto Flex" font-size="11" font-weight="600" letter-spacing="0.10em" transform="rotate(-90, 34, 186)">CLAUDE &#183; A</text>
  <text x="34" y="320" fill="#9aa0ac" font-family="Roboto Flex" font-size="11" font-weight="600" letter-spacing="0.10em" transform="rotate(-90, 34, 320)">GPT &#183; B</text>
  <g font-family="Roboto Flex">
    <text x="60"  y="78" font-size="11" font-weight="600" fill="#9aa0ac" letter-spacing="0.10em">PHASE 0</text>
    <text x="60"  y="104" font-size="16" font-weight="500" fill="#ffffff" font-family="Roboto Serif">Preflight</text>
    <text x="60"  y="124" font-size="12" fill="#9aa0ac">Normalise the brief</text>
    <text x="260" y="78" font-size="11" font-weight="600" fill="#9aa0ac" letter-spacing="0.10em">PHASE 1</text>
    <text x="260" y="104" font-size="16" font-weight="500" fill="#ffffff" font-family="Roboto Serif">Independent Research</text>
    <text x="260" y="124" font-size="12" fill="#9aa0ac">Parallel &#183; no contact</text>
    <text x="480" y="78" font-size="11" font-weight="600" fill="#9aa0ac" letter-spacing="0.10em">PHASE 2</text>
    <text x="480" y="104" font-size="16" font-weight="500" fill="#ffffff" font-family="Roboto Serif">Plan Negotiation</text>
    <text x="480" y="124" font-size="12" fill="#9aa0ac">Adversarial &#183; multi-round</text>
    <text x="700" y="78" font-size="11" font-weight="600" fill="#9aa0ac" letter-spacing="0.10em">PHASE 3</text>
    <text x="700" y="104" font-size="16" font-weight="500" fill="#ffffff" font-family="Roboto Serif">Drafting</text>
    <text x="700" y="124" font-size="12" fill="#9aa0ac">One writes &#183; one advises</text>
    <text x="900" y="78" font-size="11" font-weight="600" fill="#9aa0ac" letter-spacing="0.10em">PHASE 4</text>
    <text x="900" y="104" font-size="16" font-weight="500" fill="#ffffff" font-family="Roboto Serif">Review Loop</text>
    <text x="900" y="124" font-size="12" fill="#9aa0ac">Item-tracked</text>
  </g>
  <line x1="50" y1="134" x2="1050" y2="134" stroke="#262a31"/>
  <g transform="translate(60,152)">
    <rect width="180" height="180" rx="12" fill="#14171c" stroke="#262a31"/>
    <rect x="0" y="0" width="3" height="180" fill="#6b9cf0"/>
    <text x="16" y="22" fill="#ffffff" font-family="Roboto Flex" font-size="10" font-weight="600" letter-spacing="0.10em">PREFLIGHT</text>
    <text x="16" y="48" font-family="Roboto Flex" font-size="12" fill="#b4bac4">Single deterministic</text>
    <text x="16" y="64" font-family="Roboto Flex" font-size="12" fill="#b4bac4">turn. Normalises the</text>
    <text x="16" y="80" font-family="Roboto Flex" font-size="12" fill="#b4bac4">brief, asks clarifying</text>
    <text x="16" y="96" font-family="Roboto Flex" font-size="12" fill="#b4bac4">questions.</text>
    <rect x="16" y="116" width="148" height="22" rx="6" fill="#0d0f12" stroke="#262a31"/>
    <text x="24" y="131" font-size="11" fill="#ffffff" font-family="Roboto Mono">user brief</text>
    <text x="16" y="160" fill="#9aa0ac" font-size="11" font-family="Roboto Flex">no agent negotiation</text>
  </g>
  <g transform="translate(260,152)">
    <rect width="180" height="70" rx="12" fill="url(#po-a)" stroke="#d4a574" stroke-opacity="0.5"/>
    <rect x="0" y="0" width="3" height="70" fill="#d4a574"/>
    <text x="16" y="22" fill="#ffffff" font-family="Roboto Flex" font-size="10" font-weight="600" letter-spacing="0.10em">CLAUDE RESEARCHES</text>
    <text x="16" y="44" font-size="12" fill="#b4bac4" font-family="Roboto Flex">Cites sources independently.</text>
    <text x="16" y="60" font-size="12" fill="#b4bac4" font-family="Roboto Flex">Does not see GPT's work.</text>
  </g>
  <g transform="translate(260,286)">
    <rect width="180" height="70" rx="12" fill="url(#po-b)" stroke="#7cc4b8" stroke-opacity="0.5"/>
    <rect x="0" y="0" width="3" height="70" fill="#7cc4b8"/>
    <text x="16" y="22" fill="#ffffff" font-family="Roboto Flex" font-size="10" font-weight="600" letter-spacing="0.10em">GPT RESEARCHES</text>
    <text x="16" y="44" font-size="12" fill="#b4bac4" font-family="Roboto Flex">Cites sources independently.</text>
    <text x="16" y="60" font-size="12" fill="#b4bac4" font-family="Roboto Flex">Does not see Claude's work.</text>
  </g>
  <line x1="280" y1="248" x2="420" y2="248" stroke="#7d8290" stroke-dasharray="5 4" stroke-opacity="0.5"/>
  <text x="350" y="266" text-anchor="middle" fill="#9aa0ac" font-size="11" font-family="Roboto Flex">strictly parallel</text>
  <g transform="translate(460,152)">
    <rect width="180" height="204" rx="12" fill="#14171c" stroke="#262a31"/>
    <text x="16" y="22" fill="#ffffff" font-family="Roboto Flex" font-size="10" font-weight="600" letter-spacing="0.10em">NEGOTIATE A PLAN</text>
    <rect x="16" y="34" width="148" height="24" rx="12" fill="#d4a574" fill-opacity="0.18" stroke="#d4a574" stroke-opacity="0.5"/>
    <circle cx="28" cy="46" r="6" fill="#d4a574"/>
    <text x="40" y="50" font-size="12" font-weight="500" fill="#d4a574" font-family="Roboto Flex">Claude proposes</text>
    <path d="M90 60 L90 70" stroke="#6b9cf0" stroke-width="1.5" marker-end="url(#poMI)"/>
    <rect x="16" y="74" width="148" height="24" rx="12" fill="#7cc4b8" fill-opacity="0.18" stroke="#7cc4b8" stroke-opacity="0.5"/>
    <circle cx="28" cy="86" r="6" fill="#7cc4b8"/>
    <text x="40" y="90" font-size="12" font-weight="500" fill="#7cc4b8" font-family="Roboto Flex">GPT critiques</text>
    <path d="M76 100 L76 118" stroke="#6b9cf0" stroke-width="1.5" marker-end="url(#poMI)"/>
    <text x="90" y="132" text-anchor="middle" fill="#9aa0ac" font-size="11" font-family="Roboto Flex">&#8230; round 2 &#8230;</text>
    <line x1="16" y1="146" x2="164" y2="146" stroke="#262a31"/>
    <text x="16" y="164" fill="#9aa0ac" font-size="10" font-weight="600" letter-spacing="0.10em" font-family="Roboto Flex">CONVERGENCE GATE</text>
    <rect x="16" y="172" width="148" height="24" rx="8" fill="#6fb380" fill-opacity="0.16" stroke="#6fb380" stroke-opacity="0.5"/>
    <circle cx="28" cy="184" r="5" fill="#6fb380"/>
    <text x="40" y="188" font-size="12" font-weight="500" fill="#6fb380" font-family="Roboto Flex">plan hashes match</text>
  </g>
  <g transform="translate(680,152)">
    <rect width="180" height="70" rx="12" fill="url(#po-a)" stroke="#d4a574" stroke-opacity="0.5"/>
    <rect x="0" y="0" width="3" height="70" fill="#d4a574"/>
    <text x="16" y="22" fill="#ffffff" font-family="Roboto Flex" font-size="10" font-weight="600" letter-spacing="0.10em">DRAFTER (selected)</text>
    <text x="16" y="44" font-size="12" fill="#b4bac4" font-family="Roboto Flex">Writes the long-form draft</text>
    <text x="16" y="60" font-size="12" fill="#b4bac4" font-family="Roboto Flex">against the converged plan.</text>
  </g>
  <g transform="translate(680,286)">
    <rect width="180" height="70" rx="12" fill="url(#po-b)" stroke="#7cc4b8" stroke-opacity="0.5"/>
    <rect x="0" y="0" width="3" height="70" fill="#7cc4b8"/>
    <text x="16" y="22" fill="#ffffff" font-family="Roboto Flex" font-size="10" font-weight="600" letter-spacing="0.10em">FEEDBACK PARTNER</text>
    <text x="16" y="44" font-size="12" fill="#b4bac4" font-family="Roboto Flex">Surfaces structural issues</text>
    <text x="16" y="60" font-size="12" fill="#b4bac4" font-family="Roboto Flex">before formal review.</text>
  </g>
  <g transform="translate(900,152)">
    <rect width="140" height="204" rx="12" fill="#14171c" stroke="#262a31"/>
    <text x="16" y="22" fill="#ffffff" font-family="Roboto Flex" font-size="10" font-weight="600" letter-spacing="0.10em">REVIEW</text>
    <rect x="16" y="34" width="108" height="24" rx="12" fill="#d4a574" fill-opacity="0.18" stroke="#d4a574" stroke-opacity="0.5"/>
    <circle cx="28" cy="46" r="6" fill="#d4a574"/>
    <text x="40" y="50" font-size="11" font-weight="500" fill="#d4a574" font-family="Roboto Flex">reviews</text>
    <path d="M70 60 L70 70" stroke="#6b9cf0" stroke-width="1.5" marker-end="url(#poMI)"/>
    <rect x="16" y="74" width="108" height="24" rx="12" fill="#7cc4b8" fill-opacity="0.18" stroke="#7cc4b8" stroke-opacity="0.5"/>
    <circle cx="28" cy="86" r="6" fill="#7cc4b8"/>
    <text x="40" y="90" font-size="11" font-weight="500" fill="#7cc4b8" font-family="Roboto Flex">reviews</text>
    <line x1="16" y1="146" x2="124" y2="146" stroke="#262a31"/>
    <text x="16" y="164" fill="#9aa0ac" font-size="10" font-weight="600" letter-spacing="0.10em" font-family="Roboto Flex">CONVERGE</text>
    <rect x="16" y="172" width="108" height="24" rx="8" fill="#6fb380" fill-opacity="0.16" stroke="#6fb380" stroke-opacity="0.5"/>
    <circle cx="28" cy="184" r="5" fill="#6fb380"/>
    <text x="40" y="188" font-size="11" font-weight="500" fill="#6fb380" font-family="Roboto Flex">done</text>
  </g>
  <path d="M240 190 L260 190" stroke="#9aa0ac" stroke-width="1.5" marker-end="url(#poM)"/>
  <path d="M440 190 L460 190" stroke="#9aa0ac" stroke-width="1.5" marker-end="url(#poM)"/>
  <path d="M640 190 L680 190" stroke="#9aa0ac" stroke-width="1.5" marker-end="url(#poM)"/>
  <path d="M860 190 L900 190" stroke="#9aa0ac" stroke-width="1.5" marker-end="url(#poM)"/>
</svg>`;

  window.TourOverlay = TourOverlay;
})();
