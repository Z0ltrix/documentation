local terms = {}

local function typst_string(value)
  return value:gsub("\\", "\\\\"):gsub("\"", "\\\"")
end

local function read_file(path)
  local handle, message = io.open(path, "r")
  if not handle then
    error("Glossary file not found: " .. path .. ": " .. message)
  end
  local contents = handle:read("*a")
  handle:close()
  return contents
end

local function parse_yaml_metadata(path)
  local indented = {}
  local source = read_file(path)
  for line in (source .. "\n"):gmatch("(.-)\r?\n") do
    table.insert(indented, "  " .. line)
  end
  local markdown = "---\nitems:\n" .. table.concat(indented, "\n") .. "\n---\n"
  local ok, parsed = pcall(pandoc.read, markdown, "markdown")
  if not ok then
    error("Glossary YAML error: " .. tostring(parsed))
  end
  return parsed.meta.items
end

local function metadata_string(value, field, index)
  local value_type = pandoc.utils.type(value)
  if value_type ~= "Inlines" and value_type ~= "string" then
    error(string.format("glossary entry %d %s must be a string", index, field))
  end
  return pandoc.utils.stringify(value)
end

local function add_candidate(candidates, seen, key, value)
  if value ~= "" and not seen[value] then
    seen[value] = true
    table.insert(candidates, {
      key = key,
      text = value,
      length = pandoc.text.len(value),
    })
  end
end

local function glossary_terms(path)
  local items = parse_yaml_metadata(path)
  if pandoc.utils.type(items) ~= "List" then
    return {}
  end

  local candidates = {}
  local seen = {}
  for index, item in ipairs(items) do
    local key = metadata_string(item.key, "key", index)
    add_candidate(candidates, seen, key, metadata_string(item.short, "short", index))
    if item.long ~= nil then
      add_candidate(candidates, seen, key, metadata_string(item.long, "long", index))
    end
    if item.aliases ~= nil then
      if pandoc.utils.type(item.aliases) ~= "List" then
        error(string.format("glossary entry %d aliases must be an array", index))
      end
      for alias_index, alias in ipairs(item.aliases) do
        add_candidate(
          candidates,
          seen,
          key,
          metadata_string(alias, "aliases[" .. alias_index .. "]", index)
        )
      end
    end
  end
  table.sort(candidates, function(left, right)
    return left.length > right.length
  end)
  return candidates
end

local unicode_digit_starts = {
  0x0660, 0x06F0, 0x07C0, 0x0966, 0x09E6, 0x0A66, 0x0AE6,
  0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66, 0x0DE6, 0x0E50,
  0x0ED0, 0x0F20, 0x1040, 0x1090, 0x17E0, 0x1810, 0x1946,
  0x19D0, 0x1A80, 0x1A90, 0x1B50, 0x1BB0, 0x1C40, 0x1C50,
  0xA620, 0xA8D0, 0xA900, 0xA9D0, 0xA9F0, 0xAA50, 0xABF0,
  0xFF10, 0x104A0, 0x10D30, 0x11066, 0x110F0, 0x11136,
  0x111D0, 0x112F0, 0x11450, 0x114D0, 0x11650, 0x116C0,
  0x11730, 0x118E0, 0x11950, 0x11C50, 0x11D50, 0x11DA0,
  0x16A60, 0x16AC0, 0x16B50, 0x1E140, 0x1E2F0, 0x1E4F0,
  0x1E950,
}

local function is_unicode_digit(character)
  local codepoint = utf8.codepoint(character)
  if codepoint >= 0x1D7CE and codepoint <= 0x1D7FF then
    return true
  end
  for _, start_at in ipairs(unicode_digit_starts) do
    if codepoint >= start_at and codepoint <= start_at + 9 then
      return true
    end
  end
  return false
end

