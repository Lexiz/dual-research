# dual-research

Two AI agents (Claude Sonnet 4.6 + GPT-5.5) negotiate to a single converged research document. Fully autonomous, no human-in-loop.

## Inputs (one of)

- `--prompt "..."` — inline brief text
- `--brief path/to/file.md` — markdown brief file
- `--notion <url>` — Notion page URL; child pages are recursively pulled in

## Usage

```bash
dual-research --notion https://www.notion.so/Workspace/Page-abc123
dual-research --brief ./my-brief.md --out ./final.md
dual-research --prompt "Research X." --models test
```

## Required environment

```
ANTHROPIC_API_KEY    # console.anthropic.com
OPENAI_API_KEY       # platform.openai.com
NOTION_TOKEN         # notion.so/my-integrations (only needed for --notion)
```

For Notion: share the root page (and its descendants) with the integration via the page's `…` → Connections menu.

## Development

```bash
uv sync                            # install deps
uv run python -m dual_research --help
```
