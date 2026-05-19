// search-palette.jsx -- SPEC-0059 A11Y-04
// Command palette (Cmd+K / Ctrl+K) with client-side run search + navigation.

(function () {

const NAV_ITEMS = [
  { type: 'nav', label: 'All runs', view: 'list', icon: 'menu' },
  { type: 'nav', label: 'Compare runs', view: 'compare', icon: 'compare' },
  { type: 'nav', label: 'Cross-run search', view: 'search', icon: 'magnify' },
  { type: 'nav', label: 'How it works', view: 'how-it-works', icon: 'help-circle-outline' },
  { type: 'nav', label: 'Design language', view: 'language', icon: 'palette' },
];

function SearchPalette({ open, onClose }) {
  const [query, setQuery] = React.useState('');
  const [selectedIdx, setSelectedIdx] = React.useState(0);
  const inputRef = React.useRef(null);
  const listRef = React.useRef(null);

  // Fetch run list for filtering.
  const { rows } = useRunList();

  // Reset on open.
  React.useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIdx(0);
      // Focus is handled by Modal's focus trap, but we want to focus the input specifically.
      setTimeout(() => { if (inputRef.current) inputRef.current.focus(); }, 50);
    }
  }, [open]);

  // Build results list.
  const results = React.useMemo(() => {
    const items = [];
    const q = (query || '').toLowerCase().trim();

    // Nav items (always shown if matching or no query).
    NAV_ITEMS.forEach((nav) => {
      if (!q || nav.label.toLowerCase().includes(q)) {
        items.push(nav);
      }
    });

    // Runs (filtered by topic/id).
    if (rows && rows.length) {
      const matching = q
        ? rows.filter((r) => {
            const haystack = [r.id, r.displayId, r.topic, r.status, 'P' + r.phase]
              .filter(Boolean).join(' ').toLowerCase();
            return haystack.includes(q);
          })
        : rows.slice(0, 10); // Show first 10 when no query.
      matching.slice(0, 20).forEach((r) => {
        const displayId = r.displayId || r.id.slice(0, 4);
        items.push({
          type: 'run',
          label: r.topic || r.id,
          displayId,
          status: r.status,
          runId: r.id,
        });
      });
    }

    return items;
  }, [query, rows]);

  // Clamp selected index.
  React.useEffect(() => {
    if (selectedIdx >= results.length) {
      setSelectedIdx(Math.max(0, results.length - 1));
    }
  }, [results.length, selectedIdx]);

  // Scroll active result into view.
  React.useEffect(() => {
    if (!listRef.current) return;
    const active = listRef.current.querySelector('[data-active="true"]');
    if (active) active.scrollIntoView({ block: 'nearest' });
  }, [selectedIdx]);

  const handleSelect = (item) => {
    if (!item) return;
    if (item.type === 'nav') {
      navigate(item.view);
    } else if (item.type === 'run') {
      navigate('detail', item.runId);
    }
    onClose();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(results.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(0, i - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      handleSelect(results[selectedIdx]);
    }
  };

  if (!open) return null;

  return (
    <div className="dr-backdrop" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search palette"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        style={{
          position: 'fixed',
          top: '15%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: 'min(560px, 90vw)',
          maxHeight: '60vh',
          background: 'var(--md-surface)',
          border: '1px solid var(--md-outline-variant)',
          borderRadius: 'var(--md-shape-md)',
          boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          zIndex: 100,
        }}
      >
        {/* Search input */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px',
          borderBottom: '1px solid var(--md-outline-hair)',
        }}>
          <Mdi name="magnify" size={16} style={{ color: 'var(--md-on-surface-faint)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIdx(0); }}
            placeholder="Search runs, navigate..."
            autoFocus
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              fontSize: 14,
              fontFamily: 'var(--sans)',
              color: 'var(--md-on-surface)',
            }}
          />
          <kbd style={{
            padding: '2px 6px',
            fontSize: 10,
            fontFamily: 'var(--mono)',
            color: 'var(--md-on-surface-decor)',
            background: 'var(--md-surface-container-high)',
            border: '1px solid var(--md-outline-hair)',
            borderRadius: 3,
          }}>esc</kbd>
        </div>

        {/* Results */}
        <div ref={listRef} style={{
          flex: 1,
          overflow: 'auto',
          padding: '4px 0',
        }}>
          {results.length === 0 && (
            <div style={{
              padding: '24px 14px',
              textAlign: 'center',
              color: 'var(--md-on-surface-faint)',
              fontSize: 13,
            }}>
              No results for &ldquo;{query}&rdquo;
            </div>
          )}
          {results.map((item, i) => {
            const isActive = i === selectedIdx;
            return (
              <div
                key={item.type === 'run' ? item.runId : item.label}
                data-active={isActive}
                onClick={() => handleSelect(item)}
                onMouseEnter={() => setSelectedIdx(i)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 14px',
                  cursor: 'pointer',
                  background: isActive ? 'var(--md-surface-container-high)' : 'transparent',
                  borderLeft: isActive ? '2px solid var(--info)' : '2px solid transparent',
                }}
              >
                {item.type === 'nav' && (
                  <>
                    <Mdi name={item.icon} size={14} style={{ color: 'var(--md-on-surface-faint)', flexShrink: 0 }} />
                    <span style={{ fontSize: 13, color: 'var(--md-on-surface)' }}>{item.label}</span>
                    <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--md-on-surface-decor)', fontFamily: 'var(--mono)' }}>navigate</span>
                  </>
                )}
                {item.type === 'run' && (
                  <>
                    <span className="rid rid-sm" style={{
                      fontSize: 11, fontFamily: 'var(--mono)',
                      flexShrink: 0,
                    }}>
                      {item.displayId}
                    </span>
                    <span style={{
                      fontSize: 13, color: 'var(--md-on-surface-variant)',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                      minWidth: 0,
                    }}>
                      {item.label}
                    </span>
                    <span style={{
                      marginLeft: 'auto', flexShrink: 0,
                      fontSize: 10, color: 'var(--md-on-surface-faint)',
                      fontFamily: 'var(--mono)',
                    }}>
                      {item.status}
                    </span>
                  </>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer hint */}
        <div style={{
          padding: '6px 14px',
          borderTop: '1px solid var(--md-outline-hair)',
          display: 'flex', gap: 12, alignItems: 'center',
          fontSize: 10, color: 'var(--md-on-surface-decor)', fontFamily: 'var(--mono)',
        }}>
          <span><kbd style={{ padding: '1px 4px', background: 'var(--md-surface-container-high)', border: '1px solid var(--md-outline-hair)', borderRadius: 3, fontSize: 10 }}>&uarr;&darr;</kbd> navigate</span>
          <span><kbd style={{ padding: '1px 4px', background: 'var(--md-surface-container-high)', border: '1px solid var(--md-outline-hair)', borderRadius: 3, fontSize: 10 }}>enter</kbd> select</span>
          <span><kbd style={{ padding: '1px 4px', background: 'var(--md-surface-container-high)', border: '1px solid var(--md-outline-hair)', borderRadius: 3, fontSize: 10 }}>esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SearchPalette });
})();
