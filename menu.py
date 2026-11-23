"""
Ankisidian - Top Menu & Shortcut Integration
Configures menu bar actions, reviewer toolbar button, and global shortcut.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Dict, Optional

try:
    from aqt.qt import (
        QAction,
        QKeySequence,
        QMenu,
        QShortcut,
    )
except ImportError:
    QAction = object  # type: ignore
    QKeySequence = object  # type: ignore
    QMenu = object  # type: ignore
    QShortcut = object  # type: ignore


class AnkisidianMenuManager:
    def __init__(
        self,
        mw: Any,
        on_export: Callable[[], None],
        on_settings: Callable[[], None],
        on_toggle_button: Callable[[], None],
        config: Dict[str, Any],
    ):
        self.mw = mw
        self.on_export = on_export
        self.on_settings = on_settings
        self.on_toggle_button = on_toggle_button
        self.config = config

        self.shortcut_obj: Optional[QShortcut] = None
        self.top_menu: Optional[QMenu] = None
        self.export_action: Optional[QAction] = None
        self.toggle_button_action: Optional[QAction] = None

        self._setup_shortcut()
        self._setup_top_menu()
        self._setup_tools_menu()

    def _get_shortcut_sequence(self) -> str:
        shortcut = self.config.get("shortcut", "").strip()
        if not shortcut:
            # Default shortcut
            shortcut = "Ctrl+Shift+O"

        # On macOS, if user wrote Ctrl+Shift+O or Cmd+Shift+O, Qt handles standard sequences
        return shortcut

    def _setup_shortcut(self):
        if not self.mw:
            return

        shortcut_str = self._get_shortcut_sequence()
        try:
            if self.shortcut_obj:
                self.shortcut_obj.setEnabled(False)
                self.shortcut_obj.deleteLater()

            self.shortcut_obj = QShortcut(QKeySequence(shortcut_str), self.mw)
            self.shortcut_obj.activated.connect(self.on_export)
        except Exception as e:
            print(f"[Ankisidian] Failed to register shortcut {shortcut_str}: {e}")

    def _setup_top_menu(self):
        """Adds a top-level 'Ankisidian' menu in Anki's main menu bar."""
        if not self.mw or not hasattr(self.mw, "form") or not hasattr(self.mw.form, "menubar"):
            return

        menubar = self.mw.form.menubar

        # Create or find Ankisidian menu
        self.top_menu = menubar.addMenu("Ankisidian")

        # 1. Export Action
        shortcut_str = self._get_shortcut_sequence()
        self.export_action = QAction(f"Transfer Current Note to Obsidian\t({shortcut_str})", self.mw)
        self.export_action.triggered.connect(self.on_export)
        self.top_menu.addAction(self.export_action)

        self.top_menu.addSeparator()

        # 2. Toggle Floating Button
        show_btn = self.config.get("show_draggable_button", True)
        self.toggle_button_action = QAction("Show Draggable Floating Button", self.mw)
        self.toggle_button_action.setCheckable(True)
        self.toggle_button_action.setChecked(show_btn)
        self.toggle_button_action.triggered.connect(self.on_toggle_button)
        self.top_menu.addAction(self.toggle_button_action)

        self.top_menu.addSeparator()

        # 3. Settings Action
        settings_action = QAction("⚙️ Ankisidian Settings...", self.mw)
        settings_action.triggered.connect(self.on_settings)
        self.top_menu.addAction(settings_action)

    def _setup_tools_menu(self):
        """Also adds an action into the Tools menu for convenience."""
        if not self.mw or not hasattr(self.mw, "form") or not hasattr(self.mw.form, "menuTools"):
            return

        tools_menu = self.mw.form.menuTools
        tools_action = QAction("Ankisidian: Transfer to Obsidian", self.mw)
        tools_action.triggered.connect(self.on_export)
        tools_menu.addAction(tools_action)

    def update_config(self, new_config: Dict[str, Any]):
        self.config = new_config
        self._setup_shortcut()
        if self.toggle_button_action:
            self.toggle_button_action.setChecked(self.config.get("show_draggable_button", True))
        if self.export_action:
            shortcut_str = self._get_shortcut_sequence()
            self.export_action.setText(f"Transfer Current Note to Obsidian\t({shortcut_str})")
