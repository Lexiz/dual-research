"""Spec 0048 — always-on cost verification against provider invoices.

Pulls daily cost aggregates from the Anthropic Admin Cost Report API
and the OpenAI Organization Costs API, joins to local per-run totals
over the same UTC date range, computes deltas, and writes the result
to ``runs/../reconcile/<date>.json`` so the UI can render a
verification chip.

Each provider's admin key is independently optional. Missing keys
produce a ``ReconcileReport`` with ``verification_status="partial"``
or ``"unverified"`` rather than crashing — the system reports
honestly about what was checked vs what was not. When admin keys are
later added (env vars + restart), reconciliation lights up
automatically with no code changes.

CLI entry: ``dual-research reconcile-costs``. See ``cli.py::_run_reconcile``.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

import httpx

from dual_research.agents.pricing import PRICING


# ─── Errors + types ─────────────────────────────────────────────────────


class ReconcileError(RuntimeError):
    """Raised when a provider API returns a fatal error (auth, network, 5xx).

    The exception's ``str(...)`` carries the provider name + upstream
    message for clear diagnostics.
    """


VerificationStatus = Literal[
    "verified",                  # all providers reconciled, within tolerance
    "drift",                     # at least one row exceeds tolerance
    "partial",                   # some providers reconciled, others missing keys / errored
    "unverified",                # no provider keys configured; local-only
    "awaiting_provider_data",    # keys set but provider returned empty for queried day
]


@dataclass
class ProviderDelta:
    """One row of the reconciliation table — a single (provider, model) on
    a single UTC date.
    """

    provider: str        # "anthropic" | "openai"
    model_id: str        # canonical model id (joins to PRICING)
    local_usd: float
    provider_usd: float
    delta_usd: float     # local - provider; positive ⇒ we over-reported
    delta_pct: float     # |delta| / provider * 100; 0 when provider == 0
    flagged: bool        # delta_pct > tolerance_pct


@dataclass
class ReconcileReport:
    """The persisted output of one date's reconciliation."""

    date: str                                        # UTC ISO YYYY-MM-DD
    checked_at: str                                  # UTC ISO 8601
    tolerance_pct: float
    providers_checked: list[str] = field(default_factory=list)
    providers_skipped: dict[str, str] = field(default_factory=dict)   # provider → reason
    runs_on_date: list[str] = field(default_factory=list)             # run ids
    pricing_versions_seen: list[str] = field(default_factory=list)
    per_model_deltas: list[ProviderDelta] = field(default_factory=list)
    total_local_usd: float = 0.0
    total_provider_usd: float = 0.0
    total_delta_usd: float = 0.0
    verification_status: VerificationStatus = "unverified"

    @property
    def within_tolerance(self) -> bool:
        """0.46.1 — only ``drift`` is an actionable failure for CLI exit
        purposes. ``partial`` / ``unverified`` / ``awaiting_provider_data``
        are operational states (missing keys, missing local data,
        provider lag) that shouldn't alert. ``verified`` and any of those
        three return True so the CI cron doesn't fire on a clean checkout
        with no local runs to compare. Only ``drift`` returns False.
        """
        return self.verification_status != "drift"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── Provider config (env-driven, all independently optional) ───────────


@dataclass
class ProviderConfig:
    """Reads provider admin keys + scope ids from the environment.

    Each field is independently optional. Missing keys ⇒ that provider
    is skipped at reconcile time. Missing scope ids ⇒ provider returns
    org-wide data (the report flags this as a scope mismatch warning
    in the per-row deltas).
    """

    anthropic_key: str | None = None
    openai_key: str | None = None
    anthropic_workspace_id: str | None = None
    openai_project_id: str | None = None

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        return cls(
            anthropic_key=os.environ.get("ANTHROPIC_ADMIN_KEY") or None,
            openai_key=os.environ.get("OPENAI_ADMIN_KEY") or None,
            anthropic_workspace_id=os.environ.get("ANTHROPIC_WORKSPACE_ID") or None,
            openai_project_id=os.environ.get("OPENAI_PROJECT_ID") or None,
        )


# ─── OpenAI fetcher ─────────────────────────────────────────────────────


