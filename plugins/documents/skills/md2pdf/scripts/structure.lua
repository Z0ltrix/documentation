local function metadata_boolean(meta, name)
  if meta[name] == nil then
    return true
  end
  return pandoc.utils.stringify(meta[name]):lower() ~= "false"
end

local function typst_string(value)
  return value:gsub("\\", "\\\\"):gsub("\"", "\\\"")
end

local function typst_boolean(value)
  return value and "true" or "false"
end

function Pandoc(document)
  local meta = document.meta
  local language = meta.lang and pandoc.utils.stringify(meta.lang):lower() or "en"
  local indexes = string.format(
    "#md-indexes(toc: %s, tot: %s, tof: %s, language: \"%s\")",
    typst_boolean(metadata_boolean(meta, "md2pdf-toc")),
    typst_boolean(metadata_boolean(meta, "md2pdf-tot")),
    typst_boolean(metadata_boolean(meta, "md2pdf-tof")),
    typst_string(language)
  )
  table.insert(document.blocks, 1, pandoc.RawBlock("typst", indexes))

  if meta["md2pdf-glossary"] ~= nil then
    local path = pandoc.utils.stringify(meta["md2pdf-glossary"])
    local glossary = string.format(
      "#md-glossary-section(\"%s\", language: \"%s\")",
      typst_string(path),
      typst_string(language)
    )
    table.insert(document.blocks, pandoc.RawBlock("typst", glossary))
  end

  return document
end
