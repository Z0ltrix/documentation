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

#let md-glossary-ref(key: str, body: content) = {
  metadata((kind: "md2pdf-glossary-use", key: key))
  body
}

$body$
