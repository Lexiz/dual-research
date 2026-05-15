# Integration kickoff — paste this into a fresh Claude Code session

Open Claude Code in `~/dual-research` (or your local clone), then paste the
block below to start the integration session. The prior chat is being archived
because it's hitting its context budget; this prompt re-bootstraps a new
session with everything it needs to pick up cleanly.

---

```
We've finished the backend (v0.9.0) and the local frontend (v0.15.0).
Both are merged on `main`. Every screen of the UI renders correctly
against the nine historical session directories in `runs/`, and 214
pytest cases are green.

What's NOT yet been tested is the two halves running CONCURRENTLY —
firing a real `dual-research --prompt "..."` against the test tier
while the UI server is open, and watching the live data path end to
end (transcript appends → watchfiles → SSE snapshot → React re-render
→ visible row, body, chip update).

That is your job for this session: wire the live data path end-to-end,
fix anything that breaks, and produce a polished live experience.

Before writing any code:

1. Read `handoffs/backend-state.md` — still accurate at v0.9.0. Covers
   the orchestrator's CLI, the EventBus, the session-dir-as-source-of-
   truth pattern, every event type, and known backend limitations.

2. Read `handoffs/frontend-state.md` — comprehensive snapshot of what
   was built in specs 0009 through 0014. Has the module map, endpoint
   table, Run wire shape, chip data flow, disagreement reconstruction,
   the sparse error taxonomy, and a "Known limitations" section calling
   out exactly which surfaces have NOT been exercised against a live
   run yet (section 11 — read this twice).

3. Boot the UI: `uv run dual-research serve` (defaults to
   http://127.0.0.1:6173/). Open in a browser.

4. Pick a small but real test prompt. The cheapest reliable choice on
   the test tier is something concrete and tightly scoped that should
   converge inside 3–5 negotiation rounds. Example:

      uv run dual-research \
        --prompt "Compare SQLite vs Postgres for a single-tenant API \
                  serving 1-10M rows. Output: one-page memo." \
        --models test --soft-cap 3 --hard-cap 5

   Run it in one terminal; keep the UI open in a browser tab.

5. As the run progresses, observe:

   - The new run appearing in the All-runs list (3 s poll cadence).
   - Clicking into it: connection pill flips to "connected".
   - Phase strip advances through Phase 0 → 1 → 2 → 3 → 4 → 5.
   - The current-turn body populates within ~5 s of each turn ending
     (file lands on disk, watchfiles fires, SSE snapshot includes it).
   - Stat chips update on each Phase 2/4 turn card as it lands.
   - Disagreement explorer populates as D-N entries appear in round
     files.
   - On completion, status flips to "completed" and the Phase 5
     "Final document" card appears.

6. Surface every issue you spot — visual glitches, dropped frames,
   stale data, parse failures, agent-status that lags. Don't fix
   anything yet; just log them.

7. Then propose a spec (or specs — the engineering workflow allows
   parallel non-overlapping specs) to fix them in priority order.
   Spec 0016 is next.

The user is the same single person who shipped specs 0001–0015. Same
project posture: `spec → branch → implement → admin squash-merge`.
Backend changes ARE allowed in this session if they're needed to make
the integration work (the v0.15.0 frontend was built deliberately
without backend changes; some of the gaps in `frontend-state.md`
section 11 may now want a backend fix). Each backend change still
follows the spec workflow.

Required env vars are already set on the user's machine:
ANTHROPIC_API_KEY, OPENAI_API_KEY. NOTION_TOKEN if you ever need it.
Test-tier model spend is ~$0.20–0.80 per full run; budget accordingly.

Start by reading the two handoff documents, then boot the UI and start
the test run.
```

---

After the new session reaches its own stopping point, write
`handoffs/integration-state.md` (spec 0017 or wherever you land) so the
NEXT session can pick up from there.

*Generated 2026-05-15. Spec 0015.*
