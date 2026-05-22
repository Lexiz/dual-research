function tagCardHeadChips(card) {
  // ITER 6 — tag each head chip with a semantic data-chip-role so subsequent
  // iterations can target them robustly even after reordering.
  var head = card.querySelector('.item-card__head');
  if (!head) return;
  Array.from(head.children).forEach(function(el){
    if (el.hasAttribute('data-chip-role')) return;
    var text = (el.textContent || '').trim();
    if (el.classList.contains('item-card__sources-chip')) {
      el.setAttribute('data-chip-role', 'sources');
    } else if (el.querySelector('code')) {
      el.setAttribute('data-chip-role', 'id');
    } else if (/^(Question|Disagreement|Issue|Comment|Claim)$/i.test(text)) {
      el.setAttribute('data-chip-role', 'kind');
    } else if (/^raised by /i.test(text)) {
      el.setAttribute('data-chip-role', 'raised-by');
    } else if (/^round \d+$/i.test(text)) {
      el.setAttribute('data-chip-role', 'round');
    } else if (el.classList.contains('chip')) {
      el.setAttribute('data-chip-role', 'state');
    }
  });
}

// ITER 7 — SVG markup for provider chips. Claude + GPT cloned from the
// bar2 agent chips in the same iframe (live dump); System has no bar2
// equivalent so the Material settings-gear path is inlined here.
function leadingIconForAgent(agent, doc) {
  if (agent === 'claude' || agent === 'gpt') {
    var src = doc.querySelector('.tab-group-solid[data-group="agent"] .chip[data-agent="' + agent + '"] .chip-leading-icon');
    return src ? src.outerHTML : '';
  }
  // System — Material settings-gear inside an idle-coloured square
  return `<span class="chip-leading-icon" aria-hidden="true"><span style="display: inline-flex; align-items: center; justify-content: center; width: 12px; height: 12px; border-radius: 3px; background: var(--p-idle, #5e636d); color: #ffffff; flex-shrink: 0; line-height: 1;"><svg viewBox="0 0 24 24" width="8" height="8" aria-hidden="true"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.07,0.94l-2.03,1.58c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z" fill="currentColor"></path></svg></span></span>`;
}

// Parse a round number. Handles "round 4", "at round 2", "Round 3 —",
// or the compact "R4" / "raised·R1" form used in our rewritten head chips.
function parseRoundN(text) {
  if (!text) return null;
  var m = /round\s+(\d+)/i.exec(text);
  if (m) return m[1];
  var m2 = /\bR(\d+)\b/.exec(text);
  return m2 ? m2[1] : null;
}

// Return the round number for the terminal-state event of a card.
// Sources, in priority: lifecycle-footer text ("resolved at round 2"),
// then the last item-card__transition's text.
function getTerminalRound(card) {
  var footer = card.querySelector('.item-card__lifecycle-footer');
  if (footer) {
    var n = parseRoundN(footer.textContent);
    if (n) return n;
  }
  var transitions = card.querySelectorAll('.item-card__transition .item-card__transition-meta');
  if (transitions.length) {
    var last = transitions[transitions.length - 1];
    var n2 = parseRoundN(last.textContent);
    if (n2) return n2;
  }
  return null;
}

// ITER 10 — return the actor who triggered the terminal-state transition.
// Parses the last .item-card__transition-meta's "by X" suffix.
// Returns "claude" | "gpt" | "orchestrator" | "system" | null.
function getTerminalActor(card) {
  var transitions = card.querySelectorAll('.item-card__transition .item-card__transition-meta');
  if (!transitions.length) return null;
  var last = transitions[transitions.length - 1];
  var m = /by\s+(\w+)/i.exec(last.textContent || '');
  if (!m) return null;
  var actor = m[1].toLowerCase();
  if (actor === 'claude' || actor === 'gpt' || actor === 'orchestrator' || actor === 'system') return actor;
  return null;
}

