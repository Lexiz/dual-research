# Kickoff prompts — Spec set 0140–0147

One kickoff prompt per spec. Use them to start a new Claude Code session for that spec's implementation.

## Workflow

1. Open a new Claude Code session in `/Users/alexlisitzky/dual-research`.
2. Open `specs/_kickoff-prompts/0140.md` (or the next un-shipped spec).
3. Paste everything **below the `## Kickoff — paste into new session` heading** into the new session as the first message.
4. The session validates state → re-reads the spec → resolves open questions with you → implements → tests → PRs → merges → deploys → writes the handover on main.
5. When done, the session stops (pause-between-specs rule). Open the next spec's kickoff in a fresh session.

## Recommended shipping order

Same as the numbers (0140 → 0147). Dependencies are listed in each prompt's header — confirm dependencies are merged on main before kicking off a downstream spec.

| Spec | Depends on (must be merged) |
|---|---|
| 0140 | 0137 (already on main) |
| 0141 | 0140 |
| 0142 | — |
| 0143 | — |
| 0144 | 0140, 0141 |
| 0145 | 0142, 0143 |
| 0146 | 0143, 0145 |
| 0147 | — |

0140 / 0142 / 0143 / 0147 can be parallelised across worktrees if you want, but the simplest loop is sequential.

## Anchor run

All eight specs cite evidence from run `20260521-010637-dvs-backend-language-choice`. Re-query Supabase if you need to confirm any quoted payload during implementation.

## Inventory

`specs/_backlog-inventory.md` maps every Bxx item to its target spec. Use it to trace any spec text back to its source.
