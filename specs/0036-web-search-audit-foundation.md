---
spec: 0036
title: Web search audit foundation + protocol parser fixes + resume hardening + --notion repeatable
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.34.0
created: 2026-05-16
pr: ""
---

# Spec 0036 — Web search audit foundation + Round-2 readiness fixes

## Context

The first full end-to-end test run (post specs 0033/0034/0035) leaves one
audit gap and a small pile of round-2 readiness bugs. They share an
implementation surface (orchestrator + `protocol/parse.py`) so we land
them together rather than paying two run+verify cycles.

### The audit gap — what the model actually consulted

Spec 0033 made *what went into* every model call legible (per-turn input
bundles). Spec 0029/0031 made *how much* was consumed legible (token
counts, web-search count, tool cost). What's still invisible is **what
the model actually pulled in from the web during the call** — the
queries it issued, the URLs the search backend returned, and the
snippets it claims it read. Today the agents track only an integer
count: [`_count_web_searches`](src/dual_research/agents/anthropic_agent.py)
returns `n`; the equivalent in
[`openai_agent.py`](src/dual_research/agents/openai_agent.py) increments
`searches` per `web_search_call`. Everything richer — URLs, titles,
`page_age`, cited snippets — is read by the model and discarded.

This matters because the user's stated audit goal for dual-research is
**confidence that the final result really had all the necessary inputs
as it moved through the pipeline.** When the agents form opinions from
web sources, the human reviewer must be able to verify the model's
claims against the source material rather than trusting that a
citation URL was read in good faith.

Empirical validation against both providers (run in a scratch probe
during ideation, artefacts at `/tmp/web_search_audit_out/` if still
present) confirmed:

- **Anthropic exposes a rich audit surface.** `web_search_tool_result`
  blocks carry the full list of retrieved results (`url`, `title`,
  `page_age`, `encrypted_content`) per query. Citations in the
  model's output text carry `cited_text` — the exact source snippet
  the model attributes to each URL. A 2-turn Haiku session yielded
  50 consulted URLs and 20 citations, every one with a `cited_text`.
- **OpenAI exposes a thinner audit surface.** With
  `include=["web_search_call.action.sources"]` requested, the full
  retrieval URL list comes back (URL only — no title, no snippet, no
  `page_age`). `url_citation` annotations attach to the model's
  output text with title + char offsets, but no source-side snippet.
  Same 2-turn session yielded 6 consulted URLs and 6 citations.