-- Pandoc exposes no Unicode category API. Keep punctuation/symbol ranges narrow;
-- uncased letters, numbers, combining marks, and CJK iteration marks stay words.
local unicode_boundary_ranges = {
  {0x00A0, 0x00A9},
  {0x00AB, 0x00B1},
  {0x00B4, 0x00B4},
  {0x00B6, 0x00B8},
  {0x00BB, 0x00BB},
  {0x00BF, 0x00BF},
  {0x0609, 0x060A},
  {0x060C, 0x060D},
  {0x061B, 0x061B},
  {0x061D, 0x061F},
  {0x066A, 0x066D},
  {0x06D4, 0x06D4},
  {0x1680, 0x1680},
  {0x180E, 0x180E},
  {0x2000, 0x203E},
  {0x2041, 0x2053},
  {0x2055, 0x206F},
  {0x20A0, 0x20CF},
  {0x2190, 0x245F},
  {0x2500, 0x2BFF},
  {0x2E00, 0x2E7F},
  {0x3000, 0x3004},
  {0x3008, 0x3020},
  {0x3030, 0x3030},
  {0x3036, 0x3037},
  {0x303D, 0x303F},
  {0xFE10, 0xFE1F},
  {0xFE30, 0xFE6F},
  {0xFF01, 0xFF0F},
  {0xFF1A, 0xFF20},
  {0xFF3B, 0xFF40},
  {0xFF5B, 0xFF65},
  {0x1F000, 0x1FAFF},
}

local function is_unicode_boundary(character)
  local codepoint = utf8.codepoint(character)
  for _, range in ipairs(unicode_boundary_ranges) do
    if codepoint >= range[1] and codepoint <= range[2] then
      return true
    end
  end
  return false
end

local function is_word_character(character)
  if character == nil or character == "" then
    return false
  end
  if character:match("^[A-Za-z0-9_]$") then
    return true
  end
  if #character == 1 then
    return false
  end
  if pandoc.text.lower(character) ~= pandoc.text.upper(character)
    or is_unicode_digit(character) then
    return true
  end
  return not is_unicode_boundary(character)
end

local function has_word_boundaries(text, start_at, finish_at)
  local before = start_at > 1 and pandoc.text.sub(text, start_at - 1, start_at - 1) or nil
  local after = finish_at < pandoc.text.len(text)
    and pandoc.text.sub(text, finish_at + 1, finish_at + 1) or nil
  return not is_word_character(before) and not is_word_character(after)
end

local function find_matches(text)
  local matches = {}
  local text_length = pandoc.text.len(text)
  local position = 1
  while position <= text_length do
    local found = nil
    for _, candidate in ipairs(terms) do
      local finish_at = position + candidate.length - 1
      if finish_at <= text_length
        and pandoc.text.sub(text, position, finish_at) == candidate.text
        and has_word_boundaries(text, position, finish_at) then
        found = { start_at = position, finish_at = finish_at, key = candidate.key }
        break
      end
    end
    if found then
      table.insert(matches, found)
      position = found.finish_at + 1
    else
      position = position + 1
    end
  end
  return matches
end

local function is_text_inline(inline)
  return inline.t == "Str" or inline.t == "Space" or inline.t == "SoftBreak"
end

local excluded_inlines = {
  Image = true,
  Code = true,
  Math = true,
  RawInline = true,
  Note = true,
}

local function is_matchable_inline(inline)
  if is_text_inline(inline) then
    return true
  end
  if excluded_inlines[inline.t] or inline.content == nil or #inline.content == 0 then
    return false
  end
  for _, child in ipairs(inline.content) do
    if not is_matchable_inline(child) then
      return false
    end
  end
  return true
end

local function inline_text(inline, parts)
  if inline.t == "Str" then
    table.insert(parts, inline.text)
  elseif inline.t == "Space" or inline.t == "SoftBreak" then
    table.insert(parts, " ")
  else
    for _, child in ipairs(inline.content) do
      inline_text(child, parts)
    end
  end
end

local function run_text(run)
  local parts = {}
  for _, inline in ipairs(run) do
    inline_text(inline, parts)
  end
  return table.concat(parts)
end

local function inline_length(inline)
  if inline.t == "Str" then
    return pandoc.text.len(inline.text)
  end
  if inline.t == "Space" or inline.t == "SoftBreak" then
    return 1
  end
  local length = 0
  for _, child in ipairs(inline.content) do
    length = length + inline_length(child)
  end
  return length
end

local slice_inlines

