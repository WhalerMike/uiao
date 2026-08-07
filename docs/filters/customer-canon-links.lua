-- customer-canon-links.lua
--
-- Quarto/pandoc Lua filter. HTML output only. Applies to every published docs
-- page EXCEPT ADR wrapper pages (docs/adr/adr-NNN-*), which are owned by the
-- sibling adr-canon-links.lua — the two filters stay mutually exclusive so they
-- never both rewrite the same link.
--
-- Sibling of adr-canon-links.lua. Docs pages (e.g. the B.1.x boundary set, the
-- canon and schema reference pages, findings, and narratives) author
-- cross-references to canon SOURCE files and to other site pages using
-- on-disk-relative paths and source extensions (.qmd / .md / .yaml) — correct
-- for browsing the repo on GitHub and for the on-disk link-check, but they 404
-- on the published site because Quarto does not rewrite most of them (only
-- simple same-dir .qmd links are rewritten natively). Repo-root paths injected
-- via `{{< meta parent-leaf >}}` / `{{< meta canon-reference >}}` etc. are
-- likewise wrong on the site.
--
-- This filter rewrites those links at render time. Unlike the ADR wrappers
-- (always at docs/adr/, depth 1), docs pages sit at VARYING depths and author
-- links relative to the PAGE's own directory, so this filter:
--   * resolves each relative target against the page dir (from
--     quarto.doc.input_file), or against the repo root when written
--     repo-root-relative (docs/…, src/…, inbox/…), yielding a repo path R; then
--   * emits an ABSOLUTE site/source URL (depth-independent), by ONE rule:
--       R is a rendered docs page (docs/**.qmd|.html)  -> SITE/<rest>.html
--       R is a canon ADR source (src/uiao/canon/adr/…) -> SITE/adr/<name>.html
--       R under src|inbox|scripts|tools|tests          -> GitHub blob source
--       R is a docs asset or anything else             -> left unchanged
--
-- GitHub-blob is the repo's convention for files that do not publish to the
-- site; lychee already excludes github.com/WhalerMike/uiao/blob/ (#757). The
-- on-disk source links are untouched, so the on-disk link-check still passes;
-- only the rendered HTML is rewritten.
--
-- Registered project-wide in docs/_quarto.yml (`filters:`). No-op for every
-- non-HTML format and for every ADR wrapper page (those are handled by
-- adr-canon-links.lua), so applying it project-wide is safe and the two filters
-- never both act on the same page.

if not (FORMAT and FORMAT:match("html")) then
  return {}
end

local SITE = "https://whalermike.github.io/uiao/"
local GH_BLOB = "https://github.com/WhalerMike/uiao/blob/main/"

-- Repo dirs whose source does NOT publish to the site -> GitHub blob.
local SOURCE_DIRS = { src = true, inbox = true, scripts = true, tools = true, tests = true }

-- Page directory (repo-root-relative segments, e.g. {docs, customer-documents,
-- orgcomp-series, boundary}) that on-disk-relative links resolve
-- against. From quarto.doc.input_file in a real render; a fixed customer-doc
-- depth under bare pandoc so the rewrite logic stays unit-testable.
local TEST_SEGS = { "docs", "customer-documents", "orgcomp-series", "boundary" }

local function page_dir_segs()
  if quarto and quarto.doc and quarto.doc.input_file then
    local f = quarto.doc.input_file:gsub("\\", "/")
    -- absolute or repo-relative (…/docs/x/y.qmd) | project-relative (x/y.qmd)
    local after = f:match(".*/docs/(.+)$") or f:match("^docs/(.+)$") or f
    local segs = { "docs" }
    for s in after:gmatch("[^/]+") do
      segs[#segs + 1] = s
    end
    table.remove(segs) -- drop the filename, keep dir segments
    return segs
  end
  if not quarto then
    return TEST_SEGS -- bare-pandoc unit test
  end
  return nil -- real render but no input_file: signal "do not rewrite"
end

-- Act on every docs page EXCEPT ADR wrapper pages (docs/adr/adr-NNN-*), which
-- are owned by adr-canon-links.lua. Keeping the two gates disjoint means a link
-- is only ever rewritten by one filter.
local function should_process()
  if quarto and quarto.doc and quarto.doc.input_file then
    return quarto.doc.input_file:gsub("\\", "/"):match("adr/adr%-%d%d%d") == nil
  end
  return true -- bare pandoc: don't gate, so the logic is testable
end

local function split(s)
  local t = {}
  for seg in s:gmatch("[^/]+") do
    t[#t + 1] = seg
  end
  return t
end

-- Resolve a link target to a repo-root-relative path against the page dir
-- (or the repo root, when the target is written repo-root-relative).
local function normalize(path, page_segs)
  local segs = split(path)
  local stack = {}
  if not (segs[1] and (segs[1] == "docs" or SOURCE_DIRS[segs[1]])) then
    for _, s in ipairs(page_segs) do
      stack[#stack + 1] = s
    end
  end
  for _, seg in ipairs(segs) do
    if seg == "." then -- current dir, skip
    elseif seg == ".." then
      if #stack > 0 then
        table.remove(stack)
      end
    else
      stack[#stack + 1] = seg
    end
  end
  return table.concat(stack, "/")
end

local function rewrite_target(target, page_segs)
  -- Leave absolute URLs, protocol-relative, bare anchors, and mailto alone.
  if target:match("^%a[%w+.-]*:") or target:match("^#") or target:match("^//") then
    return nil
  end

  local path, suffix = target:match("^([^#?]*)([#?].*)$")
  if not path then
    path, suffix = target, ""
  end
  if path == "" then
    return nil
  end

  local R = normalize(path, page_segs)

  -- Rendered docs page (.qmd / already-rewritten .html publishes to .html).
  local rest = R:match("^docs/(.+)%.qmd$") or R:match("^docs/(.+)%.html$")
  if rest then
    return SITE .. rest .. ".html" .. suffix
  end

  -- Canon ADR source -> its published wrapper page at /adr/<name>.html.
  local adr = R:match("^src/uiao/canon/adr/(adr%-%d+[^/]*)%.%w+$")
  if adr then
    return SITE .. "adr/" .. adr .. ".html" .. suffix
  end

  -- Non-publishing source under a known repo dir -> authoritative GitHub source.
  local first = R:match("^([^/]+)/")
  if first and SOURCE_DIRS[first] then
    return GH_BLOB .. R .. suffix
  end

  -- docs assets and anything else: leave the link untouched.
  return nil
end

function Link(el)
  if not should_process() then
    return nil
  end
  local page_segs = page_dir_segs()
  if not page_segs then
    return nil
  end
  local nt = rewrite_target(el.target, page_segs)
  if nt then
    el.target = nt
  end
  return el
end
