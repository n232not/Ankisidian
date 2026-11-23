"""
Ankisidian - Anki to Obsidian Note Exporter Add-on
Entry point for Anki.
Integrates top menu bar, global shortcuts, draggable floating button,
browser export, and automated Obsidian vault sync.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from aqt import gui_hooks, mw
from aqt.utils import showInfo, showTooltip, tooltip

try:
    from .exporter import export_note_data, get_active_anki_note
    from .floating_button import DraggableObsidianButton
    from .menu import AnkisidianMenuManager
    from .settings_dialog import AnkisidianSettingsDialog
except (ImportError, ValueError):
    from exporter import export_note_data, get_active_anki_note
    from floating_button import DraggableObsidianButton
    from menu import AnkisidianMenuManager
    from settings_dialog import AnkisidianSettingsDialog

ADDON_NAME = __name__

# Global references
_config: Dict[str, Any] = {}
_floating_button: Optional[DraggableObsidianButton] = None
_menu_manager: Optional[AnkisidianMenuManager] = None


def load_config() -> Dict[str, Any]:
    """Loads addon configuration, merging with defaults."""
    default_config = {
        "vault_path": "",
        "target_folder": "Anki Notes",
        "media_folder": "attachments",
        "copy_media": True,
        "shortcut": "Ctrl+Shift+O",
        "show_top_menu": True,
        "show_draggable_button": True,
        "button_label": "📓 To Obsidian",
        "button_position": [20, 80],
        "open_in_obsidian_after_export": False,
        "frontmatter_enabled": True,
        "tag_prefix": "anki/",
        "cloze_style": "highlight",
        "use_wikilinks": True,
        "file_naming": "{title}",
    }

    user_config = mw.addonManager.getConfig(ADDON_NAME) if mw and mw.addonManager else {}
    if not user_config:
        user_config = {}

    merged = dict(default_config)
    merged.update(user_config)
    return merged


def save_config(new_config: Dict[str, Any]):
    """Persists updated configuration."""
    global _config
    _config = new_config
    if mw and mw.addonManager:
        mw.addonManager.writeConfig(ADDON_NAME, new_config)

    # Update menu and shortcuts
    if _menu_manager:
        _menu_manager.update_config(new_config)

    # Update floating button
    update_floating_button_state()


def open_settings_dialog():
    """Opens the Ankisidian settings dialog."""
    global _config
    dialog = AnkisidianSettingsDialog(
        parent=mw,
        config=_config,
        on_save_callback=save_config,
        on_reset_button_pos=reset_button_position,
    )
    dialog.exec()


def reset_button_position():
    """Resets floating button to default position."""
    global _floating_button, _config
    _config["button_position"] = [20, 80]
    save_config(_config)
    if _floating_button:
        _floating_button.move(20, 80)


def on_button_position_changed(x: int, y: int):
    """Callback when user finishes dragging floating button."""
    global _config
    _config["button_position"] = [x, y]
    if mw and mw.addonManager:
        mw.addonManager.writeConfig(ADDON_NAME, _config)


def toggle_floating_button():
    """Toggles visibility of the floating draggable button."""
    global _config
    current = _config.get("show_draggable_button", True)
    _config["show_draggable_button"] = not current
    save_config(_config)


def hide_floating_button():
    """Hides the floating button and updates configuration."""
    global _config
    _config["show_draggable_button"] = False
    save_config(_config)
    tooltip("Draggable button hidden. You can re-enable it in Ankisidian top menu.", period=3000)


def update_floating_button_state():
    """Shows, hides, or recreates floating button based on configuration."""
    global _floating_button, _config

    if not mw:
        return

    show_btn = _config.get("show_draggable_button", True)

    if show_btn:
        if _floating_button is None:
            _floating_button = DraggableObsidianButton(
                parent=mw,
                on_click_callback=transfer_current_note,
                on_settings_callback=open_settings_dialog,
                on_hide_callback=hide_floating_button,
                config=_config,
                on_position_changed=on_button_position_changed,
            )
        else:
            _floating_button.config = _config
            _floating_button.setText(_config.get("button_label", "📓 To Obsidian"))
            pos = _config.get("button_position", [20, 80])
            _floating_button.move(int(pos[0]), int(pos[1]))
            _floating_button.show()
            _floating_button.raise_()
    else:
        if _floating_button:
            _floating_button.hide()


def transfer_current_note():
    """
    Main export routine. Transfers the currently active note to Obsidian.
    Handles reviewer card, active editor, or browser selection.
    """
    global _config

    if not mw:
        return

    # 1. Check configuration
    vault_path = _config.get("vault_path", "").strip()
    target_folder = _config.get("target_folder", "").strip()

    if not vault_path and not target_folder:
        showInfo(
            "Welcome to Ankisidian!\n\n"
            "Please configure your Obsidian Vault path before exporting.",
            parent=mw,
            title="Ankisidian Setup",
        )
        open_settings_dialog()
        return

    # 2. Get active note
    note, card, context = get_active_anki_note(mw)
    if not note:
        tooltip(
            "⚠️ No active note found.\nPlease open a note in Reviewer or select a card in Browser.",
            period=2500,
        )
        return

    # 3. Extract metadata
    note_id = note.id
    card_id = card.id if card else None

    # Get Deck Name
    deck_name = "Default"
    if card and hasattr(card, "did"):
        deck_name = mw.col.decks.name(card.did)
    elif hasattr(note, "cards") and note.cards():
        deck_name = mw.col.decks.name(note.cards()[0].did)

    # Get Model Name
    model_name = "Unknown"
    if hasattr(note, "note_type"):
        model_name = note.note_type().get("name", "Unknown")
    elif hasattr(note, "model"):
        model_name = note.model().get("name", "Unknown")

    tags = list(note.tags)
    fields = list(note.items())

    # Get Anki media directory
    media_dir = None
    if hasattr(mw.col, "media") and hasattr(mw.col.media, "dir"):
        media_dir = mw.col.media.dir()

    # 4. Perform export
    res = export_note_data(
        note_id=note_id,
        card_id=card_id,
        deck_name=deck_name,
        model_name=model_name,
        tags=tags,
        fields=fields,
        anki_media_dir=media_dir,
        config=_config,
    )

    if res.get("success"):
        filename = res.get("filename", "")
        copied_media = res.get("copied_media", [])
        media_msg = f" (+{len(copied_media)} media)" if copied_media else ""
        tooltip(f"💎 Transferred to Obsidian: {filename}{media_msg}", period=2500)
    else:
        showInfo(
            f"Failed to export note to Obsidian:\n{res.get('error')}",
            parent=mw,
            title="Ankisidian Error",
        )


def on_browser_menus_init(browser: Any):
    """Adds 'Transfer to Obsidian' action to Browser menu."""
    from aqt.qt import QAction

    action = QAction("Ankisidian: Transfer Selected Note(s) to Obsidian", browser)

    def export_browser_selection():
        selected_nids = browser.selected_notes()
        if not selected_nids:
            tooltip("No notes selected in Browser.", period=2000)
            return

        count = 0
        media_dir = mw.col.media.dir() if hasattr(mw.col, "media") else None

        for nid in selected_nids:
            try:
                n = mw.col.get_note(nid)
                c = n.cards()[0] if n.cards() else None
                d_name = mw.col.decks.name(c.did) if c else "Default"
                m_name = n.note_type().get("name", "Unknown") if hasattr(n, "note_type") else "Unknown"

                r = export_note_data(
                    note_id=n.id,
                    card_id=c.id if c else None,
                    deck_name=d_name,
                    model_name=m_name,
                    tags=list(n.tags),
                    fields=list(n.items()),
                    anki_media_dir=media_dir,
                    config=_config,
                )
                if r.get("success"):
                    count += 1
            except Exception as e:
                print(f"[Ankisidian] Error exporting note {nid}: {e}")

        tooltip(f"💎 Transferred {count} note(s) to Obsidian!", period=3000)

    action.triggered.connect(export_browser_selection)

    # Add to Edit or Cards menu in browser
    if hasattr(browser, "form") and hasattr(browser.form, "menuEdit"):
        browser.form.menuEdit.addAction(action)


def on_reviewer_did_show_question(card: Any):
    """Ensures floating button is raised on question display."""
    if _floating_button and _config.get("show_draggable_button", True):
        _floating_button.raise_()


def init_addon():
    """Initializes the Ankisidian addon once Anki profile is loaded."""
    global _config, _menu_manager

    _config = load_config()

    # Hook into Anki Add-on Manager Config Dialog
    if mw and hasattr(mw, "addonManager"):
        mw.addonManager.setConfigAction(ADDON_NAME, open_settings_dialog)

    # Setup Menus & Shortcuts
    _menu_manager = AnkisidianMenuManager(
        mw=mw,
        on_export=transfer_current_note,
        on_settings=open_settings_dialog,
        on_toggle_button=toggle_floating_button,
        config=_config,
    )

    # Setup Draggable Floating Button
    update_floating_button_state()

    # Hooks
    gui_hooks.browser_menus_did_init.append(on_browser_menus_init)
    gui_hooks.reviewer_did_show_question.append(on_reviewer_did_show_question)


# Register startup hook
if mw:
    gui_hooks.profile_did_open.append(init_addon)
