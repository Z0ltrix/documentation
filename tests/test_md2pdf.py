import importlib.util
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "documents" / "skills" / "md2pdf" / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("md2pdf", str(SCRIPTS / "md2pdf.py"))
MD2PDF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MD2PDF)


class Md2PdfTests(unittest.TestCase):
    def test_documentation_matches_opt_in_glossary_contract(self):
        paths = [
            ROOT / "plugins" / "documents" / "skills" / "md2pdf" / "SKILL.md",
            ROOT / "plugins" / "documents" / "skills" / "md2pdf" / "references" / "cli.md",
            ROOT / "plugins" / "documents" / ".codex-plugin" / "plugin.json",
            ROOT / "README.md",
            FIXTURES / "demo.md",
        ]
        documents = [path.read_text(encoding="utf-8") for path in paths]
        combined = "\n".join(documents)
        description = next(
            line[len("description: "):]
            for line in documents[0].splitlines()
            if line.startswith("description: ")
        )

        self.assertNotIn("--no-glossary", combined)
        self.assertIn("--glossary", combined)
        self.assertIn("glossary.yml", combined)
        self.assertIn("a unique, non-empty string `key`", documents[1])
        self.assertIn(
            "`short` and `description` are required strings", documents[1]
        )
        self.assertIn("`long` is an optional string", documents[1])
        self.assertIn("`aliases` is an optional array of strings", documents[1])
        self.assertTrue(description.startswith("Use when"))
        self.assertNotIn("glossary by default", combined.lower())

    def require_render_tools(self):
        pandoc = MD2PDF.find_tool("pandoc")
        typst = MD2PDF.find_tool("typst")
        git = shutil.which("git")
        git_pdftotext = (
            Path(git).resolve().parents[1] / "mingw64" / "bin" / "pdftotext.exe"
            if git else None
        )
        pdftotext = (
            str(git_pdftotext) if git_pdftotext and git_pdftotext.is_file()
            else shutil.which("pdftotext")
        )
        if not (pandoc and typst and pdftotext):
            self.skipTest("Pandoc, Typst, and pdftotext are required")
        return pdftotext

    def pdf_text(self, pdf, pdftotext):
        result = subprocess.run(
            [pdftotext, str(pdf), "-"], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def render_demo_text(self, extra_args):
        pdftotext = self.require_render_tools()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "demo.md"
            image = root / "architecture.svg"
            output = root / "demo.pdf"
            shutil.copy2(str(FIXTURES / "demo.md"), str(source))
            shutil.copy2(str(FIXTURES / "architecture.svg"), str(image))
            with redirect_stderr(io.StringIO()):
                code = MD2PDF.main([str(source), "--output", str(output)] + extra_args)
            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())
            return self.pdf_text(output, pdftotext)

    def render_markdown(self, markdown, extra_args):
        pdftotext = self.require_render_tools()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "input.md"
            output = root / "output.pdf"
            source.write_text(markdown, encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = MD2PDF.main([str(source), "--output", str(output)] + extra_args)
            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())
            return self.pdf_text(output, pdftotext), output.read_bytes()

    def render_markdown_text(self, markdown, extra_args):
        return self.render_markdown(markdown, extra_args)[0]

    def assert_glossary_error(self, glossary_path, expected):
        self.require_render_tools()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "input.md"
            output = root / "output.pdf"
            source.write_text("# Test\n\nAPI is used.\n", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = MD2PDF.main([
                    str(source), "--output", str(output),
                    "--glossary", str(glossary_path),
                ])
            self.assertEqual(code, 1)
            self.assertIn(expected, stderr.getvalue())
            self.assertFalse(output.exists())

    def test_typst_builds_all_available_indexes(self):
        text = self.render_demo_text([])
        self.assertIn("Inhaltsverzeichnis", text)
        self.assertIn("Tabellenverzeichnis", text)
        self.assertIn("Abbildungsverzeichnis", text)

    def test_typst_respects_each_index_switch(self):
        text = self.render_demo_text(["--no-tot"])
        index_titles = {
            line.split(maxsplit=1)[1]
            for line in text.splitlines()
            if len(line.split(maxsplit=1)) == 2 and line.split(maxsplit=1)[0].isdigit()
        }
        self.assertIn("Inhaltsverzeichnis", text)
        self.assertNotIn("Tabellenverzeichnis", index_titles)
        self.assertIn("Abbildungsverzeichnis", text)

    def test_glossary_is_an_optional_path(self):
        disabled = MD2PDF.parse_args(["document.md"])
        enabled = MD2PDF.parse_args(["document.md", "--glossary", "terms.yml"])
        self.assertIsNone(disabled.glossary)
        self.assertEqual(enabled.glossary, Path("terms.yml"))
        self.assertFalse(hasattr(enabled, "no_glossary"))

    def test_no_glossary_is_rejected(self):
        with self.assertRaises(SystemExit):
            MD2PDF.parse_args(["document.md", "--no-glossary"])

    def test_pandoc_command_enables_glossary_only_with_a_staged_file(self):
        args = SimpleNamespace(
            no_toc=False, no_tot=True, no_tof=False,
            title=None, author=None, lang=None,
        )
        without = MD2PDF.build_pandoc_command(
            args, Path("document.md"), Path(".md2pdf-work"), Path("style.typ"),
            Path("document.typ"), None,
        )
        with_file = MD2PDF.build_pandoc_command(
            args, Path("document.md"), Path(".md2pdf-work"), Path("style.typ"),
            Path("document.typ"), Path(".md2pdf-work/glossary.yml"),
        )
        self.assertNotIn(str(MD2PDF.GLOSSARY_FILTER), [str(p) for p in without])
        self.assertIn(str(MD2PDF.GLOSSARY_FILTER), [str(p) for p in with_file])
        self.assertNotIn("md2pdf-glossary", " ".join(map(str, without)))
        self.assertIn("md2pdf-glossary=.md2pdf-work/glossary.yml", " ".join(map(str, with_file)))

    def test_glossary_flag_prints_only_used_entries(self):
        text = self.render_markdown_text(
            "# Test\n\nThe Application Programming Interface (API) is used here.\n",
            ["--glossary", str(FIXTURES / "glossary.yml")],
        )
        self.assertIn("Glossary", text)
        self.assertIn("A defined interface used by software systems", text)
        self.assertNotIn("This description must never appear", text)

    def test_glossary_is_absent_without_flag(self):
        text = self.render_markdown_text("# Test\n\nAPI is used here.\n", [])
        self.assertNotIn("Glossary", text)

    def test_code_only_term_does_not_create_empty_glossary(self):
        text = self.render_markdown_text(
            "# Test\n\n`Typst`\n\n```text\nAPI\n```\n",
            ["--glossary", str(FIXTURES / "glossary.yml")],
        )
        self.assertNotIn("Glossary", text)

    def test_glossary_matches_table_prose_but_skips_non_prose_contexts(self):
        text = self.render_markdown_text(
            "# Unused Term\n\n"
            "[reference](https://example.com/Typst)\n\n"
            "| Term |\n| --- |\n| Programmierschnittstelle |\n\n"
            ": Typst\n",
            ["--glossary", str(FIXTURES / "glossary.yml")],
        )
        self.assertIn("Glossary", text)
        body, glossary = text.split("Glossary", 1)
        self.assertIn("Programmierschnittstelle", body)
        self.assertIn("A defined interface used by software systems", glossary)
        self.assertNotIn("A programmable typesetting system", glossary)
        self.assertNotIn("This description must never appear", glossary)

    def test_glossary_matches_formatted_longest_candidate(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "overlap.yml"
            path.write_text(
                "- key: application\n"
                "  short: Application\n"
                "  description: Short candidate only.\n"
                "- key: api\n"
                "  short: Application Programming Interface\n"
                "  description: Long formatted candidate.\n",
                encoding="utf-8",
            )
            text = self.render_markdown_text(
                "# Test\n\nApplication *Programming* Interface.\n",
                ["--glossary", str(path)],
            )
        body, glossary = text.split("Glossary", 1)
        self.assertIn("Application Programming Interface", body)
        self.assertIn("Long formatted candidate", glossary)
        self.assertNotIn("Short candidate only", glossary)

    def test_glossary_normalizes_source_line_softbreak(self):
        text = self.render_markdown_text(
            "# Test\n\nApplication Programming\nInterface is used.\n",
            ["--glossary", str(FIXTURES / "glossary.yml")],
        )
        self.assertIn("A defined interface used by software systems", text)

    def test_glossary_uses_unicode_word_boundaries_and_links_matches(self):
        markdown = "# Test\n\nAPI‑ API， API😀 APIÄ API界\n"
        _, plain_pdf = self.render_markdown(markdown, [])
        text, glossary_pdf = self.render_markdown(
            markdown, ["--glossary", str(FIXTURES / "glossary.yml")]
        )
        self.assertIn("A defined interface used by software systems", text)
        plain_links = plain_pdf.count(b"/Subtype /Link")
        glossary_links = glossary_pdf.count(b"/Subtype /Link")
        self.assertEqual(glossary_links - plain_links, 3)

    def test_glossary_treats_arabic_and_cjk_punctuation_as_boundaries(self):
        markdown = "# Test\n\nAPI، API。\n"
        _, plain_pdf = self.render_markdown(markdown, [])
        _, glossary_pdf = self.render_markdown(
            markdown, ["--glossary", str(FIXTURES / "glossary.yml")]
        )
        plain_links = plain_pdf.count(b"/Subtype /Link")
        glossary_links = glossary_pdf.count(b"/Subtype /Link")
        self.assertEqual(glossary_links - plain_links, 2)

    def test_glossary_treats_cjk_iteration_mark_as_word_continuation(self):
        markdown = "# Test\n\nAPI々\n"
        _, plain_pdf = self.render_markdown(markdown, [])
        _, glossary_pdf = self.render_markdown(
            markdown, ["--glossary", str(FIXTURES / "glossary.yml")]
        )
        plain_links = plain_pdf.count(b"/Subtype /Link")
        glossary_links = glossary_pdf.count(b"/Subtype /Link")
        self.assertEqual(glossary_links - plain_links, 0)

    def test_glossary_distinguishes_letterlike_symbols_from_letters_and_numbers(self):
        markdown = "# Test\n\nAPI™ API℃ APIℂ APIⅣ\n"
        _, plain_pdf = self.render_markdown(markdown, [])
        _, glossary_pdf = self.render_markdown(
            markdown, ["--glossary", str(FIXTURES / "glossary.yml")]
        )
        plain_links = plain_pdf.count(b"/Subtype /Link")
        glossary_links = glossary_pdf.count(b"/Subtype /Link")
        self.assertEqual(glossary_links - plain_links, 2)

    def test_glossary_registers_footnote_prose(self):
        text = self.render_markdown_text(
            "# Test\n\nText with a note.[^1]\n\n[^1]: Typst appears here.\n",
            ["--glossary", str(FIXTURES / "glossary.yml")],
        )
        self.assertIn("Typst appears here", text)
        self.assertIn("A programmable typesetting system", text)

    def test_missing_glossary_file_is_rejected(self):
        self.assert_glossary_error(
            Path("missing-glossary.yml"), "Glossary file not found"
        )

    def test_duplicate_glossary_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "duplicate.yml"
            path.write_text(
                "- key: api\n  short: API\n  description: First.\n"
                "- key: api\n  short: API2\n  description: Second.\n",
                encoding="utf-8",
            )
            self.assert_glossary_error(path, "duplicate glossary key: api")

    def test_missing_glossary_description_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "missing-description.yml"
            path.write_text("- key: api\n  short: API\n", encoding="utf-8")
            self.assert_glossary_error(path, "description")

    def test_malformed_glossary_yaml_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "malformed.yml"
            path.write_text("- key: api\n  short: [API\n", encoding="utf-8")
            self.assert_glossary_error(path, "YAML")

    def test_style_template_is_fully_resolved(self):
        args = SimpleNamespace(
            style="modern", paper="a4", font=None, mono_font=None, accent="336699"
        )
        style = MD2PDF.render_style(args)
        self.assertNotIn("@@", style)
        self.assertIn('#let md-accent = rgb("#336699")', style)


if __name__ == "__main__":
    unittest.main()
