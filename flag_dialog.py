"""
Ankisidian - Flag Export Dialog
Dialog to export cards based on Anki color flags (Red, Orange, Green, Blue, Pink, Turquoise, Purple, or Any).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

try:
    from aqt.qt import (
        QComboBox,
        QDialog,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QVBoxLayout,
        Qt,
    )
except ImportError:
    QDialog = object  # type: ignore


class AnkisidianFlagExportDialog(QDialog):
    def __init__(
        self,
        parent: Any,
        mw: Any,
        config: Dict[str, Any],
        on_export_done: Optional[Callable[[int], None]] = None,
    ):
        super().__init__(parent)
        self.mw = mw
        self.config = config
        self.on_export_done = on_export_done

        self.setWindowTitle("Export Flagged Cards to Obsidian")
        self.setMinimumWidth(440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header = QLabel("<h3>🚩 Export Cards by Flag Color</h3>")
        layout.addWidget(header)

        form_group = QGroupBox("Filter Criteria")
        form_layout = QFormLayout(form_group)

        # Flag selection combo
        self.flag_combo = QComboBox()
        self.flag_combo.addItem("🚩 Any Flagged Card (Flags 1-7)", 0)
        self.flag_combo.addItem("🔴 Red Flag (Flag 1)", 1)
        self.flag_combo.addItem("🟠 Orange Flag (Flag 2)", 2)
        self.flag_combo.addItem("🟢 Green Flag (Flag 3)", 3)
        self.flag_combo.addItem("🔵 Blue Flag (Flag 4)", 4)
        self.flag_combo.addItem("🌸 Pink Flag (Flag 5)", 5)
        self.flag_combo.addItem("🩵 Turquoise Flag (Flag 6)", 6)
        self.flag_combo.addItem("🟣 Purple Flag (Flag 7)", 7)
        form_layout.addRow("Select Flag:", self.flag_combo)

        # Scope combo
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("Entire Collection", "all")
        if self.mw and hasattr(self.mw, "col") and self.mw.col and hasattr(self.mw.col, "decks"):
            curr_deck_id = getattr(self.mw.col.decks, "current", lambda: None)()
            if curr_deck_id:
                curr_name = self.mw.col.decks.name(curr_deck_id.get("id", 1))
                self.scope_combo.addItem(f"Current Deck Only ({curr_name})", f'deck:"{curr_name}"')
        form_layout.addRow("Search Scope:", self.scope_combo)

        layout.addWidget(form_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.cancel_btn)

        self.export_btn = QPushButton("Export to Obsidian")
        self.export_btn.setDefault(True)
        self.export_btn.setStyleSheet(
            "background-color: #7c3aed; color: white; font-weight: bold; padding: 6px 14px; border-radius: 4px;"
        )
        self.export_btn.clicked.connect(self._do_export)
        btn_box.addWidget(self.export_btn)

        layout.addLayout(btn_box)

    def _do_export(self):
        if not self.mw or not self.mw.col:
            QMessageBox.warning(self, "Error", "Anki collection is not currently loaded.")
            return

        flag_id = self.flag_combo.currentData()
        scope = self.scope_combo.currentData()

        # Build Anki search query
        if flag_id == 0:
            flag_query = "(flag:1 or flag:2 or flag:3 or flag:4 or flag:5 or flag:6 or flag:7)"
        else:
            flag_query = f"flag:{flag_id}"

        query = flag_query if scope == "all" else f"{scope} {flag_query}"

        # Find matching card IDs
        try:
            card_ids = self.mw.col.find_cards(query)
        except Exception as e:
            QMessageBox.warning(self, "Search Error", f"Failed to execute search: {e}")
            return

        if not card_ids:
            QMessageBox.information(self, "No Cards Found", "No cards match the chosen flag criteria.")
            return

        # Collect unique note IDs
        note_card_map: Dict[int, int] = {}
        for cid in card_ids:
            try:
                card = self.mw.col.get_card(cid)
                if card.nid not in note_card_map:
                    note_card_map[card.nid] = cid
            except Exception:
                pass

        total = len(note_card_map)
        if total == 0:
            QMessageBox.information(self, "No Notes", "No matching notes found.")
            return

        from .exporter import export_note_data, extract_card_stats

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.export_btn.setEnabled(False)

        exported_count = 0
        anki_media_dir = self.mw.col.media.dir() if hasattr(self.mw.col, "media") else None

        for idx, (nid, cid) in enumerate(note_card_map.items()):
            try:
                note = self.mw.col.get_note(nid)
                card = self.mw.col.get_card(cid)
                deck_name = self.mw.col.decks.name(card.did)
                model_name = note.note_type().get("name", "Unknown") if hasattr(note, "note_type") else "Unknown"
                card_stats = extract_card_stats(card, self.mw.col)

                tag_name = self.config.get("exported_tag_name", "obsidian_exported").strip() or "obsidian_exported"
                is_repeat = False
                if hasattr(note, "has_tag"):
                    is_repeat = note.has_tag(tag_name)
                elif hasattr(note, "tags"):
                    is_repeat = any(t.lower() == tag_name.lower() for t in note.tags)

                res = export_note_data(
                    note_id=note.id,
                    card_id=card.id,
                    deck_name=deck_name,
                    model_name=model_name,
                    tags=list(note.tags),
                    fields=list(note.items()),
                    anki_media_dir=anki_media_dir,
                    config=self.config,
                    card_stats=card_stats,
                    is_repeat_export=is_repeat,
                )
                if res.get("success"):
                    exported_count += 1
                    if self.config.get("auto_tag_on_export", True) and not is_repeat:
                        try:
                            if hasattr(note, "add_tag"):
                                note.add_tag(tag_name)
                            elif hasattr(note, "tags"):
                                note.tags.append(tag_name)
                            if hasattr(self.mw.col, "update_note"):
                                self.mw.col.update_note(note)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Ankisidian] Error exporting note {nid}: {e}")

            self.progress_bar.setValue(idx + 1)
            self.status_label.setText(f"Exported {idx + 1} of {total} notes...")
            if hasattr(self.mw, "app") and self.mw.app:
                self.mw.app.processEvents()

        if self.on_export_done:
            self.on_export_done(exported_count)

        QMessageBox.information(
            self,
            "Export Complete",
            f"Successfully transferred {exported_count} flagged note(s) to Obsidian!",
        )
        self.accept()
