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


def clean_title_text(name: str) -> str:
    r"""
    Cleans a string for use as the note title inside Markdown (# Title) and YAML.
    Removes raw HTML, collapses whitespace, but does NOT truncate length.
    Preserves question marks and sentence punctuation while removing spaces before punctuation.
    """
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", name)
    # Collapse newlines and tabs to spaces
    cleaned = re.sub(r"[\n\r\t]+", " ", cleaned)
    # Collapse consecutive whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Remove spaces before punctuation caused by stripped HTML tags
    cleaned = re.sub(r"\s+([,.:;?!])", r"\1", cleaned)
    return cleaned if cleaned else "Untitled Note"


def sanitize_filename(name: str, max_len: int = 240) -> str:
    r"""
    Sanitizes string for use as a cross-platform filesystem file name.
    Removes invalid characters: / \ : * ? " < > | and control characters.
    Defaults to 240 chars (OS filesystem max is 255 bytes) so long card titles are not cut off.
    """
    # Strip HTML tags if any remain
    cleaned = re.sub(r"<[^>]+>", " ", name)
    # Remove invalid characters
    cleaned = re.sub(r'[\\/*?:"<>|\n\r\t]', " ", cleaned)
    # Collapse consecutive whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip leading/trailing dots or dashes
    cleaned = cleaned.strip(". -_")

    if not cleaned:
        cleaned = "Untitled Note"

    if max_len and len(cleaned) > max_len:
        # Truncate at word boundary if possible
        truncated = cleaned[:max_len]
        if " " in truncated:
            cleaned = truncated.rsplit(" ", 1)[0].rstrip(" .-_")
        else:
            cleaned = truncated.rstrip(" .-_")

    return cleaned


def extract_note_title(fields: List[Tuple[str, str]], fallback_id: int) -> str:
    """
    Extracts the full title from the first non-empty field of the note.
    Does not truncate so full question text is preserved inside the note.
    """
    for field_name, field_val in fields:
        plain = re.sub(r"\{\{c\d+::(.*?)(?:::(.*?))?\}\}", r"\1", field_val)
        cleaned = clean_title_text(plain)
        if cleaned and cleaned != "Untitled Note":
            return cleaned

    return f"Anki Note {fallback_id}"


def extract_card_stats(card: Optional[Any], col: Optional[Any] = None) -> Dict[str, Any]:
    """
    Extracts spaced repetition review stats from an Anki card object.
    Returns dictionary with interval, ease, reps, lapses, state, due date, flag.
    """
    if not card:
        return {}

    stats: Dict[str, Any] = {}

    # Reps & Lapses
    reps = getattr(card, "reps", 0)
    lapses = getattr(card, "lapses", 0)
    stats["reps"] = reps
    stats["lapses"] = lapses

    # Ease Factor
    factor = getattr(card, "factor", 0)
    if factor:
        stats["ease"] = f"{factor // 10}%"
        stats["ease_raw"] = factor / 1000.0
    else:
        stats["ease"] = "N/A (New)"
        stats["ease_raw"] = 0

    # Interval
    ivl = getattr(card, "ivl", 0)
    if ivl > 0:
        stats["interval_days"] = ivl
        stats["interval"] = f"{ivl}d"
    elif ivl < 0:
        stats["interval_days"] = 0
        stats["interval"] = f"{abs(ivl)}s (learning)"
    else:
        stats["interval_days"] = 0
        stats["interval"] = "New"

    # Queue / State
    queue = getattr(card, "queue", 0)
    queue_map = {
        -3: "Buried (User)",
        -2: "Buried (Sched)",
        -1: "Suspended",
        0: "New",
        1: "Learning",
        2: "Review",
        3: "Day Learning",
        4: "Preview",
    }
    stats["state"] = queue_map.get(queue, "Unknown")

    # Due date calculation
    due = getattr(card, "due", 0)
    if queue == 2:  # Review queue: due is day offset
        try:
            today_day = col.sched.today if col and hasattr(col, "sched") and hasattr(col.sched, "today") else 0
            if today_day:
                diff_days = due - today_day
                due_date = datetime.date.today() + datetime.timedelta(days=diff_days)
                stats["due_date"] = due_date.strftime("%Y-%m-%d")
            else:
                stats["due_date"] = f"Day {due}"
        except Exception:
            stats["due_date"] = f"Day {due}"
    elif queue == 0:
        stats["due_date"] = f"Position {due}"
    elif queue in (1, 3):
        stats["due_date"] = "Today (Learning)"
    else:
        stats["due_date"] = "Suspended / Buried"

    # Flag
    flags = getattr(card, "flags", 0)
    flag_names = {1: "Red", 2: "Orange", 3: "Green", 4: "Blue", 5: "Pink", 6: "Turquoise", 7: "Purple"}
    stats["flag"] = flag_names.get(flags, "None")
    stats["flag_id"] = flags

    return stats


