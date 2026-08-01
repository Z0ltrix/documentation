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

This creates a table of contents, list of tables, and list of figures, but no glossary. Add a glossary only when needed:

```text
python plugins/documents/skills/md2pdf/scripts/md2pdf.py input.md --glossary glossary.yml
```

Disable automatic indexes with `--no-toc`, `--no-tot`, or `--no-tof`. Run `--install-deps` once when Pandoc or Typst is missing.

See `python plugins/documents/skills/md2pdf/scripts/md2pdf.py --help` for all style, font, color, paper, and metadata options.
