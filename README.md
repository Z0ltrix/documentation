# Documentation Marketplace

`documentation-marketplace` is a shared Codex and Claude Code marketplace for document-production workflows.

| Plugin | Status | Planned scope |
| --- | --- | --- |
| `documents` | Active | Markdown-to-PDF through Pandoc and Typst |
| `diagrams` | Scaffold | draw.io workflows |
| `slides` | Scaffold | Slidev workflows |

## Install in Codex

```text
codex plugin marketplace add <path-to-this-repository>
codex plugin add documents@documentation-marketplace
```

## Install in Claude Code

```text
claude plugin marketplace add <path-to-this-repository>
claude plugin install documents@documentation-marketplace
```

## Render Markdown directly

```text
python plugins/documents/skills/md2pdf/scripts/md2pdf.py input.md
```

The renderer creates a table of contents, list of tables, list of figures, and glossary by default. Disable individual sections with `--no-toc`, `--no-tot`, `--no-tof`, or `--no-glossary`. Run `--install-deps` once when Pandoc or Typst is missing.

See `python plugins/documents/skills/md2pdf/scripts/md2pdf.py --help` for all style, font, color, paper, and metadata options.
