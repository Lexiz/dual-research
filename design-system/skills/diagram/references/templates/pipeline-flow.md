# Template: Pipeline / flow

Use when the system is naturally described as **numbered stages left-to-right**, often with inputs funnelling into the leftmost stage and outputs emerging on the right. The canonical example is `examples/pipeline-flow.svg` (Arc knowledge layer — Inputs → Provenance gate → Storage → Recall → Cited next answer).

## When this fits

- "Data flows through 5 stages…"
- "First we ingest, then validate, then store, then index, then serve"
- "A request comes in, gets authenticated, routed, processed, response goes out"
- Any flow where order matters and the natural reading direction is left → right.
- Especially good for showing **feedback loops** (a late stage feeding back into an earlier one — "the compounding loop").

## Use a different template if...

- The stages aren't actually ordered (parallel components) → `layered-architecture`
- Time-ordered messages between specific actors → `sequence`
- Event topology (producer/topic/consumer) → `event-flow`
- Cloud topology under the pipeline → `infrastructure`

## Input contract

```
Title: <title>
Subtitle: <one-line summary>

Stages (left to right):
  Stage 1: <name> — <one-line purpose>
    Cards: <0..N cards stacked or grouped within this stage>
      - <Card name>: <type> — <purpose>
        Sub-items: <bullets>
        State: <e.g. pulsing dot>
  Stage 2: ...
  ...

Stage transitions:
  - Stage N → Stage N+1: usually a single horizontal arrow.
    Funnel-in (Stage 1 with multiple inputs): curved arrows converging.
    Funnel-out (last stage spreading to multiple sinks): curved arrows diverging.

Feedback loop (optional):
  - <late stage> → <early stage>: arc going below the row, animation: loop-arc pulse
    Label centered below the arc

Animations:
  - Loop arc pulse (subtle, opacity)
  - Optional motion-path dots flowing through primary connectors
```

### Worked example

> **User input:** "We ingest documents, validate them, run them through an ML classifier, then store them in Postgres indexed by their classification."

**Normalized canonical spec:**

```
Title: Document Ingestion Pipeline
Subtitle: PDF/DOCX/MD in, classified records out

Stages (left to right):
  Stage 1: Ingest    — Receive PDF/DOCX/MD via upload
    Cards:
      - Upload Endpoint (light card)
        Sub-items: PDF · DOCX · MD
  Stage 2: Validate  — Schema + size checks
    Cards:
      - Validator (harnessGrad)
        Sub-items: Schema · Size · MIME
  Stage 3: Classify  — ML classifier outputs (category, confidence)
    Cards:
      - Classifier (builderGrad)
        State: live dot
  Stage 4: Store     — Postgres, indexed by classification
    Cards:
      - Postgres (sandboxGrad)
        Sub-items: Indexed by category

Stage transitions: solid-primary between each adjacent stage
Feedback loop: none
Animations: one motion-dots class along the 1→4 path
```

## Layout pattern

- **Canvas:** 1660 × ~720 for a tidy 5-stage flow. Add height (~+100–150px) if there are multiple cards per stage stacked vertically.
- **Title block:** centered at top, ~28–44px from canvas top.
- **Stage labels:** at the top of each stage column, two lines:
  - Line 1: small ALL-CAPS `STAGE N`, color `#9e9b95`, letter-spacing 2
  - Line 2: short stage title in body color `#1a1a18`, weight 600, ~13px
- **Stage columns:** divide the working width (~1540 inside ~60px margins) into stages. Stages don't have to be equal width — size them to content. Maintain ~20–30px gaps between adjacent stages' bounding boxes (gap is where the connecting arrow lives).
- **Centerline:** all stages share a vertical centerline (typically around y=320 for a 720-tall canvas) so the connecting arrows are dead horizontal at the midpoint.
- **Cards within a stage:**
  - Single tall card spanning the stage's vertical band: use for "the gate", "the storage", "the surface" — anything that's one conceptual thing.
  - Multiple stacked cards: use for "the inputs" (PDF / Filed research / Authored draft) or "the recall paths" (search tool / UI tab).
- **Stage types:**
  - Inputs / sources: light cards (white) with small colored icons.
  - Hero stage (the gate, the storage, the agent): dark card with `harnessGrad`, `storageGrad`, `agentGrad`, etc.
  - Output / answer stage: dark card, often `builderGrad` (indigo) or `agentGrad`.

## Connections inside this pattern

- **Stage → Stage transitions:** solid `#4f5fb8`, stroke-width 2, with `arrowAccent`. Short and decisive.
- **Funnel-in (multiple inputs → one stage):** three curved arrows converging on the next stage's left edge. Use cubic curves (`C`) — the middle one is straight, the top/bottom ones curve toward the convergence point.
- **Feedback / compounding loop:** a single long cubic arc going below the row from a late stage back to an early stage, dashed (`stroke-dasharray="6,5"`), with `class="loop-arc"` animation. Place an ALL-CAPS label and an italic subtitle centered below the arc — the label is editorial ("The compounding loop", not just "FEEDBACK").

## Animations to consider

For pipelines, restraint is the point. The Arc knowledge diagram uses exactly **one animation class** (`loop-arc` pulse) and it works because the diagram's meaning is "this loop compounds slowly over time". Match that mood.

If the pipeline is high-traffic (request flow, streaming), add motion-path dots flowing through Stage 1 → Stage 2. Don't animate every transition — pick the most semantically meaningful one.

## Footer block

The pipeline pattern often benefits from a 1–2 line **footer takeaway** below the main diagram — the editorial summary. Use `<tspan>` to bold the first phrase and softer-color the rest:

```xml
<text x="60" y="676" font-size="11" fill="#4a4845">
  <tspan font-weight="600" fill="#1a1a18">Sparsity is the signal.</tspan>
  <tspan> No auto-ingest of every chat turn. Every entry exists because someone, or the agent with approval, had a reason to file it.</tspan>
</text>
```

## Common pitfalls

- Equal-width stage columns even when content varies. Size to content; gaps should be roughly even, not column widths.
- Too many cards per stage. A stage shouldn't be a mini-diagram. If a stage has 4+ cards, it's probably two stages.
- Loop arc that's too prominent. The compounding loop is supposed to feel ambient. Keep `stroke-width="1.8"`, dash `"6,5"`, opacity-pulsing 0.45 ↔ 0.85.
- Stage labels missing. The `STAGE N` markers are what tell the reader to scan left-to-right.
