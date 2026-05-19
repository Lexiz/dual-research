#!/usr/bin/env python3
"""Capture the Step 5 Verify shot matrix for a single spec via Playwright.

Reads queue/runs/<NNNN>/verify-plan.json (already populated by
`cli verify-begin <NNNN>`), then for each row in the plan:

  - sets viewport
  - sets theme via localStorage + body.classList
  - navigates to the route declared in the spec's § 6 visual matrix
  - waits for the page to settle
  - writes the PNG to the canonical path:
        queue/runs/<NNNN>/screenshots/NN-WxH-theme.png

Faster and more reliable than driving the preview MCP turn-by-turn:
all shots come from a single browser process, viewport/theme changes
are synchronous, and the script exits with a clear status that the
autonomous wrapper can check.

Usage:
    uv run python scripts/queue-autonomous/capture-shots.py <NNNN> [--port 6173]

If the spec's § 6 visual matrix doesn't specify a route, defaults to
`#/runs` for list-style shots and `#/runs/<canonical_fixture>` for
detail-style shots. The canonical fixture is read from
`scripts/queue-autonomous/canonical-run.txt` (currently
`20260516-035048-partner-vetting-arch-critique`, per the 2026-05-19
data-integrity arc handover).
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CANONICAL_RUN_FILE = REPO / "scripts" / "queue-autonomous" / "canonical-run.txt"


def _port_open(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def _ensure_server(host: str, port: int) -> subprocess.Popen | None:
    """Start the dual-research dev server in the background if not already
    listening on (host, port). Returns the spawned subprocess.Popen (so the
    caller can terminate it on exit), or None if the server was already up.
    """
    if _port_open(host, port):
        return None
    proc = subprocess.Popen(
        ["uv", "run", "dual-research", "serve", "--host", host, "--port", str(port)],
        cwd=str(REPO),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):  # wait up to ~30s for the server to bind
        if _port_open(host, port):
            return proc
        time.sleep(0.5)
    proc.terminate()
    raise RuntimeError(f"server did not bind {host}:{port} within 30s")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", help="zero-padded spec number, e.g. 0093")
    ap.add_argument("--port", type=int, default=6173)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    spec = args.spec.zfill(4)
    base = f"http://{args.host}:{args.port}"

    canonical = (
        CANONICAL_RUN_FILE.read_text().strip()
        if CANONICAL_RUN_FILE.exists()
        else "20260516-035048-partner-vetting-arch-critique"
    )

    plan_path = REPO / "queue" / "runs" / spec / "verify-plan.json"
    if not plan_path.exists():
        print(f"error: {plan_path} not found — did you run `cli verify-begin {spec}`?",
              file=sys.stderr)
        return 2
    plan = json.loads(plan_path.read_text())

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("error: playwright not installed. Run: uv pip install playwright && "
              "uv run python -m playwright install chromium", file=sys.stderr)
        return 3

    out_dir = plan_path.parent / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    spawned_server = _ensure_server(args.host, args.port)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900},
                                  device_scale_factor=1)
        page = ctx.new_page()
        # Bootstrap localStorage on the origin
        page.goto(base + "/", wait_until="networkidle")

        for row in plan:
            idx = int(row["index"])
            theme = row["theme"]
            viewport = row["viewport"]                  # "2200x1300"
            w, h = (int(x) for x in viewport.lower().replace("x", "×").split("×"))
            detail = (row.get("detail") or "").strip()

            # Decide route. Prefer explicit hash in detail; else fall back to
            # heuristic: 'detail' or 'run-detail' → canonical run; else /#/runs
            route = _route_from_detail(detail, canonical)

            page.set_viewport_size({"width": w, "height": h})
            page.goto(f"{base}/{route}", wait_until="networkidle")
            page.evaluate(
                "(t) => { try { localStorage.setItem('dr.theme', t); } catch(_) {} "
                "document.body.classList.toggle('light', t === 'light'); }",
                theme,
            )
            page.wait_for_timeout(800)

            out_path = out_dir / f"{idx:02d}-{viewport}-{theme}.png"
            page.screenshot(path=str(out_path), full_page=False)
            print(f"  shot {idx:02d} {viewport} {theme} → "
                  f"{out_path.relative_to(REPO)}")
        browser.close()

    if spawned_server is not None:
        spawned_server.terminate()
        try:
            spawned_server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            spawned_server.kill()

    return 0


def _route_from_detail(detail: str, canonical: str) -> str:
    """Heuristic mapping of a § 6 'detail' line to a URL fragment.

    Rules (in order):
      1. If detail contains `#/...` verbatim, take everything from the `#` to
         the next whitespace.
      2. If detail mentions `detail` / `run-detail` / `consumption`, route to
         the canonical run.
      3. Otherwise route to `#/runs` (the list view).
    """
    d = detail.lower()
    if "#/" in detail:
        # Pull the hash route
        i = detail.find("#/")
        token = detail[i:].split()[0].rstrip(",.;:)]'\"")
        # Resolve common placeholder run-ids to the canonical fixture.
        for placeholder in ("<latest>", "<canonical>", "<run>", "<run-id>"):
            token = token.replace(placeholder, canonical)
        return token
    if any(k in d for k in ("detail", "run-detail", "consumption",
                            "timeline", "critique")):
        return f"#/runs/{canonical}"
    return "#/runs"


if __name__ == "__main__":
    sys.exit(main())
