# 💎 Ankisidian — Anki to Obsidian Note Transfer Add-on

**Ankisidian** is an Anki add-on that allows you to instantly transfer the card/note you are currently viewing, reviewing, or editing in Anki directly into your Obsidian vault as a clean Markdown note.

Transfer notes with a **keyboard shortcut**, an option in the **top menu bar**, or a sleek **draggable floating button** that you can reposition anywhere on your screen.

---

## ✨ Features

- ⚡ **Instant 1-Click Transfer**: Export active notes directly from the **Reviewer** (study mode), **Card Browser**, or **Edit Current** dialog.
- 🎛️ **Multiple Trigger Options**:
  - **Keybind / Shortcut**: Customizable shortcut (default: `Ctrl+Shift+O` / `Cmd+Shift+O` on macOS).
  - **Top Menu Option**: Dedicated `Ankisidian` menu in Anki's main menu bar + `Tools -> Ankisidian: Transfer to Obsidian`.
  - **Draggable Floating Button**: A floating Obsidian-styled button (`📓 To Obsidian`) that you can drag to any position on your screen. Position persists across Anki restarts.
  - **Browser Batch Export**: Select one or multiple cards in Anki's Card Browser and export them all at once.
- 📝 **Clean Markdown & Formatting**:
  - Converts Anki HTML (paragraphs, bold, italics, underlines, lists, blockquotes, code blocks) to Markdown.
  - **Cloze Deletion Styling**: Format clozes as Obsidian highlights (`==answer==`), bold (`**answer**`), spoilers (`%%answer%%`), or keep raw Anki syntax (`{{c1::answer}}`).
  - **LaTeX & MathJax**: Converts Anki MathJax (`\( ... \)`, `\[ ... \]`) and LaTeX (`[$]...[/$]`, `[latex]...[/latex]`) to Obsidian MathJax (`$math$` and `$$\nmath\n$$`).
- 🖼️ **Automatic Media Copying**:
  - Images (`<img src="...">`) and audio files (`[sound:...]`) referenced on the card are automatically copied to your Obsidian vault's attachments folder.
  - Generates Obsidian native wikilinks (`![[image.png]]`) or standard Markdown links.
- 📊 **Spaced Repetition Review Stats (Dataview Ready)**:
  - Automatically captures review statistics: **Interval** (e.g. `21d`), **Ease Factor** (e.g. `250%`), **Reviews count** (`reps`), **Lapse count** (`lapses`), **Card State** (`New`, `Learning`, `Review`, `Suspended`), **Due Date**, and **Color Flag**.
  - Populated in YAML frontmatter (for Obsidian Dataview tables/queries) and inside the collapsible metadata section.
- 🏷️ **Automatic Anki Export Tagging (`obsidian_exported`)**:
  - Automatically adds the `obsidian_exported` tag to Anki notes in Anki's database upon export.
  - Search `-tag:obsidian_exported` in Anki's Browser anytime to see all cards you haven't transferred to Obsidian yet!
- 🔥 **High Difficulty Folder for Repeat Exports (Optional)**:
  - If you export a card to Obsidian multiple times during reviews, Ankisidian detects it as a struggle card and automatically moves it to a dedicated `Anki Notes/High Difficulty` folder.
  - Adds `anki_difficulty: "High"` and tracks `anki_export_count` in frontmatter, with an alert callout at the top of the note.
- 📊 **Built-in Obsidian Dataview Dashboard (`Anki Dashboard.md`)**:
  - Automatically creates a live interactive dashboard note in your Obsidian Anki folder with Dataview tables for:
    - *High Difficulty Cards (Repeat Exports)*
    - *Leeches & Struggle Cards (Lapses ≥ 3 or Ease ≤ 210%)*
    - *Upcoming Reviews & Due Soon*
    - *Deck Breakdown & Card Counts*
    - *Flagged Cards & Recent Transfers*
- 🌳 **Mirror Deck Hierarchy into Obsidian Subfolders (Optional)**:
  - Organizes notes according to your Anki decks: `Medicine::Cardiology::Arrhythmias` creates `ObsidianVault/Anki Notes/Medicine/Cardiology/Arrhythmias/Card.md`.