local function slice_inline(inline, first, last, position)
  local length = inline_length(inline)
  local inline_last = position + length - 1
  if last < position or first > inline_last then
    return nil, inline_last + 1
  end
  if inline.t == "Str" then
    local local_first = math.max(first, position) - position + 1
    local local_last = math.min(last, inline_last) - position + 1
    return pandoc.Str(pandoc.text.sub(inline.text, local_first, local_last)), inline_last + 1
  end
  if inline.t == "Space" or inline.t == "SoftBreak" then
    return inline:clone(), inline_last + 1
  end
  local clone = inline:clone()
  clone.content = slice_inlines(inline.content, first, last, position)
  return clone, inline_last + 1
end

slice_inlines = function(inlines, first, last, position)
  local output = pandoc.Inlines({})
  local cursor = position
  for _, inline in ipairs(inlines) do
    local sliced
    sliced, cursor = slice_inline(inline, first, last, cursor)
    if sliced ~= nil then
      output:insert(sliced)
    end
  end
  return output
end

local function slice_run(run, first, last)
  if first > last then
    return pandoc.Inlines({})
  end
  return slice_inlines(run, first, last, 1)
end

local function wrap_run(run)
  local matches = find_matches(run_text(run))
  if #matches == 0 then
    return run
  end

  local output = pandoc.Inlines({})
  local cursor = 1
  for _, match in ipairs(matches) do
    output:extend(slice_run(run, cursor, match.start_at - 1))
    output:insert(pandoc.RawInline(
      "typst", '#md-glossary-ref("' .. typst_string(match.key) .. '")['
    ))
    output:extend(slice_run(run, match.start_at, match.finish_at))
    output:insert(pandoc.RawInline("typst", "]"))
    cursor = match.finish_at + 1
  end
  output:extend(slice_run(run, cursor, pandoc.text.len(run_text(run))))
  return output
end

local process_inlines
local process_blocks

local function process_container(inline)
  if inline.t == "Note" then
    inline.content = process_blocks(inline.content)
    return inline
  end
  if inline.t == "Image" or inline.t == "Code" or inline.t == "Math"
    or inline.t == "RawInline" then
    return inline
  end
  if inline.content ~= nil then
    inline.content = process_inlines(inline.content)
  end
  return inline
end

process_inlines = function(inlines)
  local output = pandoc.Inlines({})
  local run = pandoc.Inlines({})
  local function flush_run()
    output:extend(wrap_run(run))
    run = pandoc.Inlines({})
  end
  for _, inline in ipairs(inlines) do
    if is_matchable_inline(inline) then
      run:insert(inline)
    else
      flush_run()
      output:insert(process_container(inline))
    end
  end
  flush_run()
  return output
end

local function process_prose_block(block)
  block.content = process_inlines(block.content)
  return block
end

process_blocks = function(blocks)
  local output = pandoc.Blocks({})
  for _, block in ipairs(blocks) do
    if block.t == "Para" or block.t == "Plain" then
      block = process_prose_block(block)
    elseif block.t == "BlockQuote" or block.t == "Div" then
      block.content = process_blocks(block.content)
    elseif block.t == "BulletList" then
      for index, item in ipairs(block.content) do
        block.content[index] = process_blocks(item)
      end
    elseif block.t == "OrderedList" then
      for index, item in ipairs(block.content) do
        block.content[index] = process_blocks(item)
      end
    elseif block.t == "DefinitionList" then
      for _, item in ipairs(block.content) do
        for index, definition in ipairs(item[2]) do
          item[2][index] = process_blocks(definition)
        end
      end
    elseif block.t == "Table" then
      local caption = block.caption
      block.caption = pandoc.Caption({})
      block = pandoc.walk_block(block, {
        Para = process_prose_block,
        Plain = process_prose_block,
      })
      block.caption = caption
    end
    output:insert(block)
  end
  return output
end

function Pandoc(document)
  local glossary = document.meta["md2pdf-glossary"]
  if glossary == nil then
    return document
  end
  terms = glossary_terms(pandoc.utils.stringify(glossary))
  document.blocks = process_blocks(document.blocks)
  return document
end
