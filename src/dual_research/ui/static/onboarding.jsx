// onboarding.jsx -- 3-screen first-time flow (SPEC-0061, NEW-03).
//
// Shows on first sign-in when localStorage 'dr_onboarded' is not 'true'.
// Pagination dots + next/prev + skip. Completion sets the flag.
// Reset via ?reset_onboarding=1 query param for testing.

(function () {
  const SCREENS = [
    {
      title: 'What is dual-research?',
      body: [
        'Two AI agents -- one Claude, one GPT -- hold a structured conversation to produce a single research document.',
        'They negotiate a plan, research independently, draft collaboratively, and then review each other\'s work adversarially.',
        'The result is a document with higher coverage and fewer blind spots than either agent could produce alone.',
      ],
      visual: 'duo',
    },
    {
      title: 'How a run works',
      body: [
        'Each run progresses through five phases: plan negotiation, independent research, collaborative drafting, final synthesis, and adversarial review.',
        'You can watch runs in real time as turns stream in, or read completed runs at your own pace.',
        'The timeline shows every turn with cost, token counts, and web search activity. The critique pane surfaces questions, disagreements, and issues.',
      ],
      visual: 'phases',
    },
    {
      title: 'Start exploring',
      body: [
        'The run list shows all completed and in-progress runs. Click any row to see the full detail view.',
        'Use Cmd+K to search across runs, or ? to see all keyboard shortcuts.',
        'To start a new run, use the CLI: uv run dual-research research "your topic here"',
      ],
      visual: 'cli',
    },
  ];

  function PhaseDiagram() {
    const phases = [
      { label: 'Plan', color: 'var(--fg-2)' },
      { label: 'Research', color: 'var(--agent-b)' },
      { label: 'Draft', color: 'var(--fg-1)' },
      { label: 'Synthesize', color: 'var(--agent-a)' },
      { label: 'Review', color: 'var(--warn)' },
    ];
    return (
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}>
        {phases.map((p, i) => (
          <React.Fragment key={i}>
            <div style={{
              padding: '6px 14px', borderRadius: 'var(--r-2)',
              background: 'var(--bg-2)', border: '1px solid var(--border-2)',
              fontSize: 12, color: p.color, fontWeight: 500,
              fontFamily: 'var(--mono)',
            }}>
              {i}. {p.label}
            </div>
            {i < phases.length - 1 && (
              <span style={{ color: 'var(--fg-3)', fontSize: 11 }}>&rarr;</span>
            )}
          </React.Fragment>
        ))}
      </div>
    );
  }

  function CliSnippet() {
    return (
      <div style={{
        background: 'var(--bg-2)', border: '1px solid var(--border-2)',
        borderRadius: 'var(--r-3)', padding: '12px 16px',
        fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--fg-1)',
        textAlign: 'left', maxWidth: 420, margin: '0 auto',
      }}>
        <div style={{ color: 'var(--fg-3)', marginBottom: 4 }}>$ terminal</div>
        <div><span style={{ color: 'var(--agent-a)' }}>uv run</span> dual-research research "your topic"</div>
      </div>
    );
  }

  function OnboardingScreen({ onComplete }) {
    const [step, setStep] = React.useState(0);
    const screen = SCREENS[step];

    const finish = () => {
      try { localStorage.setItem('dr_onboarded', 'true'); } catch (e) {}
      onComplete();
    };

    return (
      <div style={{
        position: 'fixed', inset: 0, zIndex: 100,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--bg-0)', color: 'var(--fg-0)',
      }}>
        <div style={{
          maxWidth: 520, width: '100%', padding: '32px 24px',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          gap: 24, textAlign: 'center',
        }}>
          {/* Visual */}
          <div style={{ minHeight: 120, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {screen.visual === 'duo' && <AgentDuoVisual />}
            {screen.visual === 'phases' && <PhaseDiagram />}
            {screen.visual === 'cli' && <CliSnippet />}
          </div>

          {/* Title */}
          <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.01em' }}>
            {screen.title}
          </div>

          {/* Body */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 440 }}>
            {screen.body.map((line, i) => (
              <div key={i} style={{ fontSize: 13, color: 'var(--fg-2)', lineHeight: 1.55 }}>
                {line}
              </div>
            ))}
          </div>

          {/* Pagination dots */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {SCREENS.map((_, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                aria-label={`Go to screen ${i + 1}`}
                style={{
                  width: i === step ? 20 : 8,
                  height: 8,
                  borderRadius: 999,
                  background: i === step ? 'var(--fg-1)' : 'var(--bg-3)',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  transition: 'width 0.15s ease',
                }}
              />
            ))}
          </div>

          {/* Navigation buttons */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            {step > 0 && (
              <button onClick={() => setStep(step - 1)} style={{
                padding: '8px 18px', borderRadius: 'var(--r-2)',
                border: '1px solid var(--border-2)', background: 'var(--bg-1)',
                color: 'var(--fg-1)', fontSize: 13, cursor: 'pointer',
                fontFamily: 'inherit',
              }}>
                Back
              </button>
            )}
            {step < SCREENS.length - 1 ? (
              <button onClick={() => setStep(step + 1)} style={{
                padding: '8px 18px', borderRadius: 'var(--r-2)',
                border: '1px solid var(--border-2)', background: 'var(--fg-1)',
                color: 'var(--bg-0)', fontSize: 13, fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
              }}>
                Next
              </button>
            ) : (
              <button onClick={finish} style={{
                padding: '8px 18px', borderRadius: 'var(--r-2)',
                border: '1px solid var(--border-2)', background: 'var(--fg-1)',
                color: 'var(--bg-0)', fontSize: 13, fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
              }}>
                Get started
              </button>
            )}
          </div>

          {/* Skip link */}
          {step < SCREENS.length - 1 && (
            <button onClick={finish} style={{
              background: 'none', border: 'none',
              color: 'var(--fg-3)', fontSize: 11,
              cursor: 'pointer', fontFamily: 'inherit',
              textDecoration: 'underline',
            }}>
              Skip intro
            </button>
          )}
        </div>
      </div>
    );
  }

  window.OnboardingScreen = OnboardingScreen;
})();
