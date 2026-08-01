# CLI reference

## Rendering

```text
python scripts/md2pdf.py INPUT [--output OUTPUT]
```

| Option | Effect |
| --- | --- |
| `--style modern|academic|minimal` | Select the Typst design preset |
| `--no-toc` | Suppress the table of contents |
| `--no-tot` | Suppress the list of tables |
| `--no-tof` | Suppress the list of figures |
| `--no-glossary` | Suppress glossary extraction and rendering |
| `--paper a4|letter` | Set the page size |
| `--font NAME` | Override the body-font stack |
| `--mono-font NAME` | Override the code-font stack |
| `--accent HEX` | Override the six-digit theme accent color |
| `--lang CODE` | Override labels, for example `de` or `en` |
| `--title TEXT` | Override the document title |
| `--author TEXT` | Override the author metadata |
| `--keep-typ` | Save generated Typst next to the PDF |
| `--verbose` | Print subprocess commands and diagnostics |

## Dependencies

```text
python scripts/md2pdf.py --check-deps
python scripts/md2pdf.py --install-deps
```

The installer downloads pinned official GitHub release assets into the user cache and verifies the SHA-256 digest published by GitHub. The renderer searches explicit environment overrides first (`MD2PDF_PANDOC`, `MD2PDF_TYPST`), then `PATH`, then the user cache.

Default tool versions:

- Pandoc 3.9.0.2
- Typst 0.14.2

No Python packages outside the standard library are required.
