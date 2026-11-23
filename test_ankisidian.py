"""
Ankisidian - Unit Tests
Tests conversion, cloze handling, media extraction, title sanitization,
frontmatter generation, and file exporting.
"""

import os
import shutil
import tempfile
import unittest

from html_to_markdown import (
    anki_html_to_markdown,
    convert_clozes,
    convert_latex,
    convert_sound_tags,
)
from exporter import (
    export_note_data,
    extract_note_title,
    format_obsidian_markdown,
    sanitize_filename,
)
from media import copy_note_media, extract_media_references


class TestHTMLToMarkdown(unittest.TestCase):
    def test_basic_formatting(self):
        html = "<b>Bold</b> and <i>Italic</i> and <s>Strike</s> and <u>Underline</u> and <code>Code</code>"
        md = anki_html_to_markdown(html)
        self.assertIn("**Bold**", md)
        self.assertIn("*Italic*", md)
        self.assertIn("~~Strike~~", md)
        self.assertIn("<u>Underline</u>", md)
        self.assertIn("`Code`", md)

    def test_paragraphs_and_breaks(self):
        html = "<div>Paragraph 1</div><div>Paragraph 2<br>Line 2</div>"
        md = anki_html_to_markdown(html)
        self.assertIn("Paragraph 1", md)
        self.assertIn("Paragraph 2\nLine 2", md)

    def test_lists(self):
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        md = anki_html_to_markdown(html)
        self.assertIn("- Item 1", md)
        self.assertIn("- Item 2", md)

    def test_cloze_conversion(self):
        text = "The capital of France is {{c1::Paris::capital city}}."
        # Highlight style
        highlight_res = convert_clozes(text, style="highlight")
        self.assertEqual(highlight_res, "The capital of France is ==Paris== *(capital city)*.")

        # Bold style
        bold_res = convert_clozes(text, style="bold")
        self.assertEqual(bold_res, "The capital of France is **Paris** *(capital city)*.")

        # Keep style
        keep_res = convert_clozes(text, style="keep")
        self.assertEqual(keep_res, text)

        # Cloze without hint
        simple = "Anki {{c2::flashcards}} are great."
        self.assertEqual(convert_clozes(simple, style="highlight"), "Anki ==flashcards== are great.")

    def test_latex_conversion(self):
        # MathJax inline
        mj_inline = r"Formula: \(E = mc^2\)"
        self.assertEqual(convert_latex(mj_inline), "Formula: $E = mc^2$")

        # MathJax block
        mj_block = r"\[\int_0^1 x dx\]"
        self.assertIn("$$\n\\int_0^1 x dx\n$$", convert_latex(mj_block))

        # Anki latex
        anki_latex = r"[$]x^2 + y^2 = z^2[/$]"
        self.assertEqual(convert_latex(anki_latex), "$x^2 + y^2 = z^2$")

    def test_media_tags(self):
        html = 'Check image: <img src="paste-12345.png" alt="test"> and audio: [sound:rec1.mp3]'
        md = anki_html_to_markdown(html, use_wikilinks=True)
        self.assertIn("![[paste-12345.png]]", md)
        self.assertIn("![[rec1.mp3]]", md)


class TestMediaExtraction(unittest.TestCase):
    def test_extract_media(self):
        fields = [
            'Here is a diagram: <img src="anatomy_brain.png"> and <img src="sub%20folder/heart.jpg">',
            'Pronunciation: [sound:pronounce_brain.mp3]',
            'External ignored: <img src="https://example.com/logo.png">',
        ]
        refs = extract_media_references(fields)
        self.assertIn("anatomy_brain.png", refs)
        self.assertIn("heart.jpg", refs)
        self.assertIn("pronounce_brain.mp3", refs)
        self.assertNotIn("https://example.com/logo.png", refs)

    def test_copy_media(self):
        temp_dir = tempfile.mkdtemp()
        anki_media = os.path.join(temp_dir, "anki_media")
        obs_media = os.path.join(temp_dir, "obs_media")
        os.makedirs(anki_media)

        # Create dummy file
        dummy_file = os.path.join(anki_media, "test_img.png")
        with open(dummy_file, "wb") as f:
            f.write(b"PNG_DATA")

        copied = copy_note_media({"test_img.png"}, anki_media, obs_media)
        self.assertIn("test_img.png", copied)
        self.assertTrue(os.path.isfile(os.path.join(obs_media, "test_img.png")))

        shutil.rmtree(temp_dir)


class TestSanitizeAndTitle(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Normal Title"), "Normal Title")
        self.assertEqual(sanitize_filename("Invalid: / \\ * ? < > | chars"), "Invalid chars")
        self.assertEqual(sanitize_filename("   ...dotted...   "), "dotted")

    def test_extract_note_title(self):
        fields = [
            ("Front", "What is the capital of <b>France</b>?"),
            ("Back", "Paris"),
        ]
        title = extract_note_title(fields, fallback_id=123)
        self.assertEqual(title, "What is the capital of France")

        # Cloze title
        cloze_fields = [
            ("Text", "{{c1::Mitochondria}} is the powerhouse of the cell."),
        ]
        cloze_title = extract_note_title(cloze_fields, fallback_id=456)
        self.assertEqual(cloze_title, "Mitochondria is the powerhouse of the cell")


class TestExporterEndToEnd(unittest.TestCase):
    def test_export_note_data(self):
        temp_dir = tempfile.mkdtemp()
        vault_dir = os.path.join(temp_dir, "MyVault")
        os.makedirs(vault_dir)

        config = {
            "vault_path": vault_dir,
            "target_folder": "Anki Cards",
            "media_folder": "attachments",
            "copy_media": True,
            "frontmatter_enabled": True,
            "cloze_style": "highlight",
            "use_wikilinks": True,
            "file_naming": "{title}",
            "open_in_obsidian_after_export": False,
        }

        fields = [
            ("Front", "<b>Question:</b> What is Python?"),
            ("Back", "Python is an interpreted, high-level programming language."),
        ]

        res = export_note_data(
            note_id=1700100200300,
            card_id=1700100200301,
            deck_name="Computer Science::Languages",
            model_name="Basic",
            tags=["programming", "cs"],
            fields=fields,
            anki_media_dir=None,
            config=config,
        )

        self.assertTrue(res["success"])
        exported_file = res["file_path"]
        self.assertTrue(os.path.isfile(exported_file))

        with open(exported_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check frontmatter
        self.assertIn("---", content)
        self.assertIn("anki_note_id: 1700100200300", content)
        self.assertIn('anki_deck: "Computer Science::Languages"', content)
        self.assertIn("tags:", content)
        self.assertIn("- anki/programming", content)

        # Check fields
        self.assertIn("## Front", content)
        self.assertIn("**Question:** What is Python?", content)
        self.assertIn("## Back", content)
        self.assertIn("Python is an interpreted, high-level programming language.", content)

        # Check backlink
        self.assertIn("anki://search?q=nid:1700100200300", content)

        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
