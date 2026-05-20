// settings.jsx — Spec 0125 unified Admin/Settings surface.
//
// One route (#/settings) with two sub-tabs:
//   • Allowlist  — existing email allowlist CRUD (was the old /settings)
//   • Users      — the user table (was the old /admin/users stub), now backed
//                  by /api/users with onboarding state, per-user actions, bulk
//                  actions, and global onboarding controls.
//
// Hash routing: /settings#allowlist (default) and /settings#users.
//
// Admin-only at the page level; non-admins see an inline message.

function SettingsScreen({ me }) {
  const isAdmin = !!me?.isAdmin;
  const [tab, setTab] = React.useState(() => {
    try {
      const h = window.location.hash || '';
      // /settings is hash-routed: full hash is "#/settings#users" or
      // "#/settings#allowlist". Split on second '#'.
      const parts = h.split('#');
      const sub = (parts[2] || '').toLowerCase();
      return sub === 'users' ? 'users' : 'allowlist';
    } catch (e) { return 'allowlist'; }
  });

  React.useEffect(() => {
    // Reflect tab in URL hash without nuking the route.
    try {
      const baseHash = '#/settings';
      const newHash = tab === 'users' ? `${baseHash}#users` : `${baseHash}#allowlist`;
      if (window.location.hash !== newHash) {
        history.replaceState(null, '', newHash);
      }
    } catch (e) {}
    // Also flip <title>.
    const prev = document.title;
    document.title = (tab === 'users' ? 'Users · Settings' : 'Allowlist · Settings') + ' · Dual Research';
    return () => { document.title = prev; };
  }, [tab]);

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

  return (
    <div className="settings-page">
      <div className="settings-page__inner">
        <header className="settings-page__header">
          <h1 className="settings-page__title">Settings</h1>
          <span className="settings-page__spacer" />
          <div className="settings-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              className={'tab' + (tab === 'allowlist' ? ' is-active' : '')}
              aria-selected={tab === 'allowlist'}
              onClick={() => setTab('allowlist')}
            >Allowlist</button>
            <button
              type="button"
              role="tab"
              className={'tab' + (tab === 'users' ? ' is-active' : '')}
              aria-selected={tab === 'users'}
              onClick={() => setTab('users')}
            >Users</button>
          </div>
        </header>

        <div className="settings-page__body">
          {tab === 'allowlist'
            ? <AllowlistManager myEmail={(me?.email || '').toLowerCase()} />
            : <UsersManager myEmail={(me?.email || '').toLowerCase()} />
          }
        </div>
      </div>
    </div>
  );
}

// ─── Allowlist sub-tab (unchanged from pre-0124) ────────────────────────────

