# Manual Add Games — Design Spec

**Date:** 2026-05-15
**Project:** Proton Game Launcher

## Overview

Allow users to manually add games to the launcher from anywhere on the filesystem, and remove manually-added games. Auto-detected games (folder scan) are unaffected.

## Data Model

A new `games.json` file at the launcher root persists manually-added games:

```json
[
  {
    "name": "Halo CE",
    "path": "/home/shaun/Games/Halo CE",
    "exe": "/home/shaun/Games/Halo CE/halo.exe"
  }
]
```

- All paths are absolute so the file works regardless of launcher location.
- `name` is the display name (user-editable at add time).
- `exe` is the resolved absolute path to the executable.
- Missing or malformed `games.json` is treated as an empty list (no error).

## Components

### `scanner.py` — two new functions

**`load_manual_games(base_dir: Path) -> list[dict]`**
- Reads `games.json` from `base_dir`.
- Returns list of `{name, path, exe}` dicts (same shape as `find_games()` output).
- Returns `[]` on missing file, JSON decode error, or OS error.
- Each entry's `path` and `exe` are converted to `Path` objects.

**`save_manual_games(base_dir: Path, games: list[dict]) -> None`**
- Writes the list to `games.json`, serialising `Path` objects to strings.
- Raises `OSError` on write failure (caller handles).

### `dialog.py` — new file

**`AddGameDialog(QDialog)`**
- Fields: Folder path (line edit + "Browse…" button), Game name (line edit), Executable (line edit + "Browse…" button).
- On folder selection: auto-fills name from folder's basename; runs `detect_exe()` from `scanner` to auto-fill exe.
- Exe field is editable — user can browse to override.
- Validation on "Add Game": folder must exist; exe must not be empty and must exist.
- Returns `{name: str, path: Path, exe: Path}` via `game()` accessor after `exec_()` returns `Accepted`.

### `card.py` — `is_manual` flag

- Constructor gains `is_manual: bool = False` parameter.
- New signal: `remove_requested = pyqtSignal(str)` (emits game name).
- When `is_manual=True`:
  - A small "manual" badge appears in the label bar.
  - A `×` button appears in the top-right corner on hover.
  - Clicking `×` emits `remove_requested`.
- Auto-detected cards (`is_manual=False`) are visually unchanged.

### `launcher.py` — wiring

**Toolbar:** "+ Add Game" button added to the right of "↺ Refresh". Green-tinted style to distinguish it.

**`_load_games()`:** Loads `find_games(BASE_DIR)` and `load_manual_games(BASE_DIR)` separately. Stores the raw manual list as `self._manual_games` (used for save/remove). Builds `self._games` by merging both, adding `'manual': True` to each manual entry. Deduplicates by name (auto-detected takes precedence if names clash).

**`_populate_grid()`:** Passes `is_manual=game.get('manual', False)` to `GameCard`. Connects `card.remove_requested` to `_on_remove_game`.

**`_on_add_game()`:**
1. Opens `AddGameDialog`.
2. On accept, appends entry to current manual list, calls `save_manual_games`, calls `_load_games`.

**`_on_remove_game(name: str)`:**
1. Shows `QMessageBox.question` confirmation: "Remove '{name}' from launcher? Files will not be deleted."
2. On confirm, removes entry from manual list, calls `save_manual_games`, calls `_load_games`.

## Error Handling

- Write failure on save: show `QMessageBox.critical` with the OS error message.
- Dialog validation: inline error label shown below the invalid field; "Add Game" button stays disabled until valid.
- If a manually-added exe no longer exists at launch time: existing "No Executable" warning already handles this (launcher checks `game['exe']` before calling `runner.launch`).

## Testing

**`test_scanner.py` additions:**
- `load_manual_games` with valid JSON returns correct list.
- `load_manual_games` with missing file returns `[]`.
- `load_manual_games` with malformed JSON returns `[]`.
- `save_manual_games` writes correct JSON; round-trip (save then load) is lossless.

**`dialog.py`:** Not unit-tested directly (Qt dialog). Logic that can be isolated (exe auto-detection, name derivation) is covered by scanner tests.

## File Structure

```
proton-launcher/
├── dialog.py        ← new: AddGameDialog
├── scanner.py       ← extended: load_manual_games, save_manual_games
├── card.py          ← extended: is_manual flag, remove_requested signal
├── launcher.py      ← extended: Add Game button, merge, remove handler
└── games.json       ← new at runtime: persisted manual game list
```

## Out of Scope

- Editing an existing manually-added game (remove and re-add).
- Bulk import.
- Drag-and-drop to add games.
