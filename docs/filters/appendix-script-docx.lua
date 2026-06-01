-- appendix-script-docx.lua
--
-- Quarto/pandoc Lua filter. DOCX output only. For every code block that
-- sits inside a `::: {.appendix-script}` fenced div, re-emit the code as a
-- single raw-OOXML paragraph set in very small monospace type (Consolas
-- 7pt), so the long reference scripts collected in the Book_07b / Book_07a
-- appendices render compactly in the per-book .docx bundles.
--
-- The HTML site already shrinks the same blocks via the `.appendix-script`
-- CSS rule in docs/styles.css; this filter is the DOCX-only counterpart,
-- because pandoc's docx writer applies the reference doc's "Source Code"
-- style (Consolas 9pt) to every CodeBlock and a fenced-div class alone
-- cannot override the code font in DOCX.
--
-- Registered project-wide in docs/_quarto.yml (`filters:`). It is a no-op
-- for every non-docx format and for every code block NOT inside an
-- `.appendix-script` div, so applying it project-wide is safe.
--
-- Font size: <w:sz> is in half-points, so 14 = 7pt. Tune here if needed.

if not (FORMAT and FORMAT:match('docx')) then
  return {}
end

local SZ = "14" -- half-points; 14 = 7pt (reference "Source Code" is 18 = 9pt)
local RPR = '<w:rPr>'
  .. '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
  .. '<w:sz w:val="' .. SZ .. '"/><w:szCs w:val="' .. SZ .. '"/>'
  .. '</w:rPr>'

local function esc(s)
  return (s:gsub('&', '&amp;'):gsub('<', '&lt;'):gsub('>', '&gt;'))
end

local function code_to_ooxml(code)
  -- Split into lines, preserving empty lines. One <w:p>, lines joined by
  -- <w:br/>, so the whole listing stays a single tight paragraph block.
  local lines = {}
  for line in (code .. '\n'):gmatch('(.-)\n') do
    lines[#lines + 1] = line
  end
  local runs = {}
  for i, line in ipairs(lines) do
    if i > 1 then
      runs[#runs + 1] = '<w:r>' .. RPR .. '<w:br/></w:r>'
    end
    runs[#runs + 1] = '<w:r>' .. RPR
      .. '<w:t xml:space="preserve">' .. esc(line) .. '</w:t></w:r>'
  end
  local ppr = '<w:pPr><w:spacing w:before="0" w:after="0" '
    .. 'w:line="200" w:lineRule="auto"/></w:pPr>'
  return '<w:p>' .. ppr .. table.concat(runs) .. '</w:p>'
end

function Div(el)
  if el.classes:includes('appendix-script') then
    local out = {}
    for _, b in ipairs(el.content) do
      if b.t == 'CodeBlock' then
        out[#out + 1] = pandoc.RawBlock('openxml', code_to_ooxml(b.text))
      else
        out[#out + 1] = b
      end
    end
    return out
  end
end
