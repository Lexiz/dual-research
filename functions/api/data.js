/**
 * Cloudflare Pages Function: GET /api/data
 *
 * Spec 0160 — serves the dashboard's live data to dashboard-bootstrap.js.
 * Reads spec frontmatter, draft frontmatter, handoff frontmatter, and
 * per-spec event sidecars directly from the Lexiz/dual-research repo via
 * GitHub's APIs, parses YAML and JSONL on the fly, and returns a single
 * JSON payload.
 *
 * Spec 0174 — blob fetching uses a single batched GraphQL POST (per file as
 * an aliased `Repository.object(expression: "<ref>:<path>")`) instead of one
 * REST `/git/blobs/<sha>` call per file. This drops subrequest count from
 * `1 + N` (tree + per-file) to ~2 (tree + GraphQL), keeping the Function
 * well under Cloudflare's 50-subrequest free-tier limit even as the repo
 * grows past 100s of files.
 *
 * Caching: response is cached at the edge for 15s (`max-age`) with a 60s
 * `stale-while-revalidate` window.
 *
 * Auth: a fine-grained PAT scoped to `Contents: Read-only` on this repo is
 * read from the `GITHUB_TOKEN` env var. The same PAT works for both REST and
 * GraphQL.
 *
 * Response shape:
 *   {
 *     generated_at:  ISO 8601 string,
 *     specs:         Array<{ number, slug, title, type, status, ... }>,
 *     drafts:        Array<{ draft_id, slug, title, type, created, status }>,
 *     handoffs:      Array<{ spec, date, version, pr }>,
 *     events:        Record<spec_number, Array<{ ts, step, data }>>,
 *   }
 *
 * Errors return `{ error: <message>, generated_at: null }` with status 502;
 * the client falls back to its localStorage cache.
 */

const REPO_OWNER = 'Lexiz';
const REPO_NAME = 'dual-research';
const REF = 'main';
const CACHE_MAX_AGE = 15; // seconds
const CACHE_SWR = 60;
// GitHub's GraphQL endpoint accepts large queries, but to stay well under
// the per-query field limit (~500) we batch in chunks of GRAPHQL_BATCH_SIZE
// aliased fields. At today's repo size (~160 files) this is one batch; at
// 1000 files it's three.
const GRAPHQL_BATCH_SIZE = 400;

export async function onRequest(context) {
  const { env, request } = context;
  const cache = caches.default;

  // Edge cache lookup. Cloudflare keys on the full Request, but for a GET
  // with no varying headers this is effectively keyed on the URL.
  const cached = await cache.match(request);
  if (cached) return cached;

  if (!env.GITHUB_TOKEN) {
    return errorResponse(
      502,
      'GITHUB_TOKEN env var not configured — set it in Pages → Settings → Environment variables.',
    );
  }

  try {
    const data = await buildPayload(env.GITHUB_TOKEN);
    const body = JSON.stringify(data);
    const response = new Response(body, {
      status: 200,
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': `public, max-age=${CACHE_MAX_AGE}, stale-while-revalidate=${CACHE_SWR}`,
        'access-control-allow-origin': '*',
      },
    });
    // Cache the response for subsequent edge hits.
    context.waitUntil(cache.put(request, response.clone()));
    return response;
  } catch (err) {
    return errorResponse(502, err && err.message ? err.message : 'fetch failed');
  }
}

function errorResponse(status, message) {
  return new Response(
    JSON.stringify({ error: message, generated_at: null }),
    {
      status,
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': 'no-store',
        'access-control-allow-origin': '*',
      },
    },
  );
}

async function buildPayload(token) {
  // Single tree call gives us the full repo file listing with per-path SHAs.
  // Recursive flag walks the whole tree in one request.
  const tree = await ghJson(`/repos/${REPO_OWNER}/${REPO_NAME}/git/trees/${REF}?recursive=1`, token);
  if (!tree.tree) throw new Error('trees response missing `tree` array');

  const specBlobs = [];
  const draftBlobs = [];
  const handoffBlobs = [];
  const eventBlobs = [];

  for (const entry of tree.tree) {
    if (entry.type !== 'blob') continue;
    const p = entry.path;
    if (/^specs\/\d{4}-[^/]+\.md$/.test(p)) specBlobs.push(entry);
    else if (/^specs\/drafts\/draft-\d{3}-[^/]+\.md$/.test(p)) draftBlobs.push(entry);
    else if (/^handoffs\/\d{4}-\d{2}-\d{2}-spec-\d{4}-[^/]+\.md$/.test(p)) handoffBlobs.push(entry);
    else if (/^dashboard\/events\/\d{4}\.jsonl$/.test(p)) eventBlobs.push(entry);
  }

  // Concatenate in a stable order so the alias-index ↔ path mapping is
  // deterministic across batches. Categories are reconstructed at parse
  // time from path regexes (same as the filtering above).
  const allBlobs = [...specBlobs, ...draftBlobs, ...handoffBlobs, ...eventBlobs];
  const texts = await fetchAllBlobTextsViaGraphQL(allBlobs, token);

  const specRows = [];
  const draftRows = [];
  const handoffRows = [];
  const eventBuckets = [];

  for (let i = 0; i < allBlobs.length; i++) {
    const entry = allBlobs[i];
    const text = texts[i] || '';
    const p = entry.path;
    if (/^specs\/\d{4}-[^/]+\.md$/.test(p)) {
      specRows.push(parseFrontmatter(text, p));
    } else if (/^specs\/drafts\/draft-\d{3}-[^/]+\.md$/.test(p)) {
      draftRows.push(parseFrontmatter(text, p));
    } else if (/^handoffs\/\d{4}-\d{2}-\d{2}-spec-\d{4}-[^/]+\.md$/.test(p)) {
      handoffRows.push(parseFrontmatter(text, p));
    } else if (/^dashboard\/events\/\d{4}\.jsonl$/.test(p)) {
      eventBuckets.push({
        number: p.match(/(\d{4})\.jsonl$/)[1],
        events: text.split('\n').filter(Boolean).map(safeJsonParse).filter(Boolean),
      });
    }
  }

  const specs = specRows
    .filter((row) => row && row.fm)
    .map((row) => ({
      number: extractNumber(row.path, /^specs\/(\d{4})-/),
      ...row.fm,
    }))
    .filter((s) => s.number);

  const drafts = draftRows
    .filter((row) => row && row.fm)
    .map((row) => ({
      draft_id: extractNumber(row.path, /^specs\/drafts\/draft-(\d{3})-/),
      ...row.fm,
    }))
    .filter((d) => d.draft_id);

  const handoffs = handoffRows
    .filter((row) => row && row.fm)
    .map((row) => row.fm);

  const events = {};
  for (const bucket of eventBuckets) {
    events[bucket.number] = bucket.events;
  }

  return {
    generated_at: new Date().toISOString(),
    specs,
    drafts,
    handoffs,
    events,
  };
}

