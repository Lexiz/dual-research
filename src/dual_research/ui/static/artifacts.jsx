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
    ['system.web_sources',                    'Web search results'],
    ['system.tool_definitions',               'Tool definitions'],
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

  window.DrArtifacts = {
    REGISTRY,
    displayName,
    isKnown,
    truncateTitle,
    phaseOrderFor,
  };
})();
