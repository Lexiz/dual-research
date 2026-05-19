---
spec: 0117
title: Deep Research artifact naming, how-it-works diagrams, and timeline full-view
label: new-feature
version-bump: MINOR
status: proposed
target-version: 1.2.0
created: 2026-05-19
pr: ""
---

# Spec 0117 — Deep Research artifact naming, how-it-works diagrams, timeline full-view

## Context

Specs 0114 (backend protocol) and 0115 (UI + validate-run + shim removal) introduce the Deep Research methodology. Both reference canonical artifacts (`system.task.*`, `user_prompt`, `agreed_interpretation`, `phase{N}.<agent>.r<N>`, `phase{N}.draft.v<N>`, `final_document`, etc.) but neither defines the **human-readable display name** for each one, nor an authoritative artifact registry that the UI / how-it-works diagrams / event payloads all read from.

In parallel, two static SVG diagrams (`diagrams/deep-research-pipeline.light.svg` and `.dark.svg`) describe the Deep Research pipeline visually. They use human-readable names like *"Preflight instructions"*, *"Agreed interpretation"*, *"Claude's research plan"* etc., with provider badges (C for Claude, G for OpenAI) and a vertical-per-phase layout. The diagrams are bundled with this spec.

The existing `how-it-works.jsx` (~2035 lines) carries legacy inline-JSX diagrams (`ProtocolOverviewMap`, `PhaseStrip`, `NegotiationRoundDiagram`, etc.) that describe the legacy single-round-P0 protocol. After spec 0114 lands these are factually wrong and visually inconsistent with the new pipeline.

Additionally, timeline cards (when clicked, opening a full-view modal) need a consistent rule for **single-document view** versus **side-by-side comparison view**, and they should label every visible artifact with the same display name used in the how-it-works diagram and in the UI's Inputs/Consumption tabs.

This spec ties all three concerns together with one authoritative artifact registry.

## Goals

1. **One canonical artifact registry** — a single source of truth, in code, that names every artifact in the Deep Research pipeline with both a stable machine ID (`user_prompt.attachment.notion:proposal-2`-style) and a human-readable display name (`"Attachment · Notion: proposal-2"`-style). Prompts, parser, persistence, events, UI, and how-it-works all read from this registry.
2. **Embed the new SVG diagrams** in how-it-works so the legacy `ProtocolOverviewMap` (and its fold) is replaced. The variant shown switches with the app's theme.
3. **Audit and update related inline-JSX diagrams** in `how-it-works.jsx` to match the Deep Research protocol (multi-round P0, agreed_* artifacts, closeout mechanism, four-category lifecycle). Remove the ones that are now redundant.
4. **Timeline card full-view mode** — define a consistent rule (single-view vs side-by-side) based on whether the artifact has a paired counterpart from the other agent for the same round, and label every visible artifact with its canonical display name.
5. **Backend-to-frontend display-name flow** — event payloads carry the artifact ID; the UI resolves the display name from the registry. No duplication of display strings outside the registry.

## Non-goals (in this spec)

- Cost tracking and per-artifact cost attribution — explicit future spec (now spec 0118), do not touch here.
- Animation of the how-it-works diagrams — static SVG is fine for v1.
- Generating the SVGs dynamically from the contract module — for v1 the SVGs are hand-authored, hand-maintained.
- Localization of display names — English-only for v1.
- New artifact kinds beyond what specs 0114/0115 establish.

## Vocabulary alignment

Both specs 0114 and 0115 are normative for *what artifacts exist*; this spec is normative for *what they are called* in the UI. The mapping is one-to-one — every artifact has exactly one canonical ID and exactly one display name.

### The artifact registry (full enumeration — NORMATIVE)

