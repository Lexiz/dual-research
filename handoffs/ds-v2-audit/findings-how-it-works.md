# Findings: how-it-works.jsx

## Summary
- File size: 1459 lines
- Total deviations found: 1
- By verdict: bespoke-bypass: 0 | token-drift: 1 | gap-in-DS: 0
- By component family: Spacing: 1

## Deviations

### Group: Spacing

#### F-hiw-001: Inline marginRight hardcoded as numeric px
- **Location**: how-it-works.jsx:861
- **Verdict**: ⚠️
- **What's there** (≤15-line snippet):
  ```jsx
  <span className="chip mono tone-neutral no-dot" style={{ marginRight: 8 }}>programmatic</span>
  ```
- **Why it deviates**: Hardcoded `8` (px) instead of consuming `var(--s-2)` token. Violates spacing consistency rule from rubric §3 (forbidden pattern: "inline style={{ padding / margin / gap / etc. }} with hardcoded px values").
- **DS v2 equivalent**: `var(--s-2)` — the 8px spacing token defined in tokens.css
- **Faithful HTML re-render**:
  ```html
  <span class="chip mono tone-neutral no-dot" style="margin-right: 8px">programmatic</span>
  ```
- **DS v2 correct render**:
  ```html
  <span class="chip mono tone-neutral no-dot" style="margin-right: var(--s-2)">programmatic</span>
  ```

---

## Compliance Summary

The file is **largely compliant**. All class names use documented DS-v2 components (`.chip`, `.hiw-*`, `.changelog-*`, `.cs-*`, `.dr-card`, etc.). No v1 tokens (`--bg-`, `--fg-`, `--border-`, `--r-`, `--t-`, `--mono`, `--sans`, `--serif`, `--w-`) detected. No raw hex/rgba colors in JSX. One isolated spacing deviation at line 861 is token-drift, easily fixed by replacing `marginRight: 8` → `marginRight: 'var(--s-2)'`.
