$for(header-includes)$
$header-includes$

$endfor$
#let md-index-labels = (
  en: (
    toc: [Table of Contents],
    tot: [List of Tables],
    tof: [List of Figures],
  ),
  de: (
    toc: [Inhaltsverzeichnis],
    tot: [Tabellenverzeichnis],
    tof: [Abbildungsverzeichnis],
  ),
)

#let md-index-section(label, target) = [
  #heading(level: 1, outlined: false)[#label]
  #outline(title: none, target: target)
  #pagebreak(weak: true)
]

#let md-indexes(toc: true, tot: true, tof: true, language: "en") = context {
  let labels = md-index-labels.at(if language.starts-with("de") { "de" } else { "en" })
  let has-toc = query(heading.where(outlined: true)).len() > 0
  let has-tot = query(figure.where(kind: table)).filter(it => it.caption != none).len() > 0
  let has-tof = query(figure.where(kind: image)).filter(it => it.caption != none).len() > 0

  if toc and has-toc {
    md-index-section(labels.toc, heading.where(outlined: true))
  }
  if tot and has-tot {
    md-index-section(labels.tot, figure.where(kind: table))
  }
  if tof and has-tof {
    md-index-section(labels.tof, figure.where(kind: image))
  }
}

#let md-glossary-label(key) = label("md2pdf-glossary-" + key)

#let md-glossary-ref(key, body) = {
  metadata((kind: "md2pdf-glossary-use", key: key))
  link(md-glossary-label(key), body)
}

#let md-glossary-required(entry, field, index) = {
  assert(field in entry, message: "glossary entry " + str(index) + " missing " + field)
  let value = entry.at(field)
  assert(
    type(value) == str,
    message: "glossary entry " + str(index) + " " + field + " must be a string",
  )
  value
}

#let md-glossary-validate(entries) = {
  assert(type(entries) == array, message: "glossary must be a YAML list")
  let keys = ()
  for (index, entry) in entries.enumerate() {
    assert(type(entry) == dictionary, message: "glossary entry " + str(index) + " must be a mapping")
    let key = md-glossary-required(entry, "key", index)
    let _ = md-glossary-required(entry, "short", index)
    let _ = md-glossary-required(entry, "description", index)
    assert(key != "", message: "glossary entry " + str(index) + " key must not be empty")
    assert(not keys.contains(key), message: "duplicate glossary key: " + key)
    keys.push(key)
    if "long" in entry {
      assert(
        type(entry.long) == str,
        message: "glossary entry " + str(index) + " long must be a string",
      )
    }
    if "aliases" in entry {
      assert(
        type(entry.aliases) == array,
        message: "glossary entry " + str(index) + " aliases must be an array",
      )
      for alias in entry.aliases {
        assert(
          type(alias) == str,
          message: "glossary entry " + str(index) + " aliases must contain strings",
        )
      }
    }
  }
  entries
}

#let md-glossary-section(path, language: "en") = context {
  let entries = md-glossary-validate(yaml(path))
  let used-keys = query(metadata).map(it => it.value).filter(value =>
    type(value) == dictionary and "kind" in value
      and value.kind == "md2pdf-glossary-use" and "key" in value
  ).map(value => value.key).dedup()
  let selected = entries.filter(entry => used-keys.contains(entry.key))
    .sorted(key: entry => lower(entry.short))

  if selected.len() > 0 {
    pagebreak(weak: true)
    heading(level: 1, outlined: false)[
      #if language.starts-with("de") { [Glossar] } else { [Glossary] }
    ]
    let cells = selected.map(entry => {
      let term = if "long" in entry and entry.long != entry.short {
        [#strong(entry.short)\ #entry.long]
      } else {
        strong(entry.short)
      }
      (
        [#metadata((kind: "md2pdf-glossary-entry", key: entry.key))#md-glossary-label(entry.key)#term],
        [#entry.description],
      )
    }).flatten()
    grid(
      columns: (1fr, 2fr),
      column-gutter: 1.2em,
      row-gutter: 0.65em,
      ..cells,
    )
  }
}

$body$