| Canonical ID | Display name template | Kind | Scope | Per-agent? |
|---|---|---|---|---|
| `system.preamble` | Methodology preamble | system | run | shared |
| `system.task.input` | Preflight instructions | system | per-turn (phase 0) | shared |
| `system.task.research_plan` | Research-plan instructions | system | per-turn (phase 1) | shared |
| `system.task.plan_negotiation` | Plan-negotiation instructions | system | per-turn (phase 2) | shared |
| `system.task.drafting` | Drafting instructions | system | per-turn (phase 3) | shared |
| `system.task.review` | Review instructions | system | per-turn (phase 4) | shared |
| `system.task.closeout` | Closeout instructions | system | per-turn (when closeout fires) | shared |
| `user_prompt` | User prompt | user | run | shared |
| `user_prompt.message` | Chat message | user (sub-section) | run | shared |
| `user_prompt.attachment.<id>` | Attachment · `<title>` | user (sub-section) | run | shared |
| `prior_turns.phase0` | Prior preflight turns | derived | per-round (R2+) | shared (perspective-flipped) |
| `prior_turns.phase2` | Prior negotiation turns | derived | per-round (R2+) | shared (perspective-flipped) |
| `prior_turns.phase4` | Prior review turns | derived | per-round (R2+) | shared (perspective-flipped) |
| `ledger.standing_items` | Ledger (standing items) | derived | per-round (R2+) | per-agent perspective |
| `closeout.request` | Closeout request | system | per-round (when fired) | per-agent |
| `phase0.<agent>.r<N>` | Preflight turn · `{agent}` · round `{n}` | agent_output | per-turn | per-agent |
| `phase1.claude` | Claude's research plan | agent_output | per-run | claude |
| `phase1.openai` | GPT's research plan | agent_output | per-run | openai |
| `phase2.<agent>.r<N>` | Negotiation turn · `{agent}` · round `{n}` | agent_output | per-turn | per-agent |
| `phase3.draft.v1` | Initial unified draft (v1) | draft | per-run | drafter only |
| `phase4.<agent>.r<N>` | Review turn · `{agent}` · round `{n}` | agent_output | per-turn | per-agent |
| `phase4.draft.v<N>` (N≥2) | Revised draft v`{n}` | draft | per-revision | drafter only |
| `current_draft` | Current draft (latest version) | draft (alias) | per-round | shared |
| `all_p2_turns` | All negotiation turns | derived | per-run | shared |
| `phase0.agreement.interpretation` | Agreed interpretation | agreement | per-run | shared |
| `phase2.agreement.plan` | Agreed plan | agreement | per-run | shared |
| `phase2.agreement.drafter` | Drafter selection | agreement | per-run | shared |
| `phase4.agreement.draft_acceptance` | Agreed draft acceptance | agreement | per-run | shared |
| `carry_forward.phase0` | Carry-forward items (phase 0) | derived | per-phase | shared |
| `carry_forward.phase2` | Carry-forward items (phase 2) | derived | per-phase | shared |
| `carry_forward.phase4` | Carry-forward items (phase 4) | derived | per-phase | shared |
| `all_carry_forward` | All carry-forward items | derived | per-run | shared |
| `final.document` | Final document | final | per-run | shared |

### Naming rules (used to derive display names for IDs with template variables)

When an ID has variable parts (`<agent>`, `<N>`, `<id>`), the display name is composed by substituting:

- `<agent>` (in ID) → `{agent}` (in display) → "Claude" or "GPT" (always title-case; **GPT not "OpenAI"** in user-visible labels)
- `<N>` (in ID) → `{n}` (in display) → numeric (1, 2, 3, …)
- `<id>` (in ID) → `{title}` (in display) → human title of the attachment (Notion page title, file name, URL host)

Examples produced by the rules:

- `phase0.claude.r3` → "Preflight turn · Claude · round 3"
- `phase4.openai.r5` → "Review turn · GPT · round 5"
- `phase4.draft.v7` → "Revised draft v7"
- `user_prompt.attachment.notion:36099f3e507f818285b7e016638453e7` → "Attachment · Notion: Partner Vetting — Architecture Proposal (Proposal 2)"

## Implementation

### 1. Extend `src/dual_research/contract/artifacts.py`

Spec 0114 introduced this module for the phase agreement-block templates + canonical hashing. This spec extends it to be the full artifact registry. **The hashing machinery (`canonical_hash`, `_normalize_for_hash`, `hash_draft_content`, `AGREED_*_TEMPLATE`, `ARTIFACT_HEADING`) stays in place untouched.** The additions:

