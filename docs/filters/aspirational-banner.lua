-- aspirational-banner.lua
--
-- Quarto Lua filter. On any page whose YAML frontmatter declares
-- `aspirational: true`, prepends a "canonically declared, not yet
-- fully adopted" callout banner to the top of the rendered output.
--
-- Single source of truth for the banner text: the `banner_md` heredoc
-- below. Edit once, applies to every page that carries the flag.
--
-- Registered in docs/_quarto.yml under format.html.filters.
--
-- To apply on a page:
--   ---
--   title: "..."
--   aspirational: true        # <-- this line, anywhere in frontmatter
--   ---
--
-- To remove the banner when a program graduates:
--   - Change to `aspirational: false`, or
--   - Delete the line entirely
--
-- Removal policy: a page drops the banner once the program or
-- capability it describes is in routine operational use with green CI,
-- documented evidence, and at least one reference deployment.

local banner_md = [[
::: {.callout-warning}
## Aspirational — canonically declared, not yet fully adopted

This page describes a program, process, or capability that is part of
the UIAO canon but **not yet fully adopted or operationally tested at
scale.** The specification is authoritative and governed by the
canon-change protocol; the operational instantiation is under
development.

**What this means for you as a reader:**

- **Readable now** — the design decisions, responsibilities, and acceptance criteria are stable enough to reference in planning, training, and agency conversations.
- **Not yet battle-tested** — real-world behavior, edge cases, and tool integrations may differ from the prose here as the substrate matures.
- **Changes are governed** — modifications follow the canon-change protocol in [`CONTRIBUTING.md`](https://github.com/WhalerMike/uiao/blob/main/CONTRIBUTING.md) with ADR-anchored decisions for doctrinal changes.

Track current adoption state on the [Substrate Status](https://whalermike.github.io/uiao/docs/substrate-status.html) page. The banner is removed from a page once the program or capability it describes is in routine operational use with green CI, documented evidence, and at least one reference deployment.
:::
]]

local function is_truthy(val)
  if val == nil then return false end
  local s = pandoc.utils.stringify(val):lower()
  return s == "true" or s == "yes" or s == "1"
end

function Pandoc(doc)
  if not is_truthy(doc.meta.aspirational) then
    return doc
  end
  local banner_blocks = pandoc.read(banner_md, "markdown").blocks
  local new_blocks = {}
  for _, b in ipairs(banner_blocks) do
    table.insert(new_blocks, b)
  end
  for _, b in ipairs(doc.blocks) do
    table.insert(new_blocks, b)
  end
  doc.blocks = new_blocks
  return doc
end
