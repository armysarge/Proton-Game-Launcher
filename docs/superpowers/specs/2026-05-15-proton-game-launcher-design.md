# Proton Game Launcher — Design Spec

**Date:** 2026-05-15
**Status:** Approved

---

## Overview

A self-contained graphical game launcher for running Windows games via standalone Proton-GE on Linux. The launcher lives entirely inside `~/winegames/` — no system-wide installation required. Game folders are copied directly from Windows into subfolders of `winegames/`, and the launcher discovers and presents them automatically.

---

## Folder Structure

```
winegames/
├── run.sh                   ← entry point, double-click to launch
├── launcher.py              ← PyQt5 application
├── proton/                  ← Proton-GE (auto-downloaded on first run)
├── .venv/                   ← Python virtualenv (auto-created on first run)
├── .compat/                 ← per-game compatibility prefixes
│   ├── Game Name/
│   └── ...
├── .cache/
│   └── covers/              ← poster images cached by game name
├── .launcher.json           ← optional per-game exe overrides
└── docs/
    └── superpowers/specs/
        └── this file
```

Game folders sit directly under `winegames/`:
```
winegames/
├── Halo CE/
├── Diablo II/
└── Warcraft III/
```

---

## Components

### `run.sh` — Entry Point

Executed on double-click (or from terminal). Performs first-run setup if needed, then launches the app.

Setup sequence:
1. If `.venv/` does not exist: create it with `python3 -m venv .venv` and install `PyQt5 requests` (~60s first run)
2. If `proton/` does not exist: fetch the latest Proton-GE release from the GitHub releases API (`https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest`), download the `.tar.gz`, extract it to `proton/`
3. Activate `.venv` and run `launcher.py`

All paths are relative to the script's own directory so the folder is relocatable.

### `launcher.py` — PyQt5 Application

**Main window:** `QMainWindow` with a dark theme (`#0d0d0d` background).

**Toolbar:**
- App title: "🎮 Proton Game Launcher"
- Search input: filters game cards in real time by name
- Refresh button: rescans game folders

**Game grid:** `QScrollArea` containing a `QGridLayout` of game cards. Columns adapt to window width (default 5 columns).

**Game card:** `QWidget` per game showing:
- Poster image (150×200px, scaled with aspect ratio preserved)
- Game name (truncated with ellipsis if too long)
- Hover state: blue border highlight + "▶ Play" label becomes visible
- Click anywhere on card to launch

**Status bar:** Shows game count and active Proton-GE version (read from `proton/version` file).

### Game Scanner

Walks direct subdirectories of `winegames/` (non-recursive at the top level). Each subdirectory that contains at least one `.exe` file is treated as a game.

**Exe detection** — selects the main executable by:
1. Filtering out files whose names match (case-insensitive): `unins*`, `setup*`, `install*`, `*redist*`, `UnityCrashHandler*`, `dxsetup*`, `vcredist*`, `dotnetfx*`, `*crash*`
2. Among remaining candidates, selecting the largest by file size
3. If `.launcher.json` has an override for this game, use that path instead

### Cover Art Fetcher

Uses the Steam Store search API (no API key required):
1. `GET https://store.steampowered.com/api/storesearch/?term={game_name}&cc=us&l=en`
2. Take the first result's `id` (appid)
3. Fetch portrait art: `https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_600x900_2x.jpg`
4. Cache to `.cache/covers/{game_name}.jpg`

On subsequent launches, cached images are used directly — no network call.

**Fallback:** If no cover is found (search returns no results, or image fetch fails), display a styled placeholder: dark gradient background with the game's initials in large text, centred.

Fetching happens in a background `QThread` so the UI stays responsive on startup.

### Launch Handler

```bash
STEAM_COMPAT_DATA_PATH="{winegames}/.compat/{game_name}" \
STEAM_COMPAT_CLIENT_INSTALL_PATH="" \
"{winegames}/proton/proton" run "{game_exe_path}"
```

- `STEAM_COMPAT_DATA_PATH` is created automatically by Proton on first launch for that game
- Process is launched detached (`QProcess::startDetached`) — the launcher stays open

---

## Data

### `.launcher.json`

Optional overrides stored as a flat JSON object keyed by game folder name:

```json
{
  "Diablo II": {
    "exe": "Diablo II/Game.exe"
  }
}
```

The `exe` path is relative to the `winegames/` root. Only the `exe` key is supported initially. Written by future "right-click → set exe" functionality (out of scope for v1 — file is read-only in v1).

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `python3` not found | `run.sh` prints a message and exits with code 1 |
| GitHub API unreachable during Proton download | `run.sh` prints error, suggests manual install |
| Game folder has no `.exe` | Card shown with placeholder art, click shows "No executable found" dialog |
| Cover art fetch fails | Placeholder art shown silently |
| Proton launch fails | Error dialog shows exit code and last stderr line |

---

## Out of Scope (v1)

- Right-click context menu (set custom exe, rename game, remove game)
- Multiple Proton versions selectable per game
- Controller/gamepad navigation
- Game metadata beyond cover art (description, genre, etc.)
- Windows or macOS support

---

## Dependencies

| Dependency | Source | Notes |
|---|---|---|
| Python 3.6+ | System | Required pre-installed |
| PyQt5 | pip (into `.venv`) | UI toolkit |
| requests | pip (into `.venv`) | HTTP for cover art + Proton download |
| Proton-GE | GitHub releases | Auto-downloaded to `proton/` |
