# whalermike.github.io — vanity-URL redirect

Tiny static site whose only job is to forward any request hitting
`https://whalermike.github.io/...` to the project-pages site at
`https://whalermike.github.io/uiao/...`, preserving the path.

## Why

The canonical UIAO docs are served from the project-pages URL
`https://whalermike.github.io/uiao/`. Anything that drops the `/uiao/`
prefix (typos, autocomplete, old links) hits the GitHub Pages 404.
This site catches those requests and forwards them.

## How it works

GitHub Pages serves user sites from a repo named exactly
`<user>.github.io`. The repo root becomes the site root.

- `index.html` — handles requests to `/` (root). Redirects to `/uiao/`.
- `404.html` — GitHub Pages serves this for any path that doesn't
  resolve to a file. The page reads `window.location.pathname` and
  client-side redirects to `https://whalermike.github.io/uiao<path>`.

Both pages set `<meta http-equiv="refresh">` as a no-JS fallback, but
the JS path-preserving redirect is the primary mechanism.

## Deploy

```bash
# From a clean directory outside this worktree:
gh repo create WhalerMike/whalermike.github.io --public \
  --description "Vanity-URL redirect to whalermike.github.io/uiao/"
git clone https://github.com/WhalerMike/whalermike.github.io.git
cp <this-dir>/{index.html,404.html,README.md} whalermike.github.io/
cd whalermike.github.io
git add .
git commit -m "init: path-preserving redirect to /uiao/"
git push -u origin main
```

Then in repo Settings → Pages → Source = "Deploy from a branch" →
Branch = `main` / root.

## Smoke test

Once deployed (allow 1–2 min for Pages build):

```bash
# Root → /uiao/
curl -sLo /dev/null -w "%{url_effective}\n" https://whalermike.github.io/

# Arbitrary path → /uiao/<path>
curl -sLo /dev/null -w "%{url_effective}\n" \
  https://whalermike.github.io/docs/substrate-status.html
```

Both should resolve under `/uiao/`.

## Caveats

- The redirect is **client-side**. Crawlers that don't execute JS will
  see the `<meta refresh>` fallback (which sends them to `/uiao/` root,
  not the path-preserved target). Acceptable for a vanity redirect;
  the canonical site at `/uiao/` is the SEO anchor (`<link rel=canonical>`
  set in `_seo-head.html`).
- This sits **outside** the `WhalerMike/uiao` repo. The CI in this
  repo does not deploy to it.
