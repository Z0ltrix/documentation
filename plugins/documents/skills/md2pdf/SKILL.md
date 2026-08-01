---
name: md2pdf
description: Convert Markdown files into polished PDF documents through Pandoc and Typst, with automatic tables of contents, tables, figures, and mechanically derived glossaries. Use when Codex or Claude Code needs to render, publish, restyle, or troubleshoot a Markdown-to-PDF workflow, including requests for typography, table styling, code-block styling, page layout, or index suppression.
---

# Markdown to PDF

Render with the bundled deterministic script. Do not recreate the Pandoc or Typst pipeline ad hoc.

## Workflow

1. Resolve the requested Markdown input and output path.
2. Run `python scripts/md2pdf.py --check-deps`.
3. If Pandoc or Typst is missing, tell the user that the installer downloads pinned upstream binaries, then run `python scripts/md2pdf.py --install-deps` only after approval.
4. Render with defaults unless the user requests specific switches:

   ```text
   python scripts/md2pdf.py input.md --output output.pdf --style modern
   ```

5. Render the produced PDF to PNG and visually inspect representative pages. Check headings, tables, code, figures, index entries, page numbers, clipping, and glyphs before delivery.

## Automatic sections

- Build the table of contents from headings.
- Add captions to uncaptained Pandoc tables and standalone figures, then build the table and figure lists from those elements.
- Build the glossary only from evidence in the document: Markdown definition lists, expanded acronyms such as `Application Programming Interface (API)`, and lead definitions such as `**Term**: meaning`. Never invent a definition.
- Omit an empty automatic section even when its switch is enabled.

Disable sections independently with `--no-toc`, `--no-tot`, `--no-tof`, and `--no-glossary`.

## Styling

Choose `modern`, `academic`, or `minimal`. Preserve the user's content and metadata; change only presentation unless asked to edit Markdown. Use `--font`, `--mono-font`, `--accent`, and `--paper` for explicit overrides.

Read [references/cli.md](references/cli.md) when selecting non-default switches or diagnosing the toolchain.

## Output rules

- Default the PDF path to the Markdown filename with a `.pdf` suffix.
- Create parent directories when needed.
- Keep intermediate Typst only when `--keep-typ` is requested.
- Report generated and suppressed sections concisely.
- Do not claim success until the current PDF has compiled and passed visual inspection.
