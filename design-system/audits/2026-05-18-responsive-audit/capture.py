"""
Responsive audit capture script.

Drives the local dual-research server at http://127.0.0.1:6173 and captures
screenshots of every meaningful surface × state at:
  - compact: 1512x982 (laptop logical, MacBook Pro 14")
  - wide:    2560x1440 (Samsung Odyssey G7 single monitor)
in both dark and light themes.

Output: screenshots/<viewport>_<theme>_<surface>[_<state>].png

Run:
  cd handoffs/2026-05-18-responsive-audit
  uv run --with playwright python capture.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = "http://127.0.0.1:6173"
RUN_ID = "20260516-035048-partner-vetting-arch-critique"  # canonical fixture
OUT_DIR = Path(__file__).parent / "screenshots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = {
    "compact": (1512, 982),
    "wide": (2560, 1440),
}
THEMES = ["dark", "light"]


def goto(page: Page, hash_path: str) -> None:
    """Navigate to a hash route and wait for app render."""
    page.evaluate(f"window.location.hash = {hash_path!r}")
    page.wait_for_load_state("networkidle", timeout=10_000)
    time.sleep(0.6)  # let React finish reconciling


def click_tab_by_text(page: Page, text: str) -> bool:
    """Click a .tab whose text starts with the given string. Returns True on success."""
    el = page.evaluate_handle(
        """
        (text) => Array.from(document.querySelectorAll('.tab, [role="tab"]'))
          .find(t => t.textContent.trim().startsWith(text))
        """,
        text,
    )
    if el.evaluate("e => !!e"):
        el.as_element().click()  # type: ignore[union-attr]
        time.sleep(0.4)
        return True
    return False


def snap(page: Page, name: str) -> None:
    """Save a screenshot. Full-page so we capture below-the-fold dense content."""
    out = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(out), full_page=True)
    print(f"  saved {out.name}")


def capture_set(page: Page, viewport_label: str, theme: str) -> None:
    """Capture every (surface, state) for one (viewport, theme)."""
    prefix = f"{viewport_label}_{theme}"
    print(f"[{prefix}]")

    # Marketing / static surfaces - default state only
    goto(page, "#/")
    snap(page, f"{prefix}_run-list")

    goto(page, "#/search")
    snap(page, f"{prefix}_search")

    goto(page, "#/compare")
    snap(page, f"{prefix}_compare")

    goto(page, "#/language")
    snap(page, f"{prefix}_design-language")

    goto(page, "#/how-it-works")
    snap(page, f"{prefix}_how-it-works")

    goto(page, "#/settings")
    snap(page, f"{prefix}_settings")

    # Run detail - the dense surface. Sweep tabs.
    goto(page, f"#/runs/{RUN_ID}")
    time.sleep(0.8)
    snap(page, f"{prefix}_run-detail_default")

    # Conversation tab is default; capture each phase
    if click_tab_by_text(page, "P4Review"):
        snap(page, f"{prefix}_run-detail_phase4")

    if click_tab_by_text(page, "ΣSummary"):
        snap(page, f"{prefix}_run-detail_summary")

    # Back to phase 2 for kind filter sweep
    click_tab_by_text(page, "P2Negotiate")
    time.sleep(0.3)

    if click_tab_by_text(page, "Questions"):
        snap(page, f"{prefix}_run-detail_questions")

    if click_tab_by_text(page, "Disagreements"):
        snap(page, f"{prefix}_run-detail_disagreements")

    if click_tab_by_text(page, "Claims"):
        snap(page, f"{prefix}_run-detail_claims")

    # Reset filter, switch to Consumption tab
    click_tab_by_text(page, "All")
    time.sleep(0.2)
    if click_tab_by_text(page, "Consumption"):
        time.sleep(0.4)
        snap(page, f"{prefix}_run-detail_consumption")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for viewport_label, (w, h) in VIEWPORTS.items():
                for theme in THEMES:
                    context = browser.new_context(
                        viewport={"width": w, "height": h},
                        device_scale_factor=1,
                    )
                    page = context.new_page()
                    # Seed theme + navigate to root once so localStorage is set
                    page.goto(BASE, wait_until="domcontentloaded")
                    page.evaluate(
                        "(t) => { try { localStorage.setItem('dr.theme', t); } catch(e){} }",
                        theme,
                    )
                    page.reload(wait_until="networkidle")
                    time.sleep(0.5)
                    capture_set(page, viewport_label, theme)
                    context.close()
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
