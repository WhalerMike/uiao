--[[ aan-callouts.lua — render AAN Quarto callout / banner divs as styled docx boxes.

Quarto's own callout rendering is unavailable under a bare Pandoc render, and
Pandoc's docx writer only paints paragraph shading + borders through NAMED
paragraph styles carried in the reference doc. This filter maps each AAN div
class to the matching style defined in aan-reference.docx (built by
build_aan_reference.py) via the `custom-style` attribute the docx writer honors.

Usage:
  pandoc book.qmd -f markdown -o book.docx \
    --reference-doc=aan-reference.docx --lua-filter=aan-callouts.lua --resource-path=.

Only affects the docx writer; for any other target the class-to-style mapping is
a harmless no-op attribute. ]]

local CLASS_TO_STYLE = {
  ["callout-warning"]   = "CalloutWarning",
  ["callout-important"] = "CalloutImportant",
  ["callout-note"]      = "CalloutNote",
  ["callout-tip"]       = "CalloutTip",
  ["callout-caution"]   = "CalloutCaution",
  ["exec-summary"]      = "ExecSummary",
  ["fouo-banner"]       = "FouoBanner",
}

function Div(el)
  for _, cls in ipairs(el.classes) do
    local style = CLASS_TO_STYLE[cls]
    if style then
      -- The docx writer applies a Div's custom-style to every paragraph inside it,
      -- giving each its shading/border/color so the whole box reads as one callout.
      el.attributes["custom-style"] = style
      return el
    end
  end
  return el
end
