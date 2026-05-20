// Spec 0120 §5.3.1 — JS-side helper for splitting a review-item body
// into its Title + Rationale segments.
//
// The protocol prompts ask agents to emit each item's body in the
// canonical form
//
//     **Title here**
//
//     Rationale paragraph(s).
//
// — first non-empty line wrapped in ``**…**`` is the title; everything
// after is the rationale. This is a soft convention enforced only by
// the prompt, not the parser. When an agent omits the bold title (or
// the parser misses it), the fallback returns the whole body as
// rationale and the renderer omits the Title segment.

(function () {
  // Anchor sub-lines (``> quote: …`` / ``> after: …``) are surfaced as
  // a separate ``Anchor`` segment on the rendered card. Strip them out
  // of the rationale so the same text isn't shown twice.
  const ANCHOR_LINE_RE = /^\s*>\s*(?:quote|after)\s*:/i;

  function stripAnchorLines(body) {
    if (typeof body !== 'string' || body.length === 0) return '';
    return body
      .split('\n')
      .filter((line) => !ANCHOR_LINE_RE.test(line))
      .join('\n');
  }

  function splitTitleAndRationale(body) {
    if (typeof body !== 'string' || body.length === 0) {
      return { title: '', rationale: '' };
    }
    const lines = body.split('\n');
    let i = 0;
    while (i < lines.length && lines[i].trim() === '') i++;
    if (i < lines.length) {
      const m = /^\s*\*\*(.+)\*\*\s*$/.exec(lines[i]);
      if (m) {
        const title = m[1].trim();
        const rationale = lines.slice(i + 1).join('\n').trim();
        return { title, rationale };
      }
    }
    return { title: '', rationale: body.trim() };
  }

  window.DrItemBody = { splitTitleAndRationale, stripAnchorLines };
})();
