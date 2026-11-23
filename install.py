#!/usr/bin/env python3
"""
Ankisidian - Add-on Installer / Linker
Automatically detects your Anki addons directory and installs/symlinks Ankisidian.
Works on macOS, Windows, and Linux.
"""

import argparse
import os
import shutil
import sys

ADDON_FOLDER_NAME = "ankisidian"


def get_anki_addons_dir() -> str:
    """Finds the default Anki addons21 directory for the current platform."""
    home = os.path.expanduser("~")

    if sys.platform == "darwin":  # macOS
        # Typical path: ~/Library/Application Support/Anki2/addons21
        return os.path.join(home, "Library", "Application Support", "Anki2", "addons21")
    elif sys.platform.startswith("win"):  # Windows
        appdata = os.environ.get("APPDATA")
        if appdata:
            return os.path.join(appdata, "Anki2", "addons21")
        return os.path.join(home, "AppData", "Roaming", "Anki2", "addons21")
    else:  # Linux
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            return os.path.join(xdg_data, "Anki2", "addons21")
        return os.path.join(home, ".local", "share", "Anki2", "addons21")


def main():
    parser = argparse.ArgumentParser(description="Install Ankisidian into Anki's addons directory.")
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of creating a symbolic link (symlink is default for easy development)",
    )
    parser.add_argument(
        "--dest",
        type=str,
        default="",
        help="Explicit destination directory for addons21 if using a custom Anki profile",
    )
    args = parser.parse_args()

    source_dir = os.path.dirname(os.path.abspath(__file__))
    addons_dir = args.dest if args.dest else get_anki_addons_dir()
    target_link = os.path.join(addons_dir, ADDON_FOLDER_NAME)

    print(f"📦 Ankisidian Installer")
    print(f"Source: {source_dir}")
    print(f"Anki Addons Directory: {addons_dir}")

    # Ensure parent addons directory exists
    try:
        if not os.path.exists(addons_dir):
            print(f"Creating addons directory: {addons_dir}")
            os.makedirs(addons_dir, exist_ok=True)
    except FileExistsError:
        pass
    except Exception as e:
        print(f"Notice: {e}")

    # Check if existing installation/link exists
    if os.path.islink(target_link) or os.path.exists(target_link):
        print(f"Removing existing link/folder at: {target_link}")
        if os.path.islink(target_link) or os.path.isfile(target_link):
            os.unlink(target_link)
        else:
            shutil.rmtree(target_link)

    if args.copy:
        print(f"Copying files to: {target_link}")
        try:
            shutil.copytree(
                source_dir,
                target_link,
                ignore=shutil.ignore_patterns(".git*", "__pycache__*", "*.pyc", "*.ankiaddon", "scratch*"),
            )
            print("✅ Files copied successfully!")
        except PermissionError:
            print("⚠️ Permission denied writing to Anki addons directory from this context.")
            print("Please run this command in your terminal directly:")
            print(f"    python3 {os.path.abspath(__file__)}")
            return
    else:
        print(f"Creating symlink: {target_link} -> {source_dir}")
        try:
            os.symlink(source_dir, target_link)
            print("✅ Symlink created successfully! Any code edits will be immediately live in Anki.")
        except PermissionError:
            print("⚠️ Permission denied writing to Anki addons directory from this context.")
            print("To link Ankisidian directly, please run in your terminal:")
            print(f'    ln -s "{source_dir}" "{target_link}"')
            print("\nAlternatively, you can install 'ankisidian.ankiaddon' directly inside Anki:")
            print("    Anki -> Tools -> Add-ons -> Install from file... -> select ankisidian.ankiaddon")
            return
        except Exception as e:
            print(f"Symlink failed ({e}). Falling back to copying files...")
            try:
                shutil.copytree(
                    source_dir,
                    target_link,
                    ignore=shutil.ignore_patterns(".git*", "__pycache__*", "*.pyc", "*.ankiaddon", "scratch*"),
                )
                print("✅ Files copied successfully!")
            except PermissionError:
                print("⚠️ Permission denied writing to Anki addons directory.")
                return

    print("\n🎉 Installation complete!")
    print("Next steps:")
    print("1. Restart Anki.")
    print("2. You will see the 'Ankisidian' menu in the top menu bar and a floating draggable button.")
    print("3. Open 'Ankisidian -> Ankisidian Settings...' (or Tools -> Add-ons -> Ankisidian -> Config) to select your Obsidian Vault path.")


if __name__ == "__main__":
    main()
