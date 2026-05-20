// onboarding.jsx — Spec 0125 rewrite.
//
// Eight-step guided tour with:
//   • Real SVG spotlight (mask cutout + radial halo) instead of flat dim.
//   • Card lift (M3 elevation-2) + agent-tinted border.
//   • Anchor-aware card placement (right / below / left / above with viewport clamp).
//   • Skip-on-missing-anchor with a corner toast.
//   • Cross-route navigation: spotlight steps that anchor inside a run-detail
//     page navigate to the most-recent run before they fire.
//   • Server-persisted state via /api/onboarding/state (spec 0125).
//   • One-shot localStorage migration on first authed boot.
//   • Phase vocabulary refreshed to match spec 0114 (Input / Research plan /
//     Negotiate plan / Draft / Review draft / Finalize). Step 4's diagram is
//     the spec-0121 pipeline SVG (theme-aware swap).

(function () {
  const TOTAL_STEPS = 8;

  const TOUR_STEPS = [
    {
      id: 1, type: 'modal',
      title: 'Welcome to dual-research',
      body: "Two AI agents — one Claude, one GPT — hold a structured conversation to produce a single research document. They negotiate a plan, research independently, draft collaboratively, and review each other's work adversarially.\n\nThis tour will walk you through the key surfaces of the app.",
    },
    {
      id: 2, type: 'spotlight', anchor: 'run-row', stepLabel: 'RUN ROW',
      route: 'list',
      title: 'One row, the whole run',
      body: 'Each row carries the run ID, topic, current phase, round, status, duration, tokens, and cost. Eight columns, scannable in one glance.',
    },
    {
      id: 3, type: 'spotlight', anchor: 'run-detail-header', stepLabel: 'RUN DETAIL',
      route: 'detail',
      title: 'The run header',
      body: 'The sticky header shows the topic, total cost, reconciliation status, phase dots, and run metadata. Everything you need to orient yourself in a run.',
    },
    {
      id: 4, type: 'modal',
      title: 'How the six phases work',
      body: "The dual-research pipeline runs through six phases: Phase 0 input (clarify the brief), Phase 1 research plan (each agent proposes), Phase 2 negotiate plan (agents argue), Phase 3 draft (one agent writes), Phase 4 review draft (both agents critique), and Finalize (the orchestrator assembles the document).",
    },
    {
      id: 5, type: 'spotlight', anchor: 'timeline-phase-rail', stepLabel: 'PHASE RAIL',
      route: 'detail',
      title: 'The timeline rail',
      body: 'The vertical rail on the left edge of the timeline marks which phase each turn belongs to. Segments light up as the run progresses through input, research plan, negotiation, drafting, and review.',
    },
    {
      id: 6, type: 'spotlight', anchor: 'critique-pane', stepLabel: 'CRITIQUE PANE',
      route: 'detail',
      title: 'Critique items, tracked',
      body: 'Every question, disagreement, issue, or comment raised during negotiation and review lives here. Items are tracked across rounds — opened, addressed, resolved, acknowledged, withdrawn, or capped.',
    },
    {
      id: 7, type: 'spotlight', anchor: 'consumption-card', stepLabel: 'CONSUMPTION',
      route: 'detail',
      title: 'Token consumption at a glance',
      body: "Each card shows one agent's token usage for the current turn: input, output, cache hits, and cost. The bar chart makes it easy to spot which turns are expensive.",
    },
    {
      id: 8, type: 'modal',
      title: "You're all set",
      body: "You now know the key surfaces. Explore a run, check the critique pane, or start a new run from the CLI.\n\nYou can re-open this tour any time from the avatar menu → Replay tour.",
    },
  ];

  // ─── Theme-aware pipeline diagram (step 4) ──────────────────────

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

  function PipelineDiagram() {
    const variant = useThemeMode();
    return (
      <div style={{ margin: '8px 0 16px', borderRadius: 8, overflow: 'hidden' }}>
        <img
          src={`/diagrams/how-it-works/01-pipeline.${variant}.svg?v=0124a`}
          alt="Dual Research six-phase pipeline"
          style={{ width: '100%', height: 'auto', display: 'block' }}
          loading="lazy"
        />
      </div>
    );
  }

  // ─── Server-persisted onboarding state ──────────────────────────

  function authedFetchOrNull(...args) {
    if (typeof window.authedFetch === 'function') return window.authedFetch(...args);
    return null;
  }

  async function fetchServerState() {
    try {
      const r = await authedFetchOrNull('/api/onboarding/state');
      if (!r || !r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }

  async function putServerState(patch) {
    try {
      const r = await authedFetchOrNull('/api/onboarding/state', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      });
      return r && r.ok;
    } catch (e) { return false; }
  }

  // One-shot localStorage → server migration. If the user has the legacy
  // dr_onboarded flag set but the server doesn't yet know they're onboarded,
  // PUT it once and then clear localStorage.
  async function migrateLegacyState(serverState) {
    if (!serverState) return;
    if (serverState.onboardedAt) {
      // Server already has it — drop any legacy localStorage.
      try {
        localStorage.removeItem('dr_onboarded');
        localStorage.removeItem('dr_tour_step');
      } catch (e) {}
      return;
    }
    let legacyOnboarded = false;
    try {
      legacyOnboarded = localStorage.getItem('dr_onboarded') === 'true';
    } catch (e) {}
    if (legacyOnboarded) {
      const ok = await putServerState({
        tourStep: 8,
        onboardedAt: new Date().toISOString(),
      });
      if (ok) {
        try {
          localStorage.removeItem('dr_onboarded');
          localStorage.removeItem('dr_tour_step');
        } catch (e) {}
      }
    }
  }

  // ─── Spotlight SVG (mask cutout + halo) ─────────────────────────

  function TourSpotlight({ rect, padding = 12 }) {
    // rect = { top, left, width, height }
    const x = Math.max(0, rect.left - padding);
    const y = Math.max(0, rect.top - padding);
    const w = rect.width + padding * 2;
    const h = rect.height + padding * 2;
    return (
      <svg
        className="tour-spotlight"
        aria-hidden="true"
        style={{ position: 'fixed', inset: 0, width: '100vw', height: '100vh', pointerEvents: 'none', zIndex: 90 }}
      >
        <defs>
          <mask id="tour-cutout">
            <rect width="100%" height="100%" fill="white" />
            <rect x={x} y={y} width={w} height={h} rx="12" fill="black" />
          </mask>
          <radialGradient id="tour-halo" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--info)" stopOpacity="0" />
            <stop offset="80%" stopColor="var(--info)" stopOpacity="0" />
            <stop offset="100%" stopColor="var(--info)" stopOpacity="0.45" />
          </radialGradient>
        </defs>
        {/* Dim with cutout */}
        <rect width="100%" height="100%" className="tour-spotlight__dim" mask="url(#tour-cutout)" />
        {/* Crisp outline at the cutout edge */}
        <rect x={x} y={y} width={w} height={h} rx="12"
              fill="none" stroke="var(--info)" strokeWidth="1.5" opacity="0.7" />
        {/* Soft halo ring just outside the cutout */}
        <rect x={x - 8} y={y - 8} width={w + 16} height={h + 16} rx="16"
              fill="none" stroke="url(#tour-halo)" strokeWidth="4" />
      </svg>
    );
  }

  // ─── Skip toast ─────────────────────────────────────────────────

  function SkipToast({ text }) {
    return (
      <div className="tour-skip-toast" role="status" aria-live="polite">
        {text}
      </div>
    );
  }

  // ─── Helpers ────────────────────────────────────────────────────

  function pickFirstRunId() {
    const firstRow = document.querySelector('[data-tour-anchor="run-row"], .run-row');
    if (!firstRow) return null;
    return (
      firstRow.getAttribute('data-run-id') ||
      firstRow.getAttribute('title') ||
      null
    );
  }

  // ─── Main overlay ───────────────────────────────────────────────

  function TourOverlay({ open, step, onClose, onAdvance, onBack, navigate }) {
    const [anchorRect, setAnchorRect] = React.useState(null);
    const [skipToast, setSkipToast] = React.useState(null);
    const calloutRef = React.useRef(null);
    const overlayRef = React.useRef(null);

    const stepDef = TOUR_STEPS[step - 1];

    // Server-state hook — only fires when the tour is open. Reads the user's
    // server-side onboarding state on mount, migrates legacy localStorage if
    // needed, and PUTs the new step on each advance.
    React.useEffect(() => {
      if (!open) return;
      (async () => {
        const s = await fetchServerState();
        await migrateLegacyState(s);
      })();
    }, [open]);

    React.useEffect(() => {
      if (!open) return;
      // Debounce the PUT a touch so a fast click-through doesn't fire 8 writes.
      const t = setTimeout(() => { putServerState({ tourStep: step }); }, 250);
      return () => clearTimeout(t);
    }, [open, step]);

    // Cross-route navigation: spotlight steps that anchor inside a run-detail
    // page need a real run to be visible.
    React.useEffect(() => {
      if (!open || !stepDef) return;
      if (stepDef.route === 'list' && window.location.hash !== '#/') {
        navigate('list');
      } else if (stepDef.route === 'detail') {
        const runId = pickFirstRunId();
        if (runId && !window.location.hash.startsWith('#/runs/')) {
          navigate('detail', runId);
        }
      }
    }, [open, step, stepDef, navigate]);

    // Anchor lookup. If the anchor isn't on the page after a retry, skip the
    // step with a toast.
    React.useEffect(() => {
      setSkipToast(null);
      setAnchorRect(null);
      if (!open || !stepDef || stepDef.type !== 'spotlight') return;

      let cancelled = false;
      const lookup = () => document.querySelector(`[data-tour-anchor="${stepDef.anchor}"]`);

      const tick = (attempt) => {
        if (cancelled) return;
        const el = lookup();
        if (el) {
          setAnchorRect(el.getBoundingClientRect());
          return;
        }
        if (attempt < 4) {
          setTimeout(() => tick(attempt + 1), 250);
        } else {
          // No anchor on this page — skip the step.
          setSkipToast({
            text: `Step ${stepDef.id} skipped — no “${stepDef.anchor}” on this page.`,
          });
          setTimeout(() => { if (!cancelled) onAdvance(); }, 1100);
        }
      };
      tick(0);

      const onRecompute = () => {
        const el = lookup();
        if (el) setAnchorRect(el.getBoundingClientRect());
      };
      window.addEventListener('resize', onRecompute);
      window.addEventListener('scroll', onRecompute, true);
      return () => {
        cancelled = true;
        window.removeEventListener('resize', onRecompute);
        window.removeEventListener('scroll', onRecompute, true);
      };
    }, [open, step, stepDef, onAdvance]);

    // Focus trap + Escape close.
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

    if (!open || !stepDef) return null;

    // Progress dots.
    const progressDots = [];
    for (let i = 1; i <= TOTAL_STEPS; i++) {
      progressDots.push(<span key={i} className={i === step ? 'on' : ''} />);
    }

    const actions = (
      <div className="row" style={{ marginTop: 16 }}>
        <div className="callout__progress">{progressDots}</div>
        <div className="callout__spacer" />
        {step > 1 && (
          <button className="md-btn md-btn--text md-btn--sm" onClick={onBack}>Back</button>
        )}
        {step < TOTAL_STEPS ? (
          <React.Fragment>
            <button className="md-btn md-btn--text md-btn--sm" onClick={onClose}>Skip</button>
            <button className="md-btn md-btn--filled md-btn--sm" onClick={onAdvance}>Continue</button>
          </React.Fragment>
        ) : (
          <button className="md-btn md-btn--filled md-btn--sm" onClick={onClose}>Done</button>
        )}
      </div>
    );

    // Modal steps (1, 4, 8) — centered card over a plain dim scrim.
    if (stepDef.type === 'modal') {
      return (
        <div className="tour-overlay" ref={overlayRef}>
          <div className="tour-scrim" />
          <div style={{
            position: 'fixed', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 100,
          }}>
            <div className="callout tour-callout tour-callout--modal" style={{
              position: 'relative',
              width: stepDef.id === 4 ? 820 : 460,
              maxWidth: 'calc(100vw - 48px)',
              maxHeight: 'calc(100vh - 48px)',
              overflow: 'auto',
            }}>
              <div className="callout__step">STEP {stepDef.id} of {TOTAL_STEPS}</div>
              <div className="callout__title">{stepDef.title}</div>
              {stepDef.id === 4 ? (
                <React.Fragment>
                  <div className="callout__body" style={{ marginBottom: 12 }}>{stepDef.body}</div>
                  <PipelineDiagram />
                </React.Fragment>
              ) : (
                <p className="callout__body" style={{ whiteSpace: 'pre-line' }}>{stepDef.body}</p>
              )}
              {actions}
            </div>
          </div>
        </div>
      );
    }

    // Spotlight steps (2, 3, 5, 6, 7).
    //
    // If the anchor isn't on the page yet and we haven't shown the skip toast,
    // we render only the dim+toast so the user gets visual feedback while the
    // 1.1 s skip timer ticks.
    if (!anchorRect) {
      return (
        <div className="tour-overlay" ref={overlayRef}>
          <div className="tour-scrim" />
          {skipToast && <SkipToast text={skipToast.text} />}
        </div>
      );
    }

    // Card placement (overflow-aware: right → below → left → above).
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const CW = 380;
    const G = 20;
    const CH_EST = 240;
    const clampY = (y) => Math.max(G, Math.min(y, vh - CH_EST - G));
    const clampX = (x) => Math.max(G, Math.min(x, vw - CW - G));
    const spaceRight = vw - anchorRect.right - G;
    const spaceBelow = vh - anchorRect.bottom - G;
    const spaceLeft = anchorRect.left - G;
    let calloutStyle = {};
    let arrowSide = 'left'; // arrow points TO the anchor (so on the SIDE of the card facing it)
    if (spaceRight >= CW + G) {
      calloutStyle = {
        position: 'fixed', top: clampY(anchorRect.top), left: anchorRect.right + G, width: CW,
      };
      arrowSide = 'left';
    } else if (spaceBelow >= CH_EST) {
      calloutStyle = {
        position: 'fixed', top: anchorRect.bottom + G, left: clampX(anchorRect.left), width: CW,
      };
      arrowSide = 'top';
    } else if (spaceLeft >= CW + G) {
      calloutStyle = {
        position: 'fixed', top: clampY(anchorRect.top), left: anchorRect.left - CW - G, width: CW,
      };
      arrowSide = 'right';
    } else {
      calloutStyle = {
        position: 'fixed',
        top: Math.max(G, anchorRect.top - CH_EST - G),
        left: clampX(anchorRect.left),
        width: CW,
      };
      arrowSide = 'bottom';
    }

    return (
      <div className="tour-overlay" ref={overlayRef}>
        <TourSpotlight rect={anchorRect} padding={12} />
        <div
          className={`callout tour-callout tour-callout--spotlight tour-callout--arrow-${arrowSide}`}
          ref={calloutRef}
          style={{ ...calloutStyle, zIndex: 100 }}
        >
          <div className="callout__step">STEP {stepDef.id} &middot; {stepDef.stepLabel}</div>
          <div className="callout__title">{stepDef.title}</div>
          <p className="callout__body" style={{ whiteSpace: 'pre-line' }}>{stepDef.body}</p>
          {actions}
        </div>
      </div>
    );
  }

  window.TourOverlay = TourOverlay;
})();