function AllowlistManager({ myEmail }) {
  const [rows, setRows] = React.useState(null);
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
    <div>
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 18, fontWeight: 600 }}>Email allowlist</div>
        <div style={{ fontSize: 13, color: 'var(--md-on-surface-muted)', marginTop: 4 }}>
          Anyone with a Google account at one of these addresses can sign in.
          Admins can manage this list.
        </div>
      </div>

      {error && (
        <div className="settings-error">{error}</div>
      )}

      <div style={{ marginTop: 16, border: '1px solid var(--md-outline-hair)', borderRadius: 8, overflow: 'hidden' }}>
        <table className="settings-table">
          <thead>
            <tr>
              <th>Email</th>
              <th style={{ width: 100 }}>Role</th>
              <th style={{ width: 100, textAlign: 'right' }}></th>
            </tr>
          </thead>
          <tbody>
            {rows === null && (
              <tr><td colSpan={3} className="settings-table__muted">Loading…</td></tr>
            )}
            {rows && rows.length === 0 && (
              <tr><td colSpan={3} className="settings-table__muted">No allowlist rows.</td></tr>
            )}
            {rows && rows.map(row => (
              <tr key={row.email}>
                <td>{row.email}</td>
                <td>
                  {row.isAdmin
                    ? <span className="settings-admin-badge">admin</span>
                    : <span style={{ color: 'var(--md-on-surface-muted)' }}>member</span>}
                </td>
                <td style={{ textAlign: 'right' }}>
                  {row.email === myEmail
                    ? <span style={{ color: 'var(--md-on-surface-muted)', fontSize: 11 }}>(you)</span>
                    : <button onClick={() => onRemove(row.email)} disabled={busy} className="settings-btn">Remove</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="settings-add-row">
        <input
          ref={inputRef}
          type="email"
          placeholder="someone@example.com"
          value={newEmail}
          onChange={e => setNewEmail(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') onAdd(); }}
          disabled={busy}
          className="settings-input"
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--md-on-surface-variant)' }}>
          <input type="checkbox" checked={newAdmin} onChange={e => setNewAdmin(e.target.checked)} />
          Admin
        </label>
        <button onClick={onAdd} disabled={busy || !newEmail.trim()} className="settings-btn settings-btn--primary">Add</button>
      </div>
    </div>
  );
}

// ─── Users sub-tab (new, replaces the old AdminUsers stub) ──────────────────

function UsersManager({ myEmail }) {
  const [rows, setRows] = React.useState(null);
  const [systemReq, setSystemReq] = React.useState(false);
  const [systemLoaded, setSystemLoaded] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [selected, setSelected] = React.useState(() => new Set());
  const [filter, setFilter] = React.useState('all'); // all | admins | pending | completed
  const [q, setQ] = React.useState('');

  const load = React.useCallback(() => {
    authedFetch('/api/users')
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(data => { setRows(data || []); setError(null); })
      .catch(e => { setError(String(e)); setRows([]); });
    authedFetch('/api/system-settings')
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(data => { setSystemReq(!!data.onboardingRequired); setSystemLoaded(true); })
      .catch(() => { setSystemLoaded(true); });
  }, []);

  React.useEffect(() => { load(); }, [load]);

  const toggleSelect = (email) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(email)) next.delete(email);
      else next.add(email);
      return next;
    });
  };

  const resetOne = async (email) => {
    if (!window.confirm(`Re-trigger onboarding for ${email}? They'll see step 1 on next page load.`)) return;
    setBusy(true);
    setError(null);
    try {
      const r = await authedFetch(`/api/users/${encodeURIComponent(email)}/reset-onboarding`, { method: 'POST' });
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

  const resetBulk = async () => {
    const emails = [...selected];
    if (emails.length === 0) return;
    if (!window.confirm(`Re-trigger onboarding for ${emails.length} user${emails.length === 1 ? '' : 's'}?`)) return;
    setBusy(true);
    setError(null);
    try {
      const r = await authedFetch('/api/users/bulk-reset-onboarding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emails }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      setSelected(new Set());
      load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const removeBulk = async () => {
    const emails = [...selected].filter(e => e !== myEmail);
    if (emails.length === 0) return;
    if (!window.confirm(`Remove ${emails.length} user${emails.length === 1 ? '' : 's'} from the allowlist?`)) return;
    setBusy(true);
    setError(null);
    try {
      for (const e of emails) {
        const r = await authedFetch(`/api/approved-emails/${encodeURIComponent(e)}`, { method: 'DELETE' });
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(`${e}: ${body.detail || `HTTP ${r.status}`}`);
        }
      }
      setSelected(new Set());
      load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const broadcastReset = async () => {
    const n = (rows || []).length;
    if (!window.confirm(`This will re-trigger onboarding for all ${n} user${n === 1 ? '' : 's'}. Continue?`)) return;
    setBusy(true);
    setError(null);
    try {
      const r = await authedFetch('/api/onboarding/broadcast-reset', { method: 'POST' });
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

  const setSystemRequired = async (flag) => {
    setSystemReq(flag);
    setBusy(true);
    setError(null);
    try {
      const r = await authedFetch('/api/system-settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ onboardingRequired: flag }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
    } catch (e) {
      // Roll back optimistic update on error.
      setSystemReq(!flag);
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  const removeOne = async (email) => {
    if (!window.confirm(`Remove ${email} from the allowlist?`)) return;
    setBusy(true);
    setError(null);
    try {
      const r = await authedFetch(`/api/approved-emails/${encodeURIComponent(email)}`, { method: 'DELETE' });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${r.status}`);
      }
      setSelected(prev => {
        const next = new Set(prev); next.delete(email); return next;
      });
      load();
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  // Status string + tone for a row.
  function statusOf(row) {
    if (row.mustRestart) return { label: 'reset pending', tone: 'warn' };
    if (row.onboardedAt) {
      const ver = row.onboardedAtVersion ? ` · v${row.onboardedAtVersion}` : '';
      return { label: `✓ completed${ver}`, tone: 'ok' };
    }
    if ((row.tourStep || 1) > 1) return { label: `in progress · step ${row.tourStep} / 8`, tone: 'info' };
    return { label: '⊘ not started', tone: 'muted' };
  }

  // Last seen — relative if < 7d, absolute date otherwise.
  function relativeTime(iso) {
    if (!iso) return '—';
    const now = Date.now();
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return '—';
    const diff = (now - t) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 7 * 86400) return `${Math.floor(diff / 86400)}d ago`;
    return new Date(t).toISOString().slice(0, 10);
  }

  // Filter + search.
  const filtered = (rows || []).filter(r => {
    if (filter === 'admins' && !r.isAdmin) return false;
    if (filter === 'pending' && (r.onboardedAt || r.mustRestart)) return false;
    if (filter === 'completed' && (!r.onboardedAt || r.mustRestart)) return false;
    if (q) {
      const blob = `${r.email} ${r.isAdmin ? 'admin' : 'member'} ${statusOf(r).label}`.toLowerCase();
      if (!blob.includes(q.toLowerCase())) return false;
    }
    return true;
  });

  const counts = {
    all: (rows || []).length,
    admins: (rows || []).filter(r => r.isAdmin).length,
    pending: (rows || []).filter(r => !r.onboardedAt || r.mustRestart).length,
    completed: (rows || []).filter(r => r.onboardedAt && !r.mustRestart).length,
  };

  const selectAllVisible = () => {
    const next = new Set(selected);
    filtered.forEach(r => next.add(r.email));
    setSelected(next);
  };
  const clearSelection = () => setSelected(new Set());

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 18, fontWeight: 600 }}>Users</div>
        <div style={{ fontSize: 13, color: 'var(--md-on-surface-muted)', marginTop: 4 }}>
          Every allowlisted user with their role and onboarding state. Reset the
          tour for one user, several at once, or everyone.
        </div>
      </div>

      {error && <div className="settings-error">{error}</div>}

      {/* Global onboarding controls */}
      <div className="global-onboarding-panel">
        <div className="gop__title">Global onboarding</div>
        <label className="gop__toggle">
          <input
            type="checkbox"
            checked={systemReq}
            onChange={(e) => setSystemRequired(e.target.checked)}
            disabled={!systemLoaded || busy}
          />
          <span>Required for all new sign-ins</span>
        </label>
        <span className="gop__spacer" />
        <button
          type="button"
          className="settings-btn settings-btn--danger"
          onClick={broadcastReset}
          disabled={busy || !(rows || []).length}
        >Reset for everyone</button>
      </div>

      {/* Filter row */}
      <div className="users-filter-row">
        {[
          ['all', 'All'],
          ['admins', 'Admins'],
          ['pending', 'Pending'],
          ['completed', 'Completed'],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={'users-chip' + (filter === key ? ' is-active' : '')}
            onClick={() => setFilter(key)}
          >
            <span>{label}</span>
            <span className="users-chip__count">{counts[key]}</span>
          </button>
        ))}
        <span className="users-filter-row__spacer" />
        <input
          type="search"
          className="settings-input settings-input--search"
          placeholder="search email or status…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="users-bulk-bar">
          <span>{selected.size} selected</span>
          <button type="button" className="settings-btn" onClick={clearSelection}>Clear</button>
          <span className="users-bulk-bar__spacer" />
          <button type="button" className="settings-btn" onClick={resetBulk} disabled={busy}>
            Reset onboarding ({selected.size})
          </button>
          <button type="button" className="settings-btn settings-btn--danger" onClick={removeBulk} disabled={busy}>
            Remove ({selected.size})
          </button>
        </div>
      )}

      {/* Table */}
      <div className="users-table-wrap">
        <table className="settings-table users-table">
          <thead>
            <tr>
              <th style={{ width: 36 }}>
                <input
                  type="checkbox"
                  checked={filtered.length > 0 && filtered.every(r => selected.has(r.email))}
                  onChange={(e) => e.target.checked ? selectAllVisible() : clearSelection()}
                />
              </th>
              <th>Email</th>
              <th style={{ width: 90 }}>Role</th>
              <th style={{ width: 240 }}>Onboarding</th>
              <th style={{ width: 110 }}>Last seen</th>
              <th style={{ width: 240, textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows === null && (
              <tr><td colSpan={6} className="settings-table__muted">Loading…</td></tr>
            )}
            {rows && filtered.length === 0 && (
              <tr><td colSpan={6} className="settings-table__muted">No users match.</td></tr>
            )}
            {filtered.map(row => {
              const st = statusOf(row);
              const isYou = row.email === myEmail;
              return (
                <tr key={row.email}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(row.email)}
                      onChange={() => toggleSelect(row.email)}
                    />
                  </td>
                  <td>{row.email}{isYou && <span className="users-you"> (you)</span>}</td>
                  <td>
                    {row.isAdmin
                      ? <span className="settings-admin-badge">admin</span>
                      : <span style={{ color: 'var(--md-on-surface-muted)' }}>member</span>}
                  </td>
                  <td><span className={`users-status users-status--${st.tone}`}>{st.label}</span></td>
                  <td><span style={{ color: 'var(--md-on-surface-muted)', fontSize: 12 }}>{relativeTime(row.lastSeenAt)}</span></td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      type="button"
                      className="settings-btn"
                      onClick={() => resetOne(row.email)}
                      disabled={busy}
                    >Reset onboarding</button>
                    {!isYou && (
                      <button
                        type="button"
                        className="settings-btn settings-btn--danger"
                        onClick={() => removeOne(row.email)}
                        disabled={busy}
                        style={{ marginLeft: 8 }}
                      >Remove</button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

window.SettingsScreen = SettingsScreen;
