// admin-users.jsx — Admin Users page with ProgressSegs strip (SPEC-0103).
//
// Renders the onboarding tour progress per user. If no admin-list
// endpoint exists, renders the current user only with their own
// ProgressSegs derived from localStorage.

(function () {
  const TOTAL_STEPS = 8;

  function AdminUsers() {
    const me = useMe();
    const tourStep = React.useMemo(() => {
      try {
        const onboarded = localStorage.getItem('dr_onboarded') === 'true';
        if (onboarded) return TOTAL_STEPS + 1; // completed all
        const saved = parseInt(localStorage.getItem('dr_tour_step'), 10);
        return (saved > 0 && saved <= TOTAL_STEPS) ? saved : 1;
      } catch (e) { return 1; }
    }, []);

    const email = me?.email || 'unknown';
    const isComplete = tourStep > TOTAL_STEPS;
    const currentStep = isComplete ? TOTAL_STEPS : tourStep;
    const statusLabel = isComplete ? 'completed' : tourStep === 1 ? 'not started' : 'in progress';
    const statusTone = isComplete ? 'ok' : tourStep === 1 ? 'muted' : 'info';

    return (
      <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
        <h2 style={{
          font: 'var(--md-w-medium) var(--md-title-l-size)/var(--md-title-l-lh) var(--md-font-brand)',
          color: 'var(--md-on-surface)',
          margin: '0 0 24px',
        }}>Users</h2>

        <div className="md-list" role="list">
          <UserRow
            email={email}
            step={currentStep}
            total={TOTAL_STEPS}
            isComplete={isComplete}
            statusLabel={statusLabel}
            statusTone={statusTone}
          />
        </div>

        <p style={{
          marginTop: 24,
          font: 'var(--md-body-s-size)/var(--md-body-s-lh) var(--md-font-plain)',
          color: 'var(--md-on-surface-faint)',
        }}>
          Showing current user only. Multi-user admin list requires a backend endpoint.
        </p>
      </div>
    );
  }

  function UserRow({ email, step, total, isComplete, statusLabel, statusTone }) {
    const segments = [];
    for (let i = 1; i <= total; i++) {
      let mod = 'queued';
      if (isComplete || i < step) mod = 'done';
      else if (i === step && !isComplete) mod = 'curr';
      segments.push(
        <div key={i} className={`seg-track__seg seg-track__seg--${mod}`} />
      );
    }

    const doneCount = isComplete ? total : Math.max(0, step - 1);

    return (
      <div className="md-list__item" role="listitem">
        <span className="ms ms-24 md-list__lead" aria-hidden="true">account_circle</span>
        <div className="md-list__body">
          <div className="md-list__headline">{email}</div>
          <div className="md-list__support">
            {isComplete ? 'tour completed' : step === 1 ? 'tour not started' : `paused at step ${step}`}
          </div>
        </div>
        <div style={{ width: 320 }}>
          <div className="seg-track" aria-label={`${doneCount} of ${total} steps`}>
            {segments}
          </div>
          <div className="t-label-s subtle" style={{ marginTop: 4 }}>{doneCount} / {total}</div>
        </div>
        <span className={`md-status md-status--${statusTone === 'info' ? 'running' : statusTone === 'ok' ? 'converged' : 'idle'}`}>
          {statusLabel}
        </span>
      </div>
    );
  }

  window.AdminUsers = AdminUsers;
})();
