#!/usr/bin/env bash
# Assembles live.html and proposed.html for the timeline workshop.
# Mirrors prototypes/critique-iteration/_build.sh but with the TIMELINE pane
# as the focus and the CRITIQUE pane as a filler stub on the right.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
TIMELINE_DUMP="$DIR/_dump-timeline.html"            # verbatim live dump (no mutations)
TIMELINE_PROPOSED="$DIR/_dump-timeline-proposed.html"  # same dump with iter-1/2/3 DOM mutations baked in
CRITIQUE_STUB="$DIR/_dump-critique-stub.html"       # .crit2 stub (bar1 + bar2 + empty body)
JS_BODY="$DIR/_inline-script.js"

# Shared CSS injected into BOTH live.html and proposed.html. Wraps the 2-pane
# shell, constrains html/body to the iframe viewport, and provides the workshop
# collapse affordance (cards that don't have .is-open-expanded hide body+actions).
shared_workshop_styles() {
cat <<'CSSJS'
<style id="wrapper-styles">
  html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
  body { background: var(--md-surface, #0f1115); color: var(--md-on-surface, #d9dee5); font-family: var(--md-font-plain, system-ui, sans-serif); }
  .wrap__banner {
    position: sticky; top: 0; z-index: 10;
    background: var(--md-surface-container, #14171c);
    border-bottom: 1px solid var(--md-outline-hair, #1c1f24);
    padding: 8px 16px; font-size: 11.5px; line-height: 1.4;
    color: var(--md-on-surface-variant, #a7adb6);
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
    font-family: var(--md-font-data, ui-monospace, SF Mono, monospace);
  }
  .wrap__banner b { color: var(--md-on-surface); }
  .wrap__banner .pill { background: var(--md-surface-container-high, #191c21); padding: 2px 8px; border-radius: 10px; }
  body { display: flex; flex-direction: column; }
  .wrap__stage { padding: 0; flex: 1 1 0%; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .wrap__stage > .timeline-host { background: var(--md-surface, #0f1115); display: flex; flex-direction: column; min-height: 0; min-width: 0; border-right: 1px solid var(--md-outline-hair); overflow: hidden; }
  .wrap__stage > .critique-stub { background: var(--md-surface, #0f1115); display: flex; flex-direction: column; min-height: 0; min-width: 0; overflow: hidden; }
  /* Timeline pane host should fill its column. The dumped .rdvc__pane uses
     display: flex flex-direction: column to lay out tl__head, tl__tabs, tl__body. */
  .wrap__stage > .timeline-host > .rdvc__pane {
    flex: 1 1 0%; min-height: 0; min-width: 0;
    border-right: 0 !important;
  }
  .wrap__stage > .critique-stub > .rdvc__pane {
    flex: 1 1 0%; min-height: 0; min-width: 0;
  }
</style>
<style id="workshop-collapse-affordance">
  /* Hide expanded-card children when the card does NOT have .is-open-expanded.
     The iter-5 CSS styles .tl-thread.is-open-expanded for the visible-expanded
     state; this rule simply hides body + actions for collapsed cards so the
     toggle handler in _inline-script.js works visually. */
  .tl-thread:not(.is-open-expanded) > .tl-thread__body,
  .tl-thread:not(.is-open-expanded) > .tl-thread__actions { display: none !important; }
  .tl-card-head { cursor: pointer; }
  /* Collapsed phase: hide the body. Phase headers default per dump. */
  .tl-phase[data-collapsed="true"] > .tl-phase__body { display: none !important; }
  .tl-phase[data-collapsed="true"] .tl-phase__hd .chev .ms { transform: rotate(-90deg); }
  .tl-phase__hd .chev .ms { transition: transform 150ms ease; }
</style>
CSSJS
}

# All iter style blocks (4-13). Iter 1, 2, 3 are DOM mutations baked into
# _dump-timeline-proposed.html, not stylesheets — so they're not in this list.
iter_styles() {
cat <<'CSSITER'
<style id="iter-13-narrow-strip-equalise">
  /* =========================================================
     Iter 13 — equalise + right-align both agent strips in narrow view

     Problem: at narrow workshop preset (1280px iframe → ~640px per pane),
     the GPT strip in .tl__tabs overflows past the pane edge while the
     Claude strip in .tl__head fits with a 20px gap. Both .as.in-header
     instances end up the same width (~380px content-fit), but they live
     in DIFFERENT parents with DIFFERENT leading-content widths:
       .tl__head  leading content = "Timeline · 40 artifacts" ≈ 239px
       .tl__tabs  leading content = "Conversation | Consumption" ≈ 292px
     The 53px difference exceeds the right-side padding budget, so the
     wider GPT row clips. The fix is to cap BOTH strips at a width that
     fits the limiting row (.tl__tabs) so they right-align to the same
     x-coordinate column.

     Computed max:
       pane width 639 − padding 40 = inner width 599
       .tl__tabs leading content (Conversation + Consumption) = 272px
       → strip max width = 599 − 272 = 327px → use 320px with a small buffer

     With both strips at 340px and `margin-left: auto`, the two strips
     occupy an identical [left..right] range. The .as-activity phrase
     truncates with ellipsis when content exceeds the strip.
     ========================================================= */
  @media (max-width: 1799px) {
    .tl__head .as.in-header,
    .tl__tabs .as.in-header {
      min-width: 0 !important;
      width: 320px !important;
      max-width: 320px !important;
      flex: 0 0 320px !important;
    }
    .tl__head .as.in-header .as-activity,
    .tl__tabs .as.in-header .as-activity {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>

<style id="iter-12-live-strip-elev">
  /* =========================================================
     Iter 12 — elevation on the live agent strip
     elev-2 reinforces the .is-live signal alongside the sweep
     animation (spec 0138 §5.1) + dot pulse + activity phrase.
     ========================================================= */
  .as.in-header.is-live {
    box-shadow: var(--md-elev-2);
    transition: box-shadow var(--md-dur-short-3, 150ms) var(--md-easing-standard, ease);
  }
</style>

<style id="iter-11-live-dot-pulse">
  /* =========================================================
     Iter 11 — activity-dot soft pulse on live strip + .is-live
     class wired in (the DOM also gets the dot color flipped to
     info + the activity phrase updated to "negotiating · round 4"
     in _dump-timeline-proposed.html).
     ========================================================= */
  @keyframes pulse-info {
    0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--p-info) 60%, transparent); }
    50%      { box-shadow: 0 0 0 4px color-mix(in srgb, var(--p-info) 0%,  transparent); }
  }
</style>

<style id="iter-10-activity-chip-bump">
  /* =========================================================
     Iter 10 — visible activity-chip background
     After iter 5 bumped the card surface to surface-container-high,
     the .mono activity chip lost its visual definition (chip and
     card became the same color). Bump up one tier to surface-
     container-highest so it reads as a discrete badge.
     ========================================================= */
  .tl-card-head .chip.tone-neutral.mono {
    background: var(--md-surface-container-highest) !important;
  }
</style>

<style id="iter-9-cat-bubble-softer">
  /* =========================================================
     Iter 9 — softer category bubbles in phase headers
     Q/D/I/C bubbles dimmed from 100% saturation to 70% alpha so
     they still beat the chip's 18%-tinted background but don't
     dominate the phase header. Scoped to .tl-phase__chips so
     critique-pane bubbles are untouched.
     ========================================================= */
  .tl-phase__chips .chip.tone-info .cat-bubble {
    background: color-mix(in srgb, var(--p-info) 70%, transparent) !important;
  }
  .tl-phase__chips .chip.tone-warn .cat-bubble {
    background: color-mix(in srgb, var(--p-warn) 70%, transparent) !important;
  }
  .tl-phase__chips .chip.tone-err .cat-bubble {
    background: color-mix(in srgb, var(--p-err) 70%, transparent) !important;
  }
  .tl-phase__chips .chip.tone-idle .cat-bubble {
    background: color-mix(in srgb, var(--p-idle) 70%, transparent) !important;
  }
</style>

<style id="iter-8-agent-tint-and-stripes">
  /* =========================================================
     Iter 8 — provider-tinted header strips + card left-stripe + radius lg
     (1) Header agent strips get 8% provider-tonal background.
     (2) Each turn card gets a 2px left stripe in the provider
         color (sable/sage/idle), matching the .as.is-a/.is-b
         pattern in the live CSS at components.css:364-365.
     (3) Card radius bumps from md (12dp) to lg (16dp) for
         M3-Expressive feel.
     ========================================================= */
  .as.is-a.in-header {
    background: color-mix(in srgb, var(--p-sable) 8%, var(--md-surface-container)) !important;
  }
  .as.is-b.in-header {
    background: color-mix(in srgb, var(--p-sage) 8%, var(--md-surface-container)) !important;
  }
  .tl-thread:has(.tl-card-head > .chip.tone-claude) {
    border-left: 2px solid var(--p-sable) !important;
  }
  .tl-thread:has(.tl-card-head > .chip.tone-gpt) {
    border-left: 2px solid var(--p-sage) !important;
  }
  .tl-thread:has(.tl-card-head > .chip.tone-neutral:not(.mono)) {
    border-left: 2px solid var(--p-idle) !important;
  }
  .tl__body .tl-thread { border-radius: var(--md-shape-lg) !important; }
</style>

<style id="iter-7-chip-polish">
  /* =========================================================
     Iter 7 — chip polish
     (1) Identity-chip backgrounds bumped to readable opacity:
         Claude/GPT at 30%, System at 20% color-mix.
     (2) Light-mode Claude/GPT chip text forced to dark
         (#3b2810 / #0a322d) because live tokens.css is missing
         the light-mode overrides for --md-on-{primary,secondary}-
         container (drift fix; see NOTES.md §3.A).
     ========================================================= */
  .tl-card-head .chip.tone-claude {
    background: color-mix(in srgb, var(--p-sable) 30%, transparent) !important;
  }
  .tl-card-head .chip.tone-gpt {
    background: color-mix(in srgb, var(--p-sage) 30%, transparent) !important;
  }
  .tl-card-head .chip.tone-neutral:not(.mono) {
    background: color-mix(in srgb, var(--p-idle) 20%, transparent) !important;
    color: var(--md-on-surface) !important;
  }
  body.light .tl-card-head .chip.tone-claude,
  body.light .tl-card-head .chip.tone-claude .chip-label {
    color: #3b2810 !important;
  }
  body.light .tl-card-head .chip.tone-gpt,
  body.light .tl-card-head .chip.tone-gpt .chip-label {
    color: #0a322d !important;
  }
</style>

<style id="iter-5-m3-card">
  /* =========================================================
     Iter 5 — M3 timeline card chrome + 16px pane gutter
     (iter 4 base + brighter surface + visible outline)

     Collapsed: filled card on surface-container-high with
                outline-variant border, hover lifts to
                surface-container-highest + outline + elev-1.
     Expanded:  surface-container-low body with surface-
                container-high header strip; elev-2 lift;
                bottom divider on head.
     ========================================================= */
  .tl-phase__hd  { padding: 12px 16px !important; }
  .tl-phase__body { gap: 6px !important; padding: 8px 16px 12px !important; }

  .tl-thread {
    background: var(--md-surface-container-high) !important;
    border: 1px solid var(--md-outline-variant) !important;
    border-radius: var(--md-shape-md) !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden;
    transition: background var(--md-dur-short-3) var(--md-easing-standard),
                box-shadow  var(--md-dur-short-3) var(--md-easing-standard),
                border-color var(--md-dur-short-3) var(--md-easing-standard);
  }
  .tl-thread:hover {
    background: var(--md-surface-container-highest) !important;
    border-color: var(--md-outline) !important;
    box-shadow: var(--md-elev-1);
  }
  .tl-thread:hover::before { opacity: 0 !important; }
  .tl-thread > .tl-card-head {
    padding: 6px 12px !important;
    gap: 6px;
    background: transparent;
    border: 0;
  }

  /* Expanded state */
  .tl-thread.is-open-expanded {
    background: var(--md-surface-container-low) !important;
    border-color: var(--md-outline-variant) !important;
    box-shadow: var(--md-elev-2);
  }
  .tl-thread.is-open-expanded > .tl-card-head {
    background: var(--md-surface-container-high);
    border-bottom: 1px solid var(--md-outline-hair);
  }
  .tl-thread.is-open-expanded .tl-card-chev[data-open="true"] svg { transform: rotate(90deg); }

  .tl-thread__body {
    padding: 14px 16px 4px !important;
    font: italic var(--md-w-regular) 13px/1.55 var(--md-font-brand) !important;
    color: var(--md-on-surface-variant) !important;
    border-top: 0 !important;
  }
  .tl-thread__actions {
    display: flex !important; align-items: center !important; gap: 8px !important;
    padding: 10px 12px 12px !important;
    flex-wrap: wrap;
  }
  .tl-thread__actions .md-btn--tonal {
    background: var(--md-primary-container);
    color: var(--md-on-primary-container);
    border: 0; border-radius: var(--md-shape-full);
    height: 32px; padding: 0 16px;
    font: var(--md-w-medium) 12px/1 var(--md-font-plain);
    letter-spacing: 0.06em;
    cursor: pointer;
    display: inline-flex; align-items: center; gap: 6px;
  }
  .tl-thread__actions .md-btn--tonal:hover { background: color-mix(in srgb, var(--md-on-primary-container) 8%, var(--md-primary-container)); }
  .tl-thread__actions > span[style*="flex"] { margin-left: auto; }
  .tl-thread__actions .md-chip--sm {
    height: 24px; padding: 0 10px;
    border-radius: var(--md-shape-full);
    background: var(--md-surface-container-high);
    color: var(--md-on-surface-variant);
    font: var(--md-w-regular) 11px/1 var(--md-font-data);
    display: inline-flex; align-items: center;
  }
</style>
CSSITER
}

# --- Build live.html ---------------------------------------------------------
# Verbatim timeline dump + critique stub, no iter blocks. Iter 1/2/3 are NOT
# applied (live.html is the "before" reference).
{
cat <<'HDR'
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Timeline pane · LIVE (verbatim) · 2026-05-22</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,100..1000&family=Roboto+Serif:opsz,wght@8..144,300..800&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=block" rel="stylesheet" />
<link rel="stylesheet" href="/src/dual_research/ui/static/tokens.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/base.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/components.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/theme.css" />
HDR
shared_workshop_styles
cat <<'HDR2'
</head>
<body class="dark">
<div class="wrap__banner">
  <span><b>Timeline pane · LIVE</b></span>
  <span class="pill">verbatim outerHTML dump</span>
  <span>run · <span class="pill">20260521-010637-dvs-backend-language-choice</span></span>
  <span>dumped · 2026-05-22</span>
  <span style="margin-left:auto">timeline focus · critique stub on right · <i>this wrapper is immutable</i></span>
</div>
<div class="wrap__stage">
  <div class="timeline-host">
HDR2
cat "$TIMELINE_DUMP"
cat <<'MID'
  </div>
  <div class="critique-stub">
MID
cat "$CRITIQUE_STUB"
cat <<'FTR_OPEN'
  </div>
</div>
<script>
(function(){
FTR_OPEN
cat "$JS_BODY"
cat <<'FTR_CLOSE'
})();
</script>
</body>
</html>
FTR_CLOSE
} > "$DIR/live.html"

# --- Build proposed.html -----------------------------------------------------
# Iter-1/2/3 DOM mutations applied (from _dump-timeline-proposed.html) +
# Iter-4..12 stacked as <style> blocks.
{
cat <<'PHDR'
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Timeline pane · PROPOSED · iters 1-12</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,100..1000&family=Roboto+Serif:opsz,wght@8..144,300..800&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=block" rel="stylesheet" />
<link rel="stylesheet" href="/src/dual_research/ui/static/tokens.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/base.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/components.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/theme.css" />
PHDR
shared_workshop_styles
iter_styles
cat <<'PHDR2'
<script>
  (function(){
    try {
      var t = new URLSearchParams(location.search).get('theme');
      document.documentElement.dataset.theme = t === 'light' ? 'light' : 'dark';
    } catch(e) {}
  })();
</script>
</head>
<body class="dark">
<script>
  (function(){
    if (document.documentElement.dataset.theme === 'light') {
      document.body.className = 'light';
    }
  })();
</script>
<div class="wrap__banner">
  <span><b>Timeline pane · PROPOSED</b></span>
  <span class="pill" id="iter-banner">iters 1-13 stacked · M3 cards · System chip · provider stripes · live-strip animation + elev-2 · narrow-view strip equalisation</span>
  <span class="pill" id="theme-banner">theme: dark</span>
  <span style="margin-left:auto">timeline focus · critique stub on right · ?theme=dark|light</span>
</div>
<div class="wrap__stage">
  <div class="timeline-host">
PHDR2
cat "$TIMELINE_PROPOSED"
cat <<'PMID'
  </div>
  <div class="critique-stub">
PMID
cat "$CRITIQUE_STUB"
cat <<'PFTR_OPEN'
  </div>
</div>
<script>
(function(){
  var tb = document.getElementById('theme-banner');
  if (tb) tb.textContent = 'theme: ' + (document.body.className === 'light' ? 'light' : 'dark');
PFTR_OPEN
cat "$JS_BODY"
cat <<'PFTR_CLOSE'
})();
</script>
</body>
</html>
PFTR_CLOSE
} > "$DIR/proposed.html"

echo "wrote $DIR/live.html ($(wc -c < "$DIR/live.html") bytes)"
echo "wrote $DIR/proposed.html ($(wc -c < "$DIR/proposed.html") bytes)"
