import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "documents" / "skills" / "md2pdf" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("md2pdf", str(SCRIPTS / "md2pdf.py"))
MD2PDF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MD2PDF)


class Md2PdfTests(unittest.TestCase):
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
