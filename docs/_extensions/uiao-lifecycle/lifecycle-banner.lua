-- docs/_extensions/uiao-lifecycle/lifecycle-banner.lua
--
-- Quarto shortcode that renders a page-lifecycle banner from frontmatter
-- per ADR-082 (Status Label Lifecycle Policy). Replaces hand-authored
-- callout-warning blocks with a rule-driven banner read from:
--
--   lifecycle: aspirational | adopted | superseded | deprecated
--   tiers_adopted: [1, 3, 4]
--   superseded_by: path/to/successor.qmd
--   deprecated_replacement: path/to/replacement.qmd
--
-- Usage in any .qmd page that has lifecycle: frontmatter:
--
--   {{< lifecycle-banner >}}
--
-- Pages without `lifecycle:` produce no banner (empty output).

-- ADR-076 tier names (5-tier conformance model).
local TIER_NAMES = {
  [1] = "Passive Observation",
  [2] = "Transformative Authoring",
  [3] = "Active Substrate",
  [4] = "Active Services",
  [5] = "Embedded Libraries",
}

local function stringify_or_empty(value)
  if value == nil then
    return ""
  end
  return pandoc.utils.stringify(value)
end

local function tiers_adopted_label(meta)
  -- meta.tiers_adopted is a Pandoc MetaList; iterate and produce
  -- a human-readable comma-separated label like:
  --   "Tier 1 (Passive Observation), Tier 3 (Active Substrate)"
  if meta.tiers_adopted == nil then
    return ""
  end
  local labels = {}
  for _, tier_meta in ipairs(meta.tiers_adopted) do
    local tier_str = pandoc.utils.stringify(tier_meta)
    local tier_num = tonumber(tier_str)
    if tier_num ~= nil and TIER_NAMES[tier_num] ~= nil then
      table.insert(
        labels,
        "Tier " .. tier_num .. " (" .. TIER_NAMES[tier_num] .. ")"
      )
    else
      table.insert(labels, "Tier " .. tier_str)
    end
  end
  return table.concat(labels, ", ")
end

return {
  ["lifecycle-banner"] = function(args, kwargs, meta)
    local lifecycle = stringify_or_empty(meta.lifecycle)
    if lifecycle == "" then
      -- No lifecycle field declared; emit nothing.
      return pandoc.Null()
    end

    local markdown

    if lifecycle == "aspirational" then
      markdown = table.concat({
        "::: {.callout-warning}",
        "## Aspirational — canonically declared, not yet fully adopted",
        "",
        "This page describes canonical intent that is not yet operationally adopted at any UIAO conformance tier. See [ADR-082](/uiao/adr/adr-082-status-label-lifecycle-policy.html) for the lifecycle policy and the [Conformance page](/uiao/conformance/) for the tier model.",
        ":::",
        "",
      }, "\n")

    elseif lifecycle == "adopted" then
      local tier_label = tiers_adopted_label(meta)
      local body
      if tier_label ~= "" then
        body = "This page is operationally adopted at: **" .. tier_label .. "**."
      else
        body = "This page is marked adopted but no tiers were declared. See `scripts/scan_lifecycle_consistency.py` for the validation rule."
      end
      markdown = table.concat({
        "::: {.callout-note}",
        "## Adopted",
        "",
        body,
        ":::",
        "",
      }, "\n")

    elseif lifecycle == "superseded" then
      local successor = stringify_or_empty(meta.superseded_by)
      local body
      if successor ~= "" then
        body = "This page is superseded. See: [`" .. successor .. "`](/uiao/" .. successor .. ")"
      else
        body = "This page is superseded. No successor link declared — see `scripts/scan_lifecycle_consistency.py` for the validation rule."
      end
      markdown = table.concat({
        "::: {.callout-important}",
        "## Superseded",
        "",
        body,
        ":::",
        "",
      }, "\n")

    elseif lifecycle == "deprecated" then
      local replacement = stringify_or_empty(meta.deprecated_replacement)
      local body
      if replacement ~= "" then
        body = "This page is deprecated. See: [`" .. replacement .. "`](/uiao/" .. replacement .. ")"
      else
        body = "This page is deprecated. No replacement was declared."
      end
      markdown = table.concat({
        "::: {.callout-warning}",
        "## Deprecated",
        "",
        body,
        ":::",
        "",
      }, "\n")

    else
      -- Unknown lifecycle value — emit a visible warning so authors notice
      -- (the scanner will also flag this as an error).
      markdown = table.concat({
        "::: {.callout-important}",
        "## Lifecycle field has unrecognized value: `" .. lifecycle .. "`",
        "",
        "Expected one of: `aspirational`, `adopted`, `superseded`, `deprecated`. See [ADR-082](/uiao/adr/adr-082-status-label-lifecycle-policy.html).",
        ":::",
        "",
      }, "\n")
    end

    return pandoc.RawBlock("markdown", markdown)
  end
}
