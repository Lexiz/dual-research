// settings.jsx — admin allowlist management UI (spec 0022).
//
// Renders at #/settings. Admin-only: non-admins see an inline "admin only"
// message instead of the table. Calls the spec-0022 CRUD endpoints:
//
//   GET    /api/approved-emails
//   POST   /api/approved-emails           { email, isAdmin }
//   DELETE /api/approved-emails/<email>
//
// Server enforces "can't remove yourself" and "can't remove the only admin"
// with 409s; the UI surfaces those as an inline error toast.

function SettingsScreen({ me }) {
  const isAdmin = !!me?.isAdmin;

  if (!isAdmin) {
    return (
      <div style={{
        height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: 'var(--md-on-surface-muted)', fontSize: 14, padding: 24, textAlign: 'center',
      }}>
        Settings are admin-only. Ask an admin to add you to the allowlist
        with admin rights if you need access.
      </div>
    );
  }
  return <AllowlistManager myEmail={(me?.email || '').toLowerCase()} />;
}

function AllowlistManager({ myEmail }) {
  const [rows, setRows] = React.useState(null);    // null = loading
  const [error, setError] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [newEmail, setNewEmail] = React.useState('');
  const [newAdmin, setNewAdmin] = React.useState(false);
  const inputRef = React.useRef(null);

  const load = React.useCallback(() => {
    authedFetch('/api/approved-emails')
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(data => { setRows(data || []); setError(null); })
      .catch(e => { setError(String(e)); setRows([]); });
  }, []);

  React.useEffect(() => { load(); }, [load]);

  const onAdd = async () => {
    const email = newEmail.trim().toLowerCase();
    if (!email.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await authedFetch('/api/approved-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, isAdmin: newAdmin }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      setNewEmail('');
      setNewAdmin(false);
      inputRef.current?.focus();
      load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const onRemove = async (email) => {
    if (!window.confirm(`Remove ${email} from the allowlist?`)) return;
    setBusy(true);
    setError(null);
    try {
      const r = await authedFetch(`/api/approved-emails/${encodeURIComponent(email)}`, { method: 'DELETE' });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: 24, color: 'var(--md-on-surface)', maxWidth: 720, margin: '0 auto', overflow: 'auto', height: '100%' }}>
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 18, fontWeight: 600 }}>Email allowlist</div>
        <div style={{ fontSize: 13, color: 'var(--md-on-surface-muted)', marginTop: 4 }}>
          Anyone with a Google account at one of these addresses can sign in.
          Admins can manage this list.
        </div>
      </div>

      {error && (
        <div style={{
          background: 'var(--warn-bg, rgba(217, 130, 80, 0.12))',
          color: 'var(--warn, #d98250)',
          border: '1px solid var(--warn-border, rgba(217, 130, 80, 0.35))',
          padding: '8px 12px', borderRadius: 6, fontSize: 13, margin: '12px 0',
        }}>
          {error}
        </div>
      )}

      <div style={{ marginTop: 16, border: '1px solid var(--md-outline-hair)', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: 'var(--md-surface-container-low)', color: 'var(--md-on-surface-muted)' }}>
              <th style={th}>Email</th>
              <th style={{ ...th, width: 100 }}>Role</th>
              <th style={{ ...th, width: 100, textAlign: 'right' }}></th>
            </tr>
          </thead>
          <tbody>
            {rows === null && (
              <tr><td colSpan={3} style={{ ...td, color: 'var(--md-on-surface-muted)' }}>Loading…</td></tr>
            )}
            {rows && rows.length === 0 && (
              <tr><td colSpan={3} style={{ ...td, color: 'var(--md-on-surface-muted)' }}>No allowlist rows.</td></tr>
            )}
            {rows && rows.map(row => (
              <tr key={row.email} style={{ borderTop: '1px solid var(--md-outline-hair)' }}>
                <td style={td}>{row.email}</td>
                <td style={td}>
                  {row.isAdmin
                    ? <span style={adminBadge}>admin</span>
                    : <span style={{ color: 'var(--md-on-surface-muted)' }}>member</span>}
                </td>
                <td style={{ ...td, textAlign: 'right' }}>
                  {row.email === myEmail
                    ? <span style={{ color: 'var(--md-on-surface-muted)', fontSize: 11 }}>(you)</span>
                    : <button onClick={() => onRemove(row.email)} disabled={busy} style={removeBtn}>Remove</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{
        marginTop: 16, padding: 16, border: '1px dashed var(--md-outline-variant)',
        borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      }}>
        <input
          ref={inputRef}
          type="email"
          placeholder="someone@example.com"
          value={newEmail}
          onChange={e => setNewEmail(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') onAdd(); }}
          disabled={busy}
          style={input}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--md-on-surface-variant)' }}>
          <input type="checkbox" checked={newAdmin} onChange={e => setNewAdmin(e.target.checked)} />
          Admin
        </label>
        <button onClick={onAdd} disabled={busy || !newEmail.trim()} style={addBtn}>Add</button>
      </div>
    </div>
  );
}

const th = { textAlign: 'left', padding: '10px 14px', fontWeight: 500, fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.04em' };
const td = { padding: '10px 14px', verticalAlign: 'middle' };
const adminBadge = {
  display: 'inline-block', padding: '1px 8px', borderRadius: 999,
  background: 'var(--agent-b-bg-strong)', color: 'var(--agent-b)',
  fontSize: 11, fontWeight: 500, border: '1px solid var(--agent-b-border)',
};
const input = {
  flex: 1, minWidth: 220,
  padding: '8px 12px', borderRadius: 6, fontSize: 13,
  background: 'var(--md-surface-container-low)', color: 'var(--md-on-surface)',
  border: '1px solid var(--md-outline-variant)', fontFamily: 'inherit',
};
const addBtn = {
  padding: '8px 14px', borderRadius: 6, cursor: 'pointer',
  background: 'var(--md-surface-container-high)', color: 'var(--md-on-surface)',
  border: '1px solid var(--md-outline-variant)', fontSize: 13, fontFamily: 'inherit',
};
const removeBtn = {
  padding: '4px 10px', borderRadius: 5, cursor: 'pointer',
  background: 'transparent', color: 'var(--md-on-surface-muted)',
  border: '1px solid var(--md-outline-variant)', fontSize: 12, fontFamily: 'inherit',
};

window.SettingsScreen = SettingsScreen;
