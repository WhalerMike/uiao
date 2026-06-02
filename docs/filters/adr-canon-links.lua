-- adr-canon-links.lua
--
-- Quarto/pandoc Lua filter. HTML output only, ADR wrapper pages only.
--
-- Each published ADR page (docs/adr/adr-NNN-*.qmd) is a thin wrapper that
-- embeds the canonical ADR source verbatim via Quarto's `{{< include >}}`
-- shortcode (see scripts/generate_adr_qmd_wrappers.py). The canon source
-- lives at src/uiao/canon/adr/ and authors its relative links RELATIVE TO
-- THAT directory and to SOURCE extensions (.md / .qmd / .yml / .py …) — which
-- is correct for browsing the repo on GitHub and is what link-check validates
-- on disk. Quarto does NOT rewrite link paths or extensions for content pulled
-- in through `{{< include >}}`, so every relative link in the canon body would
-- otherwise pass through verbatim and 404 on the published site (wrong depth,
-- a non-existent `docs/` site prefix, and a source extension where the page is
-- `.html`).
--
-- This filter rewrites those relative links at render time, by ONE rule:
-- resolve each relative target against the canon dir `src/uiao/canon/adr/`
-- (or against the repo root when the target is written repo-root-relative,
-- e.g. `docs/…`), yielding a repo path R, then:
--
--   * R is a sibling ADR (has a generated wrapper)  -> adr-NNN-*.html
--   * R is a rendered docs page (docs/**/*.qmd)      -> ../<path>.html
--   * everything else (canon source, schemas, scripts, root files, docs
--     artifacts that do not render)                  -> the authoritative
--       GitHub source: https://github.com/WhalerMike/uiao/blob/main/<R>
--
-- The GitHub-blob fallback is the repo's established convention for linking
-- rendered docs to files that do not publish to the site (see docs/about/*,
-- adr-064); lychee already excludes `github.com/WhalerMike/uiao/blob/` (#757).
--
-- Registered project-wide in docs/_quarto.yml (`filters:`). It is a no-op for
-- every non-HTML format and for every input file that is not an ADR wrapper,
-- so applying it project-wide is safe.

if not (FORMAT and FORMAT:match("html")) then
  return {}
end

local GH_BLOB = "https://github.com/WhalerMike/uiao/blob/main/"

-- canon ADR source directory, as repo-root-relative segments
local BASE = { "src", "uiao", "canon", "adr" }

-- ADRs that intentionally have NO generated wrapper (ADR-068 exclusions in
-- generate_adr_qmd_wrappers.py). References to these fall through to GitHub.
local NO_WRAPPER = {
  ["adr-000-adr-process"] = true,
  ["adr-review-protocol"] = true,
}

-- Top-level repo directories. A target whose first segment is one of these
-- (and that is not written with a leading ./ or ../) is treated as
-- repo-root-relative rather than canon-dir-relative.
local ROOT_DIRS = {
  docs = true, src = true, scripts = true, tools = true,
  inbox = true, tests = true,
}

-- Only act on ADR wrapper pages. When `quarto` is unavailable (e.g. a bare
-- pandoc unit test) we do not gate, so the rewrite logic stays testable.
local function in_adr_page()
  if quarto and quarto.doc and quarto.doc.input_file then
    return quarto.doc.input_file:match("adr[/\\]adr%-%d%d%d") ~= nil
  end
  return true
end

local function split(s)
  local t = {}
  for seg in s:gmatch("[^/]+") do
    t[#t + 1] = seg
  end
  return t
end

-- Resolve a relative path to a repo-root-relative path (no leading slash).
local function normalize(path)
  local segs = split(path)
  local stack
  if segs[1] and ROOT_DIRS[segs[1]] then
    stack = {}
  else
    stack = { BASE[1], BASE[2], BASE[3], BASE[4] }
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

local function rewrite_target(target)
  -- Leave absolute URLs, protocol-relative, bare anchors, and mailto alone.
  if target:match("^%a[%w+.-]*:") or target:match("^#") or target:match("^//") then
    return nil
  end

  -- Split off a #fragment or ?query so it survives the rewrite.
  local path, suffix = target:match("^([^#?]*)([#?].*)$")
  if not path then
    path, suffix = target, ""
  end
  if path == "" then
    return nil
  end

  local R = normalize(path)

  -- Sibling ADR with a generated wrapper -> same-dir .html
  local name = R:match("^src/uiao/canon/adr/(adr%-%d+[^/]*)%.%w+$")
  if name and not NO_WRAPPER[name] then
    return name .. ".html" .. suffix
  end

  -- Rendered docs page (.qmd publishes to .html, site rooted at docs/)
  local rest = R:match("^docs/(.+)%.qmd$")
  if rest then
    return "../" .. rest .. ".html" .. suffix
  end

  -- Anything else: link to the authoritative source on GitHub.
  return GH_BLOB .. R .. suffix
end

function Link(el)
  if not in_adr_page() then
    return nil
  end
  local nt = rewrite_target(el.target)
  if nt then
    el.target = nt
  end
  return el
end
