"""Spec 0176 — Login screen v2 structural guard.

The redesign:
1. Extracts `ThemeToggle` (+ `ThemeIconBtn`, `SunIcon`, `MoonIcon`) from
   `app.jsx` into a new shared `theme-toggle.jsx`, loaded BEFORE `auth.jsx`.
2. Replaces the inline `LandingScreen` body with `LoginHero`, `LoginTopBar`,
   `LoginChatter` siblings; adds theme-persistence reads/writes to
   `localStorage['dr.theme']`.
3. Deletes `DemoRunCapsule` and `demo-run.json`.
4. Mounts `LoginTopBar` on `NotApprovedScreen` for theme continuity.

The repo has no vitest harness for `auth.jsx` / `app.jsx`, so the structural
contract that the redesign actually shipped is guarded by static analysis.
Visual + interaction verification (chatter loop integrity, theme continuity
across sign-in, X-alignment, reduced-motion) happens manually in the live
preview (notes in the handoff).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent.parent
STATIC = REPO_ROOT / "src" / "dual_research" / "ui" / "static"
AUTH = STATIC / "auth.jsx"
APP = STATIC / "app.jsx"
THEME_TOGGLE = STATIC / "theme-toggle.jsx"
INDEX_HTML = STATIC / "index.html"
COMPONENTS_CSS = STATIC / "components.css"
DEMO_RUN_JSON = STATIC / "demo-run.json"


@pytest.fixture(scope="module")
def auth() -> str:
    return AUTH.read_text()


@pytest.fixture(scope="module")
def app() -> str:
    return APP.read_text()


@pytest.fixture(scope="module")
def theme_toggle() -> str:
    return THEME_TOGGLE.read_text()


@pytest.fixture(scope="module")
def index_html() -> str:
    return INDEX_HTML.read_text()


@pytest.fixture(scope="module")
def components_css() -> str:
    return COMPONENTS_CSS.read_text()


# ── theme-toggle.jsx extraction ──────────────────────────────────────────


def test_theme_toggle_file_exists(theme_toggle: str) -> None:
    """The extracted shared module exists and publishes via window."""
    assert THEME_TOGGLE.exists(), "theme-toggle.jsx not created"
    assert "function ThemeToggle(" in theme_toggle
    assert "function ThemeIconBtn(" in theme_toggle
    assert "function SunIcon(" in theme_toggle
    assert "function MoonIcon(" in theme_toggle
    assert "Object.assign(window, { ThemeToggle, ThemeIconBtn, SunIcon, MoonIcon })" in theme_toggle


def test_theme_toggle_accepts_active_bg(theme_toggle: str) -> None:
    """Spec 0176 §2.8 — the new `activeBg` prop lets the login screen
    override the active-segment background to `transparent`."""
    sig = re.search(r"function ThemeToggle\([^)]*\)", theme_toggle)
    assert sig and "activeBg" in sig.group(0), (
        "ThemeToggle signature must accept the activeBg override prop"
    )
    icon_sig = re.search(r"function ThemeIconBtn\([^)]*\)", theme_toggle)
    assert icon_sig and "activeBg" in icon_sig.group(0)


def test_app_jsx_no_local_theme_toggle(app: str) -> None:
    """`app.jsx` no longer carries its own inlined `ThemeToggle` /
    `ThemeIconBtn` / `SunIcon` / `MoonIcon` — they're extracted."""
    for sym in ("function ThemeToggle(", "function ThemeIconBtn(",
                "function SunIcon(", "function MoonIcon("):
        assert sym not in app, f"{sym} still defined in app.jsx — should be extracted"


def test_index_html_loads_theme_toggle_before_auth(index_html: str) -> None:
    """`theme-toggle.jsx` must load BEFORE `auth.jsx` so `window.ThemeToggle`
    is defined when LandingScreen mounts."""
    tt = re.search(r"theme-toggle\.jsx\?v=([\w-]+)", index_html)
    au = re.search(r"auth\.jsx\?v=([\w-]+)", index_html)
    assert tt is not None, "index.html must include theme-toggle.jsx"
    assert au is not None
    assert tt.start() < au.start(), (
        "theme-toggle.jsx must appear before auth.jsx in index.html"
    )
    # Both share the same cache-bust version (spec 0176 §2.1 R6 — bump
    # the cache-bust query string).
    assert tt.group(1) == au.group(1), (
        "theme-toggle.jsx and auth.jsx must share the same cache-bust string"
    )


