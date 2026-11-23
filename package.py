#!/usr/bin/env python3
"""
Ankisidian - Package Builder
Packages the add-on into an 'ankisidian.ankiaddon' file for distribution or direct installation.
"""

import os
import zipfile

OUTPUT_NAME = "ankisidian.ankiaddon"
EXCLUDED_PATTERNS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
    OUTPUT_NAME,
    "test_ankisidian.py",
    "package.py",
    "scratch",
}


def should_exclude(path: str) -> bool:
    parts = path.split(os.sep)
    for part in parts:
        if part in EXCLUDED_PATTERNS or part.endswith(".pyc"):
            return True
    return False


def build_package():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, OUTPUT_NAME)

    print(f"📦 Packaging Ankisidian into {OUTPUT_NAME}...")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_dir):
            rel_root = os.path.relpath(root, base_dir)
            if rel_root != "." and should_exclude(rel_root):
                continue

            for file in files:
                rel_file = os.path.normpath(os.path.join(rel_root, file)) if rel_root != "." else file
                if should_exclude(rel_file):
                    continue
                abs_file = os.path.join(root, file)
                zf.write(abs_file, rel_file)
                print(f"  + {rel_file}")

    print(f"\n✅ Created: {output_path} ({os.path.getsize(output_path)} bytes)")
    print("You can install it by opening Anki -> Tools -> Add-ons -> Install from file... and selecting this file!")


if __name__ == "__main__":
    build_package()
