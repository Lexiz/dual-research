# Hosting the spec dashboard on Cloudflare Pages

Cloudflare Pages serves the rendered dashboard from a private GitHub repo for free. Auto-rebuilds on every push to `main` so the dashboard reflects every `/spec-draft`, `/spec-queue`, `/spec-promote`, and `/dev-next` action within seconds.

Once set up, you bookmark one URL and it stays live.

## One-time setup

### 1. Sign in to Cloudflare Pages

Go to [pages.cloudflare.com](https://pages.cloudflare.com). Sign up if you don't have an account (free tier is sufficient).

### 2. Create a project

- Click **Create application** → **Pages** → **Connect to Git**.
- Authorize Cloudflare's GitHub app on the **Lexiz** account.
- When prompted to choose repository access, select **Only select repositories** and pick `Lexiz/dual-research` (not all repos).
- Click **Begin setup** on the dual-research entry.

### 3. Build configuration

| Field | Value |
|---|---|
| **Project name** | `dr-dashboard` (or whatever you want — becomes the subdomain) |
| **Production branch** | `main` |
| **Framework preset** | None |
| **Build command** | `pip install pyyaml && python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out dist --shell-only` |
| **Build output directory** | `dist` |
| **Root directory** | (leave blank — defaults to repo root) |

Note: the `--shell-only` flag (spec 0160) emits empty data-region placeholders for the live sections (hero, queue, feed, drafts, all-specs). The bootstrap script at `dashboard-bootstrap.js` fetches `/api/data` at runtime and populates them — so the dashboard reflects fresh repo state without paying the rebuild lag. The Pages Function at `functions/api/data.js` is what serves `/api/data` (see § Live data setup below).

Under **Environment variables** (expand the section):

| Variable | Value |
|---|---|
| `PYTHON_VERSION` | `3.11` |

Click **Save and Deploy**.

### 4. First build

Cloudflare runs the build. Takes ~30 seconds. On success the project page shows a green check and the URL — something like `https://dr-dashboard.pages.dev`.

**Bookmark that URL.** That's the dashboard. It stays at the same address forever.

### 5. (Optional) Custom subdomain

If you want `dr.lisitzky.dev` (or whatever) instead of `.pages.dev`:

- Project → **Custom domains** → **Set up a custom domain**.
- Add the CNAME at your DNS provider as instructed.

## How it stays fresh

Every push to `main` (which happens automatically when the skills run) triggers a Cloudflare rebuild. Lag from push to live page is ~30 seconds.

You don't need to do anything to refresh it. Just open the bookmark.

## How to verify locally before pushing

If you want to confirm the renderer works before relying on the Cloudflare build:

```bash
cd /Users/alexlisitzky/dual-research
uv run python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out /tmp/dr-dash
open /tmp/dr-dash/index.html
```

The output should match what Cloudflare produces.

## Troubleshooting

- **Build fails at `pip install`**: Cloudflare's default Python is too old. Confirm `PYTHON_VERSION=3.11` is set under environment variables for both Production and Preview.
- **Build succeeds but page is empty**: check the build log for `rendered N specs + M drafts → dist`. If `N=0`, the renderer didn't find spec files — check that the `Root directory` field is empty (so the build runs from repo root, not a subdirectory).
- **GitHub Actions workflow at `.github/workflows/dashboard.yml`** is unrelated to Cloudflare and can be left in place; it would only run if GitHub Pages were enabled (which is gated on repo visibility / plan, separate from Cloudflare).

## Cost

Free tier covers what we need: 500 builds/month, unlimited bandwidth and requests on the free plan.

## § Live data setup (spec 0160)

The dashboard fetches live data from a Cloudflare Pages Function at `/api/data`, which reads spec frontmatter, draft frontmatter, handoff frontmatter, and per-spec events directly from this repo via the GitHub Contents API. **This is the path that makes the dashboard reflect the repo within ~15s instead of the ~2–5 minute rebuild lag.**

Two one-time steps:

### 1. Create a GitHub fine-grained PAT

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. **Token name:** `dr-dashboard-pages-function`.
3. **Resource owner:** `Lexiz` (so the token can access this repo).
4. **Repository access:** **Only select repositories** → pick `Lexiz/dual-research`.
5. **Permissions** → **Repository permissions** → set **Contents** to **Read-only**. Leave all others as **No access**.
6. **Expiration:** pick the longest your security policy allows (1 year max). Calendar a renewal.
7. **Generate token** → **copy the token immediately** (you won't see it again).

### 2. Add the token to Cloudflare Pages

1. Cloudflare Pages → your project (`dr-dashboard`) → **Settings** → **Environment variables**.
2. **Add variable** → name `GITHUB_TOKEN`, value `<paste>`, type **Encrypted**.
3. **Scope:** both **Production** and **Preview**.
4. Save.

After both steps, the next push to `main` rebuilds the dashboard under shell mode and the Function starts serving live data immediately.

## Local Function dev (optional)

If you want to test the Function before pushing:

```bash
# Install wrangler globally (or use npx):
npm install -g wrangler   # or skip and use `npx wrangler …` below

# Put the same token in a gitignored .dev.vars at repo root:
echo "GITHUB_TOKEN=ghp_xxxxxxxxxxxxx" > .dev.vars

# Build the shell-only dashboard, then run wrangler pointing at dist/:
uv run python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out dist --shell-only
npx wrangler pages dev dist
```

Open the URL wrangler prints. The dashboard should populate from `http://localhost:8788/api/data`. `wrangler pages deployment tail` streams Function logs.

`.dev.vars` is gitignored (`.gitignore` at repo root). Never commit it.

## Live data troubleshooting

- **Dashboard shows a `stale` chip and old data:** the Function is returning an error. Open browser devtools → Network → look at the `/api/data` response. If it's 502 with `GITHUB_TOKEN env var not configured`, finish § Live data setup step 2. If it's 502 with `GitHub 401`, the PAT is expired or revoked — generate a new one.
- **GitHub API rate-limit errors (403 / "API rate limit exceeded"):** the Function makes ~30 API calls per cache miss; with a 15s `max-age` that's well under the 5000/hour fine-grained PAT limit, but a flood of misses (e.g. cache invalidation bug) could hit it. Wait an hour or wait for the next push (forces a Cloudflare rebuild, which warms the cache).
- **`stale` chip is visible but `/api/data` returns 200 in devtools:** the bootstrap script's `localStorage` cache may be sticky. Hard refresh (⌘⇧R) clears it.
