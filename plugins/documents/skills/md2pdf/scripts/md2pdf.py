#!/usr/bin/env python3
"""Render Markdown as a styled PDF with Pandoc and Typst."""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import install_deps


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_DIR / "assets"
READER = "markdown+implicit_figures+definition_lists+fenced_code_attributes+pipe_tables+grid_tables"

THEMES = {
    "modern": {
        "accent": "2563eb",
        "body_fonts": ["DejaVu Sans"],
        "mono_fonts": ["DejaVu Sans Mono"],
        "fontsize": "10.5pt",
        "linestretch": 1.1,
        "margin": {"top": "21mm", "bottom": "20mm", "left": "22mm", "right": "22mm"},
    },
    "academic": {
        "accent": "7c2d12",
        "body_fonts": ["Libertinus Serif"],
        "mono_fonts": ["DejaVu Sans Mono"],
        "fontsize": "10.8pt",
        "linestretch": 1.2,
        "margin": {"top": "24mm", "bottom": "23mm", "left": "27mm", "right": "24mm"},
    },
    "minimal": {
        "accent": "111827",
        "body_fonts": ["DejaVu Sans"],
        "mono_fonts": ["DejaVu Sans Mono"],
        "fontsize": "10.2pt",
        "linestretch": 1.08,
        "margin": {"top": "20mm", "bottom": "19mm", "left": "21mm", "right": "21mm"},
    },
}

LABELS = {
    "en": {
        "toc": "Contents",
        "tot": "List of Tables",
        "tof": "List of Figures",
        "glossary": "Glossary",
    },
    "de": {
        "toc": "Inhaltsverzeichnis",
        "tot": "Tabellenverzeichnis",
        "tof": "Abbildungsverzeichnis",
        "glossary": "Glossar",
    },
}