- 📅 **Append to Today's Daily Note (Optional)**:
  - With a single keybind (<kbd>Ctrl+Alt+D</kbd> / <kbd>Cmd+Option+D</kbd>) or menu click, appends the card directly into today's Obsidian Daily Note under `## Anki Reviews`.
- 🚩 **Batch Export by Flag Color**:
  - Export cards by flag (Red, Orange, Green, Blue, Pink, Turquoise, Purple, or Any Flag) across your whole collection or current deck.
- 🎛️ **Keybind-Only Mode (Hide Floating Button)**:
  - Prefer a clean interface without on-screen buttons? Turn off the floating button in Settings to use purely keyboard shortcuts!
- 📁 **Minimizable Supplementary Fields (Extra, Missed Questions, Lecture Notes)**:
  - Keeps your notes clean: the core card text (`Front`/`Back` or `Text`) renders directly in the note body.
  - All auxiliary fields like `Extra`, `Missed Questions`, `Lecture Notes`, `Pathoma`, `First Aid`, etc. are neatly grouped inside a separate **collapsible callout** (`> [!note]- 📑 Extra & Notes`) that is folded by default!
  - No redundant Anki metadata boxes cluttering the body — all Anki details (deck, model, card ID, ease, interval, reps, lapses, state) live cleanly in the YAML frontmatter and tags!
- 🏷️ **YAML Frontmatter & Metadata**:
  - Includes note ID, card ID, deck name, note type/model, tags, created timestamp, and updated timestamp.
- 🔗 **Two-Way Linking**:
  - Includes a clickable link inside each exported Obsidian note (`[Open in Anki (nid:...)](anki://search?q=nid:...)`) that opens Anki's browser directly to that note.
- ⚙️ **Graphical Settings Dialog**:
  - Configure vault path with a visual directory picker ("Browse...").
  - Set target folder (e.g. `Anki Notes`), attachments subfolder, shortcuts, and button styling.

---

## 🚀 Installation

### Option 1: Quick Install Script (Recommended)

Run the included installer script in your terminal:

```bash
cd /Users/nihanthpinnaka/Documents/Ankisidian
python3 install.py
```

This symlinks the add-on folder directly into Anki's `addons21` directory so you can use it immediately and any updates are instantly live.

### Option 2: Package as `.ankiaddon`

Build the `.ankiaddon` bundle:

```bash
python3 package.py
```

Then in Anki:
1. Go to **Tools** → **Add-ons**.
2. Click **Install from file...**
3. Select `ankisidian.ankiaddon`.
4. Restart Anki.

---

## 🎯 How to Use

1. **First-time Setup**:
   - Start Anki.
   - Go to the top menu: **Ankisidian** → **⚙️ Ankisidian Settings...**
   - Click **Browse...** to select your Obsidian Vault directory (e.g. `/Users/yourname/Documents/ObsidianVault`).
   - Specify your desired target subfolder (default: `Anki Notes`).
   - Click **Save Settings**.

2. **Transferring a Note**:
   - While reviewing a card in Anki:
     - **Press <kbd>5</kbd>** on your keyboard! (1-4 answer the card, **5** sends it to Obsidian).
     - **OR** press <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>O</kbd> (or <kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>O</kbd> on macOS).
     - **OR** press <kbd>Ctrl</kbd> + <kbd>Alt</kbd> + <kbd>D</kbd> (or <kbd>Cmd</kbd> + <kbd>Option</kbd> + <kbd>D</kbd>) to append to your Daily Note.
     - **OR** click the `📓 To Obsidian` floating button.
     - **OR** select **Ankisidian** → **Transfer Current Note to Obsidian** from the top menu bar.
   - A brief notification (`💎 Transferred to Obsidian: Note Title.md`) will appear confirming the export.

