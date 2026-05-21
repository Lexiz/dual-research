// Spec 0117 — JS-side mirror of the Python artifact registry.
//
// The Python file at src/dual_research/contract/artifacts.py is the
// single source of truth for canonical artifact IDs and display
// templates. This file mirrors the same data so JSX surfaces can
// resolve display names without round-tripping to a REST endpoint.
//
// IF YOU EDIT THE PYTHON REGISTRY, UPDATE THIS FILE TOO.
// A pytest in tests/contract/test_artifacts_registry_sync.py
// fails CI if the two diverge.

(function () {
  const REGISTRY = [
    ['system.preamble',                       'Methodology preamble'],
    ['system.task.input',                     'Preflight instructions'],
    ['system.task.research_plan',             'Research-plan instructions'],
    ['system.task.plan_negotiation',          'Plan-negotiation instructions'],
    ['system.task.drafting',                  'Drafting instructions'],
    ['system.task.review',                    'Review instructions'],
    ['system.task.closeout',                  'Closeout instructions'],
    ['user_prompt',                           'User prompt'],
    ['user_prompt.message',                   'Chat message'],
    ['user_prompt.attachment.<id>',           'Attachment · {title}'],
    ['prior_turns.phase0',                    'Prior preflight turns'],
    ['prior_turns.phase2',                    'Prior negotiation turns'],
    ['prior_turns.phase4',                    'Prior review turns'],
    ['ledger.standing_items',                 'Ledger (standing items)'],
    ['closeout.request',                      'Closeout request'],
    ['phase0.<agent>.r<N>',                   'Preflight turn · {agent} · round {n}'],
    ['phase1.claude',                         "Claude's research plan"],
    ['phase1.openai',                         "GPT's research plan"],
    ['phase2.<agent>.r<N>',                   'Negotiation turn · {agent} · round {n}'],
    ['phase3.draft.v1',                       'Initial unified draft (v1)'],
    ['phase4.<agent>.r<N>',                   'Review turn · {agent} · round {n}'],
    ['phase4.draft.v<N>',                     'Revised draft v{n}'],
    ['current_draft',                         'Current draft (latest version)'],
    ['all_p2_turns',                          'All negotiation turns'],
    ['phase0.agreement.interpretation',       'Agreed interpretation'],
    ['phase2.agreement.plan',                 'Agreed plan'],
    ['phase2.agreement.drafter',              'Drafter selection'],
    ['phase4.agreement.draft_acceptance',     'Agreed draft acceptance'],
    ['carry_forward.phase0',                  'Carry-forward items (phase 0)'],
    ['carry_forward.phase2',                  'Carry-forward items (phase 2)'],
    ['carry_forward.phase4',                  'Carry-forward items (phase 4)'],
    ['all_carry_forward',                     'All carry-forward items'],
    ['final.document',                        'Final document'],
  ];

  const AGENT_DISPLAY = { claude: 'Claude', openai: 'GPT', gpt: 'GPT' };

  function templateToRegex(idTemplate) {
    // Escape regex metacharacters, then swap the three placeholders
    // with named capture groups. Mirrors the Python implementation.
    let pattern = idTemplate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    pattern = pattern.replace('<agent>', '(?<agent>claude|openai|gpt)');
    pattern = pattern.replace('<N>', '(?<n>\\d+)');
    pattern = pattern.replace('<id>', '(?<id>[^.]+(?:\\..+)?)');
    return new RegExp('^' + pattern + '$');
  }

  const REGISTRY_REGEX = REGISTRY.map(([id, display]) => [
    id, display, templateToRegex(id),
  ]);

  function displayName(artifactId, { titleForId } = {}) {
    if (typeof artifactId !== 'string' || !artifactId) return artifactId;
    for (const [, display, rx] of REGISTRY_REGEX) {
      const m = rx.exec(artifactId);
      if (!m) continue;
      const groups = m.groups || {};
      const subs = {};
      if (groups.agent) subs.agent = AGENT_DISPLAY[groups.agent] || groups.agent;
      if (groups.n) subs.n = groups.n;
      if (groups.id) {
        const raw = groups.id;
        subs.title = (titleForId && titleForId[raw]) || raw;
      }
      return display.replace(/\{(agent|n|title)\}/g, (_, k) => (
        subs[k] !== undefined ? subs[k] : '{' + k + '}'
      ));
    }
    return artifactId;
  }

  function isKnown(artifactId) {
    if (typeof artifactId !== 'string' || !artifactId) return false;
    if (REGISTRY.some(([id]) => id === artifactId)) return true;
    return REGISTRY_REGEX.some(([, , rx]) => rx.test(artifactId));
  }

  function truncateTitle(title, max = 40) {
    // Spec 0117 OQ-4 default: truncate to 40 chars + ellipsis;
    // callers keep the full title for tooltips.
    if (typeof title !== 'string') return title;
    if (title.length <= max) return title;
    return title.slice(0, max - 1).trimEnd() + '…';
  }

  // ─── Spec 0145 — per-phase arrival order ────────────────────────────
  //
  // The canonical-ID order in which the modal renders piece rows for
  // each phase. The trailing 'user_prompt.attachment.*' sentinel is
  // expanded in render code into one row per attachment in the order
  // they appear in `pieces`.
  const PHASE_ORDER = {
    0: [
      'system.task.input',
      'user_prompt.message',
      'user_prompt.attachment.*',
      'prior_turns.phase0',
      'ledger.standing_items',
      'closeout.request',
    ],
    1: [
      'system.task.research_plan',
      'user_prompt.message',
      'user_prompt.attachment.*',
      'phase0.agreement.interpretation',
    ],
    2: [
      'system.task.plan_negotiation',
      'user_prompt.message',
      'user_prompt.attachment.*',
      'phase0.agreement.interpretation',
      'phase1.claude',
      'phase1.openai',
      'prior_turns.phase2',
      'ledger.standing_items',
      'closeout.request',
    ],
    3: [
      'system.task.drafting',
      'user_prompt.message',
      'user_prompt.attachment.*',
      'phase0.agreement.interpretation',
      'phase1.claude',
      'phase1.openai',
      'phase2.agreement.plan',
      'all_p2_turns',
      'carry_forward.phase2',
    ],
    4: [
      'system.task.review',
      'user_prompt.message',
      'user_prompt.attachment.*',
      'current_draft',
      'prior_turns.phase4',
      'ledger.standing_items',
      'closeout.request',
    ],
  };

  function phaseOrderFor(phaseNum) {
    const key = Number(phaseNum);
    return PHASE_ORDER[key] ? PHASE_ORDER[key].slice() : [];
  }

  // Spec 0145 §5.4 / Goal 5 — legacy short-key → canonical-ID shim.
  // Translates historical runs (the anchor run included) into the new
  // vocabulary on the read path. Both `pieces` text bundles (from
  // `inputs/<turnKey>.json`) and `prompt_pieces` token dicts (from
  // pre-spec `turn_ended` events) flow through this map.
  //
  // REMOVE AFTER 2026-08-19 (90 days post-merge; sunset follow-up
  // backfills any remaining legacy data through one push pass and
  // drops both this shim and the legacy `user_prompt` `ArtifactDef`).
  const LEGACY_KEY_TO_CANONICAL = {
    system: 'system.task.input',         // phase-specific in practice
    brief:  'user_prompt.message',
    d1:     'phase1.claude',
    d2:     'phase1.openai',
    plan:   'phase2.agreement.plan',
    hist:   'prior_turns.phase2',
    draft:  'current_draft',
    histp:  'prior_turns.phase4',
  };

  // Spec 0145 — phase-aware overrides for the `system` legacy key.
  // The legacy bundle's `system` slot always held the per-phase task
  // template; the canonical equivalent depends on the phase. The shim
  // accepts an optional `phaseNum` and resolves the system key to its
  // phase-specific canonical sibling.
  const LEGACY_SYSTEM_BY_PHASE = {
    0: 'system.task.input',
    1: 'system.task.research_plan',
    2: 'system.task.plan_negotiation',
    3: 'system.task.drafting',
    4: 'system.task.review',
  };

  function canonicaliseLegacyKey(legacyKey, opts) {
    if (typeof legacyKey !== 'string' || !legacyKey) return legacyKey;
    const phaseNum = opts && Number.isFinite(Number(opts.phaseNum))
      ? Number(opts.phaseNum)
      : null;
    if (legacyKey === 'system' && phaseNum !== null) {
      return LEGACY_SYSTEM_BY_PHASE[phaseNum] || 'system.task.input';
    }
    if (Object.prototype.hasOwnProperty.call(LEGACY_KEY_TO_CANONICAL, legacyKey)) {
      return LEGACY_KEY_TO_CANONICAL[legacyKey];
    }
    return legacyKey;
  }

  // Returns true iff at least one key on the dict looks canonical (i.e.,
  // contains a dot — every canonical ID is dotted, every legacy short
  // key is single-segment). Callers use this to decide whether the
  // shim needs to run.
  function hasCanonicalKey(pieces) {
    if (!pieces || typeof pieces !== 'object') return false;
    for (const k of Object.keys(pieces)) {
      if (typeof k === 'string' && k.includes('.')) return true;
    }
    return false;
  }

  // Map a (possibly legacy-keyed) `pieces` dict into a canonical-keyed
  // one. Idempotent: a fully-canonical input is returned as-is. Mixed
  // input is normalised; unknown keys pass through unchanged.
  function canonicalisePieces(pieces, opts) {
    if (!pieces || typeof pieces !== 'object') return pieces;
    if (hasCanonicalKey(pieces) && !Object.keys(pieces).some(
      (k) => Object.prototype.hasOwnProperty.call(LEGACY_KEY_TO_CANONICAL, k),
    )) {
      return pieces;
    }
    const out = {};
    for (const [k, v] of Object.entries(pieces)) {
      const canon = canonicaliseLegacyKey(k, opts);
      out[canon] = v;
    }
    return out;
  }

  window.DrArtifacts = {
    REGISTRY,
    displayName,
    isKnown,
    truncateTitle,
    // Spec 0145 additions:
    phaseOrderFor,
    canonicaliseLegacyKey,
    canonicalisePieces,
    hasCanonicalKey,
    LEGACY_KEY_TO_CANONICAL,
  };
})();