```python
from enum import StrEnum
from dataclasses import dataclass
import re

class ArtifactKind(StrEnum):
    SYSTEM = "system"
    USER = "user"
    DERIVED = "derived"
    AGENT_OUTPUT = "agent_output"
    AGREEMENT = "agreement"
    DRAFT = "draft"
    FINAL = "final"

@dataclass(frozen=True)
class ArtifactDef:
    id_template: str                  # e.g. "phase0.<agent>.r<N>"
    display_template: str             # e.g. "Preflight turn · {agent} · round {n}"
    kind: ArtifactKind
    scope: str                        # "run" | "per-turn" | "per-round" | "per-phase" | "per-revision"
    per_agent: bool                   # True when there's one instance per agent

REGISTRY: tuple[ArtifactDef, ...] = (
    ArtifactDef("system.preamble", "Methodology preamble",
                ArtifactKind.SYSTEM, "run", False),
    ArtifactDef("system.task.input", "Preflight instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.research_plan", "Research-plan instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.plan_negotiation", "Plan-negotiation instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.drafting", "Drafting instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.review", "Review instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.closeout", "Closeout instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("user_prompt", "User prompt",
                ArtifactKind.USER, "run", False),
    ArtifactDef("user_prompt.message", "Chat message",
                ArtifactKind.USER, "run", False),
    ArtifactDef("user_prompt.attachment.<id>", "Attachment · {title}",
                ArtifactKind.USER, "run", False),
    ArtifactDef("prior_turns.phase0", "Prior preflight turns",
                ArtifactKind.DERIVED, "per-round", False),
    ArtifactDef("prior_turns.phase2", "Prior negotiation turns",
                ArtifactKind.DERIVED, "per-round", False),
    ArtifactDef("prior_turns.phase4", "Prior review turns",
                ArtifactKind.DERIVED, "per-round", False),
    ArtifactDef("ledger.standing_items", "Ledger (standing items)",
                ArtifactKind.DERIVED, "per-round", True),
    ArtifactDef("closeout.request", "Closeout request",
                ArtifactKind.SYSTEM, "per-round", True),
    ArtifactDef("phase0.<agent>.r<N>", "Preflight turn · {agent} · round {n}",
                ArtifactKind.AGENT_OUTPUT, "per-turn", True),
    ArtifactDef("phase1.claude", "Claude's research plan",
                ArtifactKind.AGENT_OUTPUT, "run", True),
    ArtifactDef("phase1.openai", "GPT's research plan",
                ArtifactKind.AGENT_OUTPUT, "run", True),
    ArtifactDef("phase2.<agent>.r<N>", "Negotiation turn · {agent} · round {n}",
                ArtifactKind.AGENT_OUTPUT, "per-turn", True),
    ArtifactDef("phase3.draft.v1", "Initial unified draft (v1)",
                ArtifactKind.DRAFT, "run", False),
    ArtifactDef("phase4.<agent>.r<N>", "Review turn · {agent} · round {n}",
                ArtifactKind.AGENT_OUTPUT, "per-turn", True),
    ArtifactDef("phase4.draft.v<N>", "Revised draft v{n}",
                ArtifactKind.DRAFT, "per-revision", False),
    ArtifactDef("current_draft", "Current draft (latest version)",
                ArtifactKind.DRAFT, "per-round", False),
    ArtifactDef("all_p2_turns", "All negotiation turns",
                ArtifactKind.DERIVED, "run", False),
    ArtifactDef("phase0.agreement.interpretation", "Agreed interpretation",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("phase2.agreement.plan", "Agreed plan",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("phase2.agreement.drafter", "Drafter selection",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("phase4.agreement.draft_acceptance", "Agreed draft acceptance",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("carry_forward.phase0", "Carry-forward items (phase 0)",
                ArtifactKind.DERIVED, "per-phase", False),
    ArtifactDef("carry_forward.phase2", "Carry-forward items (phase 2)",
                ArtifactKind.DERIVED, "per-phase", False),
    ArtifactDef("carry_forward.phase4", "Carry-forward items (phase 4)",
                ArtifactKind.DERIVED, "per-phase", False),
    ArtifactDef("all_carry_forward", "All carry-forward items",
                ArtifactKind.DERIVED, "run", False),
    ArtifactDef("final.document", "Final document",
                ArtifactKind.FINAL, "run", False),
)

# Pattern → ArtifactDef lookup, built from REGISTRY for O(1) prefix
# matching plus variable substitution. Built lazily on first use.
_AGENT_DISPLAY = {"claude": "Claude", "openai": "GPT", "gpt": "GPT"}

_TEMPLATE_VAR_RE = re.compile(r"<(agent|N|id)>")

def _id_template_to_regex(id_template: str) -> re.Pattern:
    """Convert an id_template like 'phase0.<agent>.r<N>' into a regex
    with named groups so a concrete ID can be matched against it.
    """
    pattern = re.escape(id_template)
    pattern = pattern.replace(r"\<agent\>", r"(?P<agent>claude|openai|gpt)")
    pattern = pattern.replace(r"\<N\>", r"(?P<n>\d+)")
    pattern = pattern.replace(r"\<id\>", r"(?P<id>[^.]+(?:\..+)?)")
    return re.compile(f"^{pattern}$")

def display_name(artifact_id: str, *, title_for_id: dict[str, str] | None = None) -> str:
    """Resolve an artifact ID to its human-readable display name.

    Substitutes variable parts (<agent>, <N>, <id>) into the display
    template. For `<id>` (attachment IDs), the caller provides
    ``title_for_id`` mapping attachment-id → human title (looked up at
    run time from attachments.json). Falls back to the ID itself if no
    title is supplied.

    Returns the unchanged artifact_id if no template matches — this is
    a signal that the registry is incomplete, which the coverage test
    in the test plan turns into a CI failure.
    """
    for defn in REGISTRY:
        rx = _id_template_to_regex(defn.id_template)
        m = rx.match(artifact_id)
        if not m:
            continue
        groups = m.groupdict()
        subs = {}
        if "agent" in groups and groups["agent"]:
            subs["agent"] = _AGENT_DISPLAY.get(groups["agent"], groups["agent"])
        if "n" in groups and groups["n"]:
            subs["n"] = groups["n"]
        if "id" in groups and groups["id"]:
            raw = groups["id"]
            subs["title"] = (title_for_id or {}).get(raw, raw)
        try:
            return defn.display_template.format(**subs)
        except KeyError:
            return defn.display_template
    return artifact_id

def is_known(artifact_id: str) -> bool:
    """True iff ``artifact_id`` matches any template in REGISTRY."""
    return display_name(artifact_id) != artifact_id or any(
        d.id_template == artifact_id for d in REGISTRY
    )

def kind_of(artifact_id: str) -> ArtifactKind | None:
    """Return the ArtifactKind for the artifact, or None if unknown."""
    for defn in REGISTRY:
        if _id_template_to_regex(defn.id_template).match(artifact_id):
            return defn.kind
    return None
```

