---
spec: 0048
title: Always-on cost verification against provider invoices + pricing-version snapshot
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.46.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/49"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0048 — Always-on cost verification + pricing-version snapshot

## Context

Spec 0039 ([0039-cost-pipeline-integrity.md](./0039-cost-pipeline-integrity.md))
made local cost accounting *honest*, but there is no independent
check that local numbers match what the providers actually charge.
This spec closes that gap with an always-on verification system —
scheduled reconciliation against provider billing APIs, persisted
results per-day, surfaced on the run-detail UI as a verification
chip. Designed for graceful degradation: each provider's admin key
is optional, the system reports honestly about what it can and
cannot verify.

Two items from the 2026-05-17 audit
([`handoffs/2026-05-17-gaps-and-next-three-specs.md`](../handoffs/2026-05-17-gaps-and-next-three-specs.md)):
**C1** (cost reconciliation) and **F8** (`pricing_version` snapshot)
ship together because they share the same code surface and F8
unblocks "recompute under old rates vs today's rates" questions
that come up during reconciliation.

### Why this matters — real numbers from the partner-vetting day

A probe of the OpenAI Cost API (admin key minted 2026-05-17) shows
that on **2026-05-16** (the partner-vetting day) the dual-search
project was billed:

| Line item                             | Quantity     | USD       |
|---------------------------------------|--------------|-----------|
| gpt-5.5-2026-04-23, input             | 1,687,370    | $8.4369   |
| gpt-5.5-2026-04-23, output            | 158,928      | $4.7678   |
| gpt-5.5-2026-04-23, cached input      | 1,053,184    | $0.5266   |
| gpt-4.1-2025-04-14, input             | 68,640       | $0.1373   |
| gpt-4.1-2025-04-14, output            | 1,712        | $0.0137   |
| gpt-4.1-2025-04-14, cached input      | 0            | $0.0000   |
| web search tool calls                 | 49           | $0.4900   |
| **TOTAL — OpenAI side, 2026-05-16**   |              | **$14.37** |

The partner-vetting run's *local* GPT total is $2.48 (per
[`runs/20260516-035048-partner-vetting-arch-critique/metrics.json`](../runs/20260516-035048-partner-vetting-arch-critique/)).
Other runs that day contribute too, but the delta is in dollars, not
cents — exactly the class of drift this system must surface.

### C1 — Cost reconciliation against provider invoices

**Provider APIs** (both verified working against real keys, where
available):

- **OpenAI** — `GET https://api.openai.com/v1/organization/costs`
  with `Authorization: Bearer sk-admin-...`. Daily buckets only.
  Returns USD as high-precision decimal strings. Filterable by
  `project_ids[]`. Pagination via `has_more` + `next_page`. Verified
  end-to-end against the dual-search project. Real shape captured
  for tests.
- **Anthropic** — `GET https://api.anthropic.com/v1/organizations/cost_report`
  with `x-api-key: sk-ant-admin-...`. Daily buckets, same general
  shape. **Not currently verifiable**: the Anthropic Console has
  retired the `Settings → Admin Keys` page from this org's UI; the
  new Service Accounts feature mints only workspace-scoped
  `sk-ant-api03-` keys which return `401 invalid x-api-key` on every
  `/v1/organizations/*` endpoint regardless of workspace role.
  Multiple attempts + a support inquiry are out of scope to resolve
  in this spec; the system ships ready for the Anthropic admin key
  to be added later (env var + restart, no code changes).

**The system this spec ships.** Scheduled (daily, plus on-demand)
reconciliation that pulls per-day provider totals, joins to local
totals across every run on that day, persists a `ReconcileReport`
to `reconcile/<date>.json`, and surfaces a verification chip on each
run-detail page. **Each provider is independently optional** — the
system runs in any combination of (Anthropic absent, OpenAI absent,
both absent), reporting honestly what was checked vs what was not.

### F8 — `pricing_version` snapshot on `metrics.json`

Today [`src/dual_research/agents/pricing.py`](../src/dual_research/agents/pricing.py)
exports a `PRICING` dict with `ModelPricing` entries carrying per-
MTok rates + the per-TTL cache-write split spec 0039 introduced —
but no version constant.
[`src/dual_research/persistence/metrics.py`](../src/dual_research/persistence/metrics.py)'s
`Metrics.to_json()` records no marker indicating which pricing
table was in effect.

When provider rates change, `recompute-costs` against an older run
produces a number defensible *under today's rates* but unrelated to
*what was actually billed*. The reconciliation report needs to flag
"your local total is off because you're recomputing today's rates
against runs from before the rate change" separately from genuine
counting errors. F8 adds the `PRICING_VERSION = "YYYY-MM-DD"`
constant + `pricing_version` field on `metrics.json` to enable
that.

