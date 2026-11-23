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

### `mirror_deck_hierarchy`
`true` to automatically mirror Anki's subdeck hierarchy as nested subfolders in Obsidian (e.g. `Biology::Genetics` -> `Anki Notes/Biology/Genetics/`).
*Default:* `false`

### `daily_note_enabled`
`true` to enable the "Append to Daily Note" feature.
*Default:* `true`

### `daily_note_folder`
Subfolder in your vault where daily notes are stored (or empty for vault root).
*Default:* `"Daily Notes"`

### `daily_note_heading`
The heading inside your daily note under which Anki reviews are appended.
*Default:* `"## Anki Reviews"`

### `daily_note_shortcut`
Keyboard shortcut to append the current card to today's daily note.
*Default:* `"Ctrl+Alt+D"` (works as `Cmd+Option+D` on macOS)

### `reviewer_quick_key`
A single number or key (e.g. `"5"`) that triggers sending the card to Obsidian while reviewing cards, without needing any modifier keys like Ctrl or Cmd!
*Default:* `"5"`

### `reviewer_daily_key`
A single key (e.g. `"6"`) to append the card to your Daily Note while reviewing cards (or leave empty to disable).
*Default:* `""`

### `shortcut`
Keyboard shortcut to transfer the current note to Obsidian.
*Default:* `"Ctrl+Shift+O"` (works as `Cmd+Shift+O` on macOS)

### `show_draggable_button`
`true` to show a floating draggable button on the Anki window.
Set to `false` to disable the on-screen button completely and rely solely on the keybinds!

### `button_label`
Text and icon shown on the draggable button.
*Default:* `"📓 To Obsidian"`

### `button_position`
`[x, y]` pixel coordinates of the floating button relative to Anki's window.

### `include_stats`
`true` to calculate and include spaced repetition review statistics (Interval, Ease Factor, Reps, Lapses, State, Due Date) in frontmatter and the collapsible metadata section.
*Default:* `true`

### `cloze_style`
How to format Anki cloze deletions (`{{c1::answer}}`):
- `"highlight"`: Obsidian highlight `==answer==`
- `"bold"`: Bold `**answer**`
- `"keep"`: Keep raw cloze `{{c1::answer}}`
- `"spoiler"`: Markdown comment spoiler `%%answer%%`

### `open_in_obsidian_after_export`
`true` to immediately open the note in Obsidian after exporting.

### `frontmatter_enabled`
`true` to include YAML metadata (deck name, model name, note ID, tags, timestamps, review stats).

### `primary_fields`
Comma-separated field names that should appear directly in the main note body as core card text.
*Default:* `"Front, Back, Text, Question, Answer"`

### `collapse_supplementary_fields`
`true` to group all non-primary fields (such as `Extra`, `Missed Questions`, `Lecture Notes`, `Pathoma`, `First Aid`, etc.) into a clean, collapsible callout.
*Default:* `true`

### `supplementary_callout_title`
Title of the collapsible callout for supplementary fields.
*Default:* `"📑 Extra & Notes"`

### `show_anki_details_callout`
`true` to include a separate Anki metadata box in the note body.
*Default:* `false` (since all Anki metadata is already stored in the YAML frontmatter properties).

### `metadata_section_style`
Format of the collapsible callout:
- `"callout"`: Native Obsidian collapsible callout `> [!note]- 📑 Extra & Notes` (default)
- `"details"`: HTML collapsible tag `<details><summary>📑 Extra & Notes</summary>...</details>`

### `metadata_collapsed`
`true` to have the overarching section minimized (collapsed) by default when opening the note in Obsidian.

### `metadata_position`
`"top"` to place the minimizable section right under the title before the card text (default), or `"bottom"` to place it after the card text.
