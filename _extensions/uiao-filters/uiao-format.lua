--[[
UIAO Document Formatting Filter for Quarto/Pandoc

Applies UIAO-specific formatting:
1. Classification banners (CUI, FOUO, etc.) as header/footer
2. Document control metadata block
3. Table auto-numbering and consistent styling
4. Diagram caption formatting

Usage: Configured in _quarto.yml under filters.
Reads "classification" from document YAML frontmatter.
]]

-- Read classification from document metadata
local classification = nil

function Meta(meta)
  if meta.classification then
    classification = pandoc.utils.stringify(meta.classification)
  end
  return meta
end

-- Add classification banner to document body
function Pandoc(doc)
  if classification and classification ~= "" then
    local banner_text = string.upper(classification)

    if FORMAT:match("html") then
      local banner = pandoc.RawBlock("html",
        '<div class="classification-banner">' .. banner_text .. '</div>')
      table.insert(doc.blocks, 1, banner)
    elseif FORMAT:match("docx") then
      local banner = pandoc.Para({
        pandoc.Str("// " .. banner_text .. " //")
      })
      table.insert(doc.blocks, 1, banner)
    elseif FORMAT:match("latex") or FORMAT:match("pdf") then
      local header_cmd = pandoc.RawBlock("latex",
        "\\fancyhead[C]{\\textbf{" .. banner_text .. "}}")
      table.insert(doc.blocks, 1, header_cmd)
    end
  end
  return doc
end

-- Process tables: ensure consistent formatting
function Table(tbl)
  if FORMAT:match("html") then
    tbl.attr = tbl.attr or pandoc.Attr()
    tbl.classes = tbl.classes or {}
    table.insert(tbl.classes, "table")
    table.insert(tbl.classes, "table-striped")
    table.insert(tbl.classes, "table-hover")
  end
  return tbl
end

-- Process images/figures: ensure sizing attributes
function Image(img)
  if not img.attributes.width and not img.attributes.height then
    if img.src:match("mermaid") or img.src:match("graphviz") or img.src:match("diagram") then
      img.attributes.width = "90%"
    end
  end
  return img
end

-- Filter execution order matters
return {
  { Meta = Meta },
  { Pandoc = Pandoc },
  { Table = Table },
  { Image = Image },
}
