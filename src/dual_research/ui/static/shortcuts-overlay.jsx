// shortcuts-overlay.jsx -- SPEC-0059 A11Y-04
// Full-screen overlay listing all keyboard shortcuts by context.

(function () {

const SHORTCUT_GROUPS = [
  {
    title: 'Global',
    shortcuts: [
      { keys: ['?'], desc: 'Open this shortcuts overlay' },
      { keys: ['\u2318K', 'Ctrl+K'], desc: 'Open search palette' },
      { keys: ['/'], desc: 'Focus run-list search (when on run list)' },
      { keys: ['Esc'], desc: 'Close overlay / modal / palette' },
    ],
  },
  {
    title: 'Navigation (via search palette)',
    shortcuts: [
      { keys: ['\u2318K', 'compare'], desc: 'Compare runs (side-by-side)' },
      { keys: ['\u2318K', 'search'], desc: 'Cross-run search' },
    ],
  },
  {
    title: 'Negotiate review modal',
    shortcuts: [
      { keys: ['j', '\u2193'], desc: 'Next item' },
      { keys: ['k', '\u2191'], desc: 'Previous item' },
      { keys: ['Enter'], desc: 'Jump to active item' },
    ],
  },
];

function ShortcutsOverlay({ open, onClose }) {
  if (!open) return null;

  return (
    <Modal open={open} onClose={onClose} title="Keyboard shortcuts">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '4px 0' }}>
        {SHORTCUT_GROUPS.map((group) => (
          <div key={group.title}>
            <div style={{
              fontSize: 'var(--t-meta)',
              fontWeight: 'var(--w-semibold)',
              color: 'var(--md-on-surface-variant)',
              marginBottom: 8,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}>
              {group.title}
            </div>
            <div style={{
              display: 'flex', flexDirection: 'column', gap: 0,
              background: 'var(--md-surface-container-low)',
              border: '1px solid var(--md-outline-hair)',
              borderRadius: 'var(--md-shape-md)',
              overflow: 'hidden',
            }}>
              {group.shortcuts.map((s, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 12px',
                  borderBottom: i < group.shortcuts.length - 1 ? '1px solid var(--md-outline-hair)' : 'none',
                }}>
                  <span style={{ fontSize: 'var(--t-body)', color: 'var(--md-on-surface-variant)' }}>
                    {s.desc}
                  </span>
                  <span style={{ display: 'flex', gap: 4, flexShrink: 0, marginLeft: 16 }}>
                    {s.keys.map((k, j) => (
                      <React.Fragment key={j}>
                        {j > 0 && <span style={{ color: 'var(--md-on-surface-decor)', fontSize: 11 }}>/</span>}
                        <kbd style={{
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                          minWidth: 24, height: 22,
                          padding: '0 6px',
                          background: 'var(--md-surface-container-high)',
                          border: '1px solid var(--md-outline-variant)',
                          borderRadius: 'var(--md-shape-sm)',
                          fontFamily: 'var(--mono)',
                          fontSize: 11,
                          color: 'var(--md-on-surface)',
                          lineHeight: 1,
                        }}>
                          {k}
                        </kbd>
                      </React.Fragment>
                    ))}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}

Object.assign(window, { ShortcutsOverlay });
})();
