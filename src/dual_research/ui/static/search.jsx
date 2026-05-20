// search.jsx -- SPEC-0060 NEW-02
// Cross-run search dashboard. Queries /api/search?q=... for matches across
// all runs (topics, brief bodies, final docs). Results grouped by run.

(function () {

function CrossRunSearchScreen({ navigate }) {
  const [query, setQuery] = React.useState('');
  const [results, setResults] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [searched, setSearched] = React.useState(false);
  const inputRef = React.useRef(null);
  const debounceRef = React.useRef(null);

  React.useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, []);

  // Debounced search.
  React.useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const q = (query || '').trim();
    if (!q || q.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        if (resp.ok) {
          const data = await resp.json();
          setResults(data || []);
        } else {
          setResults([]);
        }
      } catch (e) {
        setResults([]);
      }
      setLoading(false);
      setSearched(true);
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  // Group results by runId.
  const grouped = React.useMemo(() => {
    const map = new Map();
    (results || []).forEach((r) => {
      if (!map.has(r.runId)) {
        map.set(r.runId, { runId: r.runId, displayId: r.displayId, topic: r.topic, matches: [] });
      }
      map.get(r.runId).matches.push(r);
    });
    return Array.from(map.values());
  }, [results]);

  return (
    <div style={{
      height: '100%', overflow: 'auto',
      padding: '24px 32px',
      background: 'var(--md-surface)',
    }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <h2 style={{
            fontSize: 'var(--md-title-l-size)',
            lineHeight: 'var(--md-title-l-lh)',
            fontWeight: 'var(--md-w-semi)',
            color: 'var(--md-on-surface)',
            margin: 0,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <Mdi name="magnify" size={20} />
            Cross-run search
          </h2>
          <p style={{ fontSize: 'var(--md-body-m-size)', lineHeight: 'var(--md-body-m-lh)', color: 'var(--md-on-surface-muted)', margin: '4px 0 0' }}>
            Search across all runs by topic, brief content, and final documents.
          </p>
        </div>

        {/* Search input */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px',
          background: 'var(--md-surface-container-low)',
          border: '1px solid var(--md-outline-variant)',
          borderRadius: 'var(--md-shape-md)',
          marginBottom: 20,
        }}>
          <Mdi name="magnify" size={16} style={{ color: 'var(--md-on-surface-faint)', flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to search across all runs..."
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              fontSize: 14,
              fontFamily: 'var(--md-font-plain)',
              color: 'var(--md-on-surface)',
            }}
          />
          {loading && (
            <span style={{ fontSize: 11, color: 'var(--md-on-surface-faint)', fontFamily: 'var(--md-font-data)' }}>
              searching...
            </span>
          )}
        </div>

        {/* Results */}
        {searched && results.length === 0 && (
          <div style={{
            padding: '32px 0',
            textAlign: 'center',
            color: 'var(--md-on-surface-faint)',
            fontSize: 13,
          }}>
            No results found for "{query}"
          </div>
        )}

        {grouped.map((group) => (
          <div key={group.runId} style={{
            marginBottom: 16,
            background: 'var(--md-surface-container-low)',
            border: '1px solid var(--md-outline-hair)',
            borderRadius: 'var(--md-shape-md)',
            overflow: 'hidden',
          }}>
            {/* Run header */}
            <div
              onClick={() => navigate('detail', group.runId)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 14px',
                borderBottom: '1px solid var(--md-outline-hair)',
                cursor: 'pointer',
                background: 'var(--md-surface-container-low)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--md-surface-container)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--md-surface-container-low)'; }}
            >
              <span className="rid rid-sm" style={{
                fontSize: 11, fontFamily: 'var(--md-font-data)', flexShrink: 0,
              }}>
                {group.displayId}
              </span>
              <span style={{
                fontSize: 13, color: 'var(--md-on-surface)', fontWeight: 'var(--md-w-medium)',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              }}>
                {group.topic || group.runId}
              </span>
              <span style={{
                marginLeft: 'auto', flexShrink: 0,
                fontSize: 10, color: 'var(--md-on-surface-faint)', fontFamily: 'var(--md-font-data)',
              }}>
                {group.matches.length} match{group.matches.length !== 1 ? 'es' : ''}
              </span>
            </div>

            {/* Match rows */}
            {group.matches.map((m, i) => (
              <div
                key={i}
                onClick={() => navigate('detail', m.runId)}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '8px 14px 8px 24px',
                  borderBottom: i < group.matches.length - 1 ? '1px solid var(--md-outline-hair)' : 'none',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--md-surface-container)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <span className="chip chip-sm" style={{
                  fontSize: 10, flexShrink: 0, marginTop: 2,
                }}>
                  {m.matchType}
                </span>
                <span style={{
                  fontSize: 12.5, color: 'var(--md-on-surface-variant)',
                  lineHeight: 1.4,
                  overflow: 'hidden',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                }}>
                  {m.snippet}
                </span>
              </div>
            ))}
          </div>
        ))}

        {!searched && !loading && (
          <div style={{
            padding: '48px 0',
            textAlign: 'center',
            color: 'var(--md-on-surface-faint)',
          }}>
            <Mdi name="magnify" size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
            <div style={{ fontSize: 13 }}>Enter at least 2 characters to search</div>
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { CrossRunSearchScreen });
})();
