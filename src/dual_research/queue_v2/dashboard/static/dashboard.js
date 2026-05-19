// queue-v2 dashboard — connects to /events SSE; falls back to /state.json polling.

const $statusBadge = document.getElementById("status");
const $list = document.getElementById("spec-list");
const $title = document.getElementById("right-title");
const $sub = document.getElementById("right-sub");
const $body = document.getElementById("steps-body");
const $terminal = document.getElementById("terminal");
const $table = document.getElementById("steps");

let lastState = null;

function fmt(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) return `${m}m ${String(s).padStart(2, "0")}s`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return `${h}h ${String(rm).padStart(2, "0")}m`;
}

function specStatus(state, spec) {
  if (state.active && state.active.spec === spec) return "active";
  if (state.completed.includes(spec)) return "done";
  if (state.failure && state.failure.spec === spec) return "failed";
  return "queued";
}

function renderLeft(state) {
  const all = [
    ...state.completed,
    ...(state.active ? [state.active.spec] : []),
    ...state.queue,
  ];
  const seen = new Set();
  const ordered = [];
  for (const s of all) {
    if (!seen.has(s)) { ordered.push(s); seen.add(s); }
  }
  $list.innerHTML = "";
  for (const spec of ordered) {
    const li = document.createElement("li");
    const status = specStatus(state, spec);
    li.className = status;
    li.innerHTML = `
      <span class="spec-id">${spec}</span>
      <span class="spec-status">${status}</span>
    `;
    $list.appendChild(li);
  }
}

function renderRight(state) {
  if (!state.active && !state.queue.length) {
    renderTerminal(state.terminal);
    $title.textContent = "Queue complete";
    $sub.textContent = "";
    $table.hidden = true;
    return;
  }
  $table.hidden = false;
  $terminal.hidden = true;

  if (!state.active) {
    $title.textContent = "Idle";
    $sub.textContent = `Next up: spec ${state.queue[0]}`;
    $body.innerHTML = "";
    return;
  }

  const a = state.active;
  $title.textContent = `Spec ${a.spec} — ${a.slug}`;
  $sub.textContent = `Branch \`${a.branch}\` · started ${a.started_at}`;

  $body.innerHTML = "";
  for (const step of state.step_order) {
    const meta = a.steps[step] || { status: "pending" };
    const label = state.step_labels[step];
    const median = state.medians_s[step];
    const elapsed = (step === a.step) ? state.active_step_elapsed_s : meta.duration_s;
    const detail = renderDetail(step, a.detail[step] || {}, meta);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${step.split("_")[0]}</td>
      <td>${label}</td>
      <td><span class="status-cell status-${meta.status}">${meta.status.replace("_", " ")}</span></td>
      <td>${fmt(median)}</td>
      <td>${meta.status === "in_progress" || meta.status === "done" ? fmt(elapsed) : "—"}</td>
      <td class="detail">${detail}</td>
    `;
    $body.appendChild(tr);
  }
}

function renderDetail(step, detail, meta) {
  if (meta.status === "pending") return "—";
  if (meta.status === "skipped") return `<span class="muted">${detail.reason || ""}</span>`;
  switch (step) {
    case "1_read": {
      const parts = [];
      if (detail.files_touched_count !== undefined) parts.push(`${detail.files_touched_count} files`);
      if (detail.matrix_rows !== undefined) parts.push(`${detail.matrix_rows} matrix rows`);
      if (detail.acceptance_count !== undefined) parts.push(`${detail.acceptance_count} acceptance`);
      return parts.join(" · ");
    }
    case "2_reason": {
      const n = detail.alignment_note_count ?? 0;
      return n === 0
        ? `<span class="ok">0 alignment notes</span>`
        : `<span class="pri">${n} alignment note(s) — see reason-notes.md</span>`;
    }
    case "3_rewrite": {
      if (detail.reason) return `<span class="muted">${detail.reason}</span>`;
      if (detail.edit_count !== undefined) return `${detail.edit_count} edit(s) — see rewrite-log.md`;
      return "—";
    }
    case "4_implement": {
      return detail.diff ? `<code>${detail.diff}</code>` : "—";
    }
    case "5_verify": {
      const passed = detail.rows_passed ?? 0;
      const total = detail.rows_total ?? 0;
      const failed = detail.rows_failed ?? 0;
      let badge = "";
      if (failed > 0) badge = `<span class="err">${failed} failed</span>`;
      else if (passed === total && total > 0) badge = `<span class="ok">all ${total} pass</span>`;
      else badge = `<span class="pri">${passed}/${total} captured</span>`;
      return badge;
    }
    case "6_pr": {
      return detail.pr_url
        ? `<a href="${detail.pr_url}" target="_blank">${detail.pr_url}</a>`
        : "—";
    }
    case "7_deploy": {
      const v = detail.deployed_version;
      const c = detail.merge_commit;
      return v
        ? `<span class="ok">${v}</span> · <code>${c?.slice(0, 7) ?? ""}</code>`
        : "—";
    }
    case "8_handover": {
      return detail.handover_path ? `<code>${detail.handover_path}</code>` : "—";
    }
    default:
      return "";
  }
}

function renderTerminal(t) {
  if (!t) {
    $terminal.hidden = true;
    return;
  }
  $terminal.hidden = false;
  const rows = Object.entries(t.per_step).map(([step, m]) => {
    const avg = m.avg === null ? "—" : fmt(m.avg);
    const med = m.median === null ? "—" : fmt(m.median);
    const max = m.max === null ? "—" : fmt(m.max);
    return `    ${step.padEnd(14)} ${avg.padEnd(8)} / ${med.padEnd(8)} / ${max}`;
  }).join("\n");
  $terminal.innerHTML = `
    <h3>✓ Done — ${t.total_specs} spec(s) delivered in ${fmt(t.total_time_s)}</h3>
    <pre>
  Step breakdown (avg / median / max):
${rows}
    </pre>
  `;
}

function paint(state) {
  lastState = state;
  renderLeft(state);
  renderRight(state);
}

function startSSE() {
  const es = new EventSource("/events");
  es.addEventListener("state", (e) => {
    try { paint(JSON.parse(e.data)); }
    catch (err) { console.error("bad state event", err); }
    $statusBadge.textContent = "live";
    $statusBadge.className = "status connected";
  });
  es.onerror = () => {
    $statusBadge.textContent = "reconnecting…";
    $statusBadge.className = "status error";
  };
  es.onopen = () => {
    $statusBadge.textContent = "live";
    $statusBadge.className = "status connected";
  };
}

async function initialFetch() {
  try {
    const r = await fetch("/state.json");
    paint(await r.json());
    $statusBadge.textContent = "live";
    $statusBadge.className = "status connected";
  } catch (e) {
    $statusBadge.textContent = "offline";
    $statusBadge.className = "status error";
  }
}

initialFetch().then(startSSE);
