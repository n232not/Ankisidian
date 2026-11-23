"""
Ankisidian - Settings Dialog
Provides a user-friendly graphical configuration UI inside Anki
with folder browse dialogs, shortcut customization, and formatting controls.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

try:
    from aqt.qt import (
        QCheckBox,
        QComboBox,
        QDialog,
        QFileDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        Qt,
    )
except ImportError:
    QDialog = object  # type: ignore


class AnkisidianSettingsDialog(QDialog):
    def __init__(
        self,
        parent: Any,
        config: Dict[str, Any],
        on_save_callback: Callable[[Dict[str, Any]], None],
        on_reset_button_pos: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.config = dict(config)
        self.on_save_callback = on_save_callback
        self.on_reset_button_pos = on_reset_button_pos

        self.setWindowTitle("Ankisidian Settings")
        self.setMinimumWidth(560)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)

        # Header Title
        title_label = QLabel("<h2>💎 Ankisidian — Obsidian Export Settings</h2>")
        main_layout.addWidget(title_label)

        # ----------------- Vault & Destination Group -----------------
        vault_group = QGroupBox("Obsidian Vault & Destination")
        vault_layout = QFormLayout(vault_group)

        # Vault Path with Browse Button
        vault_path_layout = QHBoxLayout()
        self.vault_edit = QLineEdit(self.config.get("vault_path", ""))
        self.vault_edit.setPlaceholderText("/Users/username/Documents/ObsidianVault")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_vault)
        vault_path_layout.addWidget(self.vault_edit)
        vault_path_layout.addWidget(browse_btn)
        vault_layout.addRow("Obsidian Vault Path:", vault_path_layout)

        # Target Subfolder
        self.target_edit = QLineEdit(self.config.get("target_folder", "Anki Notes"))
        self.target_edit.setPlaceholderText("Anki Notes (subfolder inside vault)")
        vault_layout.addRow("Target Subfolder:", self.target_edit)

        # Media Subfolder
        self.media_edit = QLineEdit(self.config.get("media_folder", "attachments"))
        self.media_edit.setPlaceholderText("attachments")
        vault_layout.addRow("Media Subfolder:", self.media_edit)

        # Copy Media Checkbox
        self.copy_media_cb = QCheckBox("Copy card images and audio to Obsidian attachments folder")
        self.copy_media_cb.setChecked(self.config.get("copy_media", True))
        vault_layout.addRow("", self.copy_media_cb)

        # Mirror Deck Hierarchy
        self.mirror_deck_cb = QCheckBox("Mirror Anki subdeck hierarchy into Obsidian subfolders")
        self.mirror_deck_cb.setChecked(self.config.get("mirror_deck_hierarchy", False))
        vault_layout.addRow("", self.mirror_deck_cb)

        # Daily Note Integration
        self.daily_note_cb = QCheckBox("Enable 'Append to Daily Note' feature")
        self.daily_note_cb.setChecked(self.config.get("daily_note_enabled", True))
        vault_layout.addRow("", self.daily_note_cb)

        self.daily_folder_edit = QLineEdit(self.config.get("daily_note_folder", "Daily Notes"))
        self.daily_folder_edit.setPlaceholderText("Daily Notes")
        vault_layout.addRow("Daily Notes Folder:", self.daily_folder_edit)

        self.daily_heading_edit = QLineEdit(self.config.get("daily_note_heading", "## Anki Reviews"))
        self.daily_heading_edit.setPlaceholderText("## Anki Reviews")
        vault_layout.addRow("Daily Note Heading:", self.daily_heading_edit)

        # Open in Obsidian after export
        self.open_obsidian_cb = QCheckBox("Open note in Obsidian immediately after export")
        self.open_obsidian_cb.setChecked(self.config.get("open_in_obsidian_after_export", False))
        vault_layout.addRow("", self.open_obsidian_cb)

        main_layout.addWidget(vault_group)

        # ----------------- Interface & Controls Group -----------------
        ui_group = QGroupBox("Keybinds & Draggable Floating Button")
        ui_layout = QFormLayout(ui_group)

        # Keybind
        self.shortcut_edit = QLineEdit(self.config.get("shortcut", "Ctrl+Shift+O"))
        self.shortcut_edit.setPlaceholderText("e.g. Ctrl+Shift+O or Cmd+Shift+O")
        ui_layout.addRow("Transfer Keybind:", self.shortcut_edit)

        # Reviewer Quick Key (e.g. 5)
        self.rev_key_edit = QLineEdit(self.config.get("reviewer_quick_key", "5"))
        self.rev_key_edit.setPlaceholderText("e.g. 5")
        ui_layout.addRow("Reviewer Quick Key (e.g. 5):", self.rev_key_edit)

        hint_rev = QLabel("<span style='color: #6b7280; font-size: 11px;'>Press this single key (e.g. <b>5</b>) during review to instantly export without any modifier keys!</span>")
        ui_layout.addRow("", hint_rev)

        # Daily Note Keybind
        self.daily_shortcut_edit = QLineEdit(self.config.get("daily_note_shortcut", "Ctrl+Alt+D"))
        self.daily_shortcut_edit.setPlaceholderText("e.g. Ctrl+Alt+D or Cmd+Option+D")
        ui_layout.addRow("Daily Note Keybind:", self.daily_shortcut_edit)

        # Draggable Button Toggle
        self.show_button_cb = QCheckBox("Show floating draggable button on Anki window")
        self.show_button_cb.setChecked(self.config.get("show_draggable_button", True))
        ui_layout.addRow("", self.show_button_cb)

        hint_label = QLabel("<span style='color: #6b7280; font-size: 11px;'>Turn this OFF to use only the keybind without any on-screen button.</span>")
        ui_layout.addRow("", hint_label)

        # Button Label
        self.btn_label_edit = QLineEdit(self.config.get("button_label", "📓 To Obsidian"))
        ui_layout.addRow("Button Text:", self.btn_label_edit)

        # Reset Button Position button
        reset_pos_btn = QPushButton("Reset Button Position to Default")
        reset_pos_btn.clicked.connect(self._reset_position)
        ui_layout.addRow("", reset_pos_btn)

        main_layout.addWidget(ui_group)

        # ----------------- Markdown & Formatting Group -----------------
        format_group = QGroupBox("Formatting & Metadata")
        format_layout = QFormLayout(format_group)

        # Spaced Repetition Stats
        self.include_stats_cb = QCheckBox("Include spaced repetition review stats (Interval, Ease, Reps, Lapses, Due)")
        self.include_stats_cb.setChecked(self.config.get("include_stats", True))
        format_layout.addRow("", self.include_stats_cb)

        # Cloze Format Dropdown
        self.cloze_combo = QComboBox()
        self.cloze_combo.addItem("Obsidian Highlight: ==answer==", "highlight")
        self.cloze_combo.addItem("Bold: **answer**", "bold")
        self.cloze_combo.addItem("Preserve Anki Cloze: {{c1::answer}}", "keep")
        self.cloze_combo.addItem("Spoiler / Comment: %%answer%%", "spoiler")

        curr_cloze = self.config.get("cloze_style", "highlight")
        idx = self.cloze_combo.findData(curr_cloze)
        if idx >= 0:
            self.cloze_combo.setCurrentIndex(idx)
        format_layout.addRow("Cloze Deletion Style:", self.cloze_combo)

        # Frontmatter Toggle
        self.frontmatter_cb = QCheckBox("Include YAML frontmatter (note ID, deck, tags, date)")
        self.frontmatter_cb.setChecked(self.config.get("frontmatter_enabled", True))
        format_layout.addRow("", self.frontmatter_cb)

        # Minimizable Supplementary Fields Callout
        self.collapse_extra_cb = QCheckBox("Collapse supplementary fields (Extra, Missed Questions, Lecture Notes) into callout")
        self.collapse_extra_cb.setChecked(self.config.get("collapse_supplementary_fields", True))
        format_layout.addRow("", self.collapse_extra_cb)

        self.primary_fields_edit = QLineEdit(self.config.get("primary_fields", "Front, Back, Text, Question, Answer"))
        self.primary_fields_edit.setPlaceholderText("Front, Back, Text, Question, Answer")
        format_layout.addRow("Primary Fields (Direct Body):", self.primary_fields_edit)

        self.callout_title_edit = QLineEdit(self.config.get("supplementary_callout_title", "📑 Extra & Notes"))
        self.callout_title_edit.setPlaceholderText("📑 Extra & Notes")
        format_layout.addRow("Callout Header Title:", self.callout_title_edit)

        self.meta_style_combo = QComboBox()
        self.meta_style_combo.addItem("Obsidian Callout: > [!note]- 📑 Extra & Notes", "callout")
        self.meta_style_combo.addItem("HTML Details: <details><summary>", "details")
        style_idx = self.meta_style_combo.findData(self.config.get("metadata_section_style", "callout"))
        if style_idx >= 0:
            self.meta_style_combo.setCurrentIndex(style_idx)
        format_layout.addRow("Callout Syntax Style:", self.meta_style_combo)

        self.meta_collapsed_cb = QCheckBox("Start supplementary callout minimized (collapsed) by default")
        self.meta_collapsed_cb.setChecked(self.config.get("metadata_collapsed", True))
        format_layout.addRow("", self.meta_collapsed_cb)

        self.anki_details_cb = QCheckBox("Include redundant 'Anki Details' metadata callout in note body")
        self.anki_details_cb.setChecked(self.config.get("show_anki_details_callout", False))
        format_layout.addRow("", self.anki_details_cb)

        # Tag Prefix
        self.tag_prefix_edit = QLineEdit(self.config.get("tag_prefix", "anki/"))
        self.tag_prefix_edit.setPlaceholderText("e.g. anki/ or leave empty")
        format_layout.addRow("Tag Prefix:", self.tag_prefix_edit)

        # Max Filename Length
        self.max_len_edit = QLineEdit(str(self.config.get("max_filename_length", 240)))
        self.max_len_edit.setPlaceholderText("240 (OS limit is 255)")
        format_layout.addRow("Max Filename Length:", self.max_len_edit)

        # Use Wikilinks for images
        self.wikilinks_cb = QCheckBox("Use Obsidian Wikilinks ![[image.png]] for images and audio")
        self.wikilinks_cb.setChecked(self.config.get("use_wikilinks", True))
        format_layout.addRow("", self.wikilinks_cb)

        main_layout.addWidget(format_group)

        # ----------------- Action Buttons -----------------
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setDefault(True)
        save_btn.setStyleSheet(
            "background-color: #7c3aed; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;"
        )
        save_btn.clicked.connect(self._save_settings)
        btn_box.addWidget(save_btn)

        main_layout.addLayout(btn_box)

    def _browse_vault(self):
        start_dir = self.vault_edit.text().strip() or os.path.expanduser("~/Documents")
        chosen = QFileDialog.getExistingDirectory(self, "Select Obsidian Vault Directory", start_dir)
        if chosen:
            self.vault_edit.setText(chosen)

    def _reset_position(self):
        self.config["button_position"] = [20, 80]
        if self.on_reset_button_pos:
            self.on_reset_button_pos()
        QMessageBox.information(self, "Position Reset", "Floating button position reset to (20, 80).")

    def _save_settings(self):
        new_vault = self.vault_edit.text().strip()
        new_target = self.target_edit.text().strip()

        if not new_vault and not new_target:
            QMessageBox.warning(
                self,
                "Vault Path Missing",
                "Please specify an Obsidian Vault path or a destination folder.",
            )
            return

        self.config["vault_path"] = new_vault
        self.config["target_folder"] = new_target or "Anki Notes"
        self.config["media_folder"] = self.media_edit.text().strip() or "attachments"
        self.config["copy_media"] = self.copy_media_cb.isChecked()
        self.config["mirror_deck_hierarchy"] = self.mirror_deck_cb.isChecked()
        self.config["daily_note_enabled"] = self.daily_note_cb.isChecked()
        self.config["daily_note_folder"] = self.daily_folder_edit.text().strip() or "Daily Notes"
        self.config["daily_note_heading"] = self.daily_heading_edit.text().strip() or "## Anki Reviews"
        self.config["open_in_obsidian_after_export"] = self.open_obsidian_cb.isChecked()

        self.config["shortcut"] = self.shortcut_edit.text().strip() or "Ctrl+Shift+O"
        self.config["reviewer_quick_key"] = self.rev_key_edit.text().strip() or "5"
        self.config["daily_note_shortcut"] = self.daily_shortcut_edit.text().strip() or "Ctrl+Alt+D"
        self.config["show_draggable_button"] = self.show_button_cb.isChecked()
        self.config["button_label"] = self.btn_label_edit.text().strip() or "📓 To Obsidian"

        self.config["include_stats"] = self.include_stats_cb.isChecked()
        self.config["cloze_style"] = self.cloze_combo.currentData()
        self.config["frontmatter_enabled"] = self.frontmatter_cb.isChecked()
        self.config["collapse_supplementary_fields"] = self.collapse_extra_cb.isChecked()
        self.config["primary_fields"] = self.primary_fields_edit.text().strip() or "Front, Back, Text, Question, Answer"
        self.config["supplementary_callout_title"] = self.callout_title_edit.text().strip() or "📑 Extra & Notes"
        self.config["show_anki_details_callout"] = self.anki_details_cb.isChecked()
        self.config["metadata_section_style"] = self.meta_style_combo.currentData()
        self.config["metadata_collapsed"] = self.meta_collapsed_cb.isChecked()
        self.config["tag_prefix"] = self.tag_prefix_edit.text().strip()
        try:
            self.config["max_filename_length"] = max(30, min(250, int(self.max_len_edit.text().strip() or "240")))
        except Exception:
            self.config["max_filename_length"] = 240
        self.config["use_wikilinks"] = self.wikilinks_cb.isChecked()

        if self.on_save_callback:
            self.on_save_callback(self.config)

        self.accept()
