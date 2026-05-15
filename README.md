# Proton Game Launcher

A self-contained launcher for running Windows games on Linux via standalone [Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom). Dark-themed poster grid with automatic cover art — no Steam required.

## Requirements

- Python 3.8+
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

## Folder Structure

```
proton-launcher/
├── run.sh              ← entry point
├── test.sh             ← run tests
├── launcher.py         ← main window
├── scanner.py          ← game discovery
├── cover.py            ← cover art fetcher
├── card.py             ← game card widget
├── runner.py           ← Proton launch helper
├── .venv/              ← Python environment (auto-created)
├── proton/             ← Proton-GE (auto-downloaded)
├── .cache/covers/      ← cached cover images
└── .compat/            ← per-game compatibility prefixes
```

## Running Tests

```bash
bash test.sh
```
