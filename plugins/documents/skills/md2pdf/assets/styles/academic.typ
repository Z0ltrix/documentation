#let md-accent = rgb("#@@ACCENT@@")
#let md-ink = rgb("#241c18")
#let md-muted = rgb("#6b5b53")
#let md-line = rgb("#b9aaa1")
#let md-panel = rgb("#f8f4ef")

#set page(
  paper: "@@PAPER@@",
  margin: (top: 24mm, bottom: 23mm, left: 27mm, right: 24mm),
  numbering: "1",
  number-align: center + bottom,
)
#set text(font: @@BODY_FONT@@, size: 10.8pt, fill: md-ink)
#set par(justify: true, leading: 0.78em, first-line-indent: 1.15em)
#set heading(numbering: "1.1")
#set table(stroke: (x: none, y: 0.55pt + md-line), inset: (x: 6pt, y: 5pt))

#show heading.where(level: 1): it => block(above: 1.8em, below: 0.8em, breakable: false)[
  #set text(size: 18pt, weight: 700, fill: md-accent)
  #it
  #v(3pt)
  #line(length: 100%, stroke: 0.8pt + md-accent)
]
#show heading.where(level: 2): it => block(above: 1.35em, below: 0.55em, breakable: false)[
  #set text(size: 13.5pt, weight: 700)
  #it
]
#show heading.where(level: 3): set text(size: 11.5pt, weight: 700, style: "italic")
#show table.cell.where(y: 0): set text(weight: 700)
#show table.cell.where(y: 0): set table.cell(fill: rgb("#eee4dc"))
#show figure.caption: set text(size: 9pt, style: "italic", fill: md-muted)
#show link: set text(fill: md-accent)
#show quote: it => block(
  stroke: (left: 1.5pt + md-accent),
  inset: (left: 13pt, right: 6pt, top: 5pt, bottom: 5pt),
)[#set text(style: "italic", fill: md-muted); #it]
#show raw.where(block: true): it => block(
  width: 100%,
  fill: md-panel,
  stroke: 0.5pt + md-line,
  inset: 9pt,
  breakable: it.text.split("\n").len() > 40,
)[#set text(font: @@MONO_FONT@@, size: 8.6pt); #it]
#show raw.where(block: false): it => box(
  fill: md-panel,
  inset: (x: 3pt, y: 1pt),
)[#set text(font: @@MONO_FONT@@, size: 0.92em); #it]
