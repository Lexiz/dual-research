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
| **Build command** | `pip install pyyaml && python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out dist` |
| **Build output directory** | `dist` |
| **Root directory** | (leave blank — defaults to repo root) |

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
