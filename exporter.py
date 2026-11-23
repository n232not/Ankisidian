"""
Ankisidian - Exporter Module
Locates the active note in Reviewer, Browser, or Editor,
formats it into Obsidian Markdown with frontmatter and media,
and saves it to the configured Obsidian vault folder.
"""

from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

try:
    from .html_to_markdown import anki_html_to_markdown
    from .media import copy_note_media, extract_media_references
except (ImportError, ValueError):
    from html_to_markdown import anki_html_to_markdown
    from media import copy_note_media, extract_media_references


def sanitize_filename(name: str, max_len: int = 80) -> str:
    r"""
    Sanitizes string for use as a cross-platform filesystem file name.
    Removes invalid characters: / \ : * ? " < > | and control characters.
    """
    # Strip HTML tags if any remain
    cleaned = re.sub(r"<[^>]+>", "", name)
    # Remove invalid characters
    cleaned = re.sub(r'[\\/*?:"<>|\n\r\t]', " ", cleaned)
    # Collapse consecutive whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip leading/trailing dots or dashes
    cleaned = cleaned.strip(". -_")

    if not cleaned:
        cleaned = "Untitled Note"

    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(" .-_")

    return cleaned


def extract_note_title(fields: List[Tuple[str, str]], fallback_id: int) -> str:
    """
    Extracts a suitable title from the first non-empty field of the note.
    """
    for field_name, field_val in fields:
        plain = re.sub(r"<[^>]+>", " ", field_val)
        plain = re.sub(r"\{\{c\d+::(.*?)(?:::(.*?))?\}\}", r"\1", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain:
            return sanitize_filename(plain)

    return f"Anki Note {fallback_id}"


def format_obsidian_markdown(
    note_id: int,
    card_id: Optional[int],
    deck_name: str,
    model_name: str,
    tags: List[str],
    fields: List[Tuple[str, str]],
    config: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Formats the note content into Obsidian Markdown.
    Returns (filename_without_ext, markdown_content).
    """
    title = extract_note_title(fields, fallback_id=note_id)
    cloze_style = config.get("cloze_style", "highlight")
    use_wikilinks = config.get("use_wikilinks", True)
    tag_prefix = config.get("tag_prefix", "anki/")
    frontmatter_enabled = config.get("frontmatter_enabled", True)

    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prepare Markdown content parts
    md_parts: List[str] = []

    # 1. Frontmatter
    if frontmatter_enabled:
        md_parts.append("---")
        escaped_title = title.replace('"', '\\"')
        md_parts.append(f'title: "{escaped_title}"')
        md_parts.append(f"anki_note_id: {note_id}")
        if card_id:
            md_parts.append(f"anki_card_id: {card_id}")
        escaped_deck = deck_name.replace('"', '\\"')
        md_parts.append(f'anki_deck: "{escaped_deck}"')
        escaped_model = model_name.replace('"', '\\"')
        md_parts.append(f'anki_model: "{escaped_model}"')

        # Tags
        formatted_tags = []
        if tag_prefix:
            formatted_tags.append("anki")
        for t in tags:
            clean_t = re.sub(r"[^\w\-_\/]", "_", t)
            if clean_t:
                formatted_tags.append(f"{tag_prefix}{clean_t}" if tag_prefix and not clean_t.startswith("anki") else clean_t)

        if formatted_tags:
            md_parts.append("tags:")
            for ft in formatted_tags:
                md_parts.append(f"  - {ft}")
        else:
            md_parts.append("tags: [anki]")

        md_parts.append(f"created: {now_iso}")
        md_parts.append(f"updated: {now_iso}")
        md_parts.append("---\n")

    # 2. Main Title Header
    md_parts.append(f"# {title}\n")

    # 3. Note Fields
    for field_name, field_html in fields:
        field_md = anki_html_to_markdown(
            field_html, cloze_style=cloze_style, use_wikilinks=use_wikilinks
        )
        md_parts.append(f"## {field_name}\n")
        if field_md:
            md_parts.append(f"{field_md}\n")
        else:
            md_parts.append("*(empty)*\n")

    # 4. Anki Quick Link / Backlink
    md_parts.append("\n---\n")
    md_parts.append(f"> 🔗 [Open in Anki (nid:{note_id})](anki://search?q=nid:{note_id})\n")

    markdown_text = "\n".join(md_parts)

    # Filename determination
    naming_template = config.get("file_naming", "{title}")
    if "{title}" in naming_template:
        filename = naming_template.format(
            title=title,
            deck=sanitize_filename(deck_name, max_len=30),
            id=note_id,
            date=datetime.datetime.now().strftime("%Y-%m-%d"),
        )
    else:
        filename = title

    filename = sanitize_filename(filename)
    return filename, markdown_text


def resolve_target_paths(config: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolves the target destination folder and media attachments folder.
    Returns (target_folder_path, media_folder_path).
    """
    vault_path = config.get("vault_path", "").strip()
    target_subfolder = config.get("target_folder", "Anki Notes").strip()
    media_subfolder = config.get("media_folder", "attachments").strip()

    if not vault_path and not target_subfolder:
        return None, None

    # If target_subfolder is an absolute path and vault_path is empty:
    if os.path.isabs(target_subfolder) and not vault_path:
        target_dir = os.path.expanduser(target_subfolder)
        media_dir = os.path.join(target_dir, media_subfolder) if media_subfolder else target_dir
        return target_dir, media_dir

    # Normal case: vault_path is set
    vault_dir = os.path.expanduser(vault_path) if vault_path else ""
    if not vault_dir:
        # User only gave a relative folder, fallback to ~/Documents/<folder> or prompt
        return None, None

    target_dir = os.path.join(vault_dir, target_subfolder) if target_subfolder else vault_dir
    media_dir = os.path.join(vault_dir, media_subfolder) if media_subfolder else vault_dir

    return target_dir, media_dir


def export_note_data(
    note_id: int,
    card_id: Optional[int],
    deck_name: str,
    model_name: str,
    tags: List[str],
    fields: List[Tuple[str, str]],
    anki_media_dir: Optional[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Exports note data to Markdown file in Obsidian vault folder.
    Pure python logic, decoupled from Anki UI.
    """
    target_dir, media_dir = resolve_target_paths(config)
    if not target_dir:
        return {
            "success": False,
            "error": "Obsidian Vault path is not configured. Please open Ankisidian Settings to set your vault folder.",
        }

    os.makedirs(target_dir, exist_ok=True)

    filename_base, md_content = format_obsidian_markdown(
        note_id=note_id,
        card_id=card_id,
        deck_name=deck_name,
        model_name=model_name,
        tags=tags,
        fields=fields,
        config=config,
    )

    # File path resolution
    target_file = os.path.join(target_dir, f"{filename_base}.md")

    # If file exists, check whether it is the same note or collision
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                existing_text = f.read(500)
            if f"anki_note_id: {note_id}" not in existing_text:
                # Collision: different note with same title, append note_id
                target_file = os.path.join(target_dir, f"{filename_base}_{note_id}.md")
        except Exception:
            pass

    # Write Markdown file
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Copy Media if enabled
    copied_media = []
    if config.get("copy_media", True) and anki_media_dir and media_dir:
        all_field_htmls = [v for _, v in fields]
        media_refs = extract_media_references(all_field_htmls)
        if media_refs:
            copied_media = copy_note_media(
                media_refs,
                anki_media_dir=anki_media_dir,
                obsidian_media_dir=media_dir,
            )

    # Open in Obsidian if requested
    if config.get("open_in_obsidian_after_export", False):
        try:
            open_file_in_obsidian(target_file, config)
        except Exception as e:
            print(f"[Ankisidian] Failed to open file in Obsidian: {e}")

    return {
        "success": True,
        "file_path": target_file,
        "filename": os.path.basename(target_file),
        "copied_media": copied_media,
    }


def open_file_in_obsidian(file_path: str, config: Dict[str, Any]):
    """
    Opens the exported file in Obsidian using obsidian:// URI or system open.
    """
    vault_path = config.get("vault_path", "")
    if vault_path and os.path.isdir(os.path.expanduser(vault_path)):
        vault_name = os.path.basename(os.path.abspath(os.path.expanduser(vault_path)))
        rel_path = os.path.relpath(file_path, os.path.expanduser(vault_path))
        uri = f"obsidian://open?vault={quote(vault_name)}&file={quote(rel_path)}"
        if sys.platform == "darwin":
            subprocess.Popen(["open", uri])
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", uri])
        elif sys.platform == "win32":
            os.startfile(uri)
    else:
        # Fallback to system file open
        if sys.platform == "darwin":
            subprocess.Popen(["open", file_path])
        elif sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", file_path])
        elif sys.platform == "win32":
            os.startfile(file_path)


def get_active_anki_note(mw: Any) -> Tuple[Optional[Any], Optional[Any], Optional[str]]:
    """
    Finds the currently active note and card in Anki.
    Checks:
      1. Reviewer (when studying cards)
      2. Active Browser window / selection
      3. Active EditCurrent dialog
      4. Active AddCards dialog
    Returns (note, card, context_description).
    """
    if not mw:
        return None, None, None

    # 1. Reviewer mode
    if getattr(mw, "state", None) == "review" and getattr(mw, "reviewer", None):
        card = getattr(mw.reviewer, "card", None)
        if card:
            return card.note(), card, "Reviewer"

    # 2. Check active top-level widgets (Browser or EditCurrent)
    app = getattr(mw, "app", None)
    if app:
        active_win = app.activeWindow()
        if active_win:
            # Check EditCurrent
            if hasattr(active_win, "editor") and getattr(active_win.editor, "note", None):
                note = active_win.editor.note
                card = getattr(active_win, "card", None)
                return note, card, "Edit Dialog"

            # Check Browser
            if hasattr(active_win, "selected_notes"):
                try:
                    selected_nids = active_win.selected_notes()
                    if selected_nids:
                        note = mw.col.get_note(selected_nids[0])
                        card = getattr(active_win, "card", None)
                        return note, card, "Browser"
                except Exception:
                    pass

    # 3. Fallback: reviewer's last card if still present
    reviewer = getattr(mw, "reviewer", None)
    if reviewer and getattr(reviewer, "card", None):
        return reviewer.card.note(), reviewer.card, "Reviewer"

    return None, None, None
