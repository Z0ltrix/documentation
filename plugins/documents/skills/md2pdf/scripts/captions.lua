-- Add evidence-based captions so Typst can build table and figure outlines.

local current_heading = ""
local language = "en"

local function is_german()
  return language:match("^de") ~= nil
end

local function empty_caption(caption)
  return pandoc.utils.stringify(caption):match("^%s*$") ~= nil
end

local function table_caption()
  if current_heading ~= "" then
    return (is_german() and "Daten zu " or "Data for ") .. current_heading
  end
  return is_german() and "Datenübersicht" or "Data overview"
end

local function figure_caption(figure)
  local description = pandoc.utils.stringify(figure.content)
  if description ~= "" then
    return description
  end
  if current_heading ~= "" then
    return (is_german() and "Abbildung zu " or "Illustration for ") .. current_heading
  end
  return is_german() and "Abbildung" or "Illustration"
end

return {
  traverse = "topdown",
  Meta = function(meta)
    if meta.lang then
      language = pandoc.utils.stringify(meta.lang):lower()
    end
    return meta
  end,
  Header = function(header)
    current_heading = pandoc.utils.stringify(header.content)
    return header
  end,
  Table = function(tbl)
    if empty_caption(tbl.caption) then
      tbl.caption = pandoc.Caption(table_caption())
    end
    return tbl
  end,
  Figure = function(figure)
    if empty_caption(figure.caption) then
      figure.caption = pandoc.Caption(figure_caption(figure))
    end
    return figure
  end,
}
