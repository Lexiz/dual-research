// Spec 0119 — JS-side helper for item-lifecycle verb labels.
//
// Maps a (fromState, toState) lifecycle transition to the canonical
// short verb used inside Chip labels on critique-card lifecycle rows.
//
// The transition table mirrors the canonical TRANSITIONS dict in
// src/dual_research/contract/lifecycle.py. A pytest in
// tests/contract/test_lifecycle_verbs_sync.py fails CI if the JS
// covers any (from, to) pair the Python table doesn't allow, or
// misses any pair the Python table does allow.
//
// IF YOU EDIT THE PYTHON TRANSITIONS TABLE, UPDATE THIS FILE TOO.

(function () {
  // ─── Verb table ───────────────────────────────────────────────
  // (fromState, toState) → verb chip label.
  //
  // The keys use "->" separator (not "→") so the file is easy to
  // grep and parse from Python.
  //
  // `addressed->open` corresponds to a raiser counter-arguing an
  // addressee's response; the verb "raised again" reads better than
  // "open" in the lifecycle stream.
  const VERBS = {
    'open->addressed':         'addressed',
    'open->withdrawn':         'withdrawn',
    'addressed->resolved':     'resolved',
    'addressed->open':         'raised again',
    'addressed->withdrawn':    'withdrawn',
    'addressed->acknowledged': 'acknowledged',
  };

  // Set of terminal states — mirrors TERMINAL_STATES in
  // contract/lifecycle.py.
  const TERMINAL = new Set(['resolved', 'acknowledged', 'withdrawn', 'capped']);

  // Resolve the canonical verb for a transition.
  //
  //   • `fromState == null`     — item creation, verb is `raised`.
  //   • `toState === 'capped'`  — orchestrator cap from any state.
  //   • otherwise               — VERBS[from + '->' + to], else the
  //                               raw `toState` as a last-resort
  //                               fallback (keeps the renderer
  //                               honest even if a new transition
  //                               slips in before the table catches
  //                               up).
  function lifecycleVerb(fromState, toState) {
    if (fromState == null) return 'raised';
    if (toState === 'capped') return 'capped';
    return VERBS[fromState + '->' + toState] || toState;
  }

  function isTerminal(state) {
    return TERMINAL.has(state);
  }

  window.DrLifecycle = { lifecycleVerb, isTerminal, VERBS, TERMINAL };
})();
