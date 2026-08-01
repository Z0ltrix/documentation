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
| `--glossary FILE` | Read glossary terms from a YAML file; omit this option for no glossary |
| `--paper a4|letter` | Set the page size |
| `--font NAME` | Override the body-font stack |
| `--mono-font NAME` | Override the code-font stack |
| `--accent HEX` | Override the six-digit theme accent color |
| `--lang CODE` | Override labels, for example `de` or `en` |
| `--title TEXT` | Override the document title |
| `--author TEXT` | Override the author metadata |
| `--keep-typ` | Save generated Typst next to the PDF |
| `--verbose` | Print subprocess commands and diagnostics |

## Glossary YAML

The file must be a YAML list. Every entry requires unique, non-empty `key`, `short`, and `description` strings. `long` is an optional string; `aliases` is an optional list of strings. Only entries referenced in document prose are rendered.

```yaml
- key: api
  short: API
  long: Application Programming Interface
  aliases:
    - Programmierschnittstelle
  description: A defined interface used by software systems to communicate.
```

Render with `--glossary glossary.yml`. Omitting `--glossary` produces no glossary.

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
