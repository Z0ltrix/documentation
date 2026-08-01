#!/usr/bin/env python3
"""Render Markdown as a styled PDF with Pandoc and Typst."""

import argparse
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
STRUCTURE_FILTER = SCRIPT_DIR / "structure.lua"
GLOSSARY_FILTER = SCRIPT_DIR / "glossary.lua"
DOCUMENT_MODULE = ASSETS_DIR / "document.typ"
READER = "markdown+implicit_figures+definition_lists+fenced_code_attributes+pipe_tables+grid_tables"

PAPERS = {
    "a4": {"typst": "a4", "width": "210mm", "height": "297mm"},
    "letter": {"typst": "us-letter", "width": "8.5in", "height": "11in"},
}

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


class RenderError(RuntimeError):
    pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="Markdown input file")
    parser.add_argument("-o", "--output", type=Path, help="PDF output path")
    parser.add_argument("--style", choices=tuple(THEMES), default="modern")
    parser.add_argument("--paper", choices=tuple(PAPERS), default="a4")
    parser.add_argument("--font", help="Body font family")
    parser.add_argument("--mono-font", help="Monospace font family")
    parser.add_argument("--accent", help="Six-digit theme color, with optional #")
    parser.add_argument("--lang", help="Label language, for example de or en")
    parser.add_argument("--title", help="Override title metadata")
    parser.add_argument("--author", help="Override author metadata")
    parser.add_argument("--no-toc", action="store_true")
    parser.add_argument("--no-tot", action="store_true")
    parser.add_argument("--no-tof", action="store_true")
    parser.add_argument(
        "--glossary", type=Path, metavar="FILE",
        help="YAML glossary file; omitted means no glossary",
    )
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
    paper = PAPERS[args.paper]
    accent = (args.accent or theme["accent"]).lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", accent):
        raise RenderError("--accent must be a six-digit hexadecimal color")
    body_fonts = [args.font] if args.font else theme["body_fonts"]
    mono_fonts = [args.mono_font] if args.mono_font else theme["mono_fonts"]
    template = (ASSETS_DIR / "styles" / "{}.typ".format(args.style)).read_text(encoding="utf-8")
    replacements = {
        "@@PAPER@@": paper["typst"],
        "@@PAGE_WIDTH@@": paper["width"],
        "@@PAGE_HEIGHT@@": paper["height"],
        "@@ACCENT@@": accent.lower(),
        "@@BODY_FONT@@": typst_font_tuple(body_fonts),
        "@@MONO_FONT@@": typst_font_tuple(mono_fonts),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    return template


def build_pandoc_command(args, source, work, style_path, generated_typst, staged_glossary=None):
    command = [
        "pandoc",
        source.name,
        "--from",
        READER,
        "--to",
        "typst",
        "--standalone",
        "--lua-filter",
        SCRIPT_DIR / "captions.lua",
        "--lua-filter",
        STRUCTURE_FILTER,
        "--template",
        DOCUMENT_MODULE,
        "--include-in-header",
        style_path,
        "--metadata",
        "md2pdf-toc={}".format(str(not args.no_toc).lower()),
        "--metadata",
        "md2pdf-tot={}".format(str(not args.no_tot).lower()),
        "--metadata",
        "md2pdf-tof={}".format(str(not args.no_tof).lower()),
        "--output",
        generated_typst,
    ]
    if staged_glossary is not None:
        glossary_path = Path(os.path.relpath(staged_glossary, source.parent)).as_posix()
        command.extend([
            "--lua-filter",
            GLOSSARY_FILTER,
            "--metadata",
            "md2pdf-glossary={}".format(glossary_path),
        ])
    if args.title:
        command.extend(["--metadata", "title={}".format(args.title)])
    if args.author:
        command.extend(["--metadata", "author={}".format(args.author)])
    if args.lang:
        command.extend(["--metadata", "lang={}".format(args.lang)])
    return command


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
    glossary = None
    if args.glossary:
        glossary = args.glossary.expanduser().resolve()
        if not glossary.is_file():
            raise RenderError("Glossary file not found: {}".format(glossary))
    output = (args.output or source.with_suffix(".pdf")).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    style_text = render_style(args)
    generated_typst = source.parent / ".md2pdf-{}.typ".format(uuid.uuid4().hex)
    try:
        with tempfile.TemporaryDirectory(prefix=".md2pdf-", dir=str(source.parent)) as work_name:
            work = Path(work_name)
            style_path = work / "style.typ"
            rendered_pdf = work / "rendered.pdf"
            staged_glossary = work / "glossary.yml" if glossary else None
            style_path.write_text(style_text, encoding="utf-8")
            if staged_glossary:
                shutil.copy2(str(glossary), str(staged_glossary))
            command = build_pandoc_command(
                args, source, work, style_path, generated_typst, staged_glossary
            )
            command[0] = pandoc
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

    print("Created: {}".format(output))
    print(
        "Sections: toc={}, tables={}, figures={}, glossary={}".format(
            "off" if args.no_toc else "auto",
            "off" if args.no_tot else "auto",
            "off" if args.no_tof else "auto",
            glossary.name if glossary else "off",
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
    except (RenderError, OSError, ValueError) as error:
        print("error: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
