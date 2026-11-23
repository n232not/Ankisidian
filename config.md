# Ankisidian Configuration

### `vault_path`
The absolute filesystem path to your Obsidian Vault root directory.
*Example:* `"/Users/yourname/Documents/Obsidian/PersonalVault"`

### `target_folder`
Folder inside your vault where Anki notes will be created.
*Example:* `"Anki Notes"` or `"Inbox/Cards"`

### `media_folder`
Folder inside your vault where card images and audio files are copied.
*Example:* `"attachments"`

### `copy_media`
`true` to automatically copy images and sound files referenced by the note to Obsidian's attachments folder.

### `shortcut`
Keyboard shortcut to transfer the current note to Obsidian.
*Default:* `"Ctrl+Shift+O"` (works as `Cmd+Shift+O` on macOS)

### `show_draggable_button`
`true` to show a floating draggable button on the Anki window.
Clicking it transfers the current note; dragging moves it to any position.

### `button_label`
Text and icon shown on the draggable button.
*Default:* `"📓 To Obsidian"`

### `button_position`
`[x, y]` pixel coordinates of the floating button relative to Anki's window.

### `cloze_style`
How to format Anki cloze deletions (`{{c1::answer}}`):
- `"highlight"`: Obsidian highlight `==answer==`
- `"bold"`: Bold `**answer**`
- `"keep"`: Keep raw cloze `{{c1::answer}}`
- `"spoiler"`: Markdown comment spoiler `%%answer%%`

### `open_in_obsidian_after_export`
`true` to immediately open the note in Obsidian after exporting.

### `frontmatter_enabled`
`true` to include YAML metadata (deck name, model name, note ID, tags, timestamps).