# ── New components in auth.jsx ───────────────────────────────────────────


def test_login_hero_defined(auth: str) -> None:
    """Hero component renders the 320×140 SVG with counter-rotating glyphs."""
    assert "function LoginHero()" in auth
    hero_match = re.search(r"function LoginHero\([^)]*\)\s*\{(?P<body>.*?)\n  \}",
                            auth, flags=re.DOTALL)
    assert hero_match is not None
    body = hero_match.group("body")
    # Document fade — the spec 0176 §2.2 keyTimes signature.
    assert 'keyTimes="0;0.40;0.50;0.62;0.75"' in body
    # Both arcs and brand-tone pulses present.
    assert "loginHeroArcTop" in body and "loginHeroArcBottom" in body
    assert "var(--agent-a)" in body and "var(--agent-b)" in body
    # Motion wrapper for reduced-motion gating.
    assert 'className="hero-motion"' in body


def test_login_topbar_defined(auth: str) -> None:
    """Top bar mounts the extracted ThemeToggle with activeBg='transparent'."""
    assert "function LoginTopBar(" in auth
    body_match = re.search(
        r"function LoginTopBar\([^)]*\)\s*\{(?P<body>.*?)\n  \}",
        auth, flags=re.DOTALL,
    )
    assert body_match is not None
    body = body_match.group("body")
    assert "window.ThemeToggle" in body, (
        "LoginTopBar must consume window.ThemeToggle from theme-toggle.jsx"
    )
    assert 'activeBg="transparent"' in body
    assert "aria-label=\"Toggle theme\"" in body
    # Moon/light mood label switches with theme.
    assert "Let there be light" in body
    assert "Turn it off, it's burning my eyes" in body


def test_login_chatter_defined(auth: str) -> None:
    """Chatter renders the two-col Claude / ChatGPT loop."""
    assert "function LoginChatter()" in auth
    # Constants present.
    assert "LOGIN_CHATTER_BANTER" in auth
    assert "LOGIN_CHATTER_INTERLUDES" in auth
    assert "LOGIN_CHATTER_SEGUE_POOL" in auth
    # 20-line main banter (spec §2.6).
    banter_count = auth.count("{ who: 'claude',") + auth.count("{ who: 'gpt',")
    # 20 banter + 16 interlude = 36; ChatGPT brand name in JSX = an extra few; check >=36
    assert banter_count >= 36, f"expected ≥ 36 banter/interlude lines, got {banter_count}"
    # Segue pool is the locked set.
    assert "[0, 4, 10, 16]" in auth or "[0,4,10,16]" in auth.replace(" ", "")
    # Visibility-aware pause.
    assert "visibilitychange" in auth
    # Right-edge alignment math (spec §2.5).
    assert "selectNodeContents" in auth
    assert "getClientRects" in auth


def test_landing_screen_uses_new_helpers(auth: str) -> None:
    """LandingScreen body composes the new helpers in the spec-§2.4 shape."""
    body_match = re.search(
        r"function LandingScreen\([^)]*\)\s*\{(?P<body>.*?)\n  \}",
        auth, flags=re.DOTALL,
    )
    assert body_match is not None
    body = body_match.group("body")
    assert "<LoginTopBar" in body
    assert "<LoginHero" in body
    assert "<LoginChatter" in body
    # Theme persistence mirrors app.jsx:20.
    assert "localStorage.getItem('dr.theme')" in body
    assert "localStorage.setItem('dr.theme'" in body
    # Punchline + serif title.
    assert "Two minds." in body
    assert "One document." in body
    # No leftover DemoRunCapsule mount.
    assert "DemoRunCapsule" not in body


def test_not_approved_screen_mounts_topbar(auth: str) -> None:
    """NotApprovedScreen gains the LoginTopBar (spec §2.3); body keeps
    AgentDuoVisual (spec §2.7 explicitly preserves that consumer)."""
    body_match = re.search(
        r"function NotApprovedScreen\([^)]*\)\s*\{(?P<body>.*?)\n  \}",
        auth, flags=re.DOTALL,
    )
    assert body_match is not None
    body = body_match.group("body")
    assert "<LoginTopBar" in body
    assert "<AgentDuoVisual" in body
    # Same theme-persistence read/write shape.
    assert "localStorage.getItem('dr.theme')" in body


