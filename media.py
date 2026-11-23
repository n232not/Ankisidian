"""
Ankisidian - Media Handler
Extracts media files (images, audio) referenced in Anki notes
and safely copies them to the Obsidian attachments folder.
"""

from __future__ import annotations

import os
import re
import shutil
from typing import List, Set
from urllib.parse import unquote


def extract_media_references(fields_text: List[str]) -> Set[str]:
    """
    Finds all referenced media file names from fields text / HTML.
    Supports <img src="...">, [sound:...], and data-src.
    """
    filenames: Set[str] = set()

    for text in fields_text:
        if not text:
            continue

        # Find <img> tags
        img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', text, re.IGNORECASE)
        for match in img_matches:
            # Anki media filenames do not have protocols like http:// or https://
            if match.startswith("http://") or match.startswith("https://") or match.startswith("data:"):
                continue
            filename = unquote(match.split("/")[-1].split("?")[0].strip())
            if filename:
                filenames.add(filename)

        # Find [sound:filename] tags
        sound_matches = re.findall(r"\[sound:([^\]]+)\]", text, re.IGNORECASE)
        for match in sound_matches:
            filename = unquote(match.strip())
            if filename:
                filenames.add(filename)

    return filenames


def copy_note_media(
    media_filenames: Set[str],
    anki_media_dir: str,
    obsidian_media_dir: str,
    overwrite: bool = False,
) -> List[str]:
    """
    Copies referenced media files from Anki media collection to Obsidian attachments folder.
    Returns list of successfully copied filenames.
    """
    copied: List[str] = []
    if not anki_media_dir or not os.path.isdir(anki_media_dir):
        return copied

    if not obsidian_media_dir:
        return copied

    os.makedirs(obsidian_media_dir, exist_ok=True)

    for filename in media_filenames:
        src_path = os.path.join(anki_media_dir, filename)
        if not os.path.isfile(src_path):
            continue

        dest_path = os.path.join(obsidian_media_dir, filename)
        if not overwrite and os.path.exists(dest_path):
            # Already exists, no need to overwrite
            copied.append(filename)
            continue

        try:
            shutil.copy2(src_path, dest_path)
            copied.append(filename)
        except Exception as e:
            print(f"[Ankisidian] Failed to copy media file {filename}: {e}")

    return copied