The module exposes (in addition to the existing hashing functions):

- `REGISTRY` — the typed tuple of every `ArtifactDef`
- `display_name(artifact_id, *, title_for_id=None) -> str` — the canonical resolver, used by every consumer
- `is_known(artifact_id) -> bool` — for validators to detect typos
- `kind_of(artifact_id) -> ArtifactKind | None` — kind lookup for UI styling

### 2. Backend changes: events carry artifact IDs, not display strings

The new event types from spec 0114 (`ItemRaised`, `ItemTransitioned`, `PhaseConverged`, `CloseoutUrged`) gain (or are confirmed to have) the relevant artifact-ID fields. **Display strings never appear in event payloads.** The frontend resolves names from the registry at render time.

For events emitted in this spec specifically — none new are added. We confirm the existing payload fields use the canonical IDs from the registry. Where they currently use ad-hoc strings (e.g. legacy `draft-claude.md` filename vs `phase1.claude`), update to the canonical ID.

The persistence layer (state.json, transcript) likewise emits IDs not display names. The CLI tools (`validate-run` from spec 0115) accept IDs but print display names via `display_name()`.

### 3. Embed the new SVG diagrams in how-it-works

Move (or copy) the two SVG files into the UI bundle:

```
src/dual_research/ui/static/diagrams/deep-research-pipeline.light.svg
src/dual_research/ui/static/diagrams/deep-research-pipeline.dark.svg
```