3. **Draggable Floating Button**:
   - Click and hold the mouse button to drag it anywhere around your Anki window.
   - Release to drop — its position is automatically remembered!
   - Single-click triggers note transfer.
   - Right-click brings up a context menu with options to transfer, open settings, or hide the button.
   - You can toggle the button on/off anytime from the **Ankisidian** menu in the top menu bar.

4. **Card Browser Batch Export**:
   - Open Anki's Card Browser (<kbd>B</kbd>).
   - Select one or more cards.
   - Select **Edit** → **Ankisidian: Transfer Selected Note(s) to Obsidian**.

---

## ⚙️ Configuration Reference

Accessible via **Ankisidian** → **⚙️ Ankisidian Settings...** or Anki's Add-on Manager:

| Option | Default | Description |
|---|---|---|
| `vault_path` | `""` | Absolute path to your Obsidian vault root folder. |
| `target_folder` | `"Anki Notes"` | Folder inside your vault where exported notes are saved. |
| `media_folder` | `"attachments"` | Subfolder inside your vault where card images and audio are copied. |
| `copy_media` | `true` | Automatically copy images and sounds referenced by notes. |
| `mirror_deck_hierarchy` | `false` | Mirror Anki subdecks into nested Obsidian subfolders. |
| `daily_note_enabled` | `true` | Enable "Append to Daily Note" feature. |
| `daily_note_folder` | `"Daily Notes"` | Subfolder for daily notes in vault (or empty for root). |
| `daily_note_heading` | `"## Anki Reviews"` | Heading inside daily note to append reviews under. |
| `daily_note_shortcut` | `"Ctrl+Alt+D"` | Keyboard shortcut to append to daily note. |
| `shortcut` | `"Ctrl+Shift+O"` | Keyboard shortcut to transfer note as a standalone file. |
| `show_draggable_button` | `true` | Show floating draggable button (turn off for keybind-only mode). |
| `button_label` | `"📓 To Obsidian"` | Text displayed on the floating button. |
| `button_position` | `[20, 80]` | Saved `[x, y]` coordinates of the floating button. |
| `include_stats` | `true` | Include spaced repetition review stats (Interval, Ease, Reps, Lapses, Due). |
| `cloze_style` | `"highlight"` | Format for clozes: `highlight` (`==ans==`), `bold` (`**ans**`), `keep`, or `spoiler`. |
| `open_in_obsidian_after_export` | `false` | Automatically reveal/open the note in Obsidian after export. |
| `frontmatter_enabled` | `true` | Add YAML metadata block at the top of each note. |
| `tag_prefix` | `"anki/"` | Prefix for imported tags (e.g. `anki/biology`). |
| `use_wikilinks` | `true` | Use `![[image.png]]` for image and audio embeds. |
| `file_naming` | `"{title}"` | Filename pattern (supports `{title}`, `{deck}`, `{id}`, `{date}`). |

---

## 📂 Exported Note Example

```markdown
---
title: "Mitochondria Function"
anki_note_id: 1718000000000
anki_card_id: 1718000000001
anki_deck: "Biology::Cell Biology"
anki_model: "Basic"
anki_ease: "250%"
anki_interval_days: 21
anki_reps: 5
anki_lapses: 0
anki_state: "Review"
tags:
  - anki
  - anki/biology
  - anki/cellular
created: 2026-11-23 01:15:00
updated: 2026-11-23 01:15:00
---

# Mitochondria Function

## Front
What is the primary function of the **mitochondria**?

![[cell_organelles.png]]

## Back
The mitochondria is known as the powerhouse of the cell. It generates most of the chemical energy needed to power the cell's biochemical reactions via ATP production.

> [!note]- 📑 Extra & Notes
> #### Extra
> Contains its own circular DNA and reproduces independently via binary fission.
>
> #### Missed Questions
> Which organelle originated from an endosymbiotic alpha-proteobacterium?
>
> #### Lecture Notes
> Prof. Davis emphasized this on slide 14 of the Bioenergetics lecture.
>
> ---
> 🔗 [Open in Anki (nid:1718000000000)](anki://search?q=nid:1718000000000)
```

---

## 🧪 Testing

Run test suite:

```bash
python3 -m unittest test_ankisidian.py
```
