// router.jsx — URL hash routing for the UI.
//
//   #/                   → run list
//   #/runs/<run_id>      → run detail
//   #/language           → design language
//   #/settings           → admin allowlist (spec 0022)
//   #/how-it-works       → protocol explanation + release notes (spec 0023)
//
// Empty hash defaults to the list. `navigate(path)` writes the hash; the
// `useRoute` hook listens for `hashchange` and re-renders.

function parseHash(hash) {
  const h = (hash || window.location.hash || '#/').replace(/^#/, '');
  // Normalize: '', '/' → list
  if (h === '' || h === '/') return { view: 'list' };
  if (h === '/language') return { view: 'language' };
  if (h === '/settings') return { view: 'settings' };
  if (h === '/how-it-works') return { view: 'how-it-works' };
  if (h === '/compare') return { view: 'compare' };
  if (h === '/search') return { view: 'search' };
  if (h === '/admin/users') return { view: 'admin-users' };
  const m = h.match(/^\/runs\/([^/?#]+)/);
  if (m) return { view: 'detail', runId: decodeURIComponent(m[1]) };
  // Unknown hash — fall back to list.
  return { view: 'list' };
}

function buildHash(route) {
  if (route.view === 'detail' && route.runId) {
    return `#/runs/${encodeURIComponent(route.runId)}`;
  }
  if (route.view === 'language') return '#/language';
  if (route.view === 'settings') return '#/settings';
  if (route.view === 'how-it-works') return '#/how-it-works';
  if (route.view === 'compare') return '#/compare';
  if (route.view === 'search') return '#/search';
  if (route.view === 'admin-users') return '#/admin/users';
  return '#/';
}

function navigate(viewOrRoute, runId) {
  const target = typeof viewOrRoute === 'string'
    ? { view: viewOrRoute, runId }
    : viewOrRoute;
  const hash = buildHash(target);
  if (window.location.hash !== hash) {
    window.location.hash = hash;
  }
}

function useRoute() {
  const [route, setRoute] = React.useState(() => parseHash());

  React.useEffect(() => {
    const onChange = () => setRoute(parseHash());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  return { route, navigate };
}

Object.assign(window, { useRoute, navigate, parseHash });
