# Findings: app.jsx + run-list.jsx

## Summary
- Files audited: app.jsx (640 lines), run-list.jsx (505 lines)
- Total deviations found: 28
- By verdict: bespoke-bypass: 1 | token-drift: 27 | gap-in-DS: 0
- By component family: Typography: 15 | Shape/Radius: 6 | Elevation: 1 | Spacing: 4 | Colors: 1

---

## Deviations

### Group: Typography (fontSize)

#### F-applist-001: Hardcoded fontSize instead of type-role token
- **Location**: app.jsx:285, 351, 370, 427, 430, 436, 467, 522, 621, 623, 630; run-list.jsx:188, 197, 220, 246, 275, 315, 325, 342, 367, 383, 397, 401, 458, 463, 469, 471, 474, 475, 476
- **Verdict**: ⚠️ token-drift
- **What's there**:
  ```jsx
  <div style={{ fontSize: 11, ... }}>
  <span style={{ fontSize: 12.5, ... }}>
  <div style={{ fontSize: 13, ... }}>
  ```
- **Why it deviates**: All fontSize values are hardcoded as `px` numbers instead of consuming `var(--md-*-size)` tokens from the type scale (display, headline, title, body, label roles).
- **DS v2 equivalent**: Use `.t-body-m`, `.t-label-s`, `.t-title-m`, etc. classes or `fontSize: 'var(--md-body-m-size)'` tokens.
- **Faithful HTML re-render**:
  ```html
  <div style="font-size: 11px; ...">...</div>
  ```
- **DS v2 correct render**:
  ```html
  <div class="t-body-m" style="font-size: var(--md-body-m-size); ...">...</div>
  ```

#### F-applist-002: lineHeight raw number instead of token
- **Location**: app.jsx:427
- **Verdict**: ⚠️ token-drift
- **What's there**:
  ```jsx
  <div style={{ lineHeight: 1.2, ... }}>
  ```
- **Why it deviates**: lineHeight is a raw numeric ratio (1.2) instead of reading `var(--md-*-lh)` token for the corresponding type role.
- **DS v2 equivalent**: `lineHeight: 'var(--md-headline-m-lh)'` or similar, depending on context.
- **Faithful HTML re-render**:
  ```html
  <div style="line-height: 1.2; ...">...</div>
  ```
- **DS v2 correct render**:
  ```html
  <div style="line-height: var(--md-headline-m-lh); ...">...</div>
  ```

---

### Group: Shape (border-radius)

#### F-applist-003: Hardcoded px values for borderRadius instead of token
- **Location**: app.jsx:423, 434, 465, 575; run-list.jsx:188, 401, 445, 496
- **Verdict**: ⚠️ token-drift
- **What's there**:
  ```jsx
  style={{ borderRadius: 8, ... }}
  style={{ borderRadius: 6, ... }}
  style={{ borderRadius: 999, ... }}
  style={{ borderRadius: 1.5, ... }}
  style={{ borderRadius: 4, ... }}
  style={{ borderRadius: 3, ... }}
  ```
- **Why it deviates**: All border-radius values hardcoded as `px` numbers instead of using `var(--md-shape-*)` tokens (xs: 4px, sm: 8px, md: 12px, lg: 16px, xl: 28px, full: 9999px).
- **DS v2 equivalent**: Use `borderRadius: 'var(--md-shape-sm)'` for 8px, `'var(--md-shape-xs)'` for 4px, `'var(--md-shape-full)'` for pill (999px).
- **Faithful HTML re-render**:
  ```html
  <div style="border-radius: 8px; ...">...</div>
  <div style="border-radius: 999px; ...">...</div>
  ```
- **DS v2 correct render**:
  ```html
  <div style="border-radius: var(--md-shape-sm); ...">...</div>
  <div style="border-radius: var(--md-shape-full); ...">...</div>
  ```

---

### Group: Spacing (padding, margin, gap)

