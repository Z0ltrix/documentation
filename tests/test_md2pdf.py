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

    def render_markdown_text(self, markdown, extra_args):
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
            return self.pdf_text(output, pdftotext)

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

    def test_style_template_is_fully_resolved(self):
        args = SimpleNamespace(
            style="modern", paper="a4", font=None, mono_font=None, accent="336699"
        )
        style = MD2PDF.render_style(args)
        self.assertNotIn("@@", style)
        self.assertIn('#let md-accent = rgb("#336699")', style)


if __name__ == "__main__":
    unittest.main()
