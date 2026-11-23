"""
Ankisidian - Anki to Obsidian Note Exporter Add-on
Entry point for Anki.
Integrates top menu bar, global shortcuts, draggable floating button,
browser export, and automated Obsidian vault sync.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    from aqt import gui_hooks, mw
    from aqt.utils import showInfo, tooltip
except ImportError:
    gui_hooks = None
    mw = None
    def showInfo(*args, **kwargs): pass
    def tooltip(*args, **kwargs): pass

try:
    from .exporter import (
        append_to_daily_note,
        export_note_data,
        extract_card_stats,
        generate_dataview_dashboard,
        get_active_anki_note,
    )
    from .flag_dialog import AnkisidianFlagExportDialog
    from .floating_button import DraggableObsidianButton
    from .menu import AnkisidianMenuManager
    from .settings_dialog import AnkisidianSettingsDialog
except (ImportError, ValueError):
    from exporter import (
        append_to_daily_note,
        export_note_data,
        extract_card_stats,
        generate_dataview_dashboard,
        get_active_anki_note,
    )
    from flag_dialog import AnkisidianFlagExportDialog
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
        "mirror_deck_hierarchy": False,
        "daily_note_enabled": True,
        "daily_note_folder": "Daily Notes",
        "daily_note_format": "%Y-%m-%d",
        "daily_note_heading": "## Anki Reviews",
        "daily_note_shortcut": "Ctrl+Alt+D",
        "reviewer_quick_key": "5",
        "reviewer_daily_key": "",
        "shortcut": "Ctrl+Shift+O",
        "show_top_menu": True,
        "show_draggable_button": True,
        "button_label": "📓 To Obsidian",
        "button_position": [20, 80],
        "open_in_obsidian_after_export": False,
        "frontmatter_enabled": True,
        "primary_fields": "Front, Back, Text, Question, Answer",
        "collapse_supplementary_fields": True,
        "supplementary_callout_title": "📑 Extra & Notes",
        "supplementary_callout_type": "note",
        "show_anki_details_callout": False,
        "metadata_section_enabled": False,
        "metadata_section_style": "callout",
        "metadata_collapsed": True,
        "metadata_position": "top",
        "include_stats": True,
        "tag_prefix": "anki/",
        "cloze_style": "highlight",
        "use_wikilinks": True,
        "max_filename_length": 240,
        "file_naming": "{title}",
        "auto_tag_on_export": True,
        "exported_tag_name": "obsidian_exported",
        "high_difficulty_folder_enabled": True,
        "high_difficulty_folder_name": "High Difficulty",
        "create_dataview_dashboard": True,
        "dashboard_filename": "Anki Dashboard.md",
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


def tag_note_as_exported(note: Any, col: Any, config: Dict[str, Any]) -> bool:
    """
    Adds the configured export tag (default: 'obsidian_exported') to the Anki note.
    Persists the change in Anki's database so the note is marked as exported.
    """
    if not config.get("auto_tag_on_export", True) or not note:
        return False

    tag = config.get("exported_tag_name", "obsidian_exported").strip()
    if not tag:
        return False

    try:
        has_tag = False
        if hasattr(note, "has_tag"):
            has_tag = note.has_tag(tag)
        elif hasattr(note, "tags"):
            has_tag = any(t.lower() == tag.lower() for t in note.tags)

        if not has_tag:
            if hasattr(note, "add_tag"):
                note.add_tag(tag)
            elif hasattr(note, "tags"):
                note.tags.append(tag)

            if col:
                if hasattr(col, "update_note"):
                    col.update_note(note)
                elif hasattr(note, "flush"):
                    note.flush()
        return True
    except Exception as e:
        print(f"[Ankisidian] Failed to tag note as exported: {e}")
        return False


def is_note_already_exported(note: Any, config: Dict[str, Any]) -> bool:
    """Checks whether note is marked as exported in Anki."""
    if not note:
        return False
    tag = config.get("exported_tag_name", "obsidian_exported").strip()
    if not tag:
        return False
    try:
        if hasattr(note, "has_tag"):
            return note.has_tag(tag)
        elif hasattr(note, "tags"):
            return any(t.lower() == tag.lower() for t in note.tags)
    except Exception:
        pass
    return False


def generate_dataview_dashboard_action():
    """Generates or updates the Dataview dashboard note in Obsidian."""
    global _config
    res = generate_dataview_dashboard(_config, overwrite=True)
    if res.get("success"):
        fn = os.path.basename(res.get("file_path", "Anki Dashboard.md"))
        tooltip(f"📊 Dataview Dashboard generated:\n{fn}", period=3000)
    else:
        showInfo(
            f"Failed to generate Dataview Dashboard:\n{res.get('error')}",
            parent=mw,
            title="Ankisidian Dashboard",
        )


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

    # 4. Extract Card Stats if enabled
    card_stats = None
    if _config.get("include_stats", True) and card:
        card_stats = extract_card_stats(card, mw.col)

    is_repeat = is_note_already_exported(note, _config)

    # 5. Perform export
    res = export_note_data(
        note_id=note_id,
        card_id=card_id,
        deck_name=deck_name,
        model_name=model_name,
        tags=tags,
        fields=fields,
        anki_media_dir=media_dir,
        config=_config,
        card_stats=card_stats,
        is_repeat_export=is_repeat,
    )

    if res.get("success"):
        tag_note_as_exported(note, mw.col, _config)
        filename = res.get("filename", "")
        copied_media = res.get("copied_media", [])
        media_msg = f" (+{len(copied_media)} media)" if copied_media else ""
        if res.get("is_high_difficulty"):
            tooltip(f"🔥 Transferred to High Difficulty: {filename}{media_msg}", period=3000)
        else:
            tooltip(f"💎 Transferred to Obsidian: {filename}{media_msg} (tagged)", period=2500)
    else:
        showInfo(
            f"Failed to export note to Obsidian:\n{res.get('error')}",
            parent=mw,
            title="Ankisidian Error",
        )


def append_current_note_to_daily():
    """
    Appends the currently active card/note into today's Obsidian Daily Note.
    """
    global _config

    if not mw:
        return

    vault_path = _config.get("vault_path", "").strip()
    if not vault_path:
        showInfo(
            "Please configure your Obsidian Vault path before appending to Daily Note.",
            parent=mw,
            title="Ankisidian Setup",
        )
        open_settings_dialog()
        return

    note, card, context = get_active_anki_note(mw)
    if not note:
        tooltip("⚠️ No active note found to append.", period=2500)
        return

    note_id = note.id
    card_id = card.id if card else None

    deck_name = "Default"
    if card and hasattr(card, "did"):
        deck_name = mw.col.decks.name(card.did)
    elif hasattr(note, "cards") and note.cards():
        deck_name = mw.col.decks.name(note.cards()[0].did)

    model_name = note.note_type().get("name", "Unknown") if hasattr(note, "note_type") else "Unknown"
    card_stats = extract_card_stats(card, mw.col) if _config.get("include_stats", True) else None
    media_dir = mw.col.media.dir() if hasattr(mw.col, "media") and hasattr(mw.col.media, "dir") else None

    res = append_to_daily_note(
        note_id=note_id,
        card_id=card_id,
        deck_name=deck_name,
        model_name=model_name,
        tags=list(note.tags),
        fields=list(note.items()),
        card_stats=card_stats,
        anki_media_dir=media_dir,
        config=_config,
    )

    if res.get("success"):
        tag_note_as_exported(note, mw.col, _config)
        if res.get("already_appended"):
            tooltip(f"ℹ️ Note was already in Daily Note: {res.get('filename')}", period=2500)
        else:
            tooltip(f"📅 Appended to Daily Note: {res.get('filename')}", period=2500)
    else:
        showInfo(
            f"Failed to append to Daily Note:\n{res.get('error')}",
            parent=mw,
            title="Ankisidian Error",
        )


def open_flag_export_dialog():
    """Opens the Export Cards by Flag Color dialog."""
    global _config
    dialog = AnkisidianFlagExportDialog(parent=mw, mw=mw, config=_config)
    dialog.exec()


def on_browser_menus_init(browser: Any):
    """Adds Ankisidian actions to the Card Browser menus and context menu."""
    from aqt.qt import QAction, QKeySequence, QShortcut

    # 1. Action: Export Selected Notes
    export_action = QAction("Ankisidian: Transfer Selected Note(s) to Obsidian", browser)

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
                c_stats = extract_card_stats(c, mw.col) if _config.get("include_stats", True) and c else None
                is_rep = is_note_already_exported(n, _config)

                r = export_note_data(
                    note_id=n.id,
                    card_id=c.id if c else None,
                    deck_name=d_name,
                    model_name=m_name,
                    tags=list(n.tags),
                    fields=list(n.items()),
                    anki_media_dir=media_dir,
                    config=_config,
                    card_stats=c_stats,
                    is_repeat_export=is_rep,
                )
                if r.get("success"):
                    tag_note_as_exported(n, mw.col, _config)
                    count += 1
            except Exception as e:
                print(f"[Ankisidian] Error exporting note {nid}: {e}")

        tooltip(f"💎 Transferred {count} note(s) to Obsidian!", period=3000)

    export_action.triggered.connect(export_browser_selection)

    # Browser shortcut (Ctrl+Shift+O / Cmd+Shift+O)
    try:
        browser_shortcut = QShortcut(QKeySequence(_config.get("shortcut", "Ctrl+Shift+O")), browser)
        browser_shortcut.activated.connect(export_browser_selection)
    except Exception:
        pass

    # 2. Action: Append Selected Notes to Daily Note
    daily_action = QAction("Ankisidian: Append Selected Note(s) to Daily Note", browser)

    def append_browser_selection():
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
                c_stats = extract_card_stats(c, mw.col) if _config.get("include_stats", True) and c else None

                r = append_to_daily_note(
                    note_id=n.id,
                    card_id=c.id if c else None,
                    deck_name=d_name,
                    model_name=m_name,
                    tags=list(n.tags),
                    fields=list(n.items()),
                    card_stats=c_stats,
                    anki_media_dir=media_dir,
                    config=_config,
                )
                if r.get("success"):
                    count += 1
            except Exception as e:
                print(f"[Ankisidian] Error appending note {nid}: {e}")

        tooltip(f"📅 Appended {count} note(s) to Daily Note!", period=3000)

    daily_action.triggered.connect(append_browser_selection)

    # 3. Action: Export Flagged Cards Dialog
    flag_action = QAction("Ankisidian: Export Cards by Flag Color...", browser)
    flag_action.triggered.connect(open_flag_export_dialog)

    # Add to Edit and Cards menus in browser
    if hasattr(browser, "form"):
        if hasattr(browser.form, "menuEdit"):
            browser.form.menuEdit.addSeparator()
            browser.form.menuEdit.addAction(export_action)
            browser.form.menuEdit.addAction(daily_action)
            browser.form.menuEdit.addAction(flag_action)


def on_reviewer_did_show_question(card: Any):
    """Ensures floating button is raised on question display if enabled."""
    if _floating_button and _config.get("show_draggable_button", True):
        _floating_button.raise_()


def on_state_shortcuts_will_change(state: str, shortcuts: list[tuple[str, Any]]):
    """
    Injects single-key review shortcuts (e.g. '5' to transfer to Obsidian)
    directly into Anki's reviewer.
    """
    if state == "review":
        rev_key = _config.get("reviewer_quick_key", "5").strip()
        if rev_key:
            shortcuts.append((rev_key, transfer_current_note))

        daily_key = _config.get("reviewer_daily_key", "").strip()
        if daily_key:
            shortcuts.append((daily_key, append_current_note_to_daily))


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
        on_daily_export=append_current_note_to_daily,
        on_flag_export=open_flag_export_dialog,
        on_settings=open_settings_dialog,
        on_toggle_button=toggle_floating_button,
        config=_config,
        on_create_dashboard=generate_dataview_dashboard_action,
    )

    # Setup Draggable Floating Button
    update_floating_button_state()

    # Hooks
    gui_hooks.browser_menus_did_init.append(on_browser_menus_init)
    gui_hooks.reviewer_did_show_question.append(on_reviewer_did_show_question)
    gui_hooks.state_shortcuts_will_change.append(on_state_shortcuts_will_change)


# Register startup hook
if mw and gui_hooks:
    gui_hooks.profile_did_open.append(init_addon)
