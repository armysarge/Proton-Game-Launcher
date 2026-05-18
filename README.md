# Proton Game Launcher

A self-contained launcher for running Windows games on Linux via standalone [Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom). Dark-themed poster grid with automatic cover art — no Steam required.

## Requirements

- Python 3.9+
- Internet connection (first run only, to download Proton-GE and cover art)

## Getting Started

```bash
bash run.sh
```

First run will:
1. Create a local Python environment (`.venv/`) and install dependencies
2. Download the latest Proton-GE release into `proton/`
3. Open the launcher

Every subsequent run opens the launcher immediately.

## Adding Games

### Auto-detected

Drop any Windows game folder directly into the launcher directory:

```
proton-launcher/
├── Diablo II/
│   └── Diablo II.exe
├── Halo CE/
│   └── halo.exe
└── Warcraft III/
    └── Warcraft III.exe
```

The launcher scans for folders containing `.exe` files on startup. Hit **↺ Refresh** to pick up newly added games without restarting.

### Manually added

Click **+ Add Game** in the toolbar to add a game from anywhere on your filesystem — no need to move files into the launcher directory.

1. Click **Browse…** next to Game Folder and select the game's folder
2. The name and executable are auto-detected — edit either if needed
3. Click **Add Game**

Manually-added games show a small **manual** badge in their card. Hover the card and click **×** to remove it from the launcher (files are not deleted). Entries are saved to `games.json` in the launcher root.

## Launching Games

Click any game card to launch it via Proton-GE. While a game is running:

- The card shows a **Starting…** overlay (animated dots) for the first 5 seconds, then switches to a **● Running** overlay
- Clicking any other card is blocked — only one game can run at a time
- The **Update Proton-GE** menu option is disabled until the game exits

When the game process exits, the card returns to its normal state automatically.

## Cover Art

Cover images are fetched automatically from the Steam store using the game folder name. They are cached in `.cache/covers/` — no API key needed.

If no cover is found, the launcher shows a styled placeholder with the game's initials.

## Per-Game Settings

To override which executable is launched for a game, create `.launcher.json` in the launcher root:

```json
{
  "Diablo II": {
    "exe": "Diablo II/Game.exe"
  }
}
```

Paths are relative to the launcher root.

## Updating Proton-GE

Click **⋮ → Update Proton-GE…** to download and install the latest Proton-GE release. A progress dialog shows download and extraction status. The existing `proton/` directory is replaced in-place.

## Desktop Shortcut

Click **⋮ → Create Desktop Shortcut…** to add a launcher shortcut to your Desktop (`~/Desktop/`) and/or app menu (`~/.local/share/applications/`).

## Folder Structure

```
proton-launcher/
├── run.sh              ← entry point
├── test.sh             ← run tests
├── launcher.py         ← main window
├── scanner.py          ← game discovery
├── cover.py            ← cover art fetcher
├── card.py             ← game card widget
├── dialog.py           ← Add Game dialog
├── runner.py           ← Proton launch helper
├── proton_updater.py   ← Proton-GE download/update thread
├── shortcut.py         ← desktop shortcut creator
├── requirements.txt    ← Python dependencies
├── games.json          ← manually-added games (auto-created, gitignored)
├── .venv/              ← Python environment (auto-created)
├── proton/             ← Proton-GE (auto-downloaded)
├── .cache/covers/      ← cached cover images
└── .compat/            ← per-game compatibility prefixes
```

## Running Tests

```bash
bash test.sh
```
