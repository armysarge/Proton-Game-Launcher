# Desktop Shortcut — Design Spec

**Date:** 2026-05-15
**Project:** Proton Game Launcher

## Overview

Add a "⋮" overflow menu to the launcher toolbar that lets the user create a `.desktop` shortcut for the launcher app itself — on the Desktop, in the app menu, or both.

## Data Model

A standard Linux `.desktop` file named `proton-game-launcher.desktop`, written to one or both of:

- `~/Desktop/proton-game-launcher.desktop`
- `~/.local/share/applications/proton-game-launcher.desktop`

File content:

```ini
[Desktop Entry]
Name=Proton Game Launcher
Comment=Run Windows games via Proton-GE
Exec=bash /absolute/path/to/proton-launcher/run.sh
Icon=applications-games
Type=Application
Categories=Game;
Terminal=false
```

- `Exec` uses the absolute path to `run.sh` derived from `launcher_dir` at runtime.
- `Icon` uses the standard system icon name `applications-games` — no bundled icon file needed.
- Parent directories are created if they don't exist.

## Components

### `shortcut.py` — new file

**`create_shortcut(launcher_dir: Path, desktop: bool, app_menu: bool) -> tuple[bool, str]`**
- Generates `.desktop` file content using `launcher_dir / 'run.sh'` as the `Exec` path.
- Writes to `~/Desktop/` if `desktop=True`.
- Writes to `~/.local/share/applications/` if `app_menu=True`.
- Creates parent directories with `mkdir(parents=True, exist_ok=True)` before writing.
- Returns `(True, '')` if all requested writes succeed.
- Returns `(False, error_message)` if any write fails, with the OS error joined into the message.
- Internal helper `_write_file(path, content) -> tuple[bool, str]` handles a single write.
- Internal helper `_desktop_content(launcher_dir) -> str` generates the file content string.

### `launcher.py` — additions

**Toolbar:** A `⋮` `QPushButton` added to the right of `+ Add Game`. Styled to match the toolbar's muted button style. On click, shows a `QMenu` with one action: "Create Desktop Shortcut…".

**`_on_create_shortcut()`:** Opens an inline `QDialog` with:
- Two `QCheckBox` widgets, both checked by default:
  - "Desktop (`~/Desktop/`)"
  - "App menu (`~/.local/share/applications/`)"
- A "Create" button (disabled when neither checkbox is checked).
- A "Cancel" button.
- On "Create": calls `create_shortcut(BASE_DIR, desktop_checked, app_menu_checked)`.
  - On success: `QMessageBox.information` — "Shortcut created."
  - On failure: `QMessageBox.critical` — shows the error string.

## Error Handling

- Write failure (permissions, missing parent): `_write_file` catches `OSError` and returns the error string. `create_shortcut` collects all errors and returns them joined.
- Both checkboxes unchecked: the "Create" button is disabled — caller can never invoke `create_shortcut` with both `False`.

## Testing

**`tests/test_shortcut.py`:**
- `test_desktop_content_fields` — generated content contains correct `Name`, `Exec`, `Icon`, `Type`, `Categories`, `Terminal` values.
- `test_create_shortcut_desktop_only` — with `desktop=True, app_menu=False`, file appears at `~/Desktop/` path (using `tmp_path` to override target dirs).
- `test_create_shortcut_app_menu_only` — with `desktop=False, app_menu=True`, file appears at `.local/share/applications/` path.
- `test_create_shortcut_both` — both files written when both flags `True`.
- `test_create_shortcut_write_failure` — returns `(False, non-empty string)` when target path is not writable.

## File Structure

```
proton-launcher/
├── shortcut.py          ← new: create_shortcut function
├── launcher.py          ← extended: ⋮ menu button, _on_create_shortcut dialog
└── tests/
    └── test_shortcut.py ← new: 5 tests
```

## Out of Scope

- Per-game desktop shortcuts.
- Custom icon (bundled image file).
- Checking whether a shortcut already exists before overwriting.
- Windows or macOS shortcut formats.