### Why grouped

- **Same code surface** (`pricing.py`, `metrics.py`, `audit/`).
- **F8 unblocks C1** (the reconciliation report needs to distinguish
  rate-table mismatches from accounting drift).
- Both bump MINOR; one release.

Prior context:

- [Spec 0039](./0039-cost-pipeline-integrity.md) — per-TTL cache-write
  pricing, `recompute-costs` CLI, `cost_usd`-includes-search-fees
  invariant.
- [Spec 0036](./0036-web-search-audit-foundation.md) — per-search-
  request fees.
- [Spec 0031](./0031-consumption-followups.md) — initial pricing
  module + per-turn cost tracking.

## Design decisions

| #    | Decision | One-liner |
| ---- | -------- | --------- |
| D1   | **`PRICING_VERSION = "YYYY-MM-DD"` constant in `pricing.py`.** | Human-bumped date stamp when any `ModelPricing` entry changes. Initial value `"2026-05-17"`. |
| D2   | **`Metrics.to_json()` includes `pricing_version: str`.** | New field; `Metrics.load()` tolerates missing-field on older files (defaults to `""`). Round-trip preserves the value. |
| D3   | **`recompute-costs` writes the live `PRICING_VERSION`.** | Recompute repricies under today's table; recording today's version makes the file honest. `RecomputeReport` carries `pricing_version_before` / `_after`; per-run diff line surfaces the transition when it changes. |
| D4   | **Each provider's admin key is independently optional.** | Reads from env (`ANTHROPIC_ADMIN_KEY`, `OPENAI_ADMIN_KEY`). Missing key ⇒ provider skipped, never crash. `verification_status` honestly reflects which providers were checked. |
| D5   | **Project / workspace scoping.** | Both provider APIs return org-wide data; we want only the dual-search project. New env vars: `OPENAI_PROJECT_ID` (e.g. `proj_0W823hZF68Md05LXB3iCXRx7`) and `ANTHROPIC_WORKSPACE_ID` (e.g. `wrkspc_...UD2QSVs`). Without these the fetch is org-wide and reconciliation marks the resulting delta as `scope_mismatch` (warning, not error). |
| D6   | **OpenAI adapter: `audit/reconcile.py::fetch_openai_daily_costs(client, start_date, end_date, api_key, project_id=None) -> dict[str, dict[str, float]]`.** | Returns `{date_iso: {model_id: usd}}`. Parses the `"<model>, <piece>"` compound `line_item` strings into `(model_id, piece)` pairs and rolls up per (date, model). Handles pagination via `has_more` + `next_page`. Endpoint: `/v1/organization/costs`. 401/403/network errors → typed `ReconcileError`. |
| D7   | **Anthropic adapter: `audit/reconcile.py::fetch_anthropic_daily_costs(client, start_date, end_date, api_key, workspace_id=None) -> dict[str, dict[str, float]]`.** | Same contract as D6. Endpoint: `/v1/organizations/cost_report` with `bucket_width=1d`. Tested against canned responses captured from the public docs (we can't hit it for real until an admin key is available). When real responses arrive and diverge from the canned shape, tests fail loudly. |
| D8   | **Daily reconciliation cadence.** | Provider data is daily-aggregated; the natural unit is one day, not one run. Reconciliation walks each UTC date, fetches that day's provider totals (per-provider, per-model), sums local totals across all runs whose `started_at` falls on that date, computes deltas. |
| D9   | **`ReconcileReport` persisted to `reconcile/<date>.json`.** | New directory in `runs/` (mirrors the per-run structure). Each file carries `{date, providers_checked, per_model_deltas, total_local, total_provider, total_delta, verification_status, runs_on_date, pricing_versions_seen, checked_at}`. Latest file wins on re-run (overwrites). |
| D10  | **`verification_status` is a five-state enum.** | `verified` (all-providers reconciled, within tolerance) · `drift` (any provider exceeds tolerance) · `partial` (some providers reconciled, some missing keys / errored) · `unverified` (no provider keys configured) · `awaiting_provider_data` (keys set but provider returned empty for the queried day — typical lag ≤ 5 min, sometimes longer). |
| D11  | **CLI: `dual-research reconcile-costs`.** | Modes: `--day YYYY-MM-DD` (single day) · `--from/--to` (date range) · `--all` (every day with at least one local run) · `--run RUN_ID` (the day containing that run). Output: text by default (per-day table + totals + flagged rows), `--format json` for machine consumption. `--out PATH` writes to file; default stdout. Exit 0 = within tolerance; 1 = any flagged row. |
| D12  | **Scheduled reconciliation.** | Local: `dual-research reconcile-costs --since-yesterday` is the recommended cron entry (the project's existing skill/launch ecosystem documents this — no in-process scheduler shipped). Hosted: a Fly scheduled machine runs the same command daily at 02:00 UTC (after provider data has settled). On failure (network, transient 5xx) the scheduled job logs + retries on the next tick — never fails the run pipeline. |
| D13  | **Run-detail UI verification chip.** | New chip in the run-detail header that reads the run's date's `reconcile/<date>.json`. Five visual states: `✓ verified $9.86` · `⚠ Δ $0.34 (billed $11.20)` · `local $9.86 · partial (✓ OpenAI · ⚠ Anthropic missing)` · `local $9.86 · unverified` · `local $9.86 · awaiting provider data`. Hover tooltip explains exactly which provider contributed what. |
| D14  | **Consumption tab: per-row "provider-billed" annotation.** | When a `reconcile/<date>.json` exists for the run's date, each Consumption-tab row card gets an additional bottom-line "Provider-billed: $X.XX · Δ $Y.YY" when we can attribute provider cost to that (model, piece). Hidden when no reconciliation exists or when the provider doesn't break down at the level we can join on. |
| D15  | **Supabase: `reconcile_results` table.** | Hosted mode persists the same `ReconcileReport` to Supabase (keyed by `org_id` + `date`). Server endpoint `GET /api/reconcile/<date>` reads from local file in dev mode, from Supabase in hosted mode. Frontend always goes through this endpoint — no direct file reads. |
| D16  | **Reads, never writes back to `metrics.json`.** | Reconciliation surfaces deltas; the system doesn't auto-edit local totals. If a real correction is needed, the user runs `recompute-costs` themselves. Auto-fix is out of scope (and conceptually wrong — provider totals are at daily granularity but `metrics.json` is per-call). |

## Proposed change

### 1. `PRICING_VERSION` constant — D1

[`src/dual_research/agents/pricing.py`](../src/dual_research/agents/pricing.py)
near the top:

```python
# Spec 0048: human-bumped marker for "which pricing table is in
# effect." Update this date whenever any ``ModelPricing`` entry
# changes; ``Metrics.to_json()`` records it so future reconcile /
# recompute can detect "your local recompute is using a different
# table than the provider was charging under."
PRICING_VERSION = "2026-05-17"
```

### 2. `pricing_version` on the metrics payload — D2

```python
# src/dual_research/persistence/metrics.py
from dual_research.agents.pricing import PRICING_VERSION

@dataclass
class Metrics:
    ...
    pricing_version: str = ""

    def to_json(self) -> dict:
        return {
            ...existing fields...,
            "pricing_version": self.pricing_version or PRICING_VERSION,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Metrics":
        return cls(
            ...existing fields...,
            pricing_version=data.get("pricing_version", ""),
        )
```

### 3. `recompute-costs` records the new version — D3

[`src/dual_research/audit/recompute.py`](../src/dual_research/audit/recompute.py):

```python
@dataclass
class RecomputeReport:
    ...existing fields...
    pricing_version_before: str
    pricing_version_after: str

def recompute_run(session_dir: Path, *, write: bool = True) -> RecomputeReport:
    ...
    before = m.pricing_version or ""
    m.pricing_version = PRICING_VERSION
    if write:
        write_metrics_json(m, ...)
    return RecomputeReport(..., pricing_version_before=before, pricing_version_after=PRICING_VERSION)
```

Per-run diff line gains a transition row when applicable:

```
20260516-035048-…: $9.8551 → $9.8551 (Δ $0.0000)
  ↳ pricing table: (unknown) → 2026-05-17
```

### 4. New module `audit/reconcile.py` — D4/D5/D6/D7/D8

```python
# src/dual_research/audit/reconcile.py
from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import httpx


class ReconcileError(RuntimeError):
    pass


VerificationStatus = Literal[
    "verified", "drift", "partial", "unverified", "awaiting_provider_data"
]


@dataclass
class ProviderDelta:
    provider: str       # "anthropic" | "openai"
    model_id: str       # canonical, matches PRICING table
    local_usd: float
    provider_usd: float
    delta_usd: float    # local - provider; positive ⇒ we over-reported
    delta_pct: float    # |delta| / provider * 100 (0 when provider == 0)
    flagged: bool       # delta_pct > tolerance


@dataclass
class ReconcileReport:
    date: str                                    # ISO YYYY-MM-DD (UTC)
    checked_at: str                              # ISO 8601 UTC
    providers_checked: list[str]                 # ["openai"] or ["openai", "anthropic"] or []
    providers_skipped: dict[str, str]            # {"anthropic": "ANTHROPIC_ADMIN_KEY not set"}
    runs_on_date: list[str]                      # run IDs whose started_at falls on this date
    pricing_versions_seen: list[str]             # collected from each run's metrics.json
    per_model_deltas: list[ProviderDelta] = field(default_factory=list)
    total_local_usd: float = 0.0
    total_provider_usd: float = 0.0
    total_delta_usd: float = 0.0
    tolerance_pct: float = 1.0
    verification_status: VerificationStatus = "unverified"

    @property
    def within_tolerance(self) -> bool:
        return self.verification_status in ("verified",)


# ─── OpenAI ─────────────────────────────────────────────────────────────

OPENAI_LINE_ITEM_RE = re.compile(r"^([\w.\-]+),\s+(.+)$")  # "gpt-5.5-2026-04-23, input"

def _parse_openai_line_item(line_item: str) -> tuple[str, str] | tuple[None, None]:
    """Parse 'gpt-5.5-2026-04-23, input' → ('gpt-5.5-2026-04-23', 'input').
    Returns (None, None) for non-model line items like 'web search tool calls'."""
    m = OPENAI_LINE_ITEM_RE.match(line_item)
    if not m:
        return None, None
    return m.group(1), m.group(2).strip()


def fetch_openai_daily_costs(
    client: httpx.Client, *,
    start_date: dt.date, end_date: dt.date,
    api_key: str, project_id: str | None = None,
) -> dict[str, dict[str, float]]:
    """Returns {date_iso: {model_id: usd}}.

    Roll-up rule: for each (date, model), sum usd across all line-item
    pieces (input + output + cached_input). Web-search tool calls are
    rolled into a synthetic 'openai-web-search' model id (so the
    `local_usd` side can compare against our existing `search_cost`
    accumulator without losing detail).
    """
    out: dict[str, dict[str, float]] = {}
    start_ts = int(dt.datetime.combine(start_date, dt.time(), dt.timezone.utc).timestamp())
    end_ts = int(dt.datetime.combine(end_date, dt.time(), dt.timezone.utc).timestamp())
    params = {
        "start_time": start_ts,
        "end_time": end_ts,
        "bucket_width": "1d",
        "group_by[]": ["line_item"] + (["project_id"] if project_id else []),
        "limit": 30,
    }
    if project_id:
        params["project_ids[]"] = [project_id]
    next_page = None
    while True:
        if next_page:
            params["page"] = next_page
        resp = client.get(
            "https://api.openai.com/v1/organization/costs",
            params=params, headers={"Authorization": f"Bearer {api_key}"}, timeout=30.0,
        )
        if resp.status_code != 200:
            raise ReconcileError(f"openai cost_report {resp.status_code}: {resp.text[:200]}")
        body = resp.json()
        for bucket in body.get("data", []):
            date_iso = bucket["start_time_iso"][:10]  # 'YYYY-MM-DD'
            day = out.setdefault(date_iso, {})
            for r in bucket.get("results", []):
                amount = float(r["amount"]["value"])
                line_item = r.get("line_item", "")
                model, piece = _parse_openai_line_item(line_item)
                if model is None:
                    model = "openai-web-search" if "web search" in line_item else "openai-other"
                day[model] = day.get(model, 0.0) + amount
        if not body.get("has_more"):
            break
        next_page = body.get("next_page")
        if not next_page:
            break
    return out


# ─── Anthropic ───────────────────────────────────────────────────────────

def fetch_anthropic_daily_costs(
    client: httpx.Client, *,
    start_date: dt.date, end_date: dt.date,
    api_key: str, workspace_id: str | None = None,
) -> dict[str, dict[str, float]]:
    """Returns {date_iso: {model_id: usd}}. Anthropic shape mirrored from
    docs; canonical response captured in tests/audit/fixtures/.

    Hits /v1/organizations/cost_report with bucket_width=1d.
    """
    ...  # implementation mirrors OpenAI version, adjusted for Anthropic params


# ─── Local totals ───────────────────────────────────────────────────────

def gather_local_totals(
    runs_dir: Path, *, start_date: dt.date, end_date: dt.date,
) -> dict[str, dict[str, tuple[float, list[str], list[str]]]]:
    """Walk runs/ + read metrics.json. Group by (date_started_at, model_id).
    Returns {date_iso: {model_id: (total_usd, [run_ids], [pricing_versions])}}.
    Date is the run's ``started_at`` rolled to UTC date.
    """
    ...


# ─── Compare ────────────────────────────────────────────────────────────

def compare_day(
    *, date: str,
    local: dict[str, tuple[float, list[str], list[str]]],
    anthropic: dict[str, float] | None,
    openai: dict[str, float] | None,
    providers_skipped: dict[str, str],
    tolerance_pct: float,
    checked_at: str,
) -> ReconcileReport:
    """Pure function. Builds the ReconcileReport for one date."""
    ...


# ─── Orchestration ──────────────────────────────────────────────────────

@dataclass
class ProviderConfig:
    anthropic_key: str | None
    openai_key: str | None
    anthropic_workspace_id: str | None
    openai_project_id: str | None

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        return cls(
            anthropic_key=os.environ.get("ANTHROPIC_ADMIN_KEY") or None,
            openai_key=os.environ.get("OPENAI_ADMIN_KEY") or None,
            anthropic_workspace_id=os.environ.get("ANTHROPIC_WORKSPACE_ID") or None,
            openai_project_id=os.environ.get("OPENAI_PROJECT_ID") or None,
        )


def reconcile_day(
    date: dt.date, *,
    client: httpx.Client,
    runs_dir: Path,
    config: ProviderConfig,
    tolerance_pct: float = 1.0,
) -> ReconcileReport:
    """Reconcile a single UTC date. Each provider is independently
    optional — missing key ⇒ provider skipped + status reflects."""
    ...


def reconcile_range(
    start_date: dt.date, end_date: dt.date, *,
    client: httpx.Client, runs_dir: Path, config: ProviderConfig,
    tolerance_pct: float = 1.0,
) -> list[ReconcileReport]: ...


# ─── Persistence ────────────────────────────────────────────────────────

def write_reconcile_json(report: ReconcileReport, runs_dir: Path) -> Path:
    """Writes runs/../reconcile/<date>.json. Atomic write."""
    ...


def read_reconcile_json(runs_dir: Path, date: str) -> ReconcileReport | None:
    """Returns the latest ReconcileReport for date, or None if not yet run."""
    ...


# ─── Report formatters ──────────────────────────────────────────────────

def format_text(reports: list[ReconcileReport]) -> str: ...
def format_json(reports: list[ReconcileReport]) -> str: ...
```

### 5. New CLI subcommand `reconcile-costs` — D11

Same registration shape as `recompute-costs`:

```python
# src/dual_research/cli.py
if raw and raw[0] == "reconcile-costs":
    return _run_reconcile(raw[1:])

def _run_reconcile(argv: list[str]) -> int:
    sub = argparse.ArgumentParser(
        prog="dual-research reconcile-costs",
        description="Verify local cost accounting against provider invoices.",
    )
    mode = sub.add_mutually_exclusive_group(required=True)
    mode.add_argument("--day", metavar="YYYY-MM-DD", help="Reconcile a single UTC date.")
    mode.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD",
                      help="Start date (inclusive); requires --to.")
    mode.add_argument("--all", action="store_true",
                      help="Every UTC date with at least one local run.")
    mode.add_argument("--run", metavar="RUN_ID", help="The UTC date containing RUN_ID's started_at.")
    mode.add_argument("--since-yesterday", action="store_true",
                      help="Yesterday + today (the recommended cron entry).")
    sub.add_argument("--to", dest="to_date", metavar="YYYY-MM-DD",
                     help="End date (inclusive); used with --from.")
    sub.add_argument("--runs-dir", metavar="PATH", help="Override runs/ directory.")
    sub.add_argument("--format", choices=("text", "json"), default="text")
    sub.add_argument("--out", metavar="PATH", help="Write report to PATH (default stdout).")
    sub.add_argument("--tolerance", type=float, default=1.0,
                     help="Per-day delta %% above which to flag the row.")
    sub.add_argument("--write-snapshots", action="store_true", default=True,
                     help="Persist ReconcileReport to reconcile/<date>.json (default true).")
    sub.add_argument("--no-write-snapshots", dest="write_snapshots", action="store_false")
    args = sub.parse_args(argv)

    config = ProviderConfig.from_env()
    client = httpx.Client(timeout=30.0)
    try:
        dates = _resolve_dates(args, runs_dir=...)
        reports = []
        for date in dates:
            r = reconcile_day(date, client=client, runs_dir=..., config=config,
                              tolerance_pct=args.tolerance)
            if args.write_snapshots:
                write_reconcile_json(r, runs_dir=...)
            reports.append(r)
    finally:
        client.close()

    body = format_json(reports) if args.format == "json" else format_text(reports)
    if args.out:
        Path(args.out).write_text(body + "\n", encoding="utf-8")
    else:
        print(body)
    return 0 if all(r.within_tolerance for r in reports) else 1
```

Exit code lets CI / cron surface drift without parsing output.

### 6. Scheduled reconciliation — D12

**Local:** the recommended cron pattern is documented in the spec
PR description (no new in-process scheduler):

```cron
0 2 * * * cd /Users/alexlisitzky/dual-research && uv run dual-research reconcile-costs --since-yesterday >> ~/.dual-research-reconcile.log 2>&1
```

**Hosted (Fly):** new scheduled machine declared in `fly.toml`:

```toml
[[processes]]
  name = "reconcile-daily"
  cmd = "uv run dual-research reconcile-costs --since-yesterday"

[[schedules]]
  process = "reconcile-daily"
  cron = "0 2 * * *"
```

Failure modes (network 5xx, rate limit, transient auth issues) log
to stderr + exit non-zero; the *next* scheduled tick retries. Never
fails the orchestrator pipeline — reconciliation is observation, not
mutation.

### 7. Server endpoint + Supabase storage — D15

```python
# src/dual_research/ui/server.py

@app.get("/api/reconcile/{date}")
async def get_reconcile(date: str) -> ReconcileReport | None:
    """Returns the latest ReconcileReport for date, or 404 if not run yet."""
    if hosted_mode:
        return await reconcile_from_supabase(date)
    return read_reconcile_json(runs_dir, date)
```

New Supabase table `reconcile_results`:

```sql
create table public.reconcile_results (
    org_id text not null,
    date date not null,
    payload jsonb not null,
    checked_at timestamptz not null default now(),
    primary key (org_id, date)
);
```

`write_reconcile_json` in hosted mode upserts to Supabase in
addition to the local file (mirrors the existing run-push pattern).

### 8. Run-detail UI verification chip — D13

`run-detail.jsx` header: new `<ReconcileChip run={run} />` that
fetches `/api/reconcile/<run.startedAt.slice(0,10)>` once on mount.
Renders one of five states (D10):

| Status                      | Chip                                                    | Tooltip                                                                |
|-----------------------------|---------------------------------------------------------|------------------------------------------------------------------------|
| `verified`                  | `✓ verified $9.86`                                       | "All providers reconciled within 1.0% tolerance."                      |
| `drift`                     | `⚠ Δ $0.34 (billed $10.20)`                              | "Provider total exceeds local by $0.34 (3.4%); threshold 1.0%."        |
| `partial`                   | `local $9.86 · ✓ OpenAI · ⚠ Anthropic missing`           | "Reconciled against OpenAI ($X.XX); Anthropic skipped (no admin key)." |
| `unverified`                | `local $9.86 · unverified`                              | "No provider admin keys configured; local-only accounting."           |
| `awaiting_provider_data`    | `local $9.86 · awaiting provider data`                  | "Reconciliation ran but provider data not yet available; retry in ~5–60 min." |

Visual style consistent with the existing `LedgerDriftChip` (spec
0043 D9) and `PaneButton` palette (spec 0046 D9). New shared
component lives near the other header chips in `run-detail.jsx`.

### 9. Consumption tab "provider-billed" annotation — D14

When a `reconcile/<date>.json` exists for the run's date AND it has
non-null per-model deltas for this row's `(model_id, piece)`, the
`ConsumptionRow`'s expanded body gains a small bottom-line:

```
Provider-billed: $11.20 · Δ $1.34 (12.0%)
```

Hidden when no reconciliation exists, or when the provider doesn't
break down at the level we can join on (e.g., the `web search tool
calls` line item is a separate row, not joinable to a per-model card).

### 10. Versioning + release notes

- `pyproject.toml`, `src/dual_research/__init__.py`: 0.45.0 → 0.46.0.
- `CHANGELOG.md`: `[Unreleased]` → `## [0.46.0]`. Headings: `### Added`
  (reconcile system, verification chip, `pricing_version`), `### Changed`
  (metrics payload, recompute report).
- `VERSION_NOTES` at the top of `how-it-works.jsx`:
  > **0.46.0 — Always-on cost verification.** The system now
  > reconciles local cost accounting against provider invoices
  > daily. Each run-detail page shows a verification chip (`✓
  > verified` / `⚠ drift` / `partial` / `unverified` / `awaiting
  > provider data`) telling you exactly what's been checked. Needs
  > admin API keys for the providers you want verified (env vars
  > `OPENAI_ADMIN_KEY` + optionally `ANTHROPIC_ADMIN_KEY`); without
  > them, accounting still works — just unverified. `metrics.json`
  > now records a `pricing_version` so the recompute / reconcile
  > flow can tell when an old run was priced under a now-superseded
  > rate table. Scheduled daily via Fly cron in hosted mode; local
  > runs document the recommended cron entry.

### 11. Files touched

Backend (new):
- [`src/dual_research/audit/reconcile.py`](../src/dual_research/audit/reconcile.py) — **new**, ~450 LOC: dataclasses, fetchers, gather/compare, persistence, formatters, orchestration.
- `tests/audit/test_reconcile_openai.py` — **new**, ~150 LOC. Fixture: canonical OpenAI response captured from the 2026-05-16 probe.
- `tests/audit/test_reconcile_anthropic.py` — **new**, ~120 LOC. Fixture: response shape per Anthropic docs.
- `tests/audit/test_reconcile_compare.py` — **new**, ~100 LOC. Pure comparison logic, all five states.
- `tests/audit/test_reconcile_persistence.py` — **new**, ~60 LOC. Round-trip `reconcile/<date>.json`.
- `tests/audit/test_reconcile_cli.py` — **new**, ~80 LOC. `_run_reconcile` end-to-end with `MockTransport`.
- `tests/agents/test_pricing_version.py` — **new**, ~30 LOC. Includes the `test_version_tracks_table` snapshot regression so a `PRICING` change can't ship without bumping the version.
- `tests/persistence/test_metrics_pricing_version.py` — **new**, ~40 LOC.
- `tests/audit/test_recompute_pricing_version.py` — **new**, ~30 LOC.
- `tests/audit/fixtures/openai_cost_report_2026_05_16.json` — **new**. Captured response.
- `tests/audit/fixtures/anthropic_cost_report_sample.json` — **new**. Mirror of docs example.

Backend (modified):
- [`src/dual_research/agents/pricing.py`](../src/dual_research/agents/pricing.py) — `PRICING_VERSION`.
- [`src/dual_research/persistence/metrics.py`](../src/dual_research/persistence/metrics.py) — `pricing_version` field + wiring.
- [`src/dual_research/audit/recompute.py`](../src/dual_research/audit/recompute.py) — version tracking on `RecomputeReport`; write live constant.
- [`src/dual_research/cli.py`](../src/dual_research/cli.py) — `reconcile-costs` subcommand + dispatch.
- [`src/dual_research/ui/server.py`](../src/dual_research/ui/server.py) — `GET /api/reconcile/<date>` endpoint.
- `fly.toml` — scheduled `reconcile-daily` process.
- Supabase migrations dir — `reconcile_results` table.

Frontend (modified):
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — `ReconcileChip` component in the run-detail header; per-row "provider-billed" annotation on `ConsumptionRow`.
- [`src/dual_research/ui/static/how-it-works.jsx`](../src/dual_research/ui/static/how-it-works.jsx) — `VERSION_NOTES`.

Pyproject + version:
- `pyproject.toml`, `src/dual_research/__init__.py`, `CHANGELOG.md`.

## Out of scope

- **Auto-correcting `metrics.json` on detected drift.** D16 — manual
  invocation only.
- **Per-call reconciliation.** Neither provider exposes per-call
  billing; daily aggregate is the finest honest grain.
- **Anthropic admin-key discovery / minting flow.** Currently
  unavailable in the user's Console UI (the new Service Accounts
  feature only mints workspace-scoped `sk-ant-api03-` keys which
  return 401 on `/v1/organizations/*`). Tracked as a separate
  out-of-band support inquiry; once the key is available, set
  `ANTHROPIC_ADMIN_KEY` env var + restart — the system lights up
  the Anthropic half automatically.
- **A `--assume-1h-cache-writes` backfill flag on `recompute-costs`.**
  Audit option 2. If reconciliation reveals systematic 1h-vs-5m
  cache-write drift on historical runs, future spec adds the flag.
- **Cron / scheduled reconciliation in pure Python (in-process).**
  We delegate to system cron / Fly schedules. The CLI is the
  contract.
- **`reconcile-costs` writing back to `metrics.json`.** Read-only.
- **A "drift over time" trend chart.** v1 surfaces today's status;
  trends are a future spec.
- **Email / Slack alerting on drift.** v1 logs to stderr + exit
  code; alerting wrapper is downstream of that.
- **Hosted-mode reconciliation across multiple orgs.** v1 assumes
  one org. Multi-tenancy is a future spec.
- **Citation `[V]`/`[U]` rendering, server-side cited-URL refetch
  (spec 0049 territory).**

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec adds ~30 new tests
      across 9 new test files.
- [ ] `PRICING_VERSION` exists + parses as ISO date; snapshot test
      forces a version bump when `PRICING` changes.
- [ ] `Metrics.to_json` carries `pricing_version`; round-trip
      preserves it; missing-field loads degrade to `""`.
- [ ] `recompute_run` writes the current `PRICING_VERSION`;
      `RecomputeReport` carries before/after.
- [ ] `_parse_openai_line_item` parses model/piece correctly for
      every shape seen in the captured 2026-05-16 fixture (input,
      output, cached input, web search, gpt-4.1 + gpt-5.5).
- [ ] `fetch_openai_daily_costs` parses single-page + paginated
      responses correctly against the canonical fixture; project
      filter passes through.
- [ ] `fetch_anthropic_daily_costs` parses canonical docs-shape
      response (will be revalidated against real responses when an
      admin key is available).
- [ ] `gather_local_totals` walks a synthetic runs dir; groups
      correctly by UTC date; collects `pricing_versions_seen`.
- [ ] `compare_day` produces correct deltas + correct
      `verification_status` for all five states.
- [ ] `reconcile_day` end-to-end with `MockTransport`-backed client
      + missing keys → `partial` / `unverified` as appropriate.
- [ ] `write_reconcile_json` / `read_reconcile_json` round-trip
      preserves every field.
- [ ] CLI `_run_reconcile` end-to-end with mocked clients; exit
      code 0 vs 1 for tolerance vs drift.
- [ ] Server endpoint `GET /api/reconcile/<date>` serves from local
      file in dev mode; returns 404 when not yet run.
- [ ] **Manual / production:** `uv run dual-research reconcile-costs
      --day 2026-05-16` against real OpenAI key produces a report
      including the partner-vetting day's $14.37 OpenAI total and
      its delta vs local. Document the actual delta in the PR.
- [ ] **Manual / production:** open
      [`runs/20260516-035048-partner-vetting-arch-critique/`](../runs/20260516-035048-partner-vetting-arch-critique/)
      in the UI — verification chip shows `partial · ✓ OpenAI · ⚠
      Anthropic missing` with correct numbers.
- [ ] **Manual:** unset `OPENAI_ADMIN_KEY` and reload the same run
      — chip flips to `unverified` cleanly with no crash.
- [ ] CHANGELOG entry under `## [0.46.0]`.
- [ ] VERSION_NOTES at the top of `how-it-works.jsx`.
- [ ] Spec front-matter `status: merged` + `pr:` populated.

## Risks

- **OpenAI's `line_item` is a compound string with unstable shape.**
  Today it's `"<model_id>, <piece>"`; if OpenAI changes the
  separator or wording, our parser drops to a fallback bucket.
  Mitigation: `_parse_openai_line_item` returns `(None, None)` on
  unparseable strings; those go into `openai-other` so cost is
  still counted in the rollup. Captured fixture locks the shape we
  saw on 2026-05-17 — if it changes, tests fail noisily.
- **OpenAI returns org-wide data unless filtered.** Without
  `OPENAI_PROJECT_ID`, the delta against local will look huge
  because we're comparing dual-search-only local totals against
  multi-project provider totals. Mitigation: D5 surfaces this as
  `scope_mismatch` in the report; documentation strongly
  recommends setting the project filter.
- **Anthropic adapter is built blind.** We can't hit
  `/v1/organizations/cost_report` without an admin key; the
  adapter is implemented against the public docs' response shape +
  tests use canned responses. When the key eventually arrives, the
  first real call may surface shape discrepancies. Mitigation:
  treat the first real-key validation as a stage gate before
  flipping the Anthropic side from `unavailable` to `verified` in
  the UI; the structure of `compare_day` already isolates this.
- **`PRICING_VERSION` is human-bumped; easy to forget.** The
  `test_version_tracks_table` snapshot regression test fails if
  `PRICING` changes without a version bump.
- **Provider data lag.** OpenAI says ≤5 min typically, occasionally
  longer; Anthropic similar. The `awaiting_provider_data` state
  handles this — if reconcile runs before data is ready, the next
  cron tick (24h later) retries. The CLI's `--since-yesterday`
  pattern ensures yesterday's runs always have ≥2h of provider lag
  margin by the time we check.
- **Admin keys are higher-privilege than regular keys.** They can
  read billing data org-wide. Mitigation: env-var only (never
  persisted to disk in code paths the spec controls);
  `~/.zshrc` per current project convention; Fly secrets for
  hosted mode.
- **Supabase schema migration coordination.** Hosted-mode requires
  the `reconcile_results` table to exist before the cron fires.
  Mitigation: migration ships in the same PR; deploy order is
  documented; the daily cron starts running on the next 02:00 UTC
  after deploy.

## Open questions

- **`Metrics.to_json()` overwrite vs preserve `pricing_version` on
  resume.** Default: overwrite at save time. Trade-off documented;
  if resume-across-rate-changes becomes a real problem, future spec
  splits into `pricing_version_started` + `pricing_version_last_save`.
- **Persist `reconcile/<date>.json` write-back to Supabase when
  cron runs locally?** v1: cron is server-side in hosted mode and
  local-only in dev. If team usage grows, future spec adds a
  push-snapshot path.
- **Default tolerance threshold of 1.0%.** Picked as a "feels
  meaningful" round number. Real reconciliation data will tell us
  whether 1% is too tight (constant noise) or too loose (real drift
  hides). Exposed as a flag so it's revisitable without code.
- **`ReconcileChip` placement: run-detail header vs near the cost
  total?** v1 puts it in the header alongside the existing status
  pill. If it competes with other header chips for space, a future
  spec might move it next to the cost figure.
- **Should the spec ship the support-email template for the
  Anthropic admin key issue?** Decided no — it's a project artifact
  noted in the PR description, not part of the codebase.