(The originals at the repo root `diagrams/` stay as the authoring source; copies in `ui/static/diagrams/` are what's bundled.)

In `how-it-works.jsx`, replace the body of `ProtocolOverviewMap` (around line 1315) and `ProtocolOverviewFold` (around line 1613):

```jsx
function ProtocolOverviewMap() {
  const theme = useTheme(); // existing hook
  const src = theme === 'dark'
    ? '/static/diagrams/deep-research-pipeline.dark.svg'
    : '/static/diagrams/deep-research-pipeline.light.svg';
  return (
    <figure className="hiw-overview-figure">
      <img
        src={src}
        alt="Deep Research pipeline · inputs and outputs per phase"
        className="hiw-overview-svg"
        loading="lazy"
      />
      <figcaption>Deep Research pipeline. Phases run left to right;
        per-phase inputs are stacked top-to-bottom in the order the
        orchestrator feeds them.</figcaption>
    </figure>
  );
}
```

The legacy inline-JSX SVG content inside the old `ProtocolOverviewMap` is deleted.

### 4. Update related inline diagrams in `how-it-works.jsx`

The smaller inline diagrams either need protocol-level updates or removal. Per spec 0114, the protocol changes are:

- **P0 is now multi-round, not single-turn** — every diagram that shows P0 as a one-shot must be updated
- **`AGREED_INTERPRETATION` is a new artifact** — diagrams showing P0 → P1 dead-end must show the artifact flow
- **The closeout mechanism replaces repair** — diagrams referencing repair turns must be updated
- **Four-category lifecycle (Q/D/I/C)** — diagrams showing the old 5-category (with `claim`) or 3-category shapes must be updated

Audit checklist — for each: **update** to match Deep Research, or **remove** if redundant with the new SVG:

| Component | Action | Notes |
|---|---|---|
| `PhaseStrip` (line ~712) | **Update** | Six-phase strip; mark P0 as multi-round; show `agreed_interpretation` flow from P0 → P1; remove any repair references; use registry display names |
| `NegotiationRoundDiagram` (line ~756) | **Update** | New turn structure (5 operation blocks: RAISE / ADDRESS / RESOLVE / ACKNOWLEDGE / WITHDRAW + status footer); per spec 0114 |
| `CallBox` (line ~885) | **Update** | Every artifact name label resolves through `display_name(artifact_id)`; no hardcoded strings |
| `LifecycleRow` (line ~935) | **Update** | Show 6-state lifecycle (open / addressed / resolved / acknowledged / withdrawn / capped); per spec 0114 |
| `ChatLifecycle` (line ~961) | **Update** | P0 outputs now feed P1 via `agreed_interpretation`; correct the "dead-end" annotation that no longer applies |
| `ProtocolOverviewMap` / `ProtocolOverviewFold` | **Replace** | Swap in the SVG embed per section 3 |

### 5. Timeline card full-view mode (NORMATIVE)

A timeline card represents one artifact in the run. Clicking opens a full-view modal. Two modes:

**Single-view** — shows one artifact's full content. Used when:
- The artifact has no paired counterpart from the other agent for the same round
- The artifact is the canonical (single) form: agreement blocks, drafts, the final document

**Side-by-side comparison view** — shows two artifacts in two panes. Used when:
- The artifact is one of a pair (same phase, same round, different agent)
- Comparing the two is more informative than showing one in isolation

**Mode mapping table (NORMATIVE):**

| Card source artifact ID | Mode | Pane content | Header text rule |
|---|---|---|---|
| `phase0.<agent>.r<N>` | **Side-by-side** | left: `phase0.claude.r<N>` ; right: `phase0.openai.r<N>` | each pane: display_name(its-own-id) |
| `phase1.claude` | **Side-by-side** | left: `phase1.claude` ; right: `phase1.openai` | each pane: display_name(its-own-id) |
| `phase1.openai` | **Side-by-side** | left: `phase1.claude` ; right: `phase1.openai` | each pane: display_name(its-own-id) |
| `phase2.<agent>.r<N>` | **Side-by-side** | left: `phase2.claude.r<N>` ; right: `phase2.openai.r<N>` | each pane: display_name(its-own-id) |
| `phase3.draft.v1` | Single | the draft | "Initial unified draft (v1) · drafted by {Claude|GPT}" |
| `phase4.<agent>.r<N>` | **Side-by-side** | left: `phase4.claude.r<N>` ; right: `phase4.openai.r<N>` | each pane: display_name(its-own-id) |
| `phase4.draft.v<N>` (N≥2) | Single | the draft revision | "Revised draft v{n} · revised by {Claude|GPT}" |
| `phase0.agreement.interpretation` | Single | the canonical block | "Agreed interpretation" |
| `phase2.agreement.plan` | Single | the canonical block | "Agreed plan" |
| `phase2.agreement.drafter` | Single | the drafter declaration | "Drafter selection" |
| `phase4.agreement.draft_acceptance` | Single | the canonical block | "Agreed draft acceptance" |
| `final.document` | Single | final.md | "Final document" |
| `user_prompt` | Single | composite view | "User prompt" |
| `user_prompt.message` | Single | the literal chat message | "Chat message" |
| `user_prompt.attachment.<id>` | Single | the attachment content | "Attachment · {title}" |

**Left/right convention in side-by-side mode:** **Claude on left, GPT on right.** Predictable beats dynamic. Don't reorder based on which card the user clicked.

**Single-mode header rule:** display_name of the artifact, plus a " · drafted by {agent}" / " · revised by {agent}" suffix when the artifact has a producer.

**Modal body in both modes** uses the existing markdown renderer + side-by-side anchor viewer from spec 0115.

### 6. Where display names appear in the UI (NORMATIVE touchpoint list)

Every place that surfaces an artifact name to the user MUST resolve through the registry. Concrete touchpoints:

- **Timeline card titles** — `display_name(artifact_id)` not the raw ID
- **Timeline card hover tooltips** — same
- **Timeline full-view modal header** — per the mode-mapping rule above
- **Inputs tab** (Spec 0033 surface) — each row labeled with the registry's display name
- **Consumption tab** (Spec 0030/0118 surface) — chip labels and row labels match the registry
- **Critique cards** (Spec 0115) — when surfacing the source artifact of an item, use the registry name
- **Final-document appendix** (Spec 0115) — each unresolved item's "raised in" / "addressed in" turn references use the registry name
- **`validate-run` CLI report** (Spec 0115) — printed lines reference the registry name in addition to the ID
- **How-it-works inline diagrams** — every artifact label resolves through the registry

The transcript and event stream keep using canonical IDs (machine-readable). Translation happens at the rendering boundary.

## Alignment with specs 0114 and 0115

This spec is purely additive on top of 0114 and 0115:

- **0114**: extends the `contract/artifacts.py` module that 0114 already creates (for phase agreement blocks) into the full artifact registry. No protocol changes; hashing machinery untouched.
- **0115**: defines naming conventions that the UI components built in 0115 consume. The UI's `CritiqueCard`, `SourceRow`, timeline cards, appendix renderer — all of them — call `display_name(artifact_id)` from this spec's registry.

If 0117 lands before 0115's UI work begins, the registry is in place and 0115's components consume it from day one. If 0117 lands after 0115, the 0115 components are updated to swap any hardcoded display strings for registry calls. Either order works.

The how-it-works embedding (sections 3 and 4 above) is independent of 0115's runtime UI changes — they touch different React files.

**Partial-implementation slice (when 0114/0115 are not fully landed):**

The artifact registry module (section 1) is fully standalone. It can be implemented and unit-tested without any other Deep Research work. If 0114 has shipped the contract module shell and the hashing machinery (current observable state), this spec's section 1 extends `artifacts.py` in-place without modifying the existing functions. Sections 2–6 depend on 0114's events being live (section 2) and 0115's UI components existing (sections 3–6), so they should pause for those prerequisites.

## Test plan

- [ ] Unit tests for `contract/artifacts.py`: every artifact ID in the registry resolves to a non-empty display name; variable-substituting templates produce expected output for sample inputs.
- [ ] Coverage test: enumerate every artifact ID used anywhere in the codebase (parser, orchestrator, events, UI); verify each is registered. Fail CI if a new ID appears without a registry entry.
- [ ] Visual QA: open how-it-works overlay in light and dark themes; verify the new SVG renders correctly in each.
- [ ] Visual QA: confirm the legacy `ProtocolOverviewMap` is removed (no orphaned imports, no leftover dead code).
- [ ] Visual QA: open each phase's timeline card on a real run; verify the card title and the full-view header show the registry display name.
- [ ] Side-by-side mode test: click a `phase2.claude.r3` card; verify side-by-side modal opens with Claude (left) + GPT (right) for round 3.
- [ ] Single-view mode test: click `phase3.draft.v1`; verify single-view modal opens.
- [ ] Integration test: change a display name in the registry; verify it propagates to every surface (timeline, full-view header, inputs tab, validate-run CLI output).
- [ ] Backward-compat: legacy runs (pre-spec-0114) — their artifacts use the legacy file-naming (`draft-claude.md` etc.); verify the legacy renderer maps these to sensible display names via a small legacy mapping table.

## Risks

- **Registry drift**: developers add new artifact IDs without updating the registry, breaking display names. Mitigation: the coverage test in the test plan fails CI on unregistered IDs.
- **SVG bundle size**: the two SVGs are ~260KB each rendered, smaller as text. Verify final bundle impact in build. If excessive, consider lazy-loading (`loading="lazy"` is already in the embed; React-side, the SVG is only loaded when the how-it-works overlay opens).
- **Legacy run compatibility**: pre-0114 runs use the legacy event payloads with file-name-style references. The legacy renderer (kept per spec 0115's "legacy mode" code path) needs a mapping table to display names — small effort, but mandatory.
- **Display-name churn**: changing a display name in the registry is a one-line edit but propagates to many UI surfaces. This is by design (single source of truth) but means small text changes affect multiple visible places. Acceptable — that's the point.
- **Theme switching latency**: the SVG variant swap happens at render based on theme state. If the user toggles theme while the overlay is open, the SVG should re-render. Confirm React re-renders the `<img>` src when theme state changes.

## Open questions (NORMATIVE — verbatim)

- **OQ-1**: The `user_prompt` attachment titles in the diagram are currently hardcoded with the audited run's specific titles ("proposal-2", "synthesis & reqs", "briefing"). For the bundled how-it-works diagram, should these be:
  - (a) Kept as the audited run's titles (concrete, but specific to one run)
  - (b) Made generic ("Attachment 1", "Attachment 2", "...")
  - (c) Hidden entirely with a "... per attached source" placeholder

  **Spec's current default: (b)** — replace with generic numbered placeholders so the diagram applies to any run. The original SVG files at the repo root `diagrams/` keep the audited titles as a reference; the bundled UI copies get the generic version.

- **OQ-2**: The side-by-side modal's Claude-left/GPT-right convention is hardcoded. Should it follow the user's last-clicked card (i.e. if you clicked the GPT card, GPT goes on the left)?

  **Spec's current default: keep it consistent (Claude always left)** for v1 — predictable beats dynamic.

- **OQ-3**: Should agreement artifacts (`agreed_interpretation`, `agreed_plan`, etc.) have their own timeline card, or are they implicit in the round-card where they were emitted?

  **Spec's current default: implicit** (the emit-on-AGREED is shown as a chip on the round-N card that achieved convergence). If a separate "Agreement" card is needed, that's a follow-up spec.

- **OQ-4**: For attachments where the title is very long (e.g. a full URL), should the display name be truncated in chip labels?

  **Spec's current default: yes, with the full title in the tooltip. Truncation rule: 40 characters + ellipsis.**
