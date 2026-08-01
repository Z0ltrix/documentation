#let md-accent = rgb("#@@ACCENT@@")
#let md-ink = rgb("#172033")
#let md-muted = rgb("#64748b")
#let md-line = rgb("#cbd5e1")
#let md-panel = rgb("#f4f7fb")

#set page(
  paper: "@@PAPER@@",
  margin: (top: 21mm, bottom: 20mm, left: 22mm, right: 22mm),
  numbering: "1",
  number-align: center + bottom,
)
#set text(font: @@BODY_FONT@@, size: 10.5pt, fill: md-ink)
#set par(justify: true, leading: 0.72em)
#set heading(numbering: "1.1")
#set table(stroke: 0.45pt + md-line, inset: (x: 7pt, y: 5.5pt))
#set list(indent: 1.15em, body-indent: 0.55em)

#show heading.where(level: 1): it => block(above: 1.7em, below: 0.75em, breakable: false)[
  #set text(size: 20pt, weight: 700, fill: md-accent)
  #it
]
#show heading.where(level: 2): it => block(above: 1.35em, below: 0.55em, breakable: false)[
  #set text(size: 14pt, weight: 650, fill: md-ink)
  #it
]
#show heading.where(level: 3): set text(size: 11.5pt, weight: 650, fill: md-muted)
#show table.cell.where(y: 0): set text(weight: 700, fill: md-accent)
#show table.cell.where(y: 0): set table.cell(fill: rgb("#dbeafe"), stroke: md-line)
#show figure.caption: set text(size: 9pt, style: "italic", fill: md-muted)
#show link: set text(fill: md-accent)
#show outline: it => block(below: 1.4em)[#it]
#show outline.entry.where(level: 1): set block(above: 0.45em)
#show quote: it => block(
  fill: md-panel,
  stroke: (left: 3pt + md-accent),
  inset: (left: 12pt, right: 10pt, top: 8pt, bottom: 8pt),
  radius: (right: 4pt),
)[#it]
#show raw.where(block: true): it => block(
  width: 100%,
  fill: rgb("#0f172a"),
  stroke: 0.5pt + rgb("#26334a"),
  radius: 5pt,
  inset: 10pt,
  breakable: it.text.split("\n").len() > 40,
)[#set text(font: @@MONO_FONT@@, size: 8.7pt, fill: rgb("#e2e8f0")); #it]
#show raw.where(block: false): it => box(
  fill: md-panel,
  radius: 3pt,
  inset: (x: 3pt, y: 1pt),
)[#set text(font: @@MONO_FONT@@, size: 0.92em); #it]