def build_metadata_section(
    note_id: int,
    card_id: Optional[int],
    deck_name: str,
    model_name: str,
    tags: List[str],
    tag_prefix: str,
    now_iso: str,
    config: Dict[str, Any],
    card_stats: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Builds a separate overarching minimizable section containing all metadata,
    tags, IDs, review stats, and the Anki backlink.
    """
    style = config.get("metadata_section_style", "callout")
    collapsed = config.get("metadata_collapsed", True)

    # Format tags for inline display
    tag_items = []
    if tag_prefix:
        tag_items.append("#anki")
    for t in tags:
        clean_t = re.sub(r"[^\w\-_\/]", "_", t)
        if clean_t:
            full_tag = f"#{tag_prefix}{clean_t}" if tag_prefix and not clean_t.startswith("anki") else f"#{clean_t}"
            if full_tag not in tag_items:
                tag_items.append(full_tag)
    tags_str = " ".join(tag_items) if tag_items else "#anki"

    anki_link = f"[Open in Anki (nid:{note_id})](anki://search?q=nid:{note_id})"

    lines = [
        f"- **Deck:** `{deck_name}`",
        f"- **Note Type:** `{model_name}`",
        f"- **Note ID:** `{note_id}`",
    ]
    if card_id:
        lines.append(f"- **Card ID:** `{card_id}`")

    # Add spaced repetition review stats if available
    if card_stats:
        ivl = card_stats.get("interval", "New")
        ease = card_stats.get("ease", "N/A")
        reps = card_stats.get("reps", 0)
        lapses = card_stats.get("lapses", 0)
        state = card_stats.get("state", "New")
        due = card_stats.get("due_date", "")
        flag = card_stats.get("flag", "None")

        lines.append(f"- **Review Stats:** Interval: `{ivl}` | Ease: `{ease}` | Reps: `{reps}` | Lapses: `{lapses}`")
        state_str = f"`{state}`"
        if due:
            state_str += f" (Due: `{due}`)"
        lines.append(f"- **Card State:** {state_str}")
        if flag and flag != "None":
            lines.append(f"- **Flag:** 🚩 `{flag}`")

    lines.append(f"- **Tags:** {tags_str}")
    lines.append(f"- **Created:** `{now_iso}`")
    lines.append(f"- 🔗 {anki_link}")

    if style == "details":
        open_attr = "" if collapsed else " open"
        inner = "\n".join(lines)
        return f"<details{open_attr}>\n<summary>📋 Anki Details</summary>\n\n{inner}\n\n</details>"
    else:  # Obsidian foldable callout
        fold_char = "-" if collapsed else "+"
        callout_lines = [f"> [!info]{fold_char} 📋 Anki Details"]
        for line in lines:
            callout_lines.append(f"> {line}")
        return "\n".join(callout_lines)


def split_fields(
    fields: List[Tuple[str, str]], config: Dict[str, Any]
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """
    Separates note fields into:
      1. Primary fields (shown directly in the note body: Front, Back, Text, Question, Answer).
      2. Supplementary fields (collapsed in callout: Extra, Missed Questions, Lecture Notes, etc.).
    """
    primary_config = config.get("primary_fields", "Front, Back, Text, Question, Answer")
    primary_names = {p.strip().lower() for p in primary_config.split(",") if p.strip()}
    collapse_supplementary = config.get("collapse_supplementary_fields", True)

    primary_fields: List[Tuple[str, str]] = []
    supplementary_fields: List[Tuple[str, str]] = []

    # Check if any field matches the primary list
    has_primary_match = any(name.strip().lower() in primary_names for name, _ in fields)

    for name, html_val in fields:
        name_clean = name.strip()
        name_lower = name_clean.lower()
        val_clean = html_val.strip()

        if not collapse_supplementary:
            primary_fields.append((name_clean, html_val))
            continue

        if has_primary_match:
            if name_lower in primary_names:
                primary_fields.append((name_clean, html_val))
            else:
                # Supplementary field: only keep if not empty
                if val_clean:
                    supplementary_fields.append((name_clean, html_val))
        else:
            # Fallback for notes without standard names: first 1 or 2 fields are primary
            cutoff = 2 if len(fields) >= 2 else 1
            if len(primary_fields) < cutoff:
                primary_fields.append((name_clean, html_val))
            else:
                if val_clean:
                    supplementary_fields.append((name_clean, html_val))

    return primary_fields, supplementary_fields


def build_supplementary_callout(
    supplementary_fields: List[Tuple[str, str]],
    note_id: int,
    config: Dict[str, Any],
) -> str:
    """
    Builds a collapsible callout grouping all supplementary fields like
    Extra, Missed Questions, Lecture Notes, etc.
    """
    cloze_style = config.get("cloze_style", "highlight")
    use_wikilinks = config.get("use_wikilinks", True)
    callout_title = config.get("supplementary_callout_title", "📑 Extra & Notes").strip() or "📑 Extra & Notes"
    callout_type = config.get("supplementary_callout_type", "note").strip() or "note"
    collapsed = config.get("metadata_collapsed", True)
    fold_char = "-" if collapsed else "+"
    style = config.get("metadata_section_style", "callout")

    rendered_items: List[Tuple[str, str]] = []
    for f_name, f_html in supplementary_fields:
        f_md = anki_html_to_markdown(f_html, cloze_style=cloze_style, use_wikilinks=use_wikilinks)
        if f_md:
            rendered_items.append((f_name, f_md))

    if not rendered_items:
        return ""

    anki_link = f"[Open in Anki (nid:{note_id})](anki://search?q=nid:{note_id})"

    if style == "details":
        open_attr = "" if collapsed else " open"
        inner_parts = []
        for f_name, f_md in rendered_items:
            inner_parts.append(f"<h4>{f_name}</h4>\n\n{f_md}\n")
        inner_parts.append(f"\n<hr>\n<p><a href=\"anki://search?q=nid:{note_id}\">🔗 {anki_link}</a></p>")
        return f"<details{open_attr}>\n<summary>{callout_title}</summary>\n\n" + "\n".join(inner_parts) + "\n</details>"
    else:  # Obsidian foldable callout
        lines = [f"> [!{callout_type}]{fold_char} {callout_title}"]
        for f_name, f_md in rendered_items:
            lines.append(f"> #### {f_name}")
            for m_line in f_md.split("\n"):
                lines.append(f"> {m_line}" if m_line.strip() else ">")
            lines.append(">")
        lines.append("> ---")
        lines.append(f"> 🔗 {anki_link}")
        return "\n".join(lines)


def format_obsidian_markdown(
    note_id: int,
    card_id: Optional[int],
    deck_name: str,
    model_name: str,
    tags: List[str],
    fields: List[Tuple[str, str]],
    config: Dict[str, Any],
    card_stats: Optional[Dict[str, Any]] = None,
    is_high_difficulty: bool = False,
    export_count: int = 1,
) -> Tuple[str, str]:
    """
    Formats the note content into Obsidian Markdown.
    Card text (Front/Back/Text) stays clean in the note body.
    Supplementary fields (Extra, Missed Questions, Lecture Notes) go into a collapsible callout.
    Anki metadata is stored cleanly in YAML frontmatter.
    """
    title = extract_note_title(fields, fallback_id=note_id)
    cloze_style = config.get("cloze_style", "highlight")
    use_wikilinks = config.get("use_wikilinks", True)
    tag_prefix = config.get("tag_prefix", "anki/")
    frontmatter_enabled = config.get("frontmatter_enabled", True)
    show_anki_details = config.get("show_anki_details_callout", False)

    now_iso = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prepare Markdown content parts
    md_parts: List[str] = []

    # 1. Frontmatter (All metadata lives cleanly here)
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

        if is_high_difficulty:
            md_parts.append('anki_difficulty: "High"')
            md_parts.append(f"anki_export_count: {export_count}")

        # Include Spaced Repetition Stats for Dataview Queries
        if card_stats:
            if "ease" in card_stats:
                md_parts.append(f'anki_ease: "{card_stats["ease"]}"')
            if "interval_days" in card_stats:
                md_parts.append(f'anki_interval_days: {card_stats["interval_days"]}')
            if "reps" in card_stats:
                md_parts.append(f'anki_reps: {card_stats["reps"]}')
            if "lapses" in card_stats:
                md_parts.append(f'anki_lapses: {card_stats["lapses"]}')
            if "state" in card_stats:
                md_parts.append(f'anki_state: "{card_stats["state"]}"')
            if "due_date" in card_stats:
                md_parts.append(f'anki_due: "{card_stats["due_date"]}"')
            if card_stats.get("flag") and card_stats["flag"] != "None":
                md_parts.append(f'anki_flag: "{card_stats["flag"]}"')

        # Tags
        formatted_tags = []
        if tag_prefix:
            formatted_tags.append("anki")
        for t in tags:
            clean_t = re.sub(r"[^\w\-_\/]", "_", t)
            if clean_t:
                formatted_tags.append(f"{tag_prefix}{clean_t}" if tag_prefix and not clean_t.startswith("anki") else clean_t)

        if is_high_difficulty:
            high_diff_tag = f"{tag_prefix}high-difficulty" if tag_prefix else "high-difficulty"
            if high_diff_tag not in formatted_tags:
                formatted_tags.append(high_diff_tag)

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

    if is_high_difficulty:
        md_parts.append("> [!warning] 🔥 **High Difficulty / Struggle Card** (Exported multiple times)\n")

    # Optional Anki Details Callout (only if explicitly enabled)
    if show_anki_details:
        meta_sec = build_metadata_section(
            note_id=note_id,
            card_id=card_id,
            deck_name=deck_name,
            model_name=model_name,
            tags=tags,
            tag_prefix=tag_prefix,
            now_iso=now_iso,
            config=config,
            card_stats=card_stats,
        )
        md_parts.append(f"{meta_sec}\n")

    # 3. Split Fields into Primary (Card Text) and Supplementary (Extra, Missed Questions, etc.)
    primary_fields, supplementary_fields = split_fields(fields, config)

    # 4. Render Primary Fields (Core Card Text)
    for field_name, field_html in primary_fields:
        field_md = anki_html_to_markdown(
            field_html, cloze_style=cloze_style, use_wikilinks=use_wikilinks
        )
        md_parts.append(f"## {field_name}\n")
        if field_md:
            md_parts.append(f"{field_md}\n")
        else:
            md_parts.append("*(empty)*\n")

    # 5. Render Supplementary Fields in Collapsible Callout
    if supplementary_fields:
        sup_callout = build_supplementary_callout(
            supplementary_fields=supplementary_fields,
            note_id=note_id,
            config=config,
        )
        if sup_callout:
            md_parts.append(f"\n{sup_callout}\n")
    else:
        # If no supplementary fields exist, provide a clean link at the end
        md_parts.append("\n---\n")
        md_parts.append(f"> 🔗 [Open in Anki (nid:{note_id})](anki://search?q=nid:{note_id})\n")

    markdown_text = "\n".join(md_parts)

    # Filename determination
    naming_template = config.get("file_naming", "{title}")
    max_fn_len = int(config.get("max_filename_length", 240))
    if "{title}" in naming_template:
        filename = naming_template.format(
            title=title,
            deck=sanitize_filename(deck_name, max_len=60),
            id=note_id,
            date=datetime.datetime.now().strftime("%Y-%m-%d"),
        )
    else:
        filename = title

    filename = sanitize_filename(filename, max_len=max_fn_len)
    return filename, markdown_text


def get_base_target_dir(config: Dict[str, Any]) -> Optional[str]:
    """
    Returns the root folder inside the Obsidian vault where Anki notes are kept.
    """
    vault_path = config.get("vault_path", "").strip()
    target_subfolder = config.get("target_folder", "Anki Notes").strip()

    if not vault_path and not target_subfolder:
        return None

    if os.path.isabs(target_subfolder) and not vault_path:
        return os.path.expanduser(target_subfolder)

    vault_dir = os.path.expanduser(vault_path) if vault_path else ""
    if not vault_dir:
        return None

    return os.path.join(vault_dir, target_subfolder) if target_subfolder else vault_dir


def resolve_target_paths(
    config: Dict[str, Any], deck_name: str = ""
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolves the target destination folder and media attachments folder.
    Supports mirroring Anki's subdeck hierarchy if configured.
    Returns (target_folder_path, media_folder_path).
    """
    vault_path = config.get("vault_path", "").strip()
    media_subfolder = config.get("media_folder", "attachments").strip()

    base_target_dir = get_base_target_dir(config)
    if not base_target_dir:
        return None, None

    vault_dir = os.path.expanduser(vault_path) if vault_path else ""
    if vault_dir:
        media_dir = os.path.join(vault_dir, media_subfolder) if media_subfolder else vault_dir
    else:
        media_dir = os.path.join(base_target_dir, media_subfolder) if media_subfolder else base_target_dir

    # Mirror deck hierarchy to folders if option is enabled
    target_dir = base_target_dir
    if config.get("mirror_deck_hierarchy", False) and deck_name:
        parts = [sanitize_filename(p) for p in deck_name.split("::") if sanitize_filename(p)]
        if parts:
            target_dir = os.path.join(base_target_dir, *parts)

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
    card_stats: Optional[Dict[str, Any]] = None,
    is_repeat_export: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Exports note data to Markdown file in Obsidian vault folder.
    If the note has already been exported previously, routes it to the
    'High Difficulty' subfolder (when enabled) and tracks export count.
    Pure python logic, decoupled from Anki UI.
    """
    target_dir, media_dir = resolve_target_paths(config, deck_name=deck_name)
    base_target_dir = get_base_target_dir(config)
    if not target_dir or not base_target_dir:
        return {
            "success": False,
            "error": "Obsidian Vault path is not configured. Please open Ankisidian Settings to set your vault folder.",
        }

    os.makedirs(target_dir, exist_ok=True)

    # Filename determination
    title = extract_note_title(fields, fallback_id=note_id)
    naming_template = config.get("file_naming", "{title}")
    max_fn_len = int(config.get("max_filename_length", 240))
    if "{title}" in naming_template:
        fn_raw = naming_template.format(
            title=title,
            deck=sanitize_filename(deck_name, max_len=60),
            id=note_id,
            date=datetime.datetime.now().strftime("%Y-%m-%d"),
        )
    else:
        fn_raw = title
    filename_base = sanitize_filename(fn_raw, max_len=max_fn_len)

    # 1. Check for Repeat Export & High Difficulty
    exp_tag = config.get("exported_tag_name", "obsidian_exported").strip() or "obsidian_exported"
    has_exported_tag = (exp_tag in tags) or any(t.lower() == exp_tag.lower() for t in tags)

    standard_file = os.path.join(target_dir, f"{filename_base}.md")
    standard_file_existed = os.path.exists(standard_file)

    high_diff_enabled = config.get("high_difficulty_folder_enabled", True)
    high_diff_name = config.get("high_difficulty_folder_name", "High Difficulty").strip() or "High Difficulty"
    high_diff_dir = os.path.join(base_target_dir, high_diff_name)
    high_diff_file = os.path.join(high_diff_dir, f"{filename_base}.md")
    high_diff_file_existed = os.path.exists(high_diff_file)

    if is_repeat_export is not None:
        repeat = is_repeat_export
    else:
        repeat = has_exported_tag or standard_file_existed or high_diff_file_existed

    # Determine export count
    export_count = 1
    existing_file_to_check = high_diff_file if high_diff_file_existed else (standard_file if standard_file_existed else None)
    if existing_file_to_check and os.path.exists(existing_file_to_check):
        try:
            with open(existing_file_to_check, "r", encoding="utf-8") as f:
                content = f.read(1000)
                m = re.search(r"anki_export_count:\s*(\d+)", content)
                if m:
                    export_count = int(m.group(1)) + 1
                else:
                    export_count = 2
        except Exception:
            export_count = 2
    elif repeat:
        export_count = 2

    is_high_diff = high_diff_enabled and repeat
    actual_dir = high_diff_dir if is_high_diff else target_dir
    os.makedirs(actual_dir, exist_ok=True)

    target_file = os.path.join(actual_dir, f"{filename_base}.md")

    # If moving note to High Difficulty, clean up the old file in the standard directory
    if is_high_diff and standard_file_existed and os.path.abspath(standard_file) != os.path.abspath(target_file):
        try:
            os.remove(standard_file)
        except Exception as e:
            print(f"[Ankisidian] Note moved to High Difficulty; cleanup of old file failed: {e}")

    # Format Markdown
    _, md_content = format_obsidian_markdown(
        note_id=note_id,
        card_id=card_id,
        deck_name=deck_name,
        model_name=model_name,
        tags=tags,
        fields=fields,
        config=config,
        card_stats=card_stats,
        is_high_difficulty=is_high_diff,
        export_count=export_count,
    )

    # Collision check
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                existing_text = f.read(500)
            if f"anki_note_id: {note_id}" not in existing_text:
                target_file = os.path.join(actual_dir, f"{filename_base}_{note_id}.md")
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

    # Auto-generate Dataview dashboard note if enabled
    if config.get("create_dataview_dashboard", True):
        try:
            generate_dataview_dashboard(config, overwrite=False)
        except Exception as e:
            print(f"[Ankisidian] Auto-creation of Dataview dashboard note failed: {e}")

    return {
        "success": True,
        "file_path": target_file,
        "filename": os.path.basename(target_file),
        "copied_media": copied_media,
        "is_high_difficulty": is_high_diff,
        "is_repeat": repeat,
        "export_count": export_count,
    }


def generate_dataview_dashboard(config: Dict[str, Any], overwrite: bool = True) -> Dict[str, Any]:
    """
    Creates or updates an Obsidian Dataview Dashboard Markdown note in the Anki cards folder.
    Provides live tables for:
      - High Difficulty Cards (Repeat Exports)
      - Leeches & Struggle Cards (Lapses >= 3 or Ease <= 210%)
      - Cards Due Soon
      - Deck Breakdown
      - Flagged Cards
      - Recently Transferred Cards
    """
    base_dir = get_base_target_dir(config)
    if not base_dir:
        return {"success": False, "error": "Obsidian Vault path is not configured."}

    os.makedirs(base_dir, exist_ok=True)
    dashboard_name = config.get("dashboard_filename", "Anki Dashboard.md").strip() or "Anki Dashboard.md"
    if not dashboard_name.endswith(".md"):
        dashboard_name += ".md"

    file_path = os.path.join(base_dir, dashboard_name)
    if not overwrite and os.path.exists(file_path):
        return {"success": True, "created": False, "file_path": file_path}

    target_subfolder = config.get("target_folder", "Anki Notes").strip()
    tag_prefix = config.get("tag_prefix", "anki/").strip()
    high_diff_name = config.get("high_difficulty_folder_name", "High Difficulty").strip() or "High Difficulty"

    # Dataview query folder scope
    folder_scope = f'"{target_subfolder}"' if target_subfolder else '""'
    clean_name = dashboard_name[:-3]

    content = f"""---
title: "Anki Obsidian Hub & Dataview Dashboard"
tags:
  - {tag_prefix}dashboard
---

# 📊 Anki Obsidian Hub & Dataview Dashboard

> [!info] 💡 Live Dashboard (Requires Dataview Plugin)
> This dashboard dynamically queries all Anki cards exported to your Obsidian vault using the community **Dataview** plugin.
> If queries appear as code blocks, install Dataview via **Obsidian Settings → Community Plugins → Browse → Dataview**.

---

## 🔥 High Difficulty Cards (Repeat Exports)
*Cards you have exported multiple times or marked as high difficulty because you struggled with them during reviews.*

```dataview
TABLE
  anki_deck AS "Deck",
  anki_lapses AS "Lapses",
  anki_ease AS "Ease",
  anki_interval_days AS "Interval (d)",
  anki_export_count AS "Export Count"
FROM {folder_scope}
WHERE anki_difficulty = "High" OR contains(file.tags, "high-difficulty") OR contains(file.folder, "{high_diff_name}")
SORT anki_lapses DESC, anki_export_count DESC
```

---

## ⚠️ Struggle Cards & Leeches (Lapses ≥ 3 or Low Ease)
*Cards with multiple lapses or an ease factor ≤ 210% that need extra review.*

```dataview
TABLE
  anki_deck AS "Deck",
  anki_lapses AS "Lapses",
  anki_ease AS "Ease",
  anki_due AS "Due Date"
FROM {folder_scope}
WHERE anki_note_id AND (anki_lapses >= 3 OR (anki_ease AND number(substring(anki_ease, 0, length(anki_ease) - 1)) <= 210))
SORT anki_lapses DESC, anki_ease ASC
LIMIT 30
```

---

## 📅 Upcoming Reviews & Due Soon
*Cards due for review soon.*

```dataview
TABLE
  anki_deck AS "Deck",
  anki_due AS "Due Date",
  anki_interval_days AS "Interval (d)",
  anki_state AS "State"
FROM {folder_scope}
WHERE anki_due AND file.name != "{clean_name}"
SORT anki_due ASC
LIMIT 25
```

---

## 📚 Deck Breakdown
*Overview of flashcards stored in your Obsidian vault grouped by Anki deck.*

```dataview
TABLE
  length(rows) AS "Total Cards",
  average(rows.anki_lapses) AS "Avg Lapses",
  average(rows.anki_interval_days) AS "Avg Interval (d)"
FROM {folder_scope}
WHERE anki_deck AND file.name != "{clean_name}"
GROUP BY anki_deck
SORT length(rows) DESC
```

---

## 🚩 Flagged Cards
*Cards marked with flags in Anki.*

```dataview
TABLE
  anki_flag AS "Flag",
  anki_deck AS "Deck",
  anki_ease AS "Ease",
  anki_interval_days AS "Interval (d)"
FROM {folder_scope}
WHERE anki_flag AND anki_flag != "None" AND file.name != "{clean_name}"
SORT anki_flag ASC
```

---

## ⏱️ Recently Transferred Cards
*The latest flashcards transferred from Anki to Obsidian.*

```dataview
TABLE
  anki_deck AS "Deck",
  file.mtime AS "Transferred"
FROM {folder_scope}
WHERE anki_note_id AND file.name != "{clean_name}"
SORT file.mtime DESC
LIMIT 15
```
"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"success": True, "created": True, "file_path": file_path}


def append_to_daily_note(
    note_id: int,
    card_id: Optional[int],
    deck_name: str,
    model_name: str,
    tags: List[str],
    fields: List[Tuple[str, str]],
    card_stats: Optional[Dict[str, Any]],
    anki_media_dir: Optional[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Appends the active card into today's Obsidian Daily Note under a review heading.
    """
    vault_path = config.get("vault_path", "").strip()
    if not vault_path:
        return {"success": False, "error": "Vault path not configured"}

    vault_dir = os.path.expanduser(vault_path)
    daily_subfolder = config.get("daily_note_folder", "Daily Notes").strip()
    daily_format = config.get("daily_note_format", "%Y-%m-%d").strip() or "%Y-%m-%d"
    heading = config.get("daily_note_heading", "## Anki Reviews").strip() or "## Anki Reviews"

    target_dir = os.path.join(vault_dir, daily_subfolder) if daily_subfolder else vault_dir
    os.makedirs(target_dir, exist_ok=True)

    today = datetime.date.today()
    date_filename = today.strftime(daily_format)
    daily_file = os.path.join(target_dir, f"{date_filename}.md")

    title = extract_note_title(fields, fallback_id=note_id)
    cloze_style = config.get("cloze_style", "highlight")
    use_wikilinks = config.get("use_wikilinks", True)

    # Split fields into primary and supplementary
    primary_fields, supplementary_fields = split_fields(fields, config)

    entry_parts = [
        f"### {title}",
        f"> 📚 *{deck_name}*",
        "",
    ]

    # Render primary fields
    for f_name, f_html in primary_fields:
        f_md = anki_html_to_markdown(f_html, cloze_style=cloze_style, use_wikilinks=use_wikilinks)
        if f_md:
            entry_parts.append(f"**{f_name}:**\n{f_md}\n")

    # Render supplementary callout (Extra, Missed Questions, etc.)
    if supplementary_fields:
        sup_callout = build_supplementary_callout(
            supplementary_fields=supplementary_fields,
            note_id=note_id,
            config=config,
        )
        if sup_callout:
            entry_parts.append(f"\n{sup_callout}\n")
    else:
        entry_parts.append(f"> 🔗 [Open in Anki (nid:{note_id})](anki://search?q=nid:{note_id})")

    entry_content = "\n".join(entry_parts).strip()

    # Read existing content if file exists
    existing_content = ""
    if os.path.exists(daily_file):
        with open(daily_file, "r", encoding="utf-8") as f:
            existing_content = f.read()

        if f"nid:{note_id}" in existing_content:
            return {
                "success": True,
                "already_appended": True,
                "file_path": daily_file,
                "filename": os.path.basename(daily_file),
            }

    # Format output
    if not existing_content.strip():
        new_content = f"# {date_filename}\n\n{heading}\n\n{entry_content}\n"
    else:
        if heading in existing_content:
            parts = existing_content.split(heading, 1)
            new_content = parts[0] + heading + "\n\n" + entry_content + "\n" + parts[1]
        else:
            new_content = existing_content.rstrip() + f"\n\n{heading}\n\n{entry_content}\n"

    with open(daily_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Copy media
    media_subfolder = config.get("media_folder", "attachments").strip()
    media_dir = os.path.join(vault_dir, media_subfolder) if media_subfolder else vault_dir
    copied_media = []
    if config.get("copy_media", True) and anki_media_dir:
        media_refs = extract_media_references([v for _, v in fields])
        if media_refs:
            copied_media = copy_note_media(media_refs, anki_media_dir, media_dir)

    return {
        "success": True,
        "file_path": daily_file,
        "filename": os.path.basename(daily_file),
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
