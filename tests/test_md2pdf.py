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
    def test_glossary_uses_document_evidence(self):
        ast = {
            "blocks": [
                {
                    "t": "DefinitionList",
                    "c": [
                        [
                            [{"t": "Str", "c": "Typst"}],
                            [[{"t": "Plain", "c": [{"t": "Str", "c": "A"}, {"t": "Space"}, {"t": "Str", "c": "typesetting"}, {"t": "Space"}, {"t": "Str", "c": "system."}]}]],
                        ]
                    ],
                },
                {
                    "t": "Para",
                    "c": [
                        {"t": "Str", "c": "Application"},
                        {"t": "Space"},
                        {"t": "Str", "c": "Programming"},
                        {"t": "Space"},
                        {"t": "Str", "c": "Interface"},
                        {"t": "Space"},
                        {"t": "Str", "c": "(API)"},
                    ],
                },
                {
                    "t": "Para",
                    "c": [
                        {"t": "Strong", "c": [{"t": "Str", "c": "Renderer"}]},
                        {"t": "Str", "c": ":"},
                        {"t": "Space"},
                        {"t": "Str", "c": "Builds"},
                        {"t": "Space"},
                        {"t": "Str", "c": "the"},
                        {"t": "Space"},
                        {"t": "Str", "c": "PDF."},
                    ],
                },
            ]
        }
        entries = dict(MD2PDF.extract_glossary(ast))
        self.assertEqual(entries["API"], "Application Programming Interface")
        self.assertEqual(entries["Typst"], "A typesetting system.")
        self.assertEqual(entries["Renderer"], "Builds the PDF.")

    def test_frontmatter_respects_individual_switches(self):
        args = SimpleNamespace(no_toc=False, no_tot=True, no_tof=False)
        text = MD2PDF.render_frontmatter(
            {"headings": 2, "tables": 1, "figures": 1}, MD2PDF.LABELS["en"], args
        )
        self.assertIn("Contents", text)
        self.assertNotIn("List of Tables", text)
        self.assertIn("List of Figures", text)

    def test_style_template_is_fully_resolved(self):
        args = SimpleNamespace(
            style="modern", paper="a4", font=None, mono_font=None, accent="336699"
        )
        style = MD2PDF.render_style(args)
        self.assertNotIn("@@", style)
        self.assertIn('#let md-accent = rgb("#336699")', style)


if __name__ == "__main__":
    unittest.main()
