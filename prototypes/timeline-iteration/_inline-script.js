// Timeline workshop · inline interactivity
// -----------------------------------------------------------------------------
// Mirrors the critique workshop's _inline-script.js but for the timeline pane.
// Handlers:
//   - .tl-phase__hd click  → toggle [data-collapsed] on the .tl-phase parent
//   - .tl-card-head click  → toggle .is-open-expanded class on the .tl-thread parent
//   - The expanded turn card in the dump retains its body + actions children;
//     a CSS rule (in the workshop's shared <style> block) hides those children
//     when the parent does NOT have .is-open-expanded.

function initTimelineState(){
  // Phase headers default to per-dump state (data-collapsed already set by live).
  // No mutation needed unless we want a different default.
  // Turn cards default to dump state (only one .is-open-expanded today).
  document.querySelectorAll('.tl-thread').forEach(function(card){
    if (!card.hasAttribute('data-expanded')) {
      card.setAttribute('data-expanded', card.classList.contains('is-open-expanded') ? 'true' : 'false');
    }
  });
}
initTimelineState();

document.addEventListener('click', function(e){
  // Phase header toggle
  var phaseHd = e.target.closest && e.target.closest('.tl-phase__hd');
  if (phaseHd) {
    var phase = phaseHd.closest('.tl-phase');
    if (phase) {
      var cur = phase.getAttribute('data-collapsed') === 'true';
      phase.setAttribute('data-collapsed', cur ? 'false' : 'true');
      e.preventDefault();
      return;
    }
  }

  // Turn-card head toggle (.tl-card-head)
  var cardHd = e.target.closest && e.target.closest('.tl-card-head');
  if (cardHd) {
    // Don't toggle if click landed on an inner button/link (e.g. category chip
    // with click handler, or future "Open full view" button).
    if (e.target.closest('button, a')) return;
    var card = cardHd.closest('.tl-thread');
    if (card) {
      var cur = card.classList.contains('is-open-expanded');
      card.classList.toggle('is-open-expanded', !cur);
      card.setAttribute('data-expanded', cur ? 'false' : 'true');
      // Sync the chevron's data-open so iter-5 CSS rotates it.
      var chev = card.querySelector('.tl-card-chev');
      if (chev) {
        if (cur) chev.removeAttribute('data-open');
        else chev.setAttribute('data-open', 'true');
      }
      e.preventDefault();
      return;
    }
  }
});