# ── Deletions ─────────────────────────────────────────────────────────────


def test_demo_run_capsule_gone(auth: str) -> None:
    """`DemoRunCapsule` function definition is deleted."""
    assert "function DemoRunCapsule(" not in auth, (
        "DemoRunCapsule function still defined in auth.jsx"
    )


def test_demo_run_capsule_export_gone(auth: str) -> None:
    """The `window.DemoRunCapsule` re-export is gone too."""
    # The Object.assign block must not list DemoRunCapsule.
    window_block = re.search(
        r"Object\.assign\(window,\s*\{(?P<body>.*?)\}\);",
        auth, flags=re.DOTALL,
    )
    assert window_block is not None
    assert "DemoRunCapsule" not in window_block.group("body"), (
        "window.DemoRunCapsule still exported"
    )


def test_demo_run_json_deleted() -> None:
    """The static fixture this spec retired must be gone from disk."""
    assert not DEMO_RUN_JSON.exists(), (
        "demo-run.json should be deleted (spec 0176 §2.7)"
    )


def test_no_demo_run_fetch(auth: str) -> None:
    """No remaining `fetch('demo-run.json')` after the capsule removal."""
    assert "demo-run.json" not in auth


# ── Kept primitives (R1 from the spec) ────────────────────────────────────


def test_agent_duo_visual_kept(auth: str) -> None:
    """`AgentDuoVisual` and `GoogleGlyph` survive — they're still consumed."""
    assert "function AgentDuoVisual(" in auth
    assert "function GoogleGlyph(" in auth
    # NotApprovedScreen still mounts AgentDuoVisual on its body.
    assert auth.count("<AgentDuoVisual") >= 1
    # The new sign-in button uses GoogleGlyph.
    assert "<GoogleGlyph" in auth


# ── CSS surfaces ──────────────────────────────────────────────────────────


def test_login_css_present(components_css: str) -> None:
    """The page-level `.login-*` surfaces ship in components.css."""
    for sel in (".login-screen", ".login-topbar", ".login-themerow",
                ".login-chatter", ".login-chatter__badge--claude",
                ".login-chatter__badge--gpt", ".login-stagger",
                ".theme-pill::after"):
        assert sel in components_css, (
            f"components.css missing `{sel}` (spec 0176 §2.3 / §2.5 / §2.7)"
        )
    # Reduced-motion guard.
    assert "@media (prefers-reduced-motion: reduce)" in components_css
    # Theme pulse keyframes.
    assert "@keyframes themePulse" in components_css
    # Light-mode multiply override.
    assert "body.light .theme-pill::after" in components_css


def test_no_hardcoded_hex_in_login_css(components_css: str) -> None:
    """CLAUDE.md rule — color must come from tokens. The login section can
    keep the Google brand white (`#fff`) on the sign-in button and the
    Google-spec border (`#dadce0`) per spec §3.3 R3; everything else
    must read from `--md-*` / `--agent-*` / `--p-*` tokens. Decorative
    `mix-blend-mode` wash overlays (`rgba(190, 215, 255, …)`,
    `rgba(15, 18, 26, …)`) are compositor effects, not component colors,
    per spec §2.11 (principle #7 footnote)."""
    # Find the spec-0176 login block by anchor comment.
    block_match = re.search(
        r"/\* ─+\n\s*Spec 0176 — Login screen v2.*?(?=\n/\* ─+|\Z)",
        components_css, flags=re.DOTALL,
    )
    assert block_match is not None, "spec 0176 login CSS block not located"
    block = block_match.group(0)
    # Any non-Google-brand and non-blend-overlay hex/rgba should be absent.
    # Use a permissive regex: catch 6-hex colors that aren't `#fff` / `#dadce0`
    # / `#3c4043` (Google brand text), and rgba values that aren't the two
    # documented blend-overlay washes or shadow rgba.
    forbidden = re.findall(r"#[0-9a-fA-F]{6}", block)
    google_brand = {"#dadce0", "#3c4043"}  # Google sign-in button brand spec
    other_hex = [h for h in forbidden if h.lower() not in google_brand]
    assert not other_hex, (
        f"non-Google-brand hex colors leaked into the login CSS: {other_hex}"
    )