function rebuildCardHead(card, doc) {
  var head = card.querySelector('.item-card__head');
  if (!head || head.dataset.iter7 === 'true') return;

  // Extract data from the original chips before we wipe.
  var agent = card.getAttribute('data-raised-by') || 'system';
  var existingKind = head.querySelector('[data-chip-role="kind"]');
  var existingRound = head.querySelector('[data-chip-role="round"]');
  var existingState = head.querySelector('[data-chip-role="state"]');
  var kindText  = existingKind  ? (existingKind.textContent  || '').trim() : '';
  var roundText = existingRound ? (existingRound.textContent || '').trim() : '';
  var stateText = existingState ? (existingState.textContent || '').trim() : '';
  var stateToneClass = existingState ? Array.from(existingState.classList).find(function(c){ return /^tone-/.test(c); }) : '';

  var raisedRound = parseRoundN(roundText);
  var terminalRound = getTerminalRound(card);

  // Build the new chips.
  var providerLabel = agent === 'claude' ? 'Claude' : agent === 'gpt' ? 'GPT' : 'System';
  var providerTone = agent === 'claude' ? 'tone-claude' : agent === 'gpt' ? 'tone-gpt' : 'tone-neutral';
  var providerHTML = `<span class="chip ${providerTone} no-dot" data-chip-role="provider">${leadingIconForAgent(agent, doc)}<span class="chip-label">${providerLabel}</span></span>`;

  // ITER 8 — round chip carries `raised · R<N>` (was just `round N`).
  var roundLabel = raisedRound
    ? `raised<span class="chip-sep" aria-hidden="true">·</span>R${raisedRound}`
    : (roundText || 'round —');
  var roundHTML = `<span class="chip tone-neutral mono no-dot" data-chip-role="round"><span class="chip-label">${roundLabel}</span></span>`;

  var kindToneMap = { 'Question': 'tone-info', 'Disagreement': 'tone-warn', 'Issue': 'tone-err', 'Comment': 'tone-idle', 'Claim': 'tone-info' };
  var kindTone = kindToneMap[kindText] || 'tone-neutral';
  var kindHTML = kindText
    ? `<span class="chip ${kindTone} no-dot" data-chip-role="kind"><span class="chip-label">${kindText}</span></span>`
    : '';

  // ITER 9 — evidence-needed badge. When the card has an
  // .item-card__evidence-needed segment ("Evidence needed — addresses must
  // cite consulted sources."), surface it as a tiny icon-only chip with the
  // full sentence as a hover tooltip. The original segment is hidden by CSS.
  var evidenceSegment = card.querySelector('.item-card__evidence-needed');
  var evidenceHTML = '';
  if (evidenceSegment) {
    var rawText = (evidenceSegment.textContent || '').trim();
    var tooltipText = rawText.replace(/"/g, '&quot;').replace(/</g, '&lt;');
    evidenceHTML = `<span class="chip tone-info no-dot chip-icon-only evidence-chip" data-chip-role="evidence" title="${tooltipText}" role="img" aria-label="${tooltipText}"><span class="ms" aria-hidden="true">link</span></span>`;
  }

  // ITER 8 — state chip carries `<state> · R<N>` where N is the terminal round.
  // ITER 10 — also inject the resolver's logo between state and round:
  // `<state> · [actor icon] · R<N>`. Skip the icon if the actor is the
  // Orchestrator / System (they cap, not resolve in the agent sense).
  var terminalActor = getTerminalActor(card);
  var actorIconHTML = '';
  if (terminalActor === 'claude' || terminalActor === 'gpt') {
    var iconWithLabel = leadingIconForAgent(terminalActor, doc);
    actorIconHTML = `<span class="state-actor" aria-label="${terminalActor === 'claude' ? 'Claude' : 'GPT'}" title="${terminalActor === 'claude' ? 'Claude' : 'GPT'}">${iconWithLabel}</span>`;
  }
  var stateLabelParts = [];
  if (stateText) stateLabelParts.push(stateText);
  if (actorIconHTML) stateLabelParts.push(actorIconHTML);
  if (terminalRound) stateLabelParts.push(`R${terminalRound}`);
  var stateLabel = stateLabelParts.join('<span class="chip-sep" aria-hidden="true">·</span>');
  var stateHTML = stateText
    ? `<span class="chip ${stateToneClass || 'tone-neutral'} no-dot" data-chip-role="state"><span class="chip-label">${stateLabel}</span></span>`
    : '';

  // Wipe and rebuild. ID chip + sources chip dropped per user direction;
  // can be re-added in a later iter if needed.
  head.innerHTML = providerHTML + roundHTML + kindHTML + evidenceHTML + stateHTML;
  head.dataset.iter7 = 'true';
}

// ITER 12 — parse a transition meta line.
// Format: "Round N — A → B (modifier) · by ACTOR"
function parseTransition(meta) {
  var text = (meta.textContent || '').trim();
  var html = meta.innerHTML || '';
  var roundM   = /round\s+(\d+)/i.exec(text);
  var verbM    = /→\s*<strong>([\w]+)<\/strong>/.exec(html) || /→\s+(\w+)/.exec(text);
  var modM     = /\(([\w_]+)\)/.exec(text);
  var actorM   = /by\s+(\w+)/i.exec(text);
  return {
    round: roundM ? roundM[1] : null,
    verb: verbM ? verbM[1].toLowerCase() : null,
    modifier: modM ? modM[1] : null,
    actor: actorM ? actorM[1].toLowerCase() : null
  };
}

var VERB_TONE = {
  raised:       'tone-info',
  addressed:    'tone-warn',
  resolved:     'tone-ok',
  acknowledged: 'tone-warn',
  capped:       'tone-err',
  withdrawn:    'tone-idle',
  ghosted:      'tone-warn',
  drift:        'tone-err'
};

function escapeText(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Build one lifecycle row: chip cluster (provider · round · verb · modifier · extras) + italic quote.
function buildLifecycleRow(opts, doc) {
  var providerHTML = '';
  if (opts.actor === 'claude' || opts.actor === 'gpt') {
    var label = opts.actor === 'claude' ? 'Claude' : 'GPT';
    var tone = opts.actor === 'claude' ? 'tone-claude' : 'tone-gpt';
    providerHTML = `<span class="chip ${tone} no-dot lc-provider">${leadingIconForAgent(opts.actor, doc)}<span class="chip-label">${label}</span></span>`;
  }
  var roundHTML = opts.round
    ? `<span class="chip tone-neutral mono no-dot lc-round"><span class="chip-label">round ${opts.round}</span></span>`
    : '';
  var verbTone = VERB_TONE[opts.verb] || 'tone-neutral';
  var verbHTML = opts.verb
    ? `<span class="chip ${verbTone} no-dot lc-verb"><span class="chip-label">${opts.verb}</span></span>`
    : '';
  var modifierHTML = opts.modifier
    ? `<span class="chip tone-neutral no-dot lc-modifier"><span class="chip-label">via ${opts.modifier.replace(/_/g, ' ')}</span></span>`
    : '';
  // ITER 13 — optional extras (source requested / source provided)
  var extrasHTML = '';
  (opts.extras || []).forEach(function(ex){
    if (ex === 'source-requested') {
      extrasHTML += `<span class="chip tone-info no-dot lc-extra" data-extra="source-requested"><span class="ms" aria-hidden="true" style="font-size:11px;vertical-align:-2px;">link</span><span class="chip-label">source requested</span></span>`;
    } else if (ex === 'source-provided') {
      extrasHTML += `<span class="chip tone-ok no-dot lc-extra" data-extra="source-provided"><span class="ms" aria-hidden="true" style="font-size:11px;vertical-align:-2px;">link</span><span class="chip-label">source provided</span></span>`;
    }
  });
  var quoteText = escapeText(opts.quote || '');
  var quoteHTML = quoteText
    ? `<p class="lc-row-quote">&ldquo;${quoteText}&rdquo;</p>`
    : '';
  return `<div class="lc-row" data-actor="${opts.actor || 'orchestrator'}"><div class="lc-row-chips">${providerHTML}${roundHTML}${verbHTML}${modifierHTML}${extrasHTML}</div>${quoteHTML}</div>`;
}

// Rebuild the expanded card view as a Lifecycle section: each round is a
// [provider · round · verb] chip cluster followed by an italic quote.
function rebuildExpandedView(card, doc) {
  if (card.dataset.iter12 === 'true') return;
  var body = card.querySelector('.item-card__body');
  var timeline = card.querySelector('.item-card__timeline');
  if (!body || !timeline) return;
  card.dataset.iter12 = 'true';

  // Extract item body text — the original raise statement. Strip the anchor
  // blockquote so it doesn't end up duplicated in the quote.
  var bodyClone = body.cloneNode(true);
  var anchor = bodyClone.querySelector('.item-card__anchor');
  if (anchor) anchor.remove();
  var bodyText = (bodyClone.textContent || '').trim();

  var raisedAgent = card.getAttribute('data-raised-by') || 'system';
  var raisedRoundChip = card.querySelector('[data-chip-role="round"] .chip-label');
  var raisedRound = raisedRoundChip ? parseRoundN(raisedRoundChip.textContent) : null;

  // ITER 13 — source-requested / source-provided badges.
  var hasEvidenceNeeded = !!card.querySelector('.item-card__evidence-needed');
  var hasSources = !!card.querySelector('.item-card__sources');
  // Find the first Claude/GPT transition — that's where sources were provided.
  var sourceProviderTransitionIndex = -1;
  var sourceProviderMeta = null;
  var transitionsAll = Array.from(timeline.querySelectorAll('.item-card__transition'));
  for (var i = 0; i < transitionsAll.length; i++) {
    var meta = transitionsAll[i].querySelector('.item-card__transition-meta');
    if (!meta) continue;
    var pa = parseTransition(meta);
    if (pa.actor === 'claude' || pa.actor === 'gpt') {
      sourceProviderTransitionIndex = i;
      sourceProviderMeta = pa;
      break;
    }
  }

  // Row 1: synthetic raised event, using body text as the quote
  var rows = [];
  rows.push(buildLifecycleRow({
    actor: raisedAgent,
    round: raisedRound,
    verb: 'raised',
    modifier: null,
    quote: bodyText,
    extras: hasEvidenceNeeded ? ['source-requested'] : []
  }, doc));

  // Subsequent rows: each transition becomes a lifecycle row
  transitionsAll.forEach(function(t, idx){
    var meta = t.querySelector('.item-card__transition-meta');
    var reason = t.querySelector('.item-card__transition-reason');
    if (!meta) return;
    var p = parseTransition(meta);
    var actor = (p.actor === 'claude' || p.actor === 'gpt') ? p.actor : null;
    var extras = [];
    if (hasSources && idx === sourceProviderTransitionIndex) extras.push('source-provided');
    rows.push(buildLifecycleRow({
      actor: actor,
      round: p.round,
      verb: p.verb,
      modifier: p.modifier,
      quote: reason ? reason.textContent.trim() : '',
      extras: extras
    }, doc));
  });

  // ITER 13 — annotate each source-row with a "round N · provider" chip in its head.
  if (hasSources && sourceProviderMeta) {
    var sourcesEl = card.querySelector('.item-card__sources');
    var sourceRows = sourcesEl ? sourcesEl.querySelectorAll('.source-row') : [];
    sourceRows.forEach(function(row){
      var head = row.querySelector('.source-row__head');
      if (!head || head.dataset.iter13Meta === 'true') return;
      head.dataset.iter13Meta = 'true';
      var agent = sourceProviderMeta.actor;
      var agentLabel = agent === 'claude' ? 'Claude' : 'GPT';
      var iconHTML = leadingIconForAgent(agent, doc);
      var metaChipHTML = `<span class="chip tone-neutral mono no-dot source-meta-chip" title="Provided by ${agentLabel} in round ${sourceProviderMeta.round}">${iconHTML}<span class="chip-label">R${sourceProviderMeta.round}</span></span>`;
      // Insert before the unverified chip if present (in .right wrapper), else before chevron's host span at end.
      var rightWrap = head.querySelector('.right');
      if (rightWrap) {
        rightWrap.insertAdjacentHTML('beforebegin', metaChipHTML);
      } else {
        head.insertAdjacentHTML('beforeend', metaChipHTML);
      }
    });
  }

  // Hide the original body + timeline; inject new lifecycle section after head.
  body.style.display = 'none';
  timeline.style.display = 'none';

  var wrapper = doc.createElement('section');
  wrapper.className = 'item-card__lifecycle iter12';
  wrapper.innerHTML = '<div class="item-card__lifecycle-hd">Lifecycle</div>' + rows.join('');
  // Place right after the head (and after iter-9's evidence-needed hidden line).
  var head = card.querySelector('.item-card__head');
  head.insertAdjacentElement('afterend', wrapper);
}

function initCollapseState(){
  // ITER 4 default: Resolved section unfolds by default; cards default collapsed.
  document.querySelectorAll('.crit-group').forEach(function(g){
    g.setAttribute('data-collapsed', 'false');
  });
  document.querySelectorAll('.item-card').forEach(function(c){
    // Detect raised-by agent for the provider stripe
    var headText = ((c.querySelector('.item-card__head')||{}).textContent || '').toLowerCase();
    if (headText.indexOf('raised by claude') >= 0) c.setAttribute('data-raised-by', 'claude');
    else if (headText.indexOf('raised by gpt') >= 0) c.setAttribute('data-raised-by', 'gpt');
    else c.setAttribute('data-raised-by', 'system');
    // Default to collapsed
    c.setAttribute('data-expanded', 'false');
    // ITER 6 — tag head chips by semantic role (needed before iter-7 rebuild)
    tagCardHeadChips(c);
    // ITER 7 — rebuild head with the new chip order + provider identity chip
    rebuildCardHead(c, document);
    // ITER 12 — rebuild the expanded view as a Lifecycle section
    rebuildExpandedView(c, document);
  });
  document.querySelectorAll('.source-row__head').forEach(function(h){
    h.setAttribute('aria-expanded', 'false');
  });
  // ITER 14 — pre-expand the FIRST source-row inside each card so the user
  // can see both the collapsed (other rows) and expanded (first row)
  // visualisations side-by-side. Cards with one source still get the
  // expanded view by default; click to collapse.
  document.querySelectorAll('.item-card__sources').forEach(function(s){
    var firstHead = s.querySelector('.source-row__head');
    if (firstHead) firstHead.setAttribute('aria-expanded', 'true');
  });
  // ITER 15 — auto-expand the FIRST card with sources in each phase-state so
  // the source UI is visible at the bottom of the card without any clicks.
  // Other cards in the same phase stay collapsed so the user can see both
  // the compact and the expanded states side-by-side.
  document.querySelectorAll('.phase-state').forEach(function(ps){
    var firstWithSources = ps.querySelector('.item-card:has(.item-card__sources)') ||
      Array.from(ps.querySelectorAll('.item-card')).find(function(c){ return c.querySelector('.item-card__sources'); });
    if (firstWithSources) firstWithSources.setAttribute('data-expanded', 'true');
  });
}
// ITER 1 — wrap kind cluster + create agent / status segmented controls
// + add drift-chip slot. Kind cluster wrapper is purely a flex group
// (no visual restyling); the segmented controls are the DS pattern.
function setChipCount(chip, count) {
  var v = chip.querySelector('.chip-value');
  if (!v) {
    v = document.createElement('span');
    v.className = 'chip-value';
    chip.appendChild(v);
  }
  v.textContent = String(count);
}

function applyIter1(root){
  root.querySelectorAll('.bar2.crit-filter-row').forEach(function(bar2){
    if (bar2.dataset.iter1 === 'true') return;
    bar2.dataset.iter1 = 'true';
    var children = Array.from(bar2.children);
    var clusters = [];
    var cur = [];
    children.forEach(function(c){
      if (c.classList.contains('crit-filter-spacer')) {
        if (cur.length) { clusters.push(cur); cur = []; }
      } else {
        cur.push(c);
      }
    });
    if (cur.length) clusters.push(cur);
    if (clusters.length !== 3) return;

    var kindWrap = document.createElement('div');
    kindWrap.className = 'kind-tabs';
    clusters[0][0].parentNode.insertBefore(kindWrap, clusters[0][0]);
    clusters[0].forEach(function(el){ kindWrap.appendChild(el); });

    // ITER 2 — drop the explicit "All" buttons from agent + status segments.
    // The kind cluster's "All (13)" chip is the global reset; the segmented
    // controls are toggle groups (click an active option to deselect = show
    // all of that filter). This saves ~136px of horizontal space so the
    // whole bar2 fits on one row at wide.
    var statusWrap = document.createElement('div');
    statusWrap.className = 'tab-group-solid';
    statusWrap.dataset.group = 'status';
    clusters[1].forEach(function(el){ statusWrap.appendChild(el); });

    var agentWrap = document.createElement('div');
    agentWrap.className = 'tab-group-solid';
    agentWrap.dataset.group = 'agent';
    clusters[2].forEach(function(el){
      var t = (el.getAttribute('title') || '').toLowerCase();
      if (t.indexOf('claude') >= 0) el.setAttribute('data-agent', 'claude');
      else if (t.indexOf('gpt') >= 0) el.setAttribute('data-agent', 'gpt');
      agentWrap.appendChild(el);
    });

    bar2.appendChild(agentWrap);
    bar2.appendChild(statusWrap);
    bar2.querySelectorAll('.crit-filter-spacer').forEach(function(s){ s.remove(); });

    // Compute counts from the cards in this phase-state and inject (N) on every
    // option label. Status chips for Open/Resolved already carry chip-value from
    // the live dump; Drift in the live impl skips it (drift 3.K) so we always
    // backfill. Agent chips get counts injected here.
    var phaseState = bar2.closest('.phase-state') || bar2.closest('.crit2');
    if (phaseState) {
      var cards = Array.from(phaseState.querySelectorAll('.item-card'));
      var counts = { all: cards.length, claude: 0, gpt: 0, drift: 0 };
      cards.forEach(function(card){
        var headText = ((card.querySelector('.item-card__head')||{}).textContent || '').toLowerCase();
        if (headText.indexOf('raised by claude') >= 0) counts.claude++;
        if (headText.indexOf('raised by gpt') >= 0) counts.gpt++;
        if (card.classList.contains('item-card--drift')) counts.drift++;
      });
      agentWrap.querySelectorAll('.chip[data-agent="claude"]').forEach(function(c){ setChipCount(c, counts.claude); });
      agentWrap.querySelectorAll('.chip[data-agent="gpt"]').forEach(function(c){ setChipCount(c, counts.gpt); });
      var driftChip = statusWrap.querySelector('.chip.tone-warn');
      if (driftChip && !driftChip.querySelector('.chip-value')) setChipCount(driftChip, counts.drift);
    }
  });

  root.querySelectorAll('.crit2 .bar1 .right').forEach(function(right){
    if (right.querySelector('.drift-chip')) return;
    var chip = document.createElement('span');
    chip.className = 'drift-chip';
    chip.dataset.count = '0';
    chip.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2L1 21h22L12 2zm0 4.5L19.5 19h-15L12 6.5zm-1 5v4h2v-4h-2zm0 5v2h2v-2h-2z"/></svg>0 drift';
    right.appendChild(chip);
  });
}
applyIter1(document);
// Run init AFTER applyIter1 so rebuildCardHead's provider-icon lookup
// finds the agent chips with data-agent already set.
initCollapseState();

function phaseKeyFromTab(tab){
  var pcode = tab.querySelector('.pcode');
  var sigma = tab.querySelector('.sigma');
  if (sigma) return 'sigma';
  if (pcode) return (pcode.textContent||'').trim().toLowerCase();
  return null;
}

document.addEventListener('click', function(e){
  var srcHd = e.target.closest && e.target.closest('.source-row__head');
  if (srcHd) {
    var cur = srcHd.getAttribute('aria-expanded') === 'true';
    srcHd.setAttribute('aria-expanded', cur ? 'false' : 'true');
    e.preventDefault();
    return;
  }
  var cardHd = e.target.closest && e.target.closest('.item-card__head');
  if (cardHd) {
    if (e.target.closest('button, a')) return;
    var card = cardHd.closest('.item-card');
    if (card) {
      var cur = card.getAttribute('data-expanded') !== 'false';
      card.setAttribute('data-expanded', cur ? 'false' : 'true');
      e.preventDefault();
      return;
    }
  }
  var segChip = e.target.closest && e.target.closest('.tab-group-solid .chip');
  if (segChip) {
    var group = segChip.closest('.tab-group-solid');
    var wasActive = segChip.getAttribute('data-active') === 'true';
    group.querySelectorAll('.chip').forEach(function(c){ c.removeAttribute('data-active'); });
    // Toggle: click an active chip to deselect (means "no filter = show all").
    if (!wasActive) segChip.setAttribute('data-active', 'true');
    e.preventDefault();
    return;
  }
  // ITER 3 — kind cluster behaves the same way: no chip active = "show all".
  // Click an active kind chip to deselect.
  var kindChip = e.target.closest && e.target.closest('.kind-tabs .chip[data-kind-filter]');
  if (kindChip) {
    var kt = kindChip.closest('.kind-tabs');
    var wasActive = kindChip.getAttribute('data-active') === 'true';
    kt.querySelectorAll('.chip[data-kind-filter]').forEach(function(c){ c.removeAttribute('data-active'); });
    if (!wasActive) kindChip.setAttribute('data-active', 'true');
    e.preventDefault();
    return;
  }
  var hd = e.target.closest && e.target.closest('.crit-group__hd');
  if (hd) {
    var grp = hd.closest('.crit-group');
    if (grp) {
      var open = grp.getAttribute('data-collapsed') !== 'true';
      grp.setAttribute('data-collapsed', open ? 'true' : 'false');
      e.preventDefault();
      return;
    }
  }
  var tab = e.target.closest && e.target.closest('.phase-tab');
  if (!tab) return;
  var key = phaseKeyFromTab(tab);
  if (!key) return;
  document.querySelectorAll('.phase-state').forEach(function(s){
    s.classList.toggle('is-visible', s.dataset.phase === key);
  });
  document.querySelectorAll('.phase-state').forEach(function(s){
    s.querySelectorAll('.phase-tab').forEach(function(t){
      t.classList.toggle('is-active', phaseKeyFromTab(t) === key);
    });
  });
  e.preventDefault();
});