class RenderError(RuntimeError):
    pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="Markdown input file")
    parser.add_argument("-o", "--output", type=Path, help="PDF output path")
    parser.add_argument("--style", choices=tuple(THEMES), default="modern")
    parser.add_argument("--paper", choices=("a4", "letter"), default="a4")
    parser.add_argument("--font", help="Body font family")
    parser.add_argument("--mono-font", help="Monospace font family")
    parser.add_argument("--accent", help="Six-digit theme color, with optional #")
    parser.add_argument("--lang", help="Label language, for example de or en")
    parser.add_argument("--title", help="Override title metadata")
    parser.add_argument("--author", help="Override author metadata")
    parser.add_argument("--no-toc", action="store_true")
    parser.add_argument("--no-tot", action="store_true")
    parser.add_argument("--no-tof", action="store_true")
    parser.add_argument("--no-glossary", action="store_true")
    parser.add_argument("--keep-typ", action="store_true")
    parser.add_argument("--check-deps", action="store_true")
    parser.add_argument("--install-deps", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def find_tool(name):
    override = os.environ.get("MD2PDF_{}".format(name.upper()))
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return candidate.resolve()
    system = shutil.which(name)
    if system:
        return Path(system).resolve()
    return install_deps.find_cached_tool(name)


def command_text(command):
    return " ".join(shlex.quote(str(part)) for part in command)


def run_command(command, cwd, verbose=False):
    if verbose:
        print("+ {}".format(command_text(command)))
    result = subprocess.run(
        [str(part) for part in command],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )
    if verbose and result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown subprocess error"
        raise RenderError("Command failed ({}):\n{}".format(result.returncode, detail))
    return result.stdout


def tool_version(path):
    try:
        result = subprocess.run(
            [str(path), "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.splitlines()[0].strip() if result.stdout else "unknown"
    except OSError:
        return "unavailable"


def dependency_status():
    return {name: find_tool(name) for name in ("pandoc", "typst")}


def print_dependency_status(status):
    for name in ("pandoc", "typst"):
        path = status[name]
        if path:
            print("{}: {} ({})".format(name, tool_version(path), path))
        else:
            print("{}: missing".format(name))


def _text_parts(value, parts):
    if isinstance(value, list):
        for item in value:
            _text_parts(item, parts)
        return
    if not isinstance(value, dict):
        return
    tag = value.get("t")
    content = value.get("c")
    if tag == "Str":
        parts.append(content)
    elif tag in ("Space", "SoftBreak", "LineBreak"):
        parts.append(" ")
    elif tag in ("Code", "Math", "RawInline", "CodeBlock", "RawBlock"):
        if isinstance(content, list) and content:
            parts.append(str(content[-1]))
    elif tag in ("Link", "Image") and isinstance(content, list) and len(content) > 1:
        _text_parts(content[1], parts)
    elif tag == "Header" and isinstance(content, list) and len(content) > 2:
        _text_parts(content[2], parts)
    else:
        _text_parts(content, parts)


def node_text(value):
    parts = []
    _text_parts(value, parts)
    text = "".join(parts)
    return re.sub(r"\s+", " ", text).strip()


def walk_nodes(value):
    if isinstance(value, dict):
        if "t" in value:
            yield value
        for child in value.values():
            for item in walk_nodes(child):
                yield item
    elif isinstance(value, list):
        for child in value:
            for item in walk_nodes(child):
                yield item


def meta_text(meta, key):
    value = meta.get(key)
    if not value:
        return ""
    return node_text(value)


def analyze_document(ast):
    counts = {"headings": 0, "tables": 0, "figures": 0}

    def visit(value, inside_figure=False):
        if isinstance(value, list):
            for child in value:
                visit(child, inside_figure)
            return
        if not isinstance(value, dict):
            return
        tag = value.get("t")
        if tag == "Header":
            counts["headings"] += 1
        elif tag == "Table":
            counts["tables"] += 1
        elif tag == "Figure":
            counts["figures"] += 1
            inside_figure = True
        elif tag == "Image" and not inside_figure:
            counts["figures"] += 1
        for child in value.values():
            visit(child, inside_figure)

    visit(ast.get("blocks", []))
    return counts


def extract_glossary(ast):
    entries = {}

    def add(term, definition):
        term = re.sub(r"\s+", " ", term).strip(" :;-–—")
        definition = re.sub(r"\s+", " ", definition).strip(" :;-–—")
        if not term or not definition or len(term) > 80 or len(definition) < 3:
            return
        key = term.casefold()
        if key not in entries or len(definition) > len(entries[key][1]):
            entries[key] = (term, definition[:500])

    for node in walk_nodes(ast.get("blocks", [])):
        tag = node.get("t")
        content = node.get("c")
        if tag == "DefinitionList" and isinstance(content, list):
            for item in content:
                if isinstance(item, list) and len(item) == 2:
                    add(node_text(item[0]), node_text(item[1]))
        if tag in ("Para", "Plain") and isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and first.get("t") == "Strong":
                term = node_text(first)
                definition = node_text(content[1:]).lstrip(" :;-–—")
                add(term, definition)

    document_text = node_text(ast.get("blocks", []))
    long_word = r"[A-ZÄÖÜ][A-Za-zÀ-ÖØ-öø-ÿ0-9-]+"
    connector = r"(?:and|or|of|for|the|in|to|und|oder|der|die|das|des|von|für|im|zur)"
    long_form = r"{}(?:\s+(?:{}|{})){{1,7}}".format(long_word, long_word, connector)
    acronym = r"[A-ZÄÖÜ][A-ZÄÖÜ0-9.-]{1,9}"
    for match in re.finditer(r"\b({})\s*\(({})\)".format(long_form, acronym), document_text):
        add(match.group(2), match.group(1))

    return sorted(entries.values(), key=lambda item: item[0].casefold())


def first_heading(ast):
    for node in walk_nodes(ast.get("blocks", [])):
        if node.get("t") == "Header":
            return node_text(node)
    return ""


def typst_string(value):
    return '"{}"'.format(
        value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    )


def typst_font_tuple(fonts):
    values = ", ".join(typst_string(font) for font in fonts)
    if len(fonts) == 1:
        values += ","
    return "({})".format(values)


def render_style(args):
    theme = THEMES[args.style]
    accent = (args.accent or theme["accent"]).lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", accent):
        raise RenderError("--accent must be a six-digit hexadecimal color")
    body_fonts = [args.font] if args.font else theme["body_fonts"]
    mono_fonts = [args.mono_font] if args.mono_font else theme["mono_fonts"]
    template = (ASSETS_DIR / "styles" / "{}.typ".format(args.style)).read_text(encoding="utf-8")
    replacements = {
        "@@PAPER@@": args.paper,
        "@@ACCENT@@": accent.lower(),
        "@@BODY_FONT@@": typst_font_tuple(body_fonts),
        "@@MONO_FONT@@": typst_font_tuple(mono_fonts),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template


def template_metadata(args):
    theme = THEMES[args.style]
    return {
        "papersize": args.paper,
        "fontsize": theme["fontsize"],
        "mainfont": args.font or theme["body_fonts"][0],
        "codefont": [args.mono_font or theme["mono_fonts"][0]],
        "linestretch": theme["linestretch"],
        "section-numbering": "1.1",
        "margin": theme["margin"],
    }


def language_key(value):
    return "de" if (value or "").lower().startswith("de") else "en"


def render_frontmatter(counts, labels, args):
    sections = []
    if counts["headings"] and not args.no_toc:
        sections.append("#outline(title: [{}], depth: 3)".format(labels["toc"]))
    if counts["tables"] and not args.no_tot:
        sections.append(
            "#outline(title: [{}], target: figure.where(kind: table))".format(labels["tot"])
        )
    if counts["figures"] and not args.no_tof:
        sections.append(
            "#outline(title: [{}], target: figure.where(kind: image))".format(labels["tof"])
        )
    if not sections:
        return ""
    return "#pagebreak(weak: true)\n" + "\n#pagebreak(weak: true)\n".join(sections) + "\n#pagebreak(weak: true)\n"


def render_glossary(entries, title):
    if not entries:
        return ""
    data = ",\n  ".join(
        "({}, {})".format(typst_string(term), typst_string(definition))
        for term, definition in entries
    )
    return """#pagebreak(weak: true)
#heading(level: 1, outlined: false)[%s]
#let md-glossary = (
  %s,
)
#for entry in md-glossary {
  grid(
    columns: (1fr, 2.6fr),
    gutter: 12pt,
    strong(entry.at(0)),
    entry.at(1),
  )
  v(0.55em)
}
""" % (title, data)


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / ".{}.{}.tmp".format(destination.name, uuid.uuid4().hex)
    try:
        shutil.copy2(str(source), str(temporary))
        os.replace(str(temporary), str(destination))
    finally:
        if temporary.exists():
            temporary.unlink()


def render(args, pandoc, typst):
    source = args.input.expanduser().resolve()
    if not source.is_file():
        raise RenderError("Markdown input not found: {}".format(source))
    output = (args.output or source.with_suffix(".pdf")).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    ast_text = run_command(
        [pandoc, source.name, "--from", READER, "--to", "json"],
        source.parent,
        args.verbose,
    )
    ast = json.loads(ast_text)
    counts = analyze_document(ast)
    glossary = [] if args.no_glossary else extract_glossary(ast)
    meta = ast.get("meta", {})
    language = args.lang or meta_text(meta, "lang") or "en"
    labels = LABELS[language_key(language)]
    title = args.title or meta_text(meta, "title") or first_heading(ast) or source.stem

    style_text = render_style(args)
    frontmatter = render_frontmatter(counts, labels, args)
    glossary_text = render_glossary(glossary, labels["glossary"])

    generated_typst = source.parent / ".md2pdf-{}.typ".format(uuid.uuid4().hex)
    try:
        with tempfile.TemporaryDirectory(prefix=".md2pdf-", dir=str(source.parent)) as work_name:
            work = Path(work_name)
            style_path = work / "style.typ"
            front_path = work / "frontmatter.typ"
            glossary_path = work / "glossary.typ"
            metadata_path = work / "template-metadata.json"
            rendered_pdf = work / "rendered.pdf"
            style_path.write_text(style_text, encoding="utf-8")
            front_path.write_text(frontmatter, encoding="utf-8")
            glossary_path.write_text(glossary_text, encoding="utf-8")
            metadata_path.write_text(
                json.dumps(template_metadata(args), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            command = [
                pandoc,
                source.name,
                "--from",
                READER,
                "--to",
                "typst",
                "--standalone",
                "--lua-filter",
                SCRIPT_DIR / "captions.lua",
                "--metadata-file",
                metadata_path,
                "--include-in-header",
                style_path,
                "--output",
                generated_typst,
            ]
            if frontmatter:
                command.extend(["--include-before-body", front_path])
            if glossary_text:
                command.extend(["--include-after-body", glossary_path])
            if args.title:
                command.extend(["--metadata", "title={}".format(args.title)])
            if args.author:
                command.extend(["--metadata", "author={}".format(args.author)])
            if args.lang:
                command.extend(["--metadata", "lang={}".format(args.lang)])
            run_command(command, source.parent, args.verbose)
            run_command(
                [typst, "compile", "--root", source.parent, generated_typst, rendered_pdf],
                source.parent,
                args.verbose,
            )
            atomic_copy(rendered_pdf, output)
            if args.keep_typ:
                atomic_copy(generated_typst, output.with_suffix(".typ"))
    finally:
        if generated_typst.exists():
            generated_typst.unlink()

    sections = {
        "toc": bool(counts["headings"] and not args.no_toc),
        "tot": bool(counts["tables"] and not args.no_tot),
        "tof": bool(counts["figures"] and not args.no_tof),
        "glossary": bool(glossary),
    }
    print("Created: {}".format(output))
    print(
        "Sections: toc={toc}, tables={tables}, figures={figures}, glossary={glossary}".format(
            toc="yes" if sections["toc"] else "no",
            tables=counts["tables"] if sections["tot"] else "off",
            figures=counts["figures"] if sections["tof"] else "off",
            glossary=len(glossary) if sections["glossary"] else "off",
        )
    )
    return output


def main(argv=None):
    args = parse_args(argv)
    status = dependency_status()

    if args.install_deps:
        try:
            for name, path in status.items():
                if not path:
                    install_deps.install_tool(name)
        except (install_deps.InstallError, OSError, ValueError) as error:
            print("error: {}".format(error), file=sys.stderr)
            return 1
        status = dependency_status()

    if args.check_deps or args.install_deps:
        print_dependency_status(status)
        if args.input is None:
            return 0 if all(status.values()) else 2

    if args.input is None:
        print("error: INPUT is required unless --check-deps or --install-deps is used", file=sys.stderr)
        return 2
    missing = [name for name, path in status.items() if not path]
    if missing:
        print(
            "error: missing {}. Run this script with --install-deps first.".format(
                ", ".join(missing)
            ),
            file=sys.stderr,
        )
        return 2

    try:
        render(args, status["pandoc"], status["typst"])
    except (RenderError, OSError, ValueError, json.JSONDecodeError) as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