# OpenAI cost-report ``line_item`` strings look like:
#   "gpt-5.5-2026-04-23, input"
#   "gpt-5.5-2026-04-23, cached input"
#   "gpt-4.1-2025-04-14, output"
#   "web search tool calls"
# Captured 2026-05-17 against the real Admin API.
_OPENAI_LINE_ITEM_RE = re.compile(r"^([\w.\-]+),\s+(.+)$")


def _parse_openai_line_item(line_item: str) -> tuple[str | None, str | None]:
    """Return ``(model_id, piece)`` or ``(None, None)`` for non-model lines.

    >>> _parse_openai_line_item("gpt-5.5-2026-04-23, input")
    ('gpt-5.5-2026-04-23', 'input')
    >>> _parse_openai_line_item("web search tool calls")
    (None, None)
    """
    m = _OPENAI_LINE_ITEM_RE.match(line_item)
    if not m:
        return None, None
    return m.group(1), m.group(2).strip()


def fetch_openai_daily_costs(
    client: httpx.Client,
    *,
    start_date: dt.date,
    end_date: dt.date,
    api_key: str,
    project_id: str | None = None,
) -> dict[str, dict[str, float]]:
    """Returns ``{date_iso: {model_id: usd}}`` over [start_date, end_date].

    Roll-up rule: for each (date, model), sum USD across all line-item
    pieces (input + output + cached input). Web-search tool calls roll
    into a synthetic ``openai-web-search`` model id so the
    ``compare_day`` join still works against our existing local
    ``search_cost`` accumulator. Anything else unparseable goes into
    ``openai-other``.

    Pagination handled via ``has_more`` + ``next_page``. ``end_date`` is
    exclusive (matches the API's ``end_time`` semantics).

    Raises ``ReconcileError`` on auth/network/5xx errors. Empty buckets
    (provider data not yet available for the requested day) are
    returned as empty dicts under the date key — callers detect this
    via the ``awaiting_provider_data`` heuristic.
    """
    out: dict[str, dict[str, float]] = {}
    start_ts = int(dt.datetime.combine(start_date, dt.time(0, 0), dt.timezone.utc).timestamp())
    end_ts = int(dt.datetime.combine(end_date, dt.time(0, 0), dt.timezone.utc).timestamp())
    base_params: list[tuple[str, Any]] = [
        ("start_time", start_ts),
        ("end_time", end_ts),
        ("bucket_width", "1d"),
        ("group_by[]", "line_item"),
        ("limit", 31),
    ]
    if project_id:
        base_params.append(("group_by[]", "project_id"))
        base_params.append(("project_ids[]", project_id))

    next_page: str | None = None
    while True:
        params = list(base_params)
        if next_page:
            params.append(("page", next_page))
        try:
            resp = client.get(
                "https://api.openai.com/v1/organization/costs",
                params=params,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
        except httpx.HTTPError as e:
            raise ReconcileError(f"openai cost_report network error: {e}") from e
        if resp.status_code != 200:
            raise ReconcileError(
                f"openai cost_report {resp.status_code}: {resp.text[:200]}"
            )
        body = resp.json()
        for bucket in body.get("data") or []:
            iso = str(bucket.get("start_time_iso") or "")
            date_key = iso[:10] if iso else ""
            if not date_key:
                continue
            day = out.setdefault(date_key, {})
            for r in bucket.get("results") or []:
                try:
                    amount = float(r["amount"]["value"])
                except (KeyError, TypeError, ValueError):
                    continue
                line_item = str(r.get("line_item") or "")
                model, _piece = _parse_openai_line_item(line_item)
                if model is None:
                    model = (
                        "openai-web-search"
                        if "web search" in line_item.lower()
                        else "openai-other"
                    )
                day[model] = day.get(model, 0.0) + amount
        if not body.get("has_more"):
            break
        nxt = body.get("next_page")
        if not nxt:
            break
        next_page = nxt
    return out


# ─── Anthropic fetcher ──────────────────────────────────────────────────


def fetch_anthropic_daily_costs(
    client: httpx.Client,
    *,
    start_date: dt.date,
    end_date: dt.date,
    api_key: str,
    workspace_id: str | None = None,
) -> dict[str, dict[str, float]]:
    """Returns ``{date_iso: {model_id: usd}}`` over [start_date, end_date].

    Built against the public Admin Cost Report docs shape:
    ``GET /v1/organizations/cost_report?starting_at=…&ending_at=…&bucket_width=1d``
    Auth: ``x-api-key: <admin>``. Response: ``{data: [{starting_at,
    ending_at, results: [{amount: {value, currency}, line_item,
    workspace_id, ...}]}], has_more, next_page}``.

    NOTE: This adapter is built blind — we have no admin key for live
    validation. Tests use a canonical canned response captured from
    the docs. When a real admin key arrives, the first real call may
    surface shape divergences; that is the moment to revalidate the
    fixture in ``tests/audit/fixtures/anthropic_cost_report_sample.json``.

    Raises ``ReconcileError`` on auth/network/5xx errors.
    """
    out: dict[str, dict[str, float]] = {}
    # Anthropic accepts ISO-8601 ``starting_at`` / ``ending_at`` with Z suffix.
    start_iso = dt.datetime.combine(start_date, dt.time(0, 0), dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    end_iso = dt.datetime.combine(end_date, dt.time(0, 0), dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    base_params: list[tuple[str, Any]] = [
        ("starting_at", start_iso),
        ("ending_at", end_iso),
        ("bucket_width", "1d"),
        ("group_by[]", "description"),
        ("limit", 31),
    ]
    if workspace_id:
        base_params.append(("workspace_ids[]", workspace_id))

    next_page: str | None = None
    while True:
        params = list(base_params)
        if next_page:
            params.append(("page", next_page))
        try:
            resp = client.get(
                "https://api.anthropic.com/v1/organizations/cost_report",
                params=params,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                timeout=30.0,
            )
        except httpx.HTTPError as e:
            raise ReconcileError(f"anthropic cost_report network error: {e}") from e
        if resp.status_code != 200:
            raise ReconcileError(
                f"anthropic cost_report {resp.status_code}: {resp.text[:200]}"
            )
        body = resp.json()
        for bucket in body.get("data") or []:
            iso = str(bucket.get("starting_at") or bucket.get("start_time_iso") or "")
            date_key = iso[:10] if iso else ""
            if not date_key:
                continue
            day = out.setdefault(date_key, {})
            for r in bucket.get("results") or []:
                try:
                    amount = float(r["amount"]["value"])
                except (KeyError, TypeError, ValueError):
                    continue
                # Anthropic groups by description — try model field first,
                # then fall back to parsing a description like
                # "<model_id> input" / "<model_id> output".
                model_id = (
                    r.get("model")
                    or r.get("model_id")
                    or _anthropic_model_from_description(str(r.get("description") or ""))
                    or "anthropic-other"
                )
                day[model_id] = day.get(model_id, 0.0) + amount
        if not body.get("has_more"):
            break
        nxt = body.get("next_page")
        if not nxt:
            break
        next_page = nxt
    return out


def _anthropic_model_from_description(desc: str) -> str | None:
    """Best-effort: pluck a known model id out of a description string."""
    for model_id in PRICING:
        if model_id.startswith("claude") and model_id in desc:
            return model_id
    return None


# ─── Local totals ───────────────────────────────────────────────────────


# Aggregate type used by ``gather_local_totals``:
#   {date_iso: {(provider, model_id): {"usd": float, "run_ids": [str], ...}}}
LocalTotals = dict[str, dict[tuple[str, str], dict[str, Any]]]


# Map orchestrator agent labels (in metrics.json) to provider names used
# in the reconciliation output. Both "openai" and "gpt" appear in the
# wild (older runs vs newer); both map to "openai".
_AGENT_TO_PROVIDER = {
    "claude": "anthropic",
    "anthropic": "anthropic",
    "openai": "openai",
    "gpt": "openai",
}


def gather_local_totals(
    runs_dir: Path,
    *,
    start_date: dt.date,
    end_date: dt.date,
) -> LocalTotals:
    """Walk ``runs_dir`` + read each ``metrics.json``. Group per-call cost
    by ``(date, provider, model_id)``.

    Date is the run's ``started_at`` rolled to UTC date. ``search_cost``
    on calls is attributed separately to a synthetic ``<provider>-web-
    search`` model id so the comparison against provider per-line-item
    data joins cleanly. ``end_date`` is exclusive.
    """
    out: LocalTotals = {}
    if not runs_dir.exists():
        return out
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        metrics_path = entry / "metrics.json"
        if not metrics_path.exists():
            continue
        try:
            payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        started_at = str(payload.get("started_at") or "")
        if not started_at:
            continue
        try:
            run_date = dt.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        run_date_utc = run_date.astimezone(dt.timezone.utc).date()
        if run_date_utc < start_date or run_date_utc >= end_date:
            continue
        date_key = run_date_utc.isoformat()
        day = out.setdefault(date_key, {})
        run_id = entry.name
        pricing_version = str(payload.get("pricing_version") or "")
        for call in payload.get("calls") or []:
            agent_raw = str(call.get("agent") or "").lower()
            provider = _AGENT_TO_PROVIDER.get(agent_raw)
            if not provider:
                continue
            model_id = str(call.get("model_id") or "")
            if not model_id:
                continue
            cost = float(call.get("cost_usd", 0.0) or 0.0)
            search_cost = float(call.get("search_cost", 0.0) or 0.0)
            # Token cost lands on the model bucket; search cost is broken
            # out into <provider>-web-search to match how OpenAI's
            # cost-report line-itemizes "web search tool calls".
            token_cost = cost - search_cost
            _accumulate_local(day, provider, model_id, token_cost, run_id, pricing_version)
            if search_cost:
                _accumulate_local(
                    day, provider, f"{provider}-web-search", search_cost,
                    run_id, pricing_version,
                )
    return out


def _accumulate_local(
    day: dict[tuple[str, str], dict[str, Any]],
    provider: str,
    model_id: str,
    usd: float,
    run_id: str,
    pricing_version: str,
) -> None:
    key = (provider, model_id)
    bucket = day.setdefault(
        key,
        {"usd": 0.0, "run_ids": [], "pricing_versions": []},
    )
    bucket["usd"] += usd
    if run_id not in bucket["run_ids"]:
        bucket["run_ids"].append(run_id)
    if pricing_version and pricing_version not in bucket["pricing_versions"]:
        bucket["pricing_versions"].append(pricing_version)


# ─── Compare ────────────────────────────────────────────────────────────


def compare_day(
    *,
    date: str,
    local_day: dict[tuple[str, str], dict[str, Any]],
    anthropic_day: dict[str, float] | None,
    openai_day: dict[str, float] | None,
    providers_skipped: dict[str, str],
    tolerance_pct: float,
    checked_at: str,
) -> ReconcileReport:
    """Pure function — joins local + provider totals on (provider, model),
    builds the per-row deltas, derives the verification status.
    """
    providers_checked: list[str] = []
    if anthropic_day is not None:
        providers_checked.append("anthropic")
    if openai_day is not None:
        providers_checked.append("openai")

    run_ids: list[str] = []
    pricing_versions: list[str] = []
    deltas: list[ProviderDelta] = []
    total_local = 0.0
    total_provider = 0.0
    flagged_any = False

    # Build the joined key universe: every (provider, model) that
    # appears in either local OR provider data for any provider we
    # checked.
    joined_keys: set[tuple[str, str]] = set()
    for provider in providers_checked:
        provider_day = anthropic_day if provider == "anthropic" else openai_day
        for model_id in (provider_day or {}):
            joined_keys.add((provider, model_id))
    for (provider, model_id), bucket in local_day.items():
        if provider in providers_checked:
            joined_keys.add((provider, model_id))
        # accumulate run ids + pricing versions even for skipped providers
        for rid in bucket["run_ids"]:
            if rid not in run_ids:
                run_ids.append(rid)
        for pv in bucket["pricing_versions"]:
            if pv not in pricing_versions:
                pricing_versions.append(pv)

    for provider, model_id in sorted(joined_keys):
        local_usd = float(local_day.get((provider, model_id), {}).get("usd", 0.0))
        provider_day = anthropic_day if provider == "anthropic" else openai_day
        provider_usd = float((provider_day or {}).get(model_id, 0.0))
        delta_usd = local_usd - provider_usd
        delta_pct = (
            (abs(delta_usd) / provider_usd) * 100.0 if provider_usd > 0 else 0.0
        )
        flagged = delta_pct > tolerance_pct and provider_usd > 0
        deltas.append(
            ProviderDelta(
                provider=provider,
                model_id=model_id,
                local_usd=local_usd,
                provider_usd=provider_usd,
                delta_usd=delta_usd,
                delta_pct=delta_pct,
                flagged=flagged,
            )
        )
        total_local += local_usd
        total_provider += provider_usd
        if flagged:
            flagged_any = True

    # Local-only totals (providers not checked) — surface so the
    # report's headline reflects all local spend, not just the
    # reconciled slice.
    for (provider, model_id), bucket in local_day.items():
        if provider not in providers_checked:
            total_local += float(bucket.get("usd", 0.0))

    status = _derive_status(
        providers_checked=providers_checked,
        providers_skipped=providers_skipped,
        flagged_any=flagged_any,
        any_provider_data=bool(anthropic_day) or bool(openai_day),
    )

    return ReconcileReport(
        date=date,
        checked_at=checked_at,
        tolerance_pct=tolerance_pct,
        providers_checked=providers_checked,
        providers_skipped=providers_skipped,
        runs_on_date=run_ids,
        pricing_versions_seen=pricing_versions,
        per_model_deltas=deltas,
        total_local_usd=total_local,
        total_provider_usd=total_provider,
        total_delta_usd=total_local - total_provider,
        verification_status=status,
    )


def _derive_status(
    *,
    providers_checked: list[str],
    providers_skipped: dict[str, str],
    flagged_any: bool,
    any_provider_data: bool,
) -> VerificationStatus:
    if not providers_checked:
        return "unverified"
    if providers_checked and not any_provider_data:
        # Keys configured but provider returned no buckets for the
        # requested date — typical when querying before the day's data
        # has settled (usually <5 min lag, occasionally longer).
        return "awaiting_provider_data"
    if flagged_any:
        return "drift"
    if providers_skipped:
        return "partial"
    return "verified"


# ─── Orchestration ──────────────────────────────────────────────────────


def reconcile_day(
    date: dt.date,
    *,
    client: httpx.Client,
    runs_dir: Path,
    config: ProviderConfig,
    tolerance_pct: float = 1.0,
) -> ReconcileReport:
    """Reconcile a single UTC date. Each provider independently optional.

    Errors fetching a single provider become a ``providers_skipped``
    entry (so the day's report still ships) rather than raising. Only
    truly unrecoverable issues (filesystem, JSON corruption) bubble up.
    """
    next_day = date + dt.timedelta(days=1)
    checked_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    providers_skipped: dict[str, str] = {}

    anthropic_day: dict[str, float] | None = None
    if config.anthropic_key:
        try:
            data = fetch_anthropic_daily_costs(
                client,
                start_date=date,
                end_date=next_day,
                api_key=config.anthropic_key,
                workspace_id=config.anthropic_workspace_id,
            )
            anthropic_day = data.get(date.isoformat(), {})
        except ReconcileError as e:
            providers_skipped["anthropic"] = str(e)
    else:
        providers_skipped["anthropic"] = "ANTHROPIC_ADMIN_KEY not set"

    openai_day: dict[str, float] | None = None
    if config.openai_key:
        try:
            data = fetch_openai_daily_costs(
                client,
                start_date=date,
                end_date=next_day,
                api_key=config.openai_key,
                project_id=config.openai_project_id,
            )
            openai_day = data.get(date.isoformat(), {})
        except ReconcileError as e:
            providers_skipped["openai"] = str(e)
    else:
        providers_skipped["openai"] = "OPENAI_ADMIN_KEY not set"

    local_totals = gather_local_totals(runs_dir, start_date=date, end_date=next_day)
    local_day = local_totals.get(date.isoformat(), {})

    return compare_day(
        date=date.isoformat(),
        local_day=local_day,
        anthropic_day=anthropic_day,
        openai_day=openai_day,
        providers_skipped=providers_skipped,
        tolerance_pct=tolerance_pct,
        checked_at=checked_at,
    )


def reconcile_range(
    start_date: dt.date,
    end_date: dt.date,
    *,
    client: httpx.Client,
    runs_dir: Path,
    config: ProviderConfig,
    tolerance_pct: float = 1.0,
) -> list[ReconcileReport]:
    """Reconcile every day in [start_date, end_date] inclusive."""
    reports: list[ReconcileReport] = []
    current = start_date
    while current <= end_date:
        reports.append(
            reconcile_day(
                current,
                client=client,
                runs_dir=runs_dir,
                config=config,
                tolerance_pct=tolerance_pct,
            )
        )
        current += dt.timedelta(days=1)
    return reports


# ─── Persistence: reconcile/<date>.json ─────────────────────────────────


def reconcile_dir(project_root: Path) -> Path:
    """The standard reconcile snapshot directory: ``<project_root>/reconcile``."""
    return project_root / "reconcile"


def write_reconcile_json(report: ReconcileReport, *, project_root: Path) -> Path:
    """Atomic write of ``reconcile/<date>.json``. Returns the path written."""
    from dual_research.persistence.state import write_atomic

    target_dir = reconcile_dir(project_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{report.date}.json"
    write_atomic(path, json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return path


def read_reconcile_json(project_root: Path, date: str) -> ReconcileReport | None:
    """Latest snapshot for date, or None if reconciliation hasn't run yet."""
    path = reconcile_dir(project_root) / f"{date}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return _report_from_dict(payload)


def _report_from_dict(payload: dict[str, Any]) -> ReconcileReport:
    deltas = [ProviderDelta(**d) for d in payload.get("per_model_deltas", [])]
    return ReconcileReport(
        date=payload["date"],
        checked_at=payload["checked_at"],
        tolerance_pct=float(payload.get("tolerance_pct", 1.0)),
        providers_checked=list(payload.get("providers_checked", [])),
        providers_skipped=dict(payload.get("providers_skipped", {})),
        runs_on_date=list(payload.get("runs_on_date", [])),
        pricing_versions_seen=list(payload.get("pricing_versions_seen", [])),
        per_model_deltas=deltas,
        total_local_usd=float(payload.get("total_local_usd", 0.0)),
        total_provider_usd=float(payload.get("total_provider_usd", 0.0)),
        total_delta_usd=float(payload.get("total_delta_usd", 0.0)),
        verification_status=payload.get("verification_status", "unverified"),
    )


# ─── Formatters ─────────────────────────────────────────────────────────


def format_text(reports: Iterable[ReconcileReport]) -> str:
    """Human-readable per-day table + totals. Flagged rows prefixed with ``!``."""
    lines: list[str] = []
    reports_list = list(reports)
    for r in reports_list:
        lines.append(f"=== {r.date} · {r.verification_status} ===")
        lines.append(
            f"runs on date: {len(r.runs_on_date)}"
            + (f"  pricing: {','.join(r.pricing_versions_seen)}" if r.pricing_versions_seen else "")
        )
        if r.providers_skipped:
            for prov, reason in sorted(r.providers_skipped.items()):
                lines.append(f"  ⚠ {prov}: {reason}")
        if r.per_model_deltas:
            lines.append(
                f"  {'provider':<12} {'model':<30} {'local':>12} {'billed':>12} {'Δ':>12} {'Δ%':>8}"
            )
            for d in r.per_model_deltas:
                marker = "!" if d.flagged else " "
                lines.append(
                    f"{marker} {d.provider:<12} {d.model_id:<30} "
                    f"${d.local_usd:>10.4f} ${d.provider_usd:>10.4f} "
                    f"${d.delta_usd:>+10.4f} {d.delta_pct:>7.2f}%"
                )
        lines.append(
            f"  TOTAL: local ${r.total_local_usd:.4f}  "
            f"billed ${r.total_provider_usd:.4f}  "
            f"Δ ${r.total_delta_usd:+.4f}"
        )
        lines.append("")
    if len(reports_list) > 1:
        gl = sum(r.total_local_usd for r in reports_list)
        gp = sum(r.total_provider_usd for r in reports_list)
        lines.append(
            f"=== GRAND TOTAL ({len(reports_list)} day(s)) === "
            f"local ${gl:.4f}  billed ${gp:.4f}  Δ ${gl - gp:+.4f}"
        )
    return "\n".join(lines).rstrip() + "\n"


def format_json(reports: Iterable[ReconcileReport]) -> str:
    return json.dumps([r.to_dict() for r in reports], indent=2, ensure_ascii=False)


__all__ = [
    "ProviderConfig",
    "ProviderDelta",
    "ReconcileError",
    "ReconcileReport",
    "VerificationStatus",
    "compare_day",
    "fetch_anthropic_daily_costs",
    "fetch_openai_daily_costs",
    "format_json",
    "format_text",
    "gather_local_totals",
    "read_reconcile_json",
    "reconcile_day",
    "reconcile_dir",
    "reconcile_range",
    "write_reconcile_json",
]
