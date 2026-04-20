-- uiao-diagrams.lua
--
-- Quarto Lua filter (Option B). Resolves UIAO-DIAGRAM directives at
-- Quarto render time so published HTML/PDF output contains the correct
-- diagram SVG without any pre-processing step.
--
-- Directive syntax (in any .qmd or .md rendered by Quarto):
--
--   <!-- UIAO-DIAGRAM: DIAG_NNN form_factor=full|nano|auto -->
--
-- Or the shortcode variant (Quarto-native):
--
--   {{< uiao-diagram DIAG_NNN form_factor=full >}}
--
-- How it works:
--   1. Walks every RawBlock in the Pandoc AST looking for HTML comments
--      matching the UIAO-DIAGRAM pattern.
--   2. Resolves the diagram ID to a rendered SVG path relative to the
--      current document.
--   3. Replaces the comment with a Figure containing the SVG image.
--   4. If the SVG doesn't exist yet (pre-CI-render), emits a styled
--      placeholder div with the diagram ID and title from the registry.
--
-- Registration:
--   Add to docs/_quarto.yml under `filters:`:
--     filters:
--       - filters/aspirational-banner.lua
--       - filters/uiao-diagrams.lua          # <-- add this line
--
-- Boundary: GCC-Moderate · Classification: Controlled
--

-- ---------------------------------------------------------------------------
-- Configuration
-- ---------------------------------------------------------------------------

-- Paths relative to the docs/ directory (where _quarto.yml lives)
local RENDERED_DIR = "../diagrams/rendered"
local REGISTRY_PATH = "../diagrams/registry/diagram-registry.yaml"

-- Default form factor when not specified in the directive
local DEFAULT_FORM = "full"

-- Container width threshold for auto form-factor selection (pixels)
-- In practice, Quarto renders to HTML so we default to "full" for auto
local AUTO_FORM = "full"

-- ---------------------------------------------------------------------------
-- Registry loader (lightweight YAML parser for the flat registry)
-- ---------------------------------------------------------------------------

local registry_cache = nil

local function load_registry()
  if registry_cache then return registry_cache end

  registry_cache = {}

  -- Resolve path relative to the Quarto project root
  local reg_path = REGISTRY_PATH
  local f = io.open(reg_path, "r")
  if not f then
    -- Try from the filter's own directory
    local script_dir = debug.getinfo(1, "S").source:match("@?(.*/)") or "./"
    reg_path = script_dir .. "/" .. REGISTRY_PATH
    f = io.open(reg_path, "r")
  end
  if not f then
    io.stderr:write("uiao-diagrams.lua: WARNING — registry not found at "
                     .. REGISTRY_PATH .. "\n")
    return registry_cache
  end

  local content = f:read("*a")
  f:close()

  -- Minimal YAML extraction: pull diagram_id and title pairs
  -- Full YAML parsing would require a dependency; this covers the
  -- flat structure of diagram-registry.yaml
  for id, title in content:gmatch('diagram_id:%s*"?(DIAG_%d+)"?.-title:%s*"([^"]*)"') do
    registry_cache[id:upper()] = title
  end

  -- Fallback pattern without quotes
  for id, title in content:gmatch("diagram_id:%s*(DIAG_%d+).-title:%s*([^\n]+)") do
    local clean_id = id:upper()
    if not registry_cache[clean_id] then
      registry_cache[clean_id] = title:gsub("^%s+", ""):gsub("%s+$", ""):gsub('"', "")
    end
  end

  return registry_cache
end


-- ---------------------------------------------------------------------------
-- SVG path resolver
-- ---------------------------------------------------------------------------

local function file_exists(path)
  local f = io.open(path, "r")
  if f then
    f:close()
    return true
  end
  return false
end


local function resolve_svg(diagram_id, form_factor)
  local svg_path = RENDERED_DIR .. "/" .. form_factor .. "/" .. diagram_id .. ".svg"
  if file_exists(svg_path) then
    return svg_path, true
  end
  -- Return the expected path even if not yet rendered
  return svg_path, false
end


-- ---------------------------------------------------------------------------
-- Directive parser
-- ---------------------------------------------------------------------------

local DIRECTIVE_PATTERN =
  "<!%-%-[%s]*UIAO%-DIAGRAM:[%s]*(DIAG_%d+)"
  .. "([^%-]-)%-%->"

local function parse_directive(raw_text)
  local diagram_id, attrs = raw_text:match(DIRECTIVE_PATTERN)
  if not diagram_id then return nil end

  diagram_id = diagram_id:upper()

  -- Parse optional attributes
  local form_factor = attrs:match("form_factor%s*=%s*(%w+)") or DEFAULT_FORM
  local caption = attrs:match('caption%s*=%s*"([^"]*)"')

  if form_factor:lower() == "auto" then
    form_factor = AUTO_FORM
  end

  return {
    id = diagram_id,
    form_factor = form_factor:lower(),
    caption = caption,
  }
end


-- ---------------------------------------------------------------------------
-- Block builders
-- ---------------------------------------------------------------------------

local function build_figure(svg_path, diagram_id, title, caption, exists)
  local alt = diagram_id .. ": " .. (title or diagram_id)
  local cap = caption or alt

  if exists then
    -- Real image
    local img = pandoc.Image(pandoc.Str(alt), svg_path, cap)
    img.attr = pandoc.Attr(diagram_id:lower(), {"uiao-diagram"}, {})
    local fig = pandoc.Figure(
      {pandoc.Plain({img})},
      {pandoc.Str(cap)},
      pandoc.Attr(diagram_id:lower() .. "-fig", {"uiao-diagram-figure"}, {})
    )
    return fig
  else
    -- Placeholder — SVG not yet rendered
    local placeholder_html = string.format([[
<div class="uiao-diagram-placeholder" id="%s"
     style="border: 2px dashed #6b7280; border-radius: 8px; padding: 1.5em;
            text-align: center; background: #f9fafb; margin: 1em 0;">
  <p style="font-size: 0.9em; color: #6b7280; margin: 0;">
    <strong>📊 %s</strong><br/>
    %s<br/>
    <em style="font-size: 0.85em;">Diagram renders after CI merge to main.
    Run <code>python diagrams/scripts/render.py</code> for local preview.</em>
  </p>
</div>
]], diagram_id:lower(), diagram_id, title or "Untitled diagram")
    return pandoc.RawBlock("html", placeholder_html)
  end
end


-- ---------------------------------------------------------------------------
-- AST walker
-- ---------------------------------------------------------------------------

local processed_count = 0
local placeholder_count = 0

function RawBlock(el)
  if el.format ~= "html" then return nil end

  local directive = parse_directive(el.text)
  if not directive then return nil end

  -- Load registry for titles
  local reg = load_registry()
  local title = reg[directive.id] or directive.id

  -- Resolve SVG
  local svg_path, exists = resolve_svg(directive.id, directive.form_factor)

  -- Build replacement
  local figure = build_figure(svg_path, directive.id, title,
                               directive.caption, exists)

  processed_count = processed_count + 1
  if not exists then
    placeholder_count = placeholder_count + 1
  end

  -- Return the directive comment followed by the figure
  -- (preserves the directive as documentation)
  return pandoc.Blocks({el, figure})
end


-- ---------------------------------------------------------------------------
-- Summary (logged to stderr during render)
-- ---------------------------------------------------------------------------

function Pandoc(doc)
  -- Post-processing summary
  if processed_count > 0 then
    io.stderr:write(string.format(
      "uiao-diagrams.lua: resolved %d diagram(s), %d placeholder(s)\n",
      processed_count, placeholder_count
    ))
  end
  return doc
end