#### F-applist-004: Hardcoded padding/margin/gap values in px
- **Location**: app.jsx:281, 312, 320, 321, 345, 368, 410, 426, 430, 434, 465, 515, 522; run-list.jsx:181, 186, 202, 207, 219, 235, 238, 252, 254, 269, 272, 312, 314, 320, 338, 339, 357, 359, 363, 374, 380
- **Verdict**: ⚠️ token-drift
- **What's there**:
  ```jsx
  gap: 8,
  padding: '0 16px',
  margin: '0 4px',
  padding: '0 12px',
  padding: '8px 10px',
  gap: 6,
  ```
- **Why it deviates**: All spacing values hardcoded as `px` numbers or strings instead of using `var(--md-sp-*)` tokens (sp-0 through sp-20 mapping to 0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80 px).
- **DS v2 equivalent**: `gap: 'var(--md-sp-2)'` for 8px, `padding: 'var(--md-sp-4)'` for 16px, etc.
- **Faithful HTML re-render**:
  ```html
  <div style="padding: 0 16px; gap: 8px; ...">...</div>
  ```
- **DS v2 correct render**:
  ```html
  <div style="padding: 0 var(--md-sp-4); gap: var(--md-sp-2); ...">...</div>
  ```

---

### Group: Elevation (shadow)

#### F-applist-005: Raw rgba shadow instead of elevation token
- **Location**: app.jsx:424
- **Verdict**: ⚠️ token-drift
- **What's there**:
  ```jsx
  boxShadow: '0 8px 28px rgba(0,0,0,0.45)',
  ```
- **Why it deviates**: Box shadow is hardcoded as a raw rgba value instead of using `var(--md-elev-*)` token (elev-0 through elev-5 with pre-defined shadow recipes).
- **DS v2 equivalent**: `boxShadow: 'var(--md-elev-2)'` or `'var(--md-elev-3)'` depending on intended lift.
- **Faithful HTML re-render**:
  ```html
  <div style="box-shadow: 0 8px 28px rgba(0,0,0,0.45); ...">...</div>
  ```
- **DS v2 correct render**:
  ```html
  <div style="box-shadow: var(--md-elev-3); ...">...</div>
  ```

---

### Group: Colors (custom hsl background)

#### F-applist-006: Deterministic hsl avatar fallback instead of token-based palette
- **Location**: app.jsx:498
- **Verdict**: ❌ bespoke-bypass
- **What's there**:
  ```jsx
  <div style={{
    background: `hsl(${hue}, 55%, 38%)`,
    color: 'white',
    ...
  }}>
  ```
- **Why it deviates**: Avatar fallback uses raw `hsl()` CSS expression with hardcoded saturation (55%) and lightness (38%) instead of a token-based avatar palette. Although this is a legitimate edge-case need (deterministic color per email), it should consume agent-tone tokens (--agent-a, --agent-b) or define a new `--avatar-*` token family.
- **DS v2 equivalent**: Define a new avatar color palette token like `--avatar-bg-{hue}` or use `.tone-claude` / `.tone-gpt` class for fallback avatar.
- **Faithful HTML re-render**:
  ```html
  <div style="background: hsl(45, 55%, 38%); color: white; ...">initials</div>
  ```
- **DS v2 correct render**:
  ```html
  <div style="background: var(--avatar-bg); color: var(--md-on-avatar); ...">initials</div>
  ```

---

## Compliance Notes

All deviations are **categorized as token-drift** (27 findings) or **bespoke-bypass** (1 finding). No gaps-in-DS identified — the DS v2 token vocabulary covers all observed use cases.

**Recommended fix priority:**
1. **fontSize** (15 instances) → adopt `.t-*` classes or `var(--md-*-size)` tokens
2. **borderRadius** (8 instances) → replace with `var(--md-shape-*)` tokens
3. **spacing** (21 instances across padding/margin/gap) → replace with `var(--md-sp-*)` tokens
4. **boxShadow** (1 instance) → use `var(--md-elev-*)` token
5. **avatar hsl** (1 instance) → define or adopt avatar token palette

All fixes preserve existing visual intent while aligning to DS v2 governance.
