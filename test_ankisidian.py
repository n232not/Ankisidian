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
    append_to_daily_note,
    export_note_data,
    extract_card_stats,
    extract_note_title,
    format_obsidian_markdown,
    generate_dataview_dashboard,
    get_base_target_dir,
    resolve_target_paths,
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
        self.assertEqual(title, "What is the capital of France?")
        self.assertEqual(sanitize_filename(title), "What is the capital of France")

        # Cloze title
        cloze_fields = [
            ("Text", "{{c1::Mitochondria}} is the powerhouse of the cell."),
        ]
        cloze_title = extract_note_title(cloze_fields, fallback_id=456)
        self.assertEqual(cloze_title, "Mitochondria is the powerhouse of the cell.")
        self.assertEqual(sanitize_filename(cloze_title), "Mitochondria is the powerhouse of the cell")

    def test_long_title_not_truncated(self):
        long_q = "What is the primary mechanism of action of nonsteroidal anti-inflammatory drugs (NSAIDs) regarding cyclooxygenase-1 and cyclooxygenase-2 inhibition and prostaglandin synthesis?"
        fields = [("Front", long_q), ("Back", "Inhibition of COX")]
        title = extract_note_title(fields, fallback_id=1)
        self.assertEqual(title, long_q)
        fn = sanitize_filename(long_q, max_len=240)
        self.assertGreater(len(fn), 100)


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
            ("Extra", "Created by Guido van Rossum in 1991."),
            ("Missed Questions", "Difference between interpreted and compiled?"),
            ("Lecture Notes", "Covered in CS101 Week 2."),
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

        # Check frontmatter contains all metadata
        self.assertIn("---", content)
        self.assertIn("anki_note_id: 1700100200300", content)
        self.assertIn('anki_deck: "Computer Science::Languages"', content)
        self.assertIn("tags:", content)
        self.assertIn("- anki/programming", content)

        # Body should NOT contain redundant Anki Details callout
        self.assertNotIn("📋 Anki Details", content)

        # Check pure card fields in main body
        self.assertIn("## Front", content)
        self.assertIn("**Question:** What is Python?", content)
        self.assertIn("## Back", content)
        self.assertIn("Python is an interpreted, high-level programming language.", content)

        # Check supplementary fields callout (Extra, Missed Questions, Lecture Notes)
        self.assertIn("> [!note]- 📑 Extra & Notes", content)
        self.assertIn("> #### Extra", content)
        self.assertIn("Created by Guido van Rossum in 1991.", content)
        self.assertIn("> #### Missed Questions", content)
        self.assertIn("Difference between interpreted and compiled?", content)
        self.assertIn("> #### Lecture Notes", content)
        self.assertIn("Covered in CS101 Week 2.", content)

        # Check Anki backlink inside callout
        self.assertIn("anki://search?q=nid:1700100200300", content)

        shutil.rmtree(temp_dir)

    def test_card_stats_extraction(self):
        class DummyCard:
            reps = 8
            lapses = 2
            factor = 2500
            ivl = 30
            queue = 2
            due = 150
            flags = 1  # Red

        card = DummyCard()
        stats = extract_card_stats(card)
        self.assertEqual(stats["reps"], 8)
        self.assertEqual(stats["lapses"], 2)
        self.assertEqual(stats["ease"], "250%")
        self.assertEqual(stats["interval_days"], 30)
        self.assertEqual(stats["state"], "Review")
        self.assertEqual(stats["flag"], "Red")

        # Test inclusion in formatted markdown (stats in frontmatter)
        _, md = format_obsidian_markdown(
            note_id=123,
            card_id=456,
            deck_name="Cardiology",
            model_name="Basic",
            tags=["med"],
            fields=[("Front", "ECG"), ("Back", "Wave")],
            config={"show_anki_details_callout": True},
            card_stats=stats,
        )
        self.assertIn('anki_ease: "250%"', md)
        self.assertIn("anki_interval_days: 30", md)
        self.assertIn('anki_flag: "Red"', md)
        self.assertIn("Interval: `30d` | Ease: `250%` | Reps: `8` | Lapses: `2`", md)
        self.assertIn("🚩 `Red`", md)

    def test_mirror_deck_hierarchy(self):
        config = {
            "vault_path": "/test/vault",
            "target_folder": "Anki Cards",
            "mirror_deck_hierarchy": True,
        }
        target_dir, _ = resolve_target_paths(config, deck_name="Medicine::Cardiology::Arrhythmias")
        self.assertTrue(target_dir.endswith(os.path.join("Anki Cards", "Medicine", "Cardiology", "Arrhythmias")))

        # Test disabled
        config["mirror_deck_hierarchy"] = False
        target_dir_flat, _ = resolve_target_paths(config, deck_name="Medicine::Cardiology::Arrhythmias")
        self.assertTrue(target_dir_flat.endswith("Anki Cards"))

    def test_append_to_daily_note(self):
        temp_dir = tempfile.mkdtemp()
        vault_dir = os.path.join(temp_dir, "MyVault")
        os.makedirs(vault_dir)

        config = {
            "vault_path": vault_dir,
            "daily_note_folder": "Daily Notes",
            "daily_note_format": "%Y-%m-%d",
            "daily_note_heading": "## Anki Reviews",
            "copy_media": False,
        }

        res = append_to_daily_note(
            note_id=777,
            card_id=888,
            deck_name="German::Vocab",
            model_name="Basic",
            tags=["vocab"],
            fields=[("Front", "der Hund"), ("Back", "the dog")],
            card_stats={"interval": "10d", "ease": "240%"},
            anki_media_dir=None,
            config=config,
        )

        self.assertTrue(res["success"])
        daily_file = res["file_path"]
        self.assertTrue(os.path.isfile(daily_file))

        with open(daily_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("## Anki Reviews", content)
        self.assertIn("### der Hund", content)
        self.assertIn("the dog", content)
        self.assertIn("German::Vocab", content)
        self.assertIn("anki://search?q=nid:777", content)

        # Test duplicate append prevention
        res2 = append_to_daily_note(
            note_id=777,
            card_id=888,
            deck_name="German::Vocab",
            model_name="Basic",
            tags=["vocab"],
            fields=[("Front", "der Hund"), ("Back", "the dog")],
            card_stats=None,
            anki_media_dir=None,
            config=config,
        )
        self.assertTrue(res2["already_appended"])

        shutil.rmtree(temp_dir)

    def test_details_style_metadata(self):
        temp_dir = tempfile.mkdtemp()
        vault_dir = os.path.join(temp_dir, "MyVault")
        os.makedirs(vault_dir)

        config = {
            "vault_path": vault_dir,
            "target_folder": "Anki Cards",
            "metadata_section_style": "details",
            "metadata_collapsed": True,
            "copy_media": False,
        }

        res = export_note_data(
            note_id=999,
            card_id=None,
            deck_name="TestDeck",
            model_name="Basic",
            tags=["test"],
            fields=[("Front", "Q"), ("Back", "A"), ("Extra", "Extra Notes")],
            anki_media_dir=None,
            config=config,
        )

        with open(res["file_path"], "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("<details>\n<summary>📑 Extra & Notes</summary>", content)
        self.assertIn("</details>", content)
        self.assertIn("Extra Notes", content)
        self.assertIn("## Front\n\nQ\n\n## Back\n\nA", content)

        shutil.rmtree(temp_dir)

    def test_reviewer_quick_key_hook(self):
        from __init__ import on_state_shortcuts_will_change
        shortcuts = [("1", lambda: None), ("2", lambda: None)]
        on_state_shortcuts_will_change("review", shortcuts)
        keys = [k for k, _ in shortcuts]
        self.assertIn("5", keys)

    def test_high_difficulty_repeat_export(self):
        temp_dir = tempfile.mkdtemp()
        vault_dir = os.path.join(temp_dir, "MyVault")
        os.makedirs(vault_dir)

        config = {
            "vault_path": vault_dir,
            "target_folder": "Anki Notes",
            "copy_media": False,
            "high_difficulty_folder_enabled": True,
            "high_difficulty_folder_name": "High Difficulty",
            "exported_tag_name": "obsidian_exported",
            "create_dataview_dashboard": False,
        }

        # First export -> standard folder
        res1 = export_note_data(
            note_id=1001,
            card_id=2001,
            deck_name="Cardiology",
            model_name="Basic",
            tags=["medicine"],
            fields=[("Front", "What is WPW syndrome?"), ("Back", "Pre-excitation syndrome.")],
            anki_media_dir=None,
            config=config,
            is_repeat_export=False,
        )
        self.assertTrue(res1["success"])
        self.assertFalse(res1["is_high_difficulty"])
        standard_path = res1["file_path"]
        self.assertTrue(os.path.isfile(standard_path))
        self.assertNotIn("High Difficulty", standard_path)

        # Second export (repeat) -> routes to High Difficulty folder & cleans up standard folder
        res2 = export_note_data(
            note_id=1001,
            card_id=2001,
            deck_name="Cardiology",
            model_name="Basic",
            tags=["medicine", "obsidian_exported"],
            fields=[("Front", "What is WPW syndrome?"), ("Back", "Pre-excitation syndrome.")],
            anki_media_dir=None,
            config=config,
            is_repeat_export=True,
        )
        self.assertTrue(res2["success"])
        self.assertTrue(res2["is_high_difficulty"])
        high_diff_path = res2["file_path"]
        self.assertTrue(os.path.isfile(high_diff_path))
        self.assertIn("High Difficulty", high_diff_path)
        # Previous standard copy should be removed to avoid duplication
        self.assertFalse(os.path.exists(standard_path))

        with open(high_diff_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('anki_difficulty: "High"', content)
        self.assertIn("anki_export_count: 2", content)
        self.assertIn("🔥 **High Difficulty / Struggle Card**", content)

        shutil.rmtree(temp_dir)

    def test_generate_dataview_dashboard(self):
        temp_dir = tempfile.mkdtemp()
        vault_dir = os.path.join(temp_dir, "MyVault")
        os.makedirs(vault_dir)

        config = {
            "vault_path": vault_dir,
            "target_folder": "Anki Notes",
            "dashboard_filename": "Anki Dashboard.md",
            "high_difficulty_folder_name": "High Difficulty",
        }

        res = generate_dataview_dashboard(config, overwrite=True)
        self.assertTrue(res["success"])
        dash_file = res["file_path"]
        self.assertTrue(os.path.isfile(dash_file))

        with open(dash_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("# 📊 Anki Obsidian Hub & Dataview Dashboard", content)
        self.assertIn("```dataview", content)
        self.assertIn('FROM "Anki Notes"', content)
        self.assertIn('anki_difficulty = "High"', content)
        self.assertIn("anki_lapses", content)
        self.assertIn("High Difficulty", content)

        shutil.rmtree(temp_dir)

    def test_auto_tag_note(self):
        from __init__ import is_note_already_exported, tag_note_as_exported

        class DummyNote:
            def __init__(self):
                self.tags = ["med", "cardio"]

            def has_tag(self, tag):
                return tag.lower() in [t.lower() for t in self.tags]

            def add_tag(self, tag):
                if not self.has_tag(tag):
                    self.tags.append(tag)

        note = DummyNote()
        config = {"auto_tag_on_export": True, "exported_tag_name": "obsidian_exported"}

        self.assertFalse(is_note_already_exported(note, config))
        tag_note_as_exported(note, col=None, config=config)
        self.assertTrue(is_note_already_exported(note, config))
        self.assertIn("obsidian_exported", note.tags)


if __name__ == "__main__":
    unittest.main()
