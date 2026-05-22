#!/usr/bin/env bash
# Assembles live.html and proposed.html from the verbatim per-phase dumps.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
P0="$DIR/_dump-p0.html"
P2="$DIR/_dump-p2.html"
P4="$DIR/_dump-p4.html"
SG="$DIR/_dump-sigma.html"
TIMELINE_STUB="$DIR/_dump-timeline-stub.html"
JS_BODY="$DIR/_inline-script.js"
DUMPS=("p0:$P0" "p2:$P2" "p4:$P4" "sigma:$SG")

shared_styles() {
cat <<'CSSJS'
<style id="workshop-collapse-affordance">
  /* Cards default expanded (faithful to live impl where ItemCard renders
     fully), source rows default collapsed (faithful to live aria-expanded
     default — workshop re-dumped with __body markup in DOM for toggling). */
  .item-card { position: relative; }
  .item-card__head { cursor: pointer; }
  .item-card__head::after {
    content: '›';
    margin-left: auto;
    color: var(--md-on-surface-faint, #8a93a0);
    font-size: 16px;
    line-height: 1;
    transform: rotate(90deg);
    transition: transform 120ms ease;
    opacity: 0.55;
  }
  .item-card[data-expanded="false"] .item-card__head::after { transform: rotate(0); }
  .item-card[data-expanded="false"] > .item-card__body,
  .item-card[data-expanded="false"] > .item-card__timeline,
  .item-card[data-expanded="false"] > .item-card__lifecycle-footer,
  .item-card[data-expanded="false"] > .item-card__sources { display: none; }

  .source-row__head[aria-expanded="false"] ~ .source-row__body { display: none; }
  .source-row__head[aria-expanded="true"] .source-row__chev { transform: rotate(90deg); display: inline-block; transition: transform 120ms ease; }
  .source-row__head .source-row__chev { transition: transform 120ms ease; display: inline-block; }
</style>
<!-- workshop-width-mode CSS removed: the workshop now resizes the iframe
     to actual narrow / wide widths, so the live @media (max-width: 1799px)
     fires naturally. No CSS override needed. -->
<style id="iter-1-ds-aligned-headers">
  /* ITER 1 — Right cluster of Bar 2 follows Design System v2.html §12.
     Kind chips (Q/D/I/C/All) are LEFT as the live chip + cat-bubble pattern —
     they share the primitive with .tl-phase__chips in the timeline pane,
     and consistency across panes outweighs the DS §12 flat-tab look.
     Only the right cluster (agent + status) is restyled to the DS
     .tab-group-solid segmented-control pattern. Bar 1 gains a .drift-chip
     slot in .right (after .crit-totals). */

  /* Bar 2 layout: kind cluster on left, segmented controls on right.
     iter-2 tightens column-gap (12→8) + horizontal padding (16→12) to
     fit on one row at wide. */
  .crit2 .bar2.crit-filter-row { gap: 8px !important; padding: 10px 12px !important; flex-wrap: wrap !important; row-gap: 8px !important; }
  .crit2 .bar2.crit-filter-row > .kind-tabs { margin-right: auto; }
  .crit2 .bar2.crit-filter-row .crit-filter-spacer { display: none !important; }

  /* .kind-tabs is purely a flex group; no visual restyling of the chips. */
  .crit2 .bar2 .kind-tabs { display: inline-flex; gap: 4px; align-items: center; flex-wrap: wrap; }

  /* ITER 3 — drop the "All" chip from the kind cluster (same convention as
     agent + status segments). No active kind = "show all categories".
     The "All" chip is the tone-neutral one; the 4 category chips are
     tone-info / warn / err / idle. */
  .crit2 .bar2 .kind-tabs .chip[data-kind-filter].tone-neutral { display: none !important; }

  /* Segmented controls (agent + status) — DS .tab-group-solid */
  .crit2 .bar2 .tab-group-solid {
    display: inline-flex;
    background: var(--md-surface-container-high);
    border-radius: var(--md-shape-full);
    padding: 4px;
    gap: 2px;
    align-items: center;
  }
  .crit2 .bar2 .tab-group-solid .chip {
    display: inline-flex !important; align-items: center !important; gap: 6px !important;
    height: 26px !important; padding: 0 10px !important;
    background: transparent !important; border: 0 !important;
    border-radius: var(--md-shape-full) !important;
    font: var(--md-w-medium) 11px/1 var(--md-font-plain) !important;
    color: var(--md-on-surface-variant) !important;
  }
  .crit2 .bar2 .tab-group-solid .chip[data-active="true"] {
    background: var(--md-surface) !important;
    color: var(--md-on-surface) !important;
    box-shadow: var(--md-elev-1);
  }
  /* Keep the status dot indicators hidden — they're redundant in a segmented control. */
  .crit2 .bar2 .tab-group-solid .chip .chip-dot { display: none !important; }
  /* Segmented-control labels stay visible at every width — "Open" / "Resolved" /
     "Drift" / "Claude" / "GPT" are essential affordances; icon-only is too cryptic. */
  .crit2 .bar2 .tab-group-solid .chip .chip-label { display: inline !important; }
  /* Backstop: bar2 never wraps to two rows. */
  .crit2 .bar2.crit-filter-row { flex-wrap: nowrap !important; }
  /* Kind cluster also nowrap — at narrow widths it was wrapping its own chips
     into 2 rows because the agent + status segments squeezed its room. */
  .crit2 .bar2 .kind-tabs { flex-wrap: nowrap !important; }
  /* Agent chips: keep the live brand icons (Claude sunburst + OpenAI rosette
     in their tinted squares). Restore .chip-leading-icon visibility so the
     icons render at their natural size. */
  .crit2 .bar2 .tab-group-solid[data-group="agent"] .chip .chip-leading-icon { display: inline-flex !important; align-items: center; }
  /* Count slot — rendered as "(N)" parens next to the label so every option
     advertises how many items it covers. The chip-value span pre-exists on
     status chips (.chip[tone-info/ok/warn] in bar2) and is injected by the
     iter-1 script for agent chips + the explicit "All" buttons we prepend. */
  .crit2 .bar2 .tab-group-solid .chip .chip-value {
    display: inline !important;
    background: transparent !important;
    padding: 0 !important;
    margin-left: 4px;
    font: var(--md-w-regular) 10.5px/1 var(--md-font-data) !important;
    color: currentColor;
    opacity: 0.6;
    min-width: 0 !important;
  }
  .crit2 .bar2 .tab-group-solid .chip .chip-value::before { content: '('; }
  .crit2 .bar2 .tab-group-solid .chip .chip-value::after  { content: ')'; }
  /* Active state — count slightly more opaque since the chip is in focus. */
  .crit2 .bar2 .tab-group-solid .chip[data-active="true"] .chip-value { opacity: 0.75; }
  /* At narrow (≤1799px viewport, fires naturally), drop the `(N)` count in
     segmented controls. Labels stay — they're the load-bearing affordance —
     and the kind cluster reclaims ~100px so it stays single-row.
     This rule MUST come after the unconditional chip-value `display: inline`
     above; otherwise the inline rule wins in source order. */
  @media (max-width: 1799px) {
    .crit2 .bar2 .tab-group-solid .chip .chip-value { display: none !important; }
  }

  /* Drift chip in bar 1 (added by script). */
  .crit2 .bar1 .drift-chip {
    display: inline-flex; align-items: center; gap: 6px;
    height: 28px; padding: 0 10px;
    border-radius: var(--md-shape-full);
    background: color-mix(in srgb, var(--p-err) 18%, transparent);
    color: var(--p-err);
    font: var(--md-w-medium) 11px/1 var(--md-font-plain);
    letter-spacing: 0.4px;
  }
  .crit2 .bar1 .drift-chip[data-count="0"] {
    background: color-mix(in srgb, var(--md-on-surface) 6%, transparent);
    color: var(--md-on-surface-faint);
    opacity: 0.55;
  }
  .crit2 .bar1 .drift-chip svg { width: 12px; height: 12px; }

  /* ITER 4 — collapsed-card frame mirrors timeline §2.4.1 + §2.4.2
     (see prototypes/timeline-iteration/NOTES.md):
       · surface-container-high background (one tier brighter than pane)
       · outline-variant border (one tier more visible than the live hair)
       · 16dp radius (--md-shape-lg, M3-Expressive card)
       · 2px left stripe in provider color (sable Claude / sage GPT / idle System)
       · hover lifts to surface-container-highest + outline + elev-1
       · 6px gap between cards inside .crit-group__body */
  .crit2 .crit-group__body { display: flex; flex-direction: column; gap: 6px; }
  .crit2 .item-card {
    background: var(--md-surface-container-high);
    border: 1px solid var(--md-outline-variant);
    border-radius: var(--md-shape-lg, 16px);
    overflow: hidden;
    transition: background 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
  }
  .crit2 .item-card[data-raised-by="claude"] { border-left: 2px solid var(--p-sable, #d4a574); }
  .crit2 .item-card[data-raised-by="gpt"]    { border-left: 2px solid var(--p-sage,  #7cc4b8); }
  .crit2 .item-card[data-raised-by="system"] { border-left: 2px solid var(--p-idle,  #6b7280); }
  .crit2 .item-card[data-expanded="false"]:hover {
    background: var(--md-surface-container-highest);
    border-color: var(--md-outline);
    box-shadow: var(--md-elev-1);
  }
  .crit2 .item-card__head { padding: 10px 14px; }

  /* ITER 5 — catch-up from timeline NOTES §3.A (light-mode tokens drift)
     + §2.4.2.a (identity-chip background opacities). Both preemptive: nothing
     in the critique card head uses .chip.tone-claude / .tone-gpt yet, but
     when iter 7 injects the provider identity chip, these rules will be
     waiting. Scoped to .item-card__head so other surfaces (bar2 agent
     chips, critique-pane summary chips elsewhere) keep their own tuning. */

  /* Identity-chip backgrounds at the card-head opacities locked in timeline §2.4.2.a */
  .crit2 .item-card__head .chip.tone-claude {
    background: color-mix(in srgb, var(--p-sable) 30%, transparent);
  }
  .crit2 .item-card__head .chip.tone-gpt {
    background: color-mix(in srgb, var(--p-sage) 30%, transparent);
  }
  .crit2 .item-card__head .chip.tone-neutral:not(.mono) {
    background: color-mix(in srgb, var(--p-idle) 20%, transparent);
    color: var(--md-on-surface);
  }

  /* Light-mode text drift fix — live tokens.css is missing
     --md-on-primary-container / -secondary-container overrides for
     body.light, so Claude/GPT chip text inherits the dark-mode cream
     values (#f3deca / #cfece6) and reads washed-out on cream cards.
     Force the deep brown/teal explicitly in the card head. */
  body.light .crit2 .item-card__head .chip.tone-claude,
  body.light .crit2 .item-card__head .chip.tone-claude .chip-label {
    color: #3b2810 !important;
  }
  body.light .crit2 .item-card__head .chip.tone-gpt,
  body.light .crit2 .item-card__head .chip.tone-gpt .chip-label {
    color: #0a322d !important;
  }

  /* ITER 7 — collapsed-card head matches the timeline turn-card pattern.
     Head order (left → right):
       [provider chip with brand SVG] [round chip · mono neutral] [kind chip · tone-coloured]
       … margin-left:auto …
       [state chip · right-aligned]
     ID chip + sources chip dropped entirely (per user direction). Iter-6's
     kind-hide is reverted — kind is back in but tone-coloured to match the
     critique chip vocabulary (Q=info, D=warn, I=err, C=idle).
     Height + spacing tuned to match timeline cards exactly:
       · card height 36px (collapsed) — was 64
       · card padding 0 (live default 12px 14px overridden, head owns its own)
       · card margin 0 (live default 8px 0 overridden, .crit-group__body gap handles it)
       · head padding 6px 12px (was 8px 12px) — matches timeline
       · no min-height — head sizes to content */
  .crit2 .item-card { padding: 0 !important; margin: 0 !important; }
  .crit2 .item-card__head {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
  }
  /* Right-align the state chip — push it to the far right of the head. */
  .crit2 .item-card__head [data-chip-role="state"] { margin-left: auto; }
  /* Workshop-affordance chevron lives in ::after; keep its position even
     when the state chip also uses margin-left:auto. */
  .crit2 .item-card__head::after { margin-left: 0; }

  /* ITER 14 — stronger affordance on .crit-group__hd so the user sees
     immediate feedback that the section header is clickable. */
  .crit2 .crit-group__hd {
    cursor: pointer;
    transition: background 120ms ease;
  }
  .crit2 .crit-group__hd:hover {
    background: color-mix(in srgb, var(--md-on-surface) 6%, transparent);
  }
  .crit2 .crit-group__hd:active {
    background: color-mix(in srgb, var(--md-on-surface) 10%, transparent);
  }

  /* ITER 15 — make the item-card head clearly clickable in BOTH states so
     the user can collapse an expanded card by clicking the head. The
     collapsed hover-lift was already there from iter-4; this adds the
     same affordance to the expanded state. */
  .crit2 .item-card__head {
    cursor: pointer;
    transition: background 120ms ease;
  }
  .crit2 .item-card[data-expanded="true"] .item-card__head:hover {
    background: color-mix(in srgb, var(--md-on-surface) 5%, transparent);
  }
  .crit2 .item-card[data-expanded="true"] .item-card__head:active {
    background: color-mix(in srgb, var(--md-on-surface) 9%, transparent);
  }

  /* ITER 8 — subtle separator between paired tokens inside a single chip:
     "Raised · R1" (round chip) and "Resolved · R2" (state chip). The
     middle dot is dim + tight-spaced so the chip still reads as one unit. */
  .crit2 .item-card__head .chip .chip-sep {
    display: inline-block;
    margin: 0 4px;
    opacity: 0.4;
    font-weight: 400;
  }
  /* ITER 8.1 — capitalize round + state labels (Raised / Resolved / Capped /
     Acknowledged / Withdrawn). The R1 suffix stays uppercase because
     text-transform: capitalize only changes the first letter of each text
     node, and "R" is already uppercase. */
  .crit2 .item-card__head [data-chip-role="round"] .chip-label,
  .crit2 .item-card__head [data-chip-role="state"] .chip-label {
    text-transform: capitalize;
  }

  /* ITER 12 — expanded card view modelled on the user's screenshot.
     Layout (under the head when data-expanded="true"):
       · LIFECYCLE label
       · Sequence of rows: [provider chip · round chip · verb chip · modifier?]
         + italic-serif "quote" beneath
       · First row = synthetic "raised" using item body as the quote
       · Subsequent rows = parsed from .item-card__transition entries
       · Orchestrator transitions skip the provider chip
       · lifecycle-footer below (already styled per terminal state)
       · sources segment below that (with collapsible rows) */
  .item-card[data-expanded="true"] > .item-card__lifecycle-footer,
  .item-card[data-expanded="true"] > .item-card__sources {
    display: block !important;
  }
  /* The legacy body + timeline are hidden by the JS rebuild (display: none
     inline); the iter-12 .item-card__lifecycle section replaces them. */

  /* Lifecycle wrapper */
  .item-card .item-card__lifecycle.iter12 {
    padding: 14px 16px 16px;
    border-top: 1px solid var(--md-outline-hair);
    display: flex; flex-direction: column; gap: 18px;
  }
  .item-card .item-card__lifecycle-hd {
    font: var(--md-w-semi, 600) 10.5px/1 var(--md-font-data, ui-monospace, monospace);
    letter-spacing: 0.10em; text-transform: uppercase;
    color: var(--md-on-surface-faint);
    padding: 0;
  }

  /* Lifecycle row — chips on top, quote beneath */
  .item-card .lc-row {
    display: flex; flex-direction: column; gap: 8px;
  }
  .item-card .lc-row-chips {
    display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap;
  }
  .item-card .lc-row-quote {
    margin: 0;
    font-family: var(--md-font-brand, "Roboto Serif", Georgia, serif);
    font-style: italic;
    font-size: 13px;
    line-height: 1.55;
    color: var(--md-on-surface);
  }
  /* Re-use the head's provider-chip background tuning */
  .item-card .lc-row-chips .chip.tone-claude {
    background: color-mix(in srgb, var(--p-sable) 30%, transparent);
  }
  .item-card .lc-row-chips .chip.tone-gpt {
    background: color-mix(in srgb, var(--p-sage) 30%, transparent);
  }
  /* ITER 13 — source-requested / source-provided extras (info / ok tones) */
  .item-card .lc-row-chips .lc-extra { gap: 4px; }
  .item-card .lc-row-chips .lc-extra .ms {
    font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 20;
  }
  /* ITER 13 — meta chip on source-row head: "[provider icon · R3]"
     Right-aligned so it sits next to the unverified chip (when present) or
     at the far right of the head row otherwise. */
  .item-card .source-row__head .source-meta-chip {
    height: 22px;
    padding: 0 8px 0 6px;
    gap: 4px;
    flex: 0 0 auto;
    font-size: 10.5px;
    margin-left: auto;
  }
  .item-card .source-row__head .source-row__host + .source-meta-chip { margin-left: auto; }
  .item-card .source-row__head .source-meta-chip .chip-leading-icon { line-height: 0; }
  /* Title gets a max-width so it ellipsises rather than pushing meta-chip
     off-screen. */
  .item-card .source-row__head .source-row__title {
    flex: 0 1 auto;
    max-width: 280px;
  }
  body.light .item-card .lc-row-chips .chip.tone-claude,
  body.light .item-card .lc-row-chips .chip.tone-claude .chip-label { color: #3b2810 !important; }
  body.light .item-card .lc-row-chips .chip.tone-gpt,
  body.light .item-card .lc-row-chips .chip.tone-gpt .chip-label { color: #0a322d !important; }

  /* Lifecycle footer — terminal-state summary line beneath the rows */
  .item-card[data-expanded="true"] .item-card__lifecycle-footer {
    padding: 10px 16px 14px;
    border-top: 1px dashed var(--md-outline-hair);
    font: var(--md-w-medium, 500) 11.5px/1.3 var(--md-font-data, ui-monospace, monospace);
    color: var(--p-ok);
    letter-spacing: 0.04em;
    display: flex; align-items: center; gap: 6px;
  }
  .item-card--capped[data-expanded="true"] .item-card__lifecycle-footer,
  .item-card--withdrawn[data-expanded="true"] .item-card__lifecycle-footer {
    color: var(--p-err);
  }
  .item-card--acknowledged[data-expanded="true"] .item-card__lifecycle-footer {
    color: var(--p-warn);
  }

  /* SOURCES segment — header + collapsible rows */
  .item-card[data-expanded="true"] .item-card__sources {
    padding: 14px 16px 16px;
    border-top: 1px dashed var(--md-outline-hair);
  }
  .item-card .item-card__sources-hd {
    font: var(--md-w-semi, 600) 10.5px/1 var(--md-font-data, ui-monospace, monospace);
    letter-spacing: 0.10em; text-transform: uppercase;
    color: var(--md-on-surface-faint);
    margin: 0 0 10px;
  }
  .item-card .source-row {
    background: var(--md-surface-container-low);
    border: 1px solid var(--md-outline-hair);
    border-radius: var(--md-shape-md, 8px);
    margin: 0 0 8px;
    overflow: hidden;
  }
  .item-card .source-row__head {
    padding: 8px 10px;
    cursor: pointer;
    display: flex; align-items: center; gap: 8px;
    user-select: none;
  }
  .item-card .source-row__head[aria-expanded="true"] {
    border-bottom: 1px solid var(--md-outline-hair);
  }
  .item-card .source-row__chev {
    color: var(--md-on-surface-variant);
    font-size: 9px;
    width: 12px;
    transition: transform 120ms ease;
  }
  .item-card .source-row__head[aria-expanded="true"] .source-row__chev {
    transform: rotate(90deg);
  }
  .item-card .source-row__title {
    color: var(--md-on-surface);
    font-size: 12.5px;
    font-weight: var(--md-w-medium, 500);
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .item-card .source-row__host {
    color: var(--md-on-surface-faint);
    font-size: 11px;
    font-family: var(--md-font-data);
  }
  .item-card .source-row.is-unverified .source-row__head::after {
    content: '⚠ unverified';
    font: var(--md-w-medium, 500) 10.5px/1 var(--md-font-data, ui-monospace, monospace);
    color: var(--p-warn);
    background: color-mix(in srgb, var(--p-warn) 14%, transparent);
    padding: 3px 8px;
    border-radius: var(--md-shape-full);
    letter-spacing: 0.04em;
    margin-left: auto;
  }
  /* Source row body (URL, search query, fetched, unverified reason, excerpt) */
  .item-card .source-row__body {
    padding: 10px 14px 12px;
    display: flex; flex-direction: column; gap: 8px;
  }
  .item-card .source-row__field {
    display: grid;
    grid-template-columns: 130px 1fr;
    align-items: baseline;
    column-gap: 12px;
    font-size: 12px;
    color: var(--md-on-surface);
    line-height: 1.45;
  }
  .item-card .source-row__label {
    font: var(--md-w-semi, 600) 10px/1 var(--md-font-data, ui-monospace, monospace);
    letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--md-on-surface-faint);
    padding-top: 2px;
  }
  .item-card .source-row__url {
    color: var(--p-info);
    word-break: break-all;
    font-family: var(--md-font-data);
    font-size: 11.5px;
    text-decoration: none;
  }
  .item-card .source-row__url:hover { text-decoration: underline; }
  .item-card .source-row__excerpt-wrap { margin-top: 4px; }
  .item-card .source-row__excerpt {
    margin: 4px 0 0;
    padding: 10px 12px;
    background: var(--md-surface-container);
    border-left: 2px solid var(--md-outline-variant);
    border-radius: 0 var(--md-shape-xs, 4px) var(--md-shape-xs, 4px) 0;
    font-family: var(--md-font-brand, "Roboto Serif", Georgia, serif);
    font-style: italic;
    font-size: 12.5px;
    line-height: 1.55;
    color: var(--md-on-surface);
  }

  /* ITER 10 — terminal actor icon inside the state chip. Renders the 12×12
     brand square inline between the state text and the `R<N>` round,
     surrounded by .chip-sep middle dots. capitalize on the state label
     (iter 8.1) skips text inside this span because it has no text content. */
  .crit2 .item-card__head [data-chip-role="state"] .state-actor {
    display: inline-flex;
    align-items: center;
    vertical-align: middle;
    cursor: help;
  }
  .crit2 .item-card__head [data-chip-role="state"] .state-actor .chip-leading-icon {
    display: inline-flex;
    align-items: center;
  }

  /* ITER 9 — evidence-needed signal as a tiny icon chip with hover tooltip.
     The full sentence ("Evidence needed — addresses must cite consulted
     sources.") is hidden from the body so the card height never breaks; it
     lives in the chip's `title` attribute instead. */
  .crit2 .item-card__evidence-needed { display: none !important; }
  .crit2 .item-card__head .evidence-chip {
    cursor: help;
    padding: 0 6px;
    height: 22px;
    min-width: 22px;
    align-items: center;
    justify-content: center;
  }
  .crit2 .item-card__head .evidence-chip .ms {
    font-size: 14px;
    font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 20;
    line-height: 1;
  }
</style>
CSSJS
}

# --- Build live.html ---------------------------------------------------------
{
cat <<'HDR'
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Critique pane · LIVE (verbatim) · 2026-05-22</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,100..1000&family=Roboto+Serif:opsz,wght@8..144,300..800&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=block" rel="stylesheet" />
<link rel="stylesheet" href="/src/dual_research/ui/static/tokens.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/base.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/components.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/theme.css" />
<style id="wrapper-styles">
  html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
  /* Constrain html + body to iframe viewport so .crit2__body (with its
     own overflow:auto from the live CSS) becomes the scroll container,
     not the html element. Without this, expanding Resolved makes the
     iframe page itself scroll and the scrollbar steals ~5-17px from
     the pane width, wrapping bar2 to two rows. */
  body { background: var(--md-background, #0f1115); color: var(--md-on-surface, #d9dee5); font-family: var(--md-font-plain, system-ui, sans-serif); }
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
  .wrap__stage { padding: 0; flex: 1 1 0%; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .wrap__stage > .timeline-pane { background: var(--md-surface, #0f1115); display: flex; flex-direction: column; min-height: 0; min-width: 0; border-right: 1px solid var(--md-outline-hair); overflow: hidden; }
  .wrap__stage > .critique-host { background: var(--md-surface, #0f1115); display: flex; flex-direction: column; min-height: 0; min-width: 0; }
  .critique-host > .phase-state { display: none; flex: 1 1 0%; min-height: 0; }
  .critique-host > .phase-state.is-visible { display: flex; flex-direction: column; flex: 1 1 0%; min-height: 0; }
  .critique-host > .phase-state > .crit2 { flex: 1 1 0%; min-height: 0; display: flex; flex-direction: column; }
  body { display: flex; flex-direction: column; }
</style>
HDR
shared_styles
cat <<'HDR2'
</head>
<body class="dark">
<div class="wrap__banner">
  <span><b>Critique pane · LIVE</b></span>
  <span class="pill">verbatim outerHTML dump</span>
  <span>run · <span class="pill">20260521-010637-dvs-backend-language-choice</span></span>
  <span>dumped · 2026-05-22</span>
  <span style="margin-left:auto">click the phase tabs inside the pane below to switch state · <i>this wrapper is immutable</i></span>
</div>
<div class="wrap__stage">
  <div class="timeline-pane">
HDR2

cat "$TIMELINE_STUB"

cat <<'MID'
  </div>
  <div class="critique-host">
MID

for entry in "${DUMPS[@]}"; do
  key="${entry%%:*}"
  file="${entry##*:}"
  cls="phase-state"
  if [ "$key" = "p0" ]; then cls="phase-state is-visible"; fi
  printf '    <section class="%s" data-phase="%s">\n' "$cls" "$key"
  cat "$file"
  printf '\n    </section>\n'
done

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
{
cat <<'PHDR'
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Critique pane · PROPOSED · iter 1</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,100..1000&family=Roboto+Serif:opsz,wght@8..144,300..800&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=block" rel="stylesheet" />
<link rel="stylesheet" href="/src/dual_research/ui/static/tokens.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/base.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/components.css" />
<link rel="stylesheet" href="/src/dual_research/ui/static/theme.css" />
<style id="wrapper-styles">
  html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
  /* Constrain html + body to iframe viewport so .crit2__body (with its
     own overflow:auto from the live CSS) becomes the scroll container,
     not the html element. Without this, expanding Resolved makes the
     iframe page itself scroll and the scrollbar steals ~5-17px from
     the pane width, wrapping bar2 to two rows. */
  body { background: var(--md-background, #0f1115); color: var(--md-on-surface, #d9dee5); font-family: var(--md-font-plain, system-ui, sans-serif); }
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
  .wrap__stage { padding: 0; flex: 1 1 0%; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .wrap__stage > .timeline-pane { background: var(--md-surface, #0f1115); display: flex; flex-direction: column; min-height: 0; min-width: 0; border-right: 1px solid var(--md-outline-hair); overflow: hidden; }
  .wrap__stage > .critique-host { background: var(--md-surface, #0f1115); display: flex; flex-direction: column; min-height: 0; min-width: 0; }
  .critique-host > .phase-state { display: none; flex: 1 1 0%; min-height: 0; }
  .critique-host > .phase-state.is-visible { display: flex; flex-direction: column; flex: 1 1 0%; min-height: 0; }
  .critique-host > .phase-state > .crit2 { flex: 1 1 0%; min-height: 0; display: flex; flex-direction: column; }
  body { display: flex; flex-direction: column; }
</style>
PHDR
shared_styles
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
  <span><b>Critique pane · PROPOSED</b></span>
  <span class="pill" id="iter-banner">iter 15 · expanded-card click affordance · auto-expand first card with sources per phase</span>
  <span class="pill" id="theme-banner">theme: dark</span>
  <span>click phase tabs to switch state · iframe-loadable via ?theme=dark|light</span>
</div>
<div class="wrap__stage">
  <div class="timeline-pane">
PHDR2

cat "$TIMELINE_STUB"

cat <<'PMID'
  </div>
  <div class="critique-host">
PMID

for entry in "${DUMPS[@]}"; do
  key="${entry%%:*}"
  file="${entry##*:}"
  cls="phase-state"
  if [ "$key" = "p0" ]; then cls="phase-state is-visible"; fi
  printf '    <section class="%s" data-phase="%s">\n' "$cls" "$key"
  cat "$file"
  printf '\n    </section>\n'
done

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
