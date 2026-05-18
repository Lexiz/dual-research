"""Supplemental capture: Consumption tab (the big density area)."""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:6173"
RUN_ID = "20260516-035048-partner-vetting-arch-critique"
OUT_DIR = Path(__file__).parent / "screenshots"

VIEWPORTS = {"compact": (1512, 982), "wide": (2560, 1440)}
THEMES = ["dark", "light"]


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vlabel, (w, h) in VIEWPORTS.items():
            for theme in THEMES:
                ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
                page = ctx.new_page()
                page.goto(BASE, wait_until="domcontentloaded")
                page.evaluate("(t) => localStorage.setItem('dr.theme', t)", theme)
                page.evaluate(f"window.location.hash = '#/runs/{RUN_ID}'")
                page.reload(wait_until="networkidle")
                time.sleep(1.0)
                clicked = page.evaluate(
                    """
                    () => {
                      const candidates = Array.from(document.querySelectorAll('.tab'))
                        .filter(t => t.textContent.trim() === 'Consumption');
                      if (candidates.length === 0) return false;
                      candidates[0].click();
                      return true;
                    }
                    """
                )
                if not clicked:
                    print(f"[{vlabel}_{theme}] consumption tab not found")
                    ctx.close()
                    continue
                time.sleep(0.8)
                out = OUT_DIR / f"{vlabel}_{theme}_run-detail_consumption.png"
                page.screenshot(path=str(out), full_page=True)
                print(f"  saved {out.name}")
                ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