- **Both providers' web search is real content retrieval**, not
  title-skimming. The `search_context_size` parameter on OpenAI
  (`low` / `medium` / `high`) controls how much page content the
  model receives before generating. Documented community complaints
  about "hallucinated citations" are about the developer-side audit
  gap (can't see what the model consumed), not about the model not
  reading content.

### Round-2 readiness bugs

The first prod-tier run also surfaced parser + orchestrator bugs that
block clean round-2 testing:

1. **CRITICAL** — `EVIDENCE_CHECKED_SECTION_RE` in
   [`parse.py`](src/dual_research/protocol/parse.py) is too strict. The
   regex requires `## Evidence checked this round` followed only by
   trailing whitespace, but agents emit trailing context like
   `## Evidence checked this round (3 sources)` or `## Evidence checked
   this round:` — the regex misses, the UI's evidence-section badge
   never lights up.
2. **CRITICAL** — `extract_revised_draft` returns `"----"` (a
   horizontal-rule-only body) as a valid revised draft. When the agent
   emits `## Revised draft` followed by an HR separator and a (now
   sibling) sub-heading, the body up to the next `## ` heading is just
   `----`. The orchestrator treats this as a valid draft, the round
   succeeds spuriously, the timeline shows a "draft" card with no
   content.
3. **CRITICAL** — Drafter format trap (parser side). The drafter
   sometimes emits revised-draft sub-sections (`## Plan summary`,
   `## Implementation steps`, …) as siblings of `## Revised draft`
   instead of nested `###` sub-sections. `extract_fenced_section`
   truncates at the next `## ` and returns only the empty preamble
   before the first sibling. Prompt-side guidance already shipped in
   spec 0034; parser-side handling is still open and is the durable
   fix (the prompt is best-effort, the parser is the contract).
4. **HIGH** — `emit_final` (in the orchestrator's finalisation path)
   crashes on `--resume` when `phase2_outcome is None`. Specifically
   `confidence_tag` and `render_metadata_header` both dereference
   `phase2_outcome` fields without a None-guard. Pre-Phase-3 resumes
   work; post-Phase-2-completed resumes are fine; the broken case is
   resuming a run that errored *during* Phase 2 before an outcome was
   recorded.
5. **HIGH** — The repair-turn path (the spec-0032 force-verbatim-copy
   repair + the standard P2 repair) uses
   `max_output_tokens=6144`. Large repaired turns truncate.
   Should match the regular turn budget (~16384) or the original
   turn's budget when known.
6. **MEDIUM** — Phase 4 doesn't skip rounds whose turn files already
   exist on disk during `--resume`. Phase 2 has this skip already
   (added in spec 0032's repair work); Phase 4 lacks the symmetric
   guard. Resuming a long Phase 4 re-runs early rounds.
7. **CLI ergonomics** — `--notion` is single-valued today. The user
   wants it repeatable (`--notion URL1 --notion URL2`), with the
   fetched contents concatenated in CLI argument order alongside any
   `--brief` and `--prompt` inputs. The spec-0021 Notion fetcher
   already handles single-root fetching; the change is at the CLI
   layer plus a concatenation rule.

### Why all of this lands together

Items 1–3 touch `protocol/parse.py` directly. Item 6 touches
`orchestrator/phase4.py` (the same orchestrator package as the
audit-event emission site). Items 4, 5, 7 are small enough that
splitting them into separate one-bug specs would burn more workflow
overhead than they cost to fix inline. Bundling them into the
audit-foundation PR means one branch, one verify cycle, one CHANGELOG
entry. The UI surfacing of the audit data (search-count chip on
collapsed cards, gist on expanded cards, "Web Search" tab in full-view
modal, hallucination warnings) lives in a follow-up spec — that work
is pure-frontend and the data layer ships clean here first.

Prior context: spec 0005 wired both providers' web_search tool; spec
0030 added `prompt_pieces` size data; spec 0031 surfaced per-phase
web-search count + tool cost in the Consumption tab; spec 0033
established the on-disk `inputs/` artefact pattern this spec mirrors
for `searches/`. The Anthropic web-search-version pin
(`web_search_20250305`) and the OpenAI tool name (`web_search`) match
what's in main today.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **A new `TurnSearches` event carries the per-turn audit payload, emitted by the orchestrator after the agent returns but before `TurnEnded`.** | `TurnEnded` already carries the integer `searches` count; adding the full audit payload to it would balloon the event by hundreds of KB for any web-search-heavy turn. A separate event mirrors spec 0033's `TurnInputs` pattern: small lifecycle events (`TurnStarted` / `TurnEnded`) stay narrow, bulk audit data (`TurnInputs`, `TurnSearches`) is its own event consumed by the aggregator and written to disk. |
| D2 | **Audit payloads are persisted to `session_dir/searches/<turn-key>.json`, parallel to `inputs/`.** | Same lazy-load pattern as input bundles (spec 0033). The aggregator's handler writes the JSON; `TurnTokenUsage.search_audit_path` is stamped so the wire signals which turns have audit data available. Bundles are NOT pushed over SSE — the frontend fetches on demand via `GET /api/runs/<id>/searches/<key>` when a Web Search tab is opened (UI is spec 0037; the endpoint ships here so the data layer is complete). |
| D3 | **One provider-neutral audit schema; per-provider normalisers feed it.** | Per the ideation probe, Anthropic and OpenAI expose materially different shapes (Anthropic gives full retrievals + `cited_text`; OpenAI gives URL-only retrievals + offset-only citations). A unified `TurnSearchAudit` schema with optional fields lets downstream code (validator, future UI) treat both providers uniformly while still capturing what each actually exposes. Asymmetry is **visible in the data** (Anthropic citations carry `cited_text`, OpenAI's don't) rather than hidden behind dispatch logic. |
| D4 | **OpenAI calls force `search_context_size: "high"` and `include: ["web_search_call.action.sources"]`.** | The two knobs that close most of OpenAI's audit gap. `search_context_size: "high"` increases the page content the model receives before generating (reduces "hallucinated citation" failure mode); `include` surfaces the full URL list rather than only cited URLs. Both are forced ON for prod-tier runs because the cost increment is negligible against an audit-grade pipeline and the alternative is shipping with a much weaker audit story on the OpenAI side. Per `web_search_enabled()`, web search itself remains togglable; when on, the include + context-size knobs ride with it. |
| D5 | **The raw `web_search_tool_result.encrypted_content` (Anthropic) is persisted but never rendered.** | The opaque blob is what Anthropic uses to maintain citation continuity across turns. Storing it preserves forensic value (a future spec could replay or cross-reference); the UI spec (0037) won't surface it because it's not human-readable. Same treatment for `encrypted_index` on citations. |
| D6 | **No server-side re-fetch in this spec.** | Re-fetching cited URLs ourselves (to close the OpenAI snippet gap and hedge link rot) was a tempting addition. Out of scope here because it introduces new failure surfaces (403/paywall/JS-rendered/ToS questions) that we don't yet know we need. Deferred to a later spec; the audit data this spec ships is enough for human verification of every Anthropic claim and for hallucinated-citation detection on both providers. Spec 0037 (UI) will surface the asymmetry honestly so users see exactly what's missing on the OpenAI side. |
| D7 | **Validators are implemented but their flags ride only on the audit payload — no UI surfacing here.** | The `cited_url_not_in_consulted_sources` / `citations_without_search_event` / `queries_missing_from_actions` checks run in the aggregator handler and stamp their results on the persisted bundle. Spec 0037 will read these flags to render warning chips. Shipping the validation logic now means the audit-grade data has its flags baked in from day one; reviewers can `jq '.flags' session_dir/searches/*.json` to spot-check without UI. |
| D8 | **The new code lives in `src/dual_research/audit/` as its own package.** | Schema + normalisers + validators are a discrete concern that doesn't naturally belong inside `agents/` (which would couple two providers' agents to each other) or `protocol/` (which is for prompt+parse logic). A new top-level package keeps it factored and testable. Three files: `schema.py`, `normalize.py`, `validate.py`. The reference implementation from the ideation phase (`/tmp/web_audit/`) ports across with minor reshape for project conventions. |
| D9 | **Audit data flows through `AgentResult.extras["search_audit"]` as a dict — not a new field on `AgentResult`.** | `AgentResult` is shared by both agents; adding a typed field would force every callsite to know about audit. `extras` is the existing escape hatch for provider-specific bits (`stop_reason`, `searches`). The orchestrator pulls the dict out, converts to the `TurnSearchAudit` dataclass, and emits. Keeps `AgentResult`'s typed surface stable. |
| D10 | **Replay safety: pre-0036 transcripts have no `searches/` folder; `search_audit_path` stays None; the UI's future Web Search tab renders an empty-state.** | Same pattern as spec 0033's pre-0033 transcript handling. No migration required. Old runs simply don't have audit data — the chrome surfaces "no audit data recorded — this run pre-dates spec 0036" when the UI ships. |
| D11 | **The `## Evidence checked this round` regex gains a `\b` word-boundary anchor and accepts trailing content.** | Change `r"^##\s+Evidence checked this round\s*$"` → `r"^##\s+Evidence checked this round\b"`. Word boundary prevents false-positive matches against `roundup` / `roundtable`; dropping the `\s*$` lets the heading carry trailing context the agents naturally emit (`## Evidence checked this round (3 sources)`, `## Evidence checked this round:`). |
| D12 | **`extract_revised_draft` strips horizontal-rule-only bodies before returning.** | A new helper `_strip_horizontal_rules(body)` removes lines that are `^-{3,}$` or `^_{3,}$` or `^\*{3,}$` (the three Markdown HR forms). After stripping + re-stripping whitespace, if the body is empty, return None. Keeps the existing `extract_fenced_section` contract for the general case; the HR-only edge is now handled at the call site that cares. |
| D13 | **Drafter format parser tolerates sibling sub-sections.** | New helper `extract_revised_draft_inclusive(turn_text)` that, when `## Revised draft` is followed by an immediate `## <other-heading>` that does NOT match any known protocol heading (the protocol-heading allowlist), consumes through it as part of the draft body. The allowlist is the existing set of expected `## …` headings the protocol emits in the same turn (e.g. `## Summary`, `## STATUS block`, `## Disagreement carryover audit`, `## Evidence checked this round`, the four review-item section headings). Any `##` not in that allowlist after `## Revised draft` is treated as a stray sibling that should have been `###` and is absorbed. This is durable (the agent's formatting drift is contained at the parser) and reversible (the allowlist is one constant). |
| D14 | **`emit_final` and its helpers guard against `phase2_outcome is None`.** | Two specific call sites in the finalisation path dereference `phase2_outcome` without a None-check. The guard renders a clear "Phase 2 did not complete" badge in the final document's metadata header rather than crashing. The orchestrator's resume path already records *that* Phase 2 errored; this fix just lets the same recording flow to the final markdown without erroring on emit. |
| D15 | **Repair-turn `max_output_tokens` rises to the same default as a regular turn (`16384`).** | `6144` was a conservative early default. Repair turns are sometimes larger than regular turns (they often replay the full canonical plan plus the response that drifted), so the conservative budget bites in practice. Match the regular budget; if a future repair-turn proves persistently larger we'll raise further. |
| D16 | **Phase 4 round-skip mirrors Phase 2's pattern.** | `phase2.py` already checks `session_dir / "phase2" / f"round-{R}-{agent}.md"` existence before running a round during resume. `phase4.py` gains the same guard, same path pattern (`session_dir / "phase4" / f"round-{R}-{agent}.md"`). One copy-paste-and-rename; no protocol change. |
| D17 | **`--notion` becomes `action="append"`; the orchestrator concatenates in CLI order.** | The Notion fetcher already returns markdown for a single root. CLI gains `nargs=1, action="append"` (each occurrence appends to `args.notion: list[str]`). A new helper `build_combined_brief(brief_path, prompt_text, notion_roots)` fetches each Notion root in order, concatenates with `\n\n---\n\n` separators between sources, prepends `--brief` content if any, prepends `--prompt` content if any. The combined brief is what feeds `phase0` onward — no protocol change. |
| D18 | **All bug fixes are unconditional; no flag.** | Audit emission is gated by the existing `web_search_enabled()` (off → no `TurnSearches` event, same as today's `searches=0`). The parser fixes are pure improvements (no flag would make sense). The `--notion` repeatable is additive — single-value invocation still works (one `append` returns a 1-element list). |

## Proposed change

### 1. Audit module — `src/dual_research/audit/`

New package, four files.

#### 1a. `audit/__init__.py`

Re-exports the public surface:

```python
from dual_research.audit.schema import (
    Citation,
    ConsultedSource,
    ToolEvent,
    TurnSearchAudit,
    TurnSearchFlags,
)
from dual_research.audit.normalize import (
    normalize_anthropic_search_audit,
    normalize_openai_search_audit,
)
from dual_research.audit.validate import validate_search_audit
```

#### 1b. `audit/schema.py`

Dataclasses mirroring the schema validated in the ideation probe.
Keys match the unified shape (provider-neutral); optional fields
capture provider asymmetry.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ConsultedSource:
    url: str
    title: str | None = None       # OpenAI sources have no title at retrieval time
    page_age: str | None = None    # Anthropic-only
    encrypted_content: str | None = None  # Anthropic-only, opaque, persisted not rendered


@dataclass
class Citation:
    url: str
    title: str | None = None
    text_span_start: int | None = None    # offset into the turn's final text
    text_span_end: int | None = None
    cited_text: str | None = None         # Anthropic only; None for OpenAI
    encrypted_index: str | None = None    # Anthropic only, opaque
    matched_query_id: str | None = None   # cross-ref: which query retrieved this URL
                                           # (None if cited URL not in any retrieval set)


@dataclass
class ToolEvent:
    event_id: str
    type: str = "web_search"
    action_type: Literal["search", "open_page", "find_in_page", "unknown"] = "search"
    queries: list[str] = field(default_factory=list)
    consulted_sources: list[ConsultedSource] = field(default_factory=list)


@dataclass
class TurnSearchFlags:
    search_performed: bool = False
    citations_without_search_event: bool = False
    cited_url_not_in_consulted_sources: bool = False
    queries_missing_from_actions: bool = False


@dataclass
class TurnSearchAudit:
    provider: str             # "anthropic" | "openai"
    model: str
    turn_key: str             # snake_case turn key, same as inputs/<key>.json
    phase: str
    agent: str
    label: str
    emitted_at: str           # ISO-8601
    tool_events: list[ToolEvent] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    flags: TurnSearchFlags = field(default_factory=TurnSearchFlags)
```

JSON serialisation uses `dataclasses.asdict` with a tiny `default=str`
fallback for any future datetime — same pattern as the input-bundle
JSON.

#### 1c. `audit/normalize.py`

Two functions — `normalize_anthropic_search_audit(message, *, turn_key,
phase, agent, label)` and `normalize_openai_search_audit(response, *,
turn_key, phase, agent, label)`. Each walks its respective response
shape and returns a `TurnSearchAudit`.

For Anthropic, walks `message.content` blocks:

- `server_tool_use` with `name == "web_search"` → appends a `ToolEvent`
  with `event_id = block.id`, `queries = [block.input.get("query")]`.
- `web_search_tool_result` → finds the matching pending `ToolEvent` by
  `tool_use_id`, appends each `web_search_result` item to
  `consulted_sources` (capturing `url`, `title`, `page_age`,
  `encrypted_content`).
- `text` blocks → accumulates the model's output text; each
  `citation` annotation is converted to a `Citation` (capturing
  `url`, `title`, `cited_text`, `encrypted_index`).

For OpenAI, walks `response.output` items:

- `web_search_call` → reads `action.type`, `action.query` (+ optional
  `action.queries` list), `action.sources` list. Builds a `ToolEvent`
  with `queries = [...]` and `consulted_sources = [ConsultedSource(url=...)
  for s in action.sources]`. Title / page_age / encrypted_content
  stay None (OpenAI doesn't expose them).
- `message` items with `output_text` → accumulates text; each
  `url_citation` annotation becomes a `Citation` with `url`,
  `title`, `text_span_start`, `text_span_end`. `cited_text` /
  `encrypted_index` stay None.

Both normalisers leave `matched_query_id` and `flags` unpopulated —
`validate_search_audit` computes those (next section).

#### 1d. `audit/validate.py`

```python
def validate_search_audit(audit: TurnSearchAudit) -> TurnSearchAudit:
    """Run all validation rules; populate audit.citations[*].matched_query_id
    and audit.flags. Mutates and returns the audit.
    """
```

Steps:

1. Build a normalised URL set per `ToolEvent` (strip tracking params
   like `utm_source=openai`, lowercase host, drop trailing `/`).
2. For each citation, find the first event whose URL set contains the
   citation's normalised URL; stamp `matched_query_id = event.event_id`.
   If no event matches, leave `matched_query_id = None`.
3. Stamp `flags.search_performed = len(tool_events) > 0`.
4. Stamp `flags.cited_url_not_in_consulted_sources` if ANY citation's
   `matched_query_id is None` AND the consulted set is non-empty.
   (The "consulted set non-empty" guard avoids OpenAI false positives
   when no `include` came back — we don't have a retrieval set to
   compare against, so we can't claim a hallucination.)
5. Stamp `flags.citations_without_search_event = bool(citations) and
   not flags.search_performed`.
6. Stamp `flags.queries_missing_from_actions = any(not ev.queries for ev
   in tool_events if ev.action_type == "search")` — captures
   Perplexity's documented "OpenAI says queries are usually but not
   always included" caveat.

A helper `_normalize_url(u)` strips `?utm_source=…`, lowercases the
scheme + host, drops trailing slash. Lives at module scope so it's
testable in isolation.

### 2. `AgentResult.extras["search_audit"]` plumbing — agents

#### 2a. `src/dual_research/agents/anthropic_agent.py`

The agent already counts `_count_web_searches(final_msg)`. The change:
after the existing count, also build the audit dict from
`final_msg.content` via `normalize_anthropic_search_audit(final_msg,
turn_key=..., phase=..., agent="claude", label=...)`. The four
context fields (turn_key, phase, agent, label) aren't known to the
agent (they're orchestrator concepts) — passed via `agent.run()`
kwargs added in this spec:

```python
async def run(
    self,
    prompt: str,
    *,
    max_output_tokens: int = 8192,
    stream_to: TextIO | None = None,
    stream_prefix: str = "",
    audit_context: dict | None = None,  # NEW: {phase, agent, label, turn_key}
) -> AgentResult:
```

When `audit_context is None`, the agent skips audit construction
entirely (preserves current contract for any call site that hasn't
been updated). The orchestrator's call sites do pass it.

The audit dict is dumped to `extras["search_audit"]`. The existing
`extras["searches"]` integer survives (consumption tab + cost
calculation depend on it).

#### 2b. `src/dual_research/agents/openai_agent.py`

Two changes:

1. The `WEB_SEARCH_TOOL` constant gains `search_context_size: "high"`:
   ```python
   WEB_SEARCH_TOOL = {"type": "web_search", "search_context_size": "high"}
   ```
2. The `responses.create` call gains `include=["web_search_call.action.sources"]`
   when `web_search_enabled()` is true.
3. Same `audit_context` kwarg added to `run()`. The agent's streaming
   path is already tracking `searches`; in the same `response.completed`
   / `response.incomplete` / `response.failed` event handler that
   captures `final_usage`, also stash `resp` itself
   (`final_response = resp`). After the stream completes, if
   `audit_context` is set, call
   `normalize_openai_search_audit(final_response, **audit_context)`
   and dump to `extras["search_audit"]`.

The streaming path doesn't deliver all `web_search_call` items inline
— some details arrive on `response.completed`. The normaliser walks
`final_response.output` which carries the full assembled list, so
streaming-vs-final divergence isn't an issue.

#### 2c. Provider-specific cost / search-count contracts unchanged

`extras["searches"]` (int) stays. `cost_usd` stays. The audit dict is
purely additive.

### 3. `TurnSearches` event — orchestrator

#### 3a. `src/dual_research/events/types.py`

```python
@dataclass(frozen=True, kw_only=True)
class TurnSearches(Event):
    """Spec 0036 — per-turn web-search audit payload.

    Emitted by the orchestrator after the agent returns but before
    ``TurnEnded``, so the aggregator can persist the audit bundle and
    stamp ``search_audit_path`` on the turn's ``TurnTokenUsage`` row
    before the ``TurnEnded`` handler runs.

    Empty when web search is disabled (no event emitted at all).
    """
    agent: str
    phase: str
    label: str
    turn_key: str
    audit: dict           # serialised TurnSearchAudit (asdict)
    kind: str = "turn_searches"
```

`turn_key` matches the snake_case key used by `inputs/` /
`searches/` filenames (same `_to_turn_key` helper from spec 0033).

#### 3b. Orchestrator call sites emit `TurnSearches`

`src/dual_research/orchestrator/_call.py` (or wherever
`run_one_call()` lives — single source of truth for agent
dispatch). After the agent returns and `TurnEnded` is built but
before it's emitted:

```python
audit_dict = (result.extras or {}).get("search_audit")
if audit_dict:
    emit(TurnSearches(
        agent=agent_label,
        phase=phase,
        label=label,
        turn_key=turn_key,
        audit=audit_dict,
    ))
emit(TurnEnded(...))
```

The dispatch site already knows `turn_key` from spec 0033's input-bundle
path; no new plumbing.

### 4. Aggregator handler + persistence

#### 4a. `_on_turn_searches` in `src/dual_research/ui/aggregator.py`

Mirrors `_on_turn_inputs` (spec 0033). Path:
`session_dir / "searches" / f"{turn_key}.json"`. Body: the audit dict
verbatim. Also runs `validate_search_audit` on the reconstructed
`TurnSearchAudit` dataclass before persisting — populates
`matched_query_id` and `flags`.

```python
def _on_turn_searches(self, event: TurnSearches, run: Run, session_dir: Path) -> None:
    audit = TurnSearchAudit(**event.audit)  # reconstruct from dict
    validate_search_audit(audit)             # populate flags + matched_query_ids
    target = session_dir / "searches" / f"{event.turn_key}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(audit), indent=2, default=str))
    # Stamp the wire signal.
    row = run.phase_token_usage.setdefault(event.turn_key, TurnTokenUsage())
    row.search_audit_path = str(target.relative_to(session_dir))
```

#### 4b. `TurnTokenUsage.search_audit_path`

`src/dual_research/ui/models.py`. New field:
`search_audit_path: str | None = None`. Camelised to
`searchAuditPath` on the wire by the existing `_to_camel`
serialiser.

#### 4c. Aggregator dispatcher

`Aggregator.handle(event)` registers `_on_turn_searches` for the new
event type. Spec 0033's pattern.

### 5. HTTP endpoints — UI server

#### 5a. `GET /api/runs/{run_id}/searches/{turn_key}`

Mirrors the spec-0033 `inputs/` endpoint exactly:

- Validates `run_id`.
- Normalises `turn_key` (accepts both `phase2Round3Claude` and
  `phase2_round3_claude`).
- Resolves `session_dir / "searches" / f"{key}.json"`; 404 if missing.
- Returns JSON verbatim.

#### 5b. `GET /api/runs/{run_id}/searches/index`

Returns the list of available turn-keys so the UI can detect pre-0036
runs without probing each turn. Same pattern as `inputs/index`.

### 6. Protocol parser fixes — `src/dual_research/protocol/parse.py`

#### 6a. `EVIDENCE_CHECKED_SECTION_RE` word-boundary fix

```python
# Before:
EVIDENCE_CHECKED_SECTION_RE = re.compile(
    r"^##\s+Evidence checked this round\s*$", re.MULTILINE
)
# After:
EVIDENCE_CHECKED_SECTION_RE = re.compile(
    r"^##\s+Evidence checked this round\b", re.MULTILINE
)
```

Word boundary prevents `roundup` / `roundtable` false positives;
dropping `\s*$` lets the heading carry trailing context. Likewise
update `CARRYOVER_AUDIT_SECTION_RE`:

```python
CARRYOVER_AUDIT_SECTION_RE = re.compile(
    r"^##\s+Disagreement carryover audit\b", re.MULTILINE
)
```

(Same too-strict shape; same fix.)

#### 6b. `extract_revised_draft` HR-stripping

New private helper `_strip_horizontal_rules(body: str | None) -> str | None`:

```python
_HR_LINE_RE = re.compile(r"^\s*[-_*]{3,}\s*$", re.MULTILINE)

def _strip_horizontal_rules(body: str | None) -> str | None:
    if not body:
        return body
    cleaned = _HR_LINE_RE.sub("", body).strip()
    return cleaned or None
```

`extract_revised_draft` calls it on the result of
`extract_fenced_section`:

```python
def extract_revised_draft(turn_text: str) -> str | None:
    raw = extract_fenced_section(turn_text, "Revised draft")
    return _strip_horizontal_rules(raw)
```

#### 6c. Drafter sibling-section tolerance — `extract_revised_draft_inclusive`

New function alongside `extract_revised_draft`. Replaces the call
site in the orchestrator that needs the inclusive form (the drafter
turn parser). `extract_revised_draft` itself stays strict for other
callers.

```python
# Known protocol headings that legitimately appear after ## Revised draft
# in the same turn body. Anything ELSE that uses `## ` is treated as a
# stray sibling and absorbed into the draft.
_PROTOCOL_TOP_HEADINGS = frozenset({
    "summary",
    "status block",
    "disagreement carryover audit",
    "evidence checked this round",
    "open questions for",          # prefix match — see _is_protocol_heading
    "substantive disagreements i'm holding",
    "resolved or non-blocking differences",
    "final-surfaced disagreements",
    "comments on the current draft",
    "issue ledger",                # prefix match
    "agreed_plan",
    "diff vs",                     # prefix match
    "answers to",                  # prefix match
})

def _is_protocol_heading(line: str) -> bool:
    """True iff `line` is a `## ...` heading matching a known protocol section."""
    m = re.match(r"^##\s+(.+?)\s*$", line)
    if not m:
        return False
    text = m.group(1).lower()
    if text in _PROTOCOL_TOP_HEADINGS:
        return True
    return any(text.startswith(prefix) for prefix in
               ("open questions for", "issue ledger", "diff vs", "answers to"))


def extract_revised_draft_inclusive(turn_text: str) -> str | None:
    """Like extract_revised_draft but absorbs stray sibling sub-sections.

    Spec 0036: the drafter sometimes emits revised-draft sub-headings as
    `## …` siblings of `## Revised draft` instead of `### …`. The strict
    extractor truncates at the first such sibling and returns an empty
    body. This variant walks forward through `## …` headings; if a
    heading is NOT in the protocol allowlist, it's absorbed as part of
    the draft body. The first protocol-allowlisted heading ends the
    draft.
    """
```

Implementation walks line-by-line from the `## Revised draft` heading,
absorbing lines until it hits a `## ` heading that `_is_protocol_heading`
classifies as protocol-known. The accumulated body is then
HR-stripped and returned.

The orchestrator switches its drafter-parse call site to use
`extract_revised_draft_inclusive`. Callers that legitimately want the
strict form (none in main today, but defensively) keep using
`extract_revised_draft`.

### 7. Orchestrator hardening — emit_final + repair budget + Phase 4 resume

#### 7a. `emit_final` None-guard

`src/dual_research/orchestrator/<finalise>.py` (locate by grep
`emit_final`, `confidence_tag`, `render_metadata_header`). Two specific
field accesses on `phase2_outcome` are unguarded:

- `confidence_tag(phase2_outcome)` — accesses
  `phase2_outcome.confidence` or similar.
- `render_metadata_header(...)` — accesses
  `phase2_outcome.converged_round`, etc.

Both become:

```python
if phase2_outcome is None:
    confidence = "unknown"
    converged_round = None
else:
    confidence = confidence_tag(phase2_outcome)
    converged_round = phase2_outcome.converged_round
```

Or equivalent — the exact shape depends on the helper signatures.
The rendered metadata header carries `Phase 2 did not complete` for
the None case so the audit trail in `final.md` is honest about the
state.

#### 7b. Repair budget

Find the repair call site (grep `max_output_tokens=6144`). Constant
moves into a named module-level value in the orchestrator:

```python
REPAIR_MAX_OUTPUT_TOKENS = 16384  # spec 0036 — raised from 6144 to match regular turn budget
```

Apply at both repair call sites (the standard P2 repair + the spec-0032
force-verbatim-copy repair).

#### 7c. Phase 4 resume-aware round skip

`src/dual_research/orchestrator/phase4.py`. Mirror the existing Phase 2
skip pattern (search the package for `session_dir / "phase2"` to find
the existing check). New guard at the top of each round loop iteration:

```python
turn_paths = [
    session_dir / "phase4" / f"round-{round_num}-claude.md",
    session_dir / "phase4" / f"round-{round_num}-openai.md",
]
if resume and all(p.exists() for p in turn_paths):
    log.info(f"phase4: skipping round {round_num} — turn files exist on disk")
    # Replay parsed outcome from disk via existing _replay_phase4_round helper
    continue
```

Reuses the existing replay helper that Phase 2 uses for the same
purpose. If no symmetric helper exists in Phase 4, add a thin one that
re-parses each turn file via `parse_turn` and reconstructs the
`Round` state.

### 8. CLI — `--notion` repeatable

`src/dual_research/cli.py` (or `cli/main.py` — locate by grep
`--notion`). Two changes:

1. The argparse declaration:
   ```python
   parser.add_argument(
       "--notion",
       action="append",
       default=[],
       metavar="URL_OR_ID",
       help=(
           "Notion page or database URL/ID to fetch and concatenate "
           "into the brief. Repeat for multiple roots. Order is preserved."
       ),
   )
   ```
2. A new helper `build_combined_brief(args) -> str` in the CLI module
   that:
   - Loads `--brief` content (if any).
   - Loads `--prompt` content (if any).
   - For each item in `args.notion` (in CLI order), invokes the
     existing Notion fetcher (from spec 0021) and collects the
     returned markdown.
   - Concatenates: `--brief` content first, then each Notion root,
     then `--prompt` content. Separator between adjacent sources:
     `"\n\n---\n\n# Source: <descriptor>\n\n"` so the model can tell
     them apart. `<descriptor>` is the path basename for `--brief`,
     the Notion title for Notion roots, `"--prompt"` for the prompt.

   If only one source exists, no separator is added (legacy behaviour).

The orchestrator entry point that consumes `args.brief` /
`args.prompt` switches to calling `build_combined_brief(args)`.

Validation: `args.notion` and `args.brief` and `args.prompt` can be
freely combined; missing-source error only fires when ALL three are
empty (currently the error fires when `args.brief is None`).

### 9. Tests

Backend-only. The audit module has the highest test surface.

- `tests/audit/test_schema.py` — `TurnSearchAudit` round-trips through
  `asdict` / dataclass reconstruction without loss.
- `tests/audit/test_normalize_anthropic.py` — feed a fixture
  Anthropic response (captured from the ideation probe and trimmed)
  into `normalize_anthropic_search_audit`; assert tool events match,
  consulted sources match (with `page_age` populated), citations
  include `cited_text`.
- `tests/audit/test_normalize_openai.py` — fixture OpenAI response
  with `web_search_call.action.sources` populated and a `message`
  carrying `url_citation` annotations. Assert audit captures URLs
  + offsets but `cited_text` is None.
- `tests/audit/test_validate.py` — six cases:
  1. Clean turn (search performed, all citations matched, no flags
     set except `search_performed`).
  2. Hallucinated citation (cited URL not in any retrieval set →
     `cited_url_not_in_consulted_sources` flag set,
     `matched_query_id` is None on the offending citation).
  3. Citations without search event (synthetic — should not happen
     in real data but the rule catches it).
  4. Queries missing from actions (synthetic — search event with
     empty queries list).
  5. URL normalisation strips `?utm_source=openai` so an OpenAI
     citation matches a consulted source whose URL has the same
     suffix.
  6. Empty consulted set (OpenAI without `include`) — does NOT flag
     `cited_url_not_in_consulted_sources` (the guard prevents false
     positives).
- `tests/events/test_turn_searches.py` — `TurnSearches` event
  shape; payload schema matches dataclass.
- `tests/ui/test_aggregator_search_persistence.py` — feeding a
  `TurnSearches` event to the aggregator writes
  `searches/<key>.json`; `TurnTokenUsage.search_audit_path` is set;
  the persisted JSON has `flags` populated by the validator.
- `tests/ui/test_server.py` — `/api/runs/<id>/searches/<key>` returns
  200 + JSON; 404 for missing keys; both camel + snake key forms
  accepted; `/searches/index` lists available keys.
- `tests/protocol/test_parse.py` (extend):
  - `## Evidence checked this round (3 sources)` is now matched.
  - `## Evidence checked this roundup of sources` is NOT matched
    (word-boundary regression check).
  - `extract_revised_draft` returns None for HR-only bodies (`----`,
    `___`, `***`).
  - `extract_revised_draft_inclusive` absorbs a stray `## Plan
    summary` sibling but stops at `## Summary` (allowlisted protocol
    heading).
- `tests/orchestrator/test_emit_final_resume.py` (new) — feed a
  resume scenario where `phase2_outcome is None`; `emit_final`
  produces a valid `final.md` with "Phase 2 did not complete" in
  the metadata header.
- `tests/orchestrator/test_repair_budget.py` (new) — assert the
  repair call sites pass `max_output_tokens=16384`.
- `tests/orchestrator/test_phase4_resume.py` (new) — pre-populate
  `session_dir/phase4/round-{1,2}-{claude,openai}.md`; resume; round
  3 starts without re-running rounds 1+2.
- `tests/cli/test_notion_repeatable.py` (new) — argparse accepts
  multiple `--notion`; `build_combined_brief` concatenates in order
  with separators; `--brief` + N × `--notion` + `--prompt` all
  combine; single-source case has no separator.

Frontend: no changes in this spec (spec 0037 covers the UI). One
manual verification: `jq '.flags' session_dir/searches/*.json` on a
fresh prod-tier run shows expected flag shape.

### 10. Files touched

New files (audit module + tests):
- `src/dual_research/audit/__init__.py`
- `src/dual_research/audit/schema.py`
- `src/dual_research/audit/normalize.py`
- `src/dual_research/audit/validate.py`
- `tests/audit/__init__.py`
- `tests/audit/test_schema.py`
- `tests/audit/test_normalize_anthropic.py`
- `tests/audit/test_normalize_openai.py`
- `tests/audit/test_validate.py`

Modified backend files:
- `src/dual_research/events/types.py` — add `TurnSearches`.
- `src/dual_research/agents/anthropic_agent.py` —
  `audit_context` kwarg + audit dict construction.
- `src/dual_research/agents/openai_agent.py` —
  `search_context_size: "high"` constant, `include` parameter,
  `audit_context` kwarg + audit dict construction.
- `src/dual_research/orchestrator/_call.py` (and any sibling
  dispatch site) — emit `TurnSearches`, pass `audit_context` into
  `agent.run()`.
- `src/dual_research/orchestrator/<finalise>.py` —
  `phase2_outcome is None` guard in `emit_final`.
- `src/dual_research/orchestrator/<repair>.py` —
  `REPAIR_MAX_OUTPUT_TOKENS = 16384`.
- `src/dual_research/orchestrator/phase4.py` —
  resume-aware round skip.
- `src/dual_research/protocol/parse.py` —
  word-boundary regex fix, `_strip_horizontal_rules` helper,
  `extract_revised_draft_inclusive`, `_PROTOCOL_TOP_HEADINGS`.
- `src/dual_research/ui/aggregator.py` —
  `_on_turn_searches` handler, dispatcher registration.
- `src/dual_research/ui/models.py` —
  `TurnTokenUsage.search_audit_path`.
- `src/dual_research/ui/server.py` —
  `/api/runs/<id>/searches/<key>` and `/searches/index` endpoints.
- `src/dual_research/cli.py` (or `cli/main.py`) —
  `--notion` repeatable, `build_combined_brief`.

Extended tests:
- `tests/protocol/test_parse.py` — regex + HR + inclusive-draft cases.
- `tests/events/test_turn_searches.py` (new).
- `tests/ui/test_aggregator_search_persistence.py` (new).
- `tests/ui/test_server.py` — searches endpoints.
- `tests/orchestrator/test_emit_final_resume.py` (new).
- `tests/orchestrator/test_repair_budget.py` (new).
- `tests/orchestrator/test_phase4_resume.py` (new).
- `tests/cli/test_notion_repeatable.py` (new).

### 11. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.33.0 → 0.34.0.
- `CHANGELOG.md`: new `## [0.34.0] — YYYY-MM-DD` entry covering all
  deltas grouped by sub-concern (audit foundation, parser fixes,
  orchestrator hardening, CLI ergonomics).
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`: a short
  note mentioning that web-search audit data is now captured per
  turn. The UI surfacing comes in spec 0037; the version-notes
  entry can preview it without exposing UI yet.

## Out of scope

- **UI surfacing of audit data.** The search-count chip on collapsed
  cards, gist line on expanded cards, "Web Search" tab in full-view
  modal, hallucination warning chips, and the agent-header
  alignment fix (Claude/GPT chip parity in the Timeline pane) — all
  spec 0037. This spec ships the data layer; spec 0037 reads it.
- **Server-side re-fetch of cited URLs for content audit.** D6 — the
  failure surfaces and maintenance burden don't earn their keep until
  we've used the spec-0037 UI in practice and felt the OpenAI snippet
  gap. Deferred to a later spec, possibly bundled with Notion-as-MCP.
- **Notion-as-MCP for agents (runtime tool agents invoke
  mid-inference).** Different concern from `--notion` CLI (which is
  input-time concatenation). Deferred.
- **Cross-turn audit aggregation / session-level audit summary.** The
  data is persisted per-turn; aggregating into a session-level audit
  view (e.g. "this run had 3 hallucinated citations across phases")
  is a spec-0037 concern (run-header summary).
- **Cost recalculation per-search.** Spec 0031 already prices web
  search via flat per-1000 rates (`ANTHROPIC_WEB_SEARCH_PER_1K`,
  `OPENAI_WEB_SEARCH_PER_1K`). The audit data exposes per-query
  counts, but the cost calculation stays at the `searches` integer.
- **Migrating pre-0036 transcripts to synthesise audit data from
  markdown.** Old runs have no captured `web_search_tool_result`
  blocks; the URL-only `[V]`-tag-in-markdown approach is lossy and
  not worth the parser work. Pre-0036 runs render with empty audit
  surfaces.
- **Streaming `TurnSearches` over SSE.** Same reasoning as spec 0033's
  input-bundle SSE call: bundles can be hundreds of KB, the UI
  fetches on demand, the event flows only through the aggregator
  to disk.
- **Replay of an `encrypted_content` chain for citation continuity.**
  We persist the encrypted blobs; we don't use them. Anthropic's
  citation-continuity mechanism is internal to their API; replaying
  it would require sending the encrypted blobs back in a follow-up
  message, which is out of dual-research's call shape (we only do
  one-shot turns, not back-and-forth within a turn).
- **A "compare what the model claimed vs what the search returned"
  diff view.** Spec 0037 surfaces the data such that a human can
  eyeball the diff; an automated diff renderer is a future spec.
- **OpenAI `web_search_preview` tool variant.** OpenAI docs note
  it's not recommended; we stay on `web_search`.
- **Reasoning-model `open_page` / `find_in_page` actions on OpenAI.**
  `gpt-4.1` and other non-reasoning models only emit `search` actions.
  The normaliser captures `action_type` faithfully so reasoning-model
  runs surface the extra actions automatically, but no special UI is
  built for them in this spec.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0036 adds at least
      18 new tests (audit schema round-trip, two normalisers, six
      validator cases, event shape, aggregator persistence, server
      endpoint, three parser cases, three orchestrator fixes, CLI
      `--notion` repeat).
- [ ] Manual: fresh prod-tier run with web search enabled (default).
      After run completes, inspect `session_dir/searches/`:
      `phase1_claude.json` exists, has 1+ tool_events, each event has
      `consulted_sources` with `url` + `title` + `page_age`,
      `citations` carry `cited_text` for Anthropic, `matched_query_id`
      populated, `flags.search_performed` is True. Repeat for
      `phase1_openai.json`: `consulted_sources` URL-only, `citations`
      have `start_index/end_index`, `cited_text` is null.
- [ ] Manual: `jq '.flags.cited_url_not_in_consulted_sources'
      session_dir/searches/*.json` returns `false` for all turns in
      a clean run (no hallucinations).
- [ ] Manual: pre-0036 transcript (load any spec-0035 run). No
      `searches/` folder. `phaseTokenUsage[*].searchAuditPath` is
      None for every turn. `/api/runs/<id>/searches/index` returns an
      empty list. No 500s.
- [ ] Manual (parser fix 1): the Phase 2 timeline's "evidence
      section" badge lights up on the next prod-tier run (was dark
      before due to the regex bug). Confirm by inspecting one turn
      file that contains `## Evidence checked this round (N sources)`
      and verifying the corresponding `phaseReviewItems` shape on the
      wire includes the evidence flag.
- [ ] Manual (parser fix 2): synthesise a Phase 4 round turn whose
      `## Revised draft` body is HR-only (`----`). The orchestrator
      treats the draft as absent (not crashed, not falsely
      promoted); the revised-draft handling falls through to the
      "no revision this round" path.
- [ ] Manual (parser fix 3): synthesise a drafter turn with sibling
      `## Plan summary` after `## Revised draft` (typical agent
      formatting drift). `extract_revised_draft_inclusive` absorbs
      it; the resulting `phase3/draft-v1.md` contains both the
      preamble and the absorbed sibling content.
- [ ] Manual (orchestrator fix 1): resume a run that errored during
      Phase 2 (synth via killing the process mid-Phase-2). Resume
      proceeds to emit `final.md` with metadata header reading
      "Phase 2 did not complete" rather than crashing.
- [ ] Manual (orchestrator fix 2): inspect the repair-call code path
      and confirm the constant is `16384` not `6144`.
- [ ] Manual (orchestrator fix 3): pre-populate
      `session_dir/phase4/round-{1,2}-{claude,openai}.md`. Resume.
      Phase 4 round 3 starts; rounds 1 and 2 are skipped with a log
      line per round.
- [ ] Manual (CLI): `dual-research --notion ROOT_A --notion ROOT_B
      --brief brief.md --prompt 'follow up'` produces a combined
      brief in this order: brief.md content, Notion ROOT_A content,
      Notion ROOT_B content, prompt text. Each separated by
      `---` and a `# Source:` header.
- [ ] Manual (hosted UI): deploy 0.34.0. `/api/runs/<id>/searches/<key>`
      returns valid JSON on a recent run; `/searches/index` lists
      keys; CORS / auth path matches `inputs/` endpoints exactly.

## Risks

- **Audit payload doubles per-turn I/O.** Same shape as spec 0033's
  input-bundle risk. A web-search-heavy turn (3 queries × 10
  Anthropic results × ~500 chars per result snippet) is ~15KB; with
  10 turns per run, ~150KB extra per run. Trivial on local disk;
  negligible on Supabase. Mitigation captured in D2 (no SSE push;
  fetched on demand).
- **`search_context_size: "high"` increases OpenAI token cost.** High
  context can multiply input tokens by 3–5× for the OpenAI web_search
  step. Mitigation: the cost is in service of the audit-grade goal
  that justifies the whole spec, and the OpenAI prod-tier model
  (`gpt-5.5`) is priced such that even a 5× context bump per search
  is sub-dollar per run. Document the cost implication in the
  CHANGELOG.
- **Anthropic SDK shape drift.** The `web_search_tool_result` block
  shape and the `citation` annotation shape are SDK-versioned. A
  future SDK bump could rename `cited_text` → `text`, etc.
  Mitigation: the normaliser reads fields via `.get()` with safe
  defaults; fixture tests pin the shape; integration test in the
  prod-tier verify step catches drift before merge.
- **OpenAI `include` parameter regression.** OpenAI could deprecate
  `web_search_call.action.sources` (the docs are clear it's
  supported as of 2026-05, but APIs shift). Mitigation: the
  normaliser tolerates an empty `sources` list (returns a `ToolEvent`
  with empty `consulted_sources`); the validator's
  empty-consulted-set guard prevents false hallucination flags.
- **`extract_revised_draft_inclusive`'s allowlist drifts from the
  protocol.** Adding a new `## …` section to a Phase 3/4 prompt
  without adding it to `_PROTOCOL_TOP_HEADINGS` causes the new
  section to be absorbed into the draft body. Mitigation: capture
  the allowlist next to the prompt definitions in `protocol/`, and
  add a test that asserts every `## ` heading in
  `protocol/prompts.py` is in the allowlist (or explicitly excluded
  with a comment). The test enforces the discipline.
- **`audit_context` kwarg adds a new agent-API surface.** Any third
  party / test calling `agent.run()` directly without
  `audit_context` continues to work (the None default skips audit).
  Internal call sites all update in this spec; no external callers
  exist today.
- **`--notion` repeatable changes the implicit "you can only pass
  one" contract.** Pre-0036 invocations that passed `--notion`
  twice silently took the last value (argparse default for
  `nargs=1` without `action="append"`); post-0036 they take both.
  Mitigation: this is a strict improvement (no broken script can
  produce a worse output than before); the CHANGELOG flags the
  behaviour change.
- **Combined-brief separator inflates the brief's token count.**
  Each separator is ~20 chars; with N Notion roots + brief +
  prompt, ~120 chars of overhead. Negligible.
- **The validator's URL normalisation is heuristic.** It strips
  `?utm_source=openai` and lowercases the host — adequate for the
  observed asymmetry in the ideation probe. Edge cases (URL
  fragments `#section`, trailing query params unrelated to UTM)
  could cause false negatives on cross-reference. Mitigation: a
  failure mode is the worst case (a citation flagged as
  not-in-consulted-set when in reality the URLs differ only by
  fragment); fix forward as observed in real runs.
- **Phase 4 resume helper duplicates Phase 2's replay logic.** If
  Phase 4's replay helper diverges in subtle ways (e.g., different
  state reconstruction), future maintenance pays twice.
  Mitigation: extract a common `_replay_round(phase, round_num,
  session_dir)` helper if the Phase 4 implementation matches Phase
  2's needs verbatim; if not, leave both and add a docstring noting
  the intentional divergence.

## Open questions

- Whether to **truncate `cited_text` and stored result content** at
  the persistence layer to bound `searches/*.json` file size. v1
  stores verbatim — empirically ~15KB per turn is fine. If a
  future high-search-volume run blows past 1MB per file, add a
  cap with `…[truncated 5234 chars]` markers.
- Whether the audit payload should include the **prompt that
  triggered the search** for cross-reference. v1 doesn't (the
  prompt is already captured by spec 0033's input bundle; the
  audit cross-references via `turn_key`). If reviewers ask "what
  prompt led the model to issue this query," the spec-0037 UI can
  link from the Web Search tab to the Input tab without duplicating
  data.
- Whether `_PROTOCOL_TOP_HEADINGS` should be auto-derived from
  `protocol/prompts.py` rather than maintained as a constant. v1
  picks the constant for clarity; auto-derivation is a future
  refactor if drift bites.
- Whether `--notion` should accept a comma-separated list as a
  single argument value (`--notion ROOT_A,ROOT_B`) in addition to
  repeatable. v1 picks repeatable only — clearer in scripts,
  matches argparse idiom.
- Whether the `## Disagreement carryover audit` regex word-boundary
  fix (D11) is strictly needed alongside the evidence-section fix.
  The user only flagged the evidence section. We're fixing the
  parallel regex defensively (same shape, same risk) because
  finding out three runs later that it has the same bug costs
  more than the four-character edit. If anyone disagrees, easy to
  revert.
- Whether the **repair max_output_tokens** should be a function of
  the original turn's budget (e.g. `min(2 × original, 32768)`)
  rather than a flat `16384`. v1 picks the flat constant for
  simplicity; if a repair turn ever exceeds 16384 we'll either
  raise it or make it adaptive.
