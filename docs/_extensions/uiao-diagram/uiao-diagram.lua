-- uiao-diagram shortcode extension
--
-- Quarto shortcode variant for embedding UIAO diagrams.
-- Usage in .qmd files:
--
--   {{< uiao-diagram DIAG_010 >}}
--   {{< uiao-diagram DIAG_010 form_factor=nano >}}
--   {{< uiao-diagram DIAG_010 form_factor=full caption="Platform Overview" >}}
--
-- This shortcode is functionally equivalent to the HTML comment directive:
--   <!-- UIAO-DIAGRAM: DIAG_010 form_factor=full -->
--
-- but uses Quarto's native shortcode system for better IDE support and
-- rendering pipeline integration.
--
-- Boundary: GCC-Moderate · Classification: Controlled

local RENDERED_DIR = "../diagrams/rendered"
local DEFAULT_FORM = "full"

local function file_exists(path)
  local f = io.open(path, "r")
  if f then f:close() return true end
  return false
end

return {
  ["uiao-diagram"] = function(args, kwargs)
    -- First positional arg is the diagram ID
    local diagram_id = pandoc.utils.stringify(args[1] or ""):upper()
    if diagram_id == "" then
      return pandoc.Null()
    end

    local form_factor = pandoc.utils.stringify(kwargs["form_factor"] or DEFAULT_FORM):lower()
    local caption = pandoc.utils.stringify(kwargs["caption"] or "")

    if form_factor == "auto" then form_factor = "full" end

    local svg_path = RENDERED_DIR .. "/" .. form_factor .. "/" .. diagram_id .. ".svg"
    local exists = file_exists(svg_path)

    if caption == "" then caption = diagram_id end

    if exists then
      return pandoc.Figure(
        {pandoc.Plain({pandoc.Image(pandoc.Str(diagram_id), svg_path, caption)})},
        {pandoc.Str(caption)},
        pandoc.Attr(diagram_id:lower() .. "-fig", {"uiao-diagram-figure"}, {})
      )
    else
      -- Placeholder
      local html = string.format([[
<div class="uiao-diagram-placeholder" id="%s"
     style="border: 2px dashed #6b7280; border-radius: 8px; padding: 1.5em;
            text-align: center; background: #f9fafb; margin: 1em 0;">
  <p style="font-size: 0.9em; color: #6b7280; margin: 0;">
    <strong>📊 %s</strong><br/>
    <em>Diagram renders after CI merge to main.</em>
  </p>
</div>]], diagram_id:lower(), diagram_id)
      return pandoc.RawBlock("html", html)
    end
  end
}
