// theme-toggle.jsx — Shared `ThemeToggle` primitive family.
//
// Spec 0024 introduced the compact dual-icon segmented pill that lives
// in the in-app `ChromeBar`'s right cluster. Spec 0176 extracts it
// here so the pre-login `LandingScreen` can mount the SAME primitive
// at the SAME X coordinate the post-login chrome occupies — the
// theme-icon doesn't shift position when the user signs in.
//
// Loaded as <script type="text/babel"> BEFORE auth.jsx and app.jsx in
// index.html (per spec 0176 §2.1). Publishes via Object.assign(window,
// …) to match the rest of the file-set's loading model.
//
// Visual change vs the inlined version: the `activeBg` prop overrides
// the active-segment background. The in-chrome consumer keeps the
// existing `var(--md-surface)` default; the login top-bar passes
// `"transparent"` so the spec-0176 §2.3 pulse wash hits the pill
// uniformly without the active segment blocking it.

(function () {
  'use strict';

  function SunIcon() {
    return (
      <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
           stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="8" cy="8" r="2.8"/>
        <path d="M8 1.5v1.4M8 13.1v1.4M1.5 8h1.4M13.1 8h1.4M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/>
      </svg>
    );
  }

  function MoonIcon() {
    return (
      <svg width="13" height="13" viewBox="0 0 16 16" fill="none"
           stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13.5 9.5A6 6 0 1 1 6.5 2.5 5 5 0 0 0 13.5 9.5Z"/>
      </svg>
    );
  }

  function ThemeIconBtn({ active, onClick, label, children, activeBg }) {
    // Spec 0176 §2.3 — `activeBg` is an optional override for the
    // active-segment background. Default = `var(--md-surface)` (the
    // pre-0176 behaviour). The login top-bar passes "transparent" so
    // the surrounding `.theme-pill` pulse wash composites uniformly.
    const effectiveActiveBg = activeBg != null ? activeBg : 'var(--md-surface)';
    return (
      <button
        onClick={onClick}
        aria-pressed={active}
        title={label}
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: 24, height: 22,
          background: active ? effectiveActiveBg : 'transparent',
          color: active ? 'var(--md-on-surface)' : 'var(--md-on-surface-faint)',
          border: active ? '1px solid var(--md-outline-hair)' : '1px solid transparent',
          borderRadius: 999,
          cursor: active ? 'default' : 'pointer',
          padding: 0, fontFamily: 'inherit',
        }}>
        {children}
      </button>
    );
  }

  // Compact single-pill theme toggle (spec 0024, extracted by spec 0176).
  // One container, two icon buttons side by side; the active one is
  // highlighted, clicking the inactive one flips the theme.
  function ThemeToggle({ theme, onToggle, activeBg }) {
    const isDark = theme === 'dark';
    const goLight = () => { if (isDark) onToggle(); };
    const goDark  = () => { if (!isDark) onToggle(); };
    return (
      <div style={{
        display: 'flex', alignItems: 'center',
        borderLeft: '1px solid var(--md-outline-hair)',
        padding: '0 10px',
      }}>
        <div role="group" aria-label="Theme"
             className="theme-pill"
             style={{
               position: 'relative',
               display: 'inline-flex', alignItems: 'center',
               background: 'var(--md-surface-container)',
               border: '1px solid var(--md-outline-hair)',
               borderRadius: 999,
               padding: 2,
               height: 26,
             }}>
          <ThemeIconBtn active={!isDark} onClick={goLight} label="Switch to light theme" activeBg={activeBg}>
            <SunIcon />
          </ThemeIconBtn>
          <ThemeIconBtn active={isDark} onClick={goDark} label="Switch to dark theme" activeBg={activeBg}>
            <MoonIcon />
          </ThemeIconBtn>
        </div>
      </div>
    );
  }

  Object.assign(window, { ThemeToggle, ThemeIconBtn, SunIcon, MoonIcon });
})();