/**
 * Fetch the text content of every blob in `entries` using GitHub's GraphQL
 * API. Each batch is a single POST with up to GRAPHQL_BATCH_SIZE aliased
 * `Repository.object(expression: "<ref>:<path>")` fields. Returns an array
 * of texts aligned with `entries` (missing / binary blobs become `''`).
 */
async function fetchAllBlobTextsViaGraphQL(entries, token) {
  const texts = new Array(entries.length).fill('');
  if (entries.length === 0) return texts;

  for (let start = 0; start < entries.length; start += GRAPHQL_BATCH_SIZE) {
    const chunk = entries.slice(start, start + GRAPHQL_BATCH_SIZE);
    const fields = chunk.map((entry, idx) => {
      const expr = `${REF}:${entry.path}`;
      // Local alias is just the in-chunk index. We track positions
      // separately when copying results back into `texts`.
      return `f${idx}: object(expression: ${JSON.stringify(expr)}) { ... on Blob { text isBinary } }`;
    }).join('\n      ');

    const query = `query DashboardBundle {
  repository(owner: ${JSON.stringify(REPO_OWNER)}, name: ${JSON.stringify(REPO_NAME)}) {
      ${fields}
  }
}`;

    const data = await ghGraphQL(query, token);
    const repo = data && data.repository;
    if (!repo) throw new Error('GraphQL response missing `repository`');

    for (let idx = 0; idx < chunk.length; idx++) {
      const node = repo[`f${idx}`];
      if (!node || node.isBinary || typeof node.text !== 'string') {
        // Missing or binary blob — leave as ''.
        continue;
      }
      texts[start + idx] = node.text;
    }
  }

  return texts;
}

async function ghJson(path, token) {
  const url = 'https://api.github.com' + path;
  const r = await fetch(url, {
    headers: {
      authorization: `Bearer ${token}`,
      accept: 'application/vnd.github+json',
      'x-github-api-version': '2022-11-28',
      'user-agent': 'dual-research-pages-function/1.0',
    },
  });
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    throw new Error(`GitHub ${r.status} on ${path}: ${body.slice(0, 200)}`);
  }
  return r.json();
}

async function ghGraphQL(query, token) {
  const r = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      accept: 'application/vnd.github+json',
      'content-type': 'application/json',
      'user-agent': 'dual-research-pages-function/1.0',
    },
    body: JSON.stringify({ query }),
  });
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    throw new Error(`GitHub graphql ${r.status}: ${body.slice(0, 200)}`);
  }
  const json = await r.json();
  if (json.errors && json.errors.length) {
    const first = json.errors[0];
    throw new Error(`GitHub graphql error: ${first.message || JSON.stringify(first)}`);
  }
  return json.data;
}

function extractNumber(path, regex) {
  const m = path.match(regex);
  return m ? m[1] : '';
}

function safeJsonParse(line) {
  try { return JSON.parse(line); } catch (e) { return null; }
}

/**
 * Minimal YAML frontmatter parser tuned for the spec/draft/handoff schema.
 * Handles: simple `key: value` lines, quoted strings, ISO timestamps,
 * inline lists like `depends_on: ["0154"]`, and empty values.
 * Doesn't support nested mappings or YAML anchors — the schema doesn't use
 * them. Errors fall through silently and the row is skipped at the call site.
 */
function parseFrontmatter(text, path) {
  if (typeof text !== 'string') return { path, fm: null };
  const m = text.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!m) return { path, fm: null };
  const fm = {};
  const body = m[1];
  for (const rawLine of body.split('\n')) {
    const line = rawLine.replace(/#.*$/, '').trim();
    if (!line) continue;
    const colon = line.indexOf(':');
    if (colon <= 0) continue;
    const key = line.slice(0, colon).trim();
    let val = line.slice(colon + 1).trim();
    if (val === '' || val === '""' || val === "''") {
      fm[key] = '';
      continue;
    }
    if ((val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))) {
      fm[key] = val.slice(1, -1);
      continue;
    }
    if (val.startsWith('[') && val.endsWith(']')) {
      // Inline list — parse as JSON after normalising single quotes.
      try {
        fm[key] = JSON.parse(val.replace(/'/g, '"'));
      } catch (e) {
        fm[key] = [];
      }
      continue;
    }
    fm[key] = val;
  }
  return { path, fm };
}
