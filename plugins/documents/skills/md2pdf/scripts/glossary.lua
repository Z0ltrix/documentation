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

local unicode_separators = {
  [" "] = true, [" "] = true, [" "] = true, [" "] = true,
  [" "] = true, [" "] = true, [" "] = true, [" "] = true,
  [" "] = true, [" "] = true, [" "] = true, [" "] = true,
  ["–"] = true, ["—"] = true, ["‘"] = true, ["’"] = true,
  ["“"] = true, ["”"] = true, ["…"] = true,
}

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
  return not unicode_separators[character]
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

local function is_run_inline(inline)
  return inline.t == "Str" or inline.t == "Space"
    or inline.t == "SoftBreak" or inline.t == "LineBreak"
end

local function run_text(run)
  local parts = {}
  for _, inline in ipairs(run) do
    if inline.t == "Str" then
      table.insert(parts, inline.text)
    elseif inline.t == "Space" then
      table.insert(parts, " ")
    else
      table.insert(parts, "\n")
    end
  end
  return table.concat(parts)
end

local function wrap_run(run)
  local matches = find_matches(run_text(run))
  if #matches == 0 then
    return run
  end

  local opens = {}
  local closes = {}
  for _, match in ipairs(matches) do
    opens[match.start_at] = pandoc.RawInline(
      "typst", '#md-glossary-ref("' .. typst_string(match.key) .. '")['
    )
    closes[match.finish_at + 1] = pandoc.RawInline("typst", "]")
  end

  local output = pandoc.Inlines({})
  local position = 1
  local function emit_boundary(at)
    if closes[at] then
      output:insert(closes[at])
      closes[at] = nil
    end
    if opens[at] then
      output:insert(opens[at])
      opens[at] = nil
    end
  end

  for _, inline in ipairs(run) do
    if inline.t == "Str" then
      local inline_length = pandoc.text.len(inline.text)
      local inline_end = position + inline_length
      local local_position = 1
      while position < inline_end do
        emit_boundary(position)
        local next_boundary = inline_end
        for boundary in pairs(opens) do
          if boundary > position and boundary < next_boundary then
            next_boundary = boundary
          end
        end
        for boundary in pairs(closes) do
          if boundary > position and boundary < next_boundary then
            next_boundary = boundary
          end
        end
        local part_length = next_boundary - position
        output:insert(pandoc.Str(
          pandoc.text.sub(inline.text, local_position, local_position + part_length - 1)
        ))
        position = next_boundary
        local_position = local_position + part_length
      end
      emit_boundary(position)
    else
      emit_boundary(position)
      output:insert(inline)
      position = position + 1
      emit_boundary(position)
    end
  end
  return output
end

local process_inlines

local function process_container(inline)
  if inline.t == "Image" or inline.t == "Code" or inline.t == "Math"
    or inline.t == "RawInline" or inline.t == "Note" then
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
    if is_run_inline(inline) then
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

local function process_blocks(blocks)
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
