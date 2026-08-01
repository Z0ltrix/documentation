#let md-accent = rgb("#@@ACCENT@@")
#let md-ink = rgb("#111827")
#let md-muted = rgb("#6b7280")
#let md-line = rgb("#d1d5db")
#let md-panel = rgb("#f9fafb")
#let md-content-width = @@PAGE_WIDTH@@ - 21mm - 21mm
#let md-content-height = @@PAGE_HEIGHT@@ - 20mm - 19mm

#set page(
  paper: "@@PAPER@@",
  margin: (top: 20mm, bottom: 19mm, left: 21mm, right: 21mm),
  numbering: "1",
  number-align: right + bottom,
)
#set text(font: @@BODY_FONT@@, size: 10.2pt, fill: md-ink)
#set par(justify: false, leading: 0.7em)
#set heading(numbering: "1.1")
#set table(stroke: (x: none, y: 0.4pt + md-line), inset: (x: 5pt, y: 4.5pt))

#show heading.where(level: 1): it => block(above: 1.55em, below: 0.65em, breakable: false)[
  #set text(size: 18pt, weight: 650, fill: md-accent)
  #it
]
#show heading.where(level: 2): set text(size: 13pt, weight: 650)
#show heading.where(level: 3): set text(size: 11pt, weight: 650, fill: md-muted)
#show table.cell.where(y: 0): set text(weight: 650)
#show table.cell.where(y: 0): set table.cell(fill: rgb("#f3f4f6"))
#show figure.caption: set text(size: 8.8pt, fill: md-muted)
#show link: set text(fill: md-accent)
#show quote: it => block(
  stroke: (left: 2pt + md-line),
  inset: (left: 10pt, top: 4pt, bottom: 4pt),
)[#set text(fill: md-muted); #it]
#let md-code-block(it, breakable: true) = block(
  width: 100%,
  fill: md-panel,
  stroke: 0.4pt + md-line,
  radius: 2pt,
  inset: 8pt,
  breakable: breakable,
)[#set text(font: @@MONO_FONT@@, size: 8.6pt); #it]
#show raw.where(block: true): it => context {
  let code = md-code-block(it)
  let code-height = measure(code, width: md-content-width).height
  md-code-block(it, breakable: code-height > md-content-height)
}
#show raw.where(block: false): it => box(
  fill: md-panel,
  inset: (x: 2.5pt, y: 1pt),
)[#set text(font: @@MONO_FONT@@, size: 0.92em); #it]
