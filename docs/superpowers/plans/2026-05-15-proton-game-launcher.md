# Proton Game Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained PyQt5 game launcher that auto-discovers Windows game folders, fetches cover art from Steam, and launches games via a locally-bundled Proton-GE.

**Architecture:** `run.sh` bootstraps a `.venv` and downloads Proton-GE on first run, then launches `launcher.py`. The main window shows a 5-column poster grid; a background `QThread` fetches cover art from the Steam Store API. Each module (`scanner`, `cover`, `runner`, `card`) has one clear responsibility and is independently testable.

**Tech Stack:** Python 3.10+, PyQt5, requests, pytest, Bash

---

## File Map

| File | Responsibility |
|---|---|
| `run.sh` | Entry point: bootstrap `.venv`, download Proton-GE, launch app |
| `launcher.py` | Main window: toolbar, 5-column grid, search filter, status bar |
| `scanner.py` | Discover game dirs with `.exe` files; detect main exe; read `.launcher.json` |
| `cover.py` | Fetch and cache cover art from Steam Store API in a background `QThread` |
| `card.py` | Game card widget: poster, hover highlight, click signal |
| `runner.py` | Build Proton-GE launch args/env and start the game process |
| `tests/test_scanner.py` | Unit tests for scanner logic |
| `tests/test_runner.py` | Unit tests for runner command building |
| `tests/test_cover.py` | Unit tests for cover URL/cache helpers |

---

## Task 1: Project Scaffold

**Files:**
- Create: `run.sh`
- Create: `test.sh`
- Create: `.gitignore`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialise git repo and create .gitignore**

```bash
cd /home/shaun/winegames
git init
```

```
# .gitignore
.venv/
proton/
.compat/
.cache/
.superpowers/
__pycache__/
*.pyc
*.pyo
```

Write to `/home/shaun/winegames/.gitignore`.

- [ ] **Step 2: Create run.sh**

Write to `/home/shaun/winegames/run.sh`:

```bash
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PROTON_DIR="$SCRIPT_DIR/proton"

# --- Python venv setup ---
if [ ! -f "$VENV/bin/python" ]; then
    echo "Setting up Python environment (first run)..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet PyQt5 requests pytest
fi

# --- Proton-GE download ---
if [ ! -d "$PROTON_DIR" ]; then
    echo "Downloading Proton-GE (first run, ~500 MB)..."
    RELEASE_JSON=$(curl -sf https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest)
    if [ -z "$RELEASE_JSON" ]; then
        echo "ERROR: Could not reach GitHub API. Check your internet connection." >&2
        echo "To install manually: download a Proton-GE .tar.gz from" >&2
        echo "https://github.com/GloriousEggroll/proton-ge-custom/releases" >&2
        echo "and extract it to $PROTON_DIR" >&2
        exit 1
    fi
    TARBALL_URL=$(echo "$RELEASE_JSON" | "$VENV/bin/python" -c \
        "import sys,json; d=json.load(sys.stdin); print(next(a['browser_download_url'] for a in d['assets'] if a['name'].endswith('.tar.gz')))")
    TARBALL_NAME=$(basename "$TARBALL_URL")
    echo "  Downloading $TARBALL_NAME..."
    curl -L --progress-bar -o "/tmp/$TARBALL_NAME" "$TARBALL_URL"
    echo "  Extracting..."
    mkdir -p "$PROTON_DIR"
    tar -xzf "/tmp/$TARBALL_NAME" -C "$PROTON_DIR" --strip-components=1
    rm "/tmp/$TARBALL_NAME"
    echo "  Proton-GE ready."
fi

exec "$VENV/bin/python" "$SCRIPT_DIR/launcher.py"
```

- [ ] **Step 3: Create test.sh**

Write to `/home/shaun/winegames/test.sh`:

```bash
#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
if [ ! -f "$VENV/bin/pytest" ]; then
    echo "Run run.sh first to set up the environment." >&2
    exit 1
fi
exec "$VENV/bin/pytest" "$SCRIPT_DIR/tests/" -v "$@"
```

- [ ] **Step 4: Make scripts executable and create tests dir**

```bash
chmod +x /home/shaun/winegames/run.sh /home/shaun/winegames/test.sh
mkdir -p /home/shaun/winegames/tests
touch /home/shaun/winegames/tests/__init__.py
```

- [ ] **Step 5: Bootstrap the venv (skip Proton download)**

```bash
cd /home/shaun/winegames
VENV=.venv
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet PyQt5 requests pytest
```

Expected: no errors, `.venv/bin/python` exists.

- [ ] **Step 6: Commit**

```bash
cd /home/shaun/winegames
git add run.sh test.sh .gitignore tests/__init__.py
git commit -m "feat: project scaffold with run.sh and venv bootstrap"
```

---

## Task 2: Game Scanner

**Files:**
- Create: `scanner.py`
- Create: `tests/test_scanner.py`

- [ ] **Step 1: Write the failing tests**

Write to `/home/shaun/winegames/tests/test_scanner.py`:

```python
import json
import pytest
from pathlib import Path
from scanner import find_games, detect_exe, EXCLUDE_PATTERN


def test_exclude_pattern_blocks_setup_variants():
    assert EXCLUDE_PATTERN.match('setup.exe')
    assert EXCLUDE_PATTERN.match('Setup.exe')
    assert EXCLUDE_PATTERN.match('setup64.exe')
    assert EXCLUDE_PATTERN.match('unins000.exe')
    assert EXCLUDE_PATTERN.match('UnityCrashHandler64.exe')
    assert EXCLUDE_PATTERN.match('vcredist_x64.exe')
    assert EXCLUDE_PATTERN.match('dotnetfx35.exe')
    assert EXCLUDE_PATTERN.match('dxsetup.exe')


def test_exclude_pattern_allows_game_exe():
    assert not EXCLUDE_PATTERN.match('game.exe')
    assert not EXCLUDE_PATTERN.match('Halo.exe')
    assert not EXCLUDE_PATTERN.match('Diablo II.exe')


def test_detect_exe_picks_largest(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'small.exe').write_bytes(b'x' * 100)
    (game / 'large.exe').write_bytes(b'x' * 1000)
    assert detect_exe(game) == game / 'large.exe'


def test_detect_exe_excludes_setup_even_if_larger(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'setup.exe').write_bytes(b'x' * 2000)
    (game / 'game.exe').write_bytes(b'x' * 100)
    assert detect_exe(game) == game / 'game.exe'


def test_detect_exe_returns_none_when_no_exes(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    assert detect_exe(game) is None


def test_detect_exe_returns_none_when_only_excluded(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'setup.exe').write_bytes(b'x' * 100)
    assert detect_exe(game) is None


def test_detect_exe_finds_exe_in_subdirectory(tmp_path):
    game = tmp_path / 'TestGame'
    sub = game / 'bin'
    sub.mkdir(parents=True)
    (sub / 'game.exe').write_bytes(b'x' * 500)
    assert detect_exe(game) == sub / 'game.exe'


def test_detect_exe_respects_launcher_json_override(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'main.exe').write_bytes(b'x' * 1000)
    (game / 'alt.exe').write_bytes(b'x' * 100)
    config = {'TestGame': {'exe': 'TestGame/alt.exe'}}
    (tmp_path / '.launcher.json').write_text(json.dumps(config))
    assert detect_exe(game) == game / 'alt.exe'


def test_find_games_skips_hidden_dirs(tmp_path):
    hidden = tmp_path / '.venv'
    hidden.mkdir()
    (hidden / 'python.exe').write_bytes(b'x' * 100)
    assert find_games(tmp_path) == []


def test_find_games_skips_dirs_without_exe(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'readme.txt').write_text('hello')
    assert find_games(tmp_path) == []


def test_find_games_returns_game_with_exe(tmp_path):
    game = tmp_path / 'Diablo II'
    game.mkdir()
    exe = game / 'Diablo II.exe'
    exe.write_bytes(b'x' * 1000)
    games = find_games(tmp_path)
    assert len(games) == 1
    assert games[0]['name'] == 'Diablo II'
    assert games[0]['path'] == game
    assert games[0]['exe'] == exe


def test_find_games_sorted_alphabetically(tmp_path):
    for name in ['Zork', 'Aardvark', 'Monkey Island']:
        d = tmp_path / name
        d.mkdir()
        (d / 'game.exe').write_bytes(b'x')
    names = [g['name'] for g in find_games(tmp_path)]
    assert names == sorted(names)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/shaun/winegames && bash test.sh tests/test_scanner.py
```

Expected: `ModuleNotFoundError: No module named 'scanner'`

- [ ] **Step 3: Implement scanner.py**

Write to `/home/shaun/winegames/scanner.py`:

```python
import json
import re
from pathlib import Path

EXCLUDE_PATTERN = re.compile(
    r'^(unins.*|setup.*|install.*|.*redist.*|unitycrashandler.*'
    r'|dxsetup.*|vcredist.*|dotnetfx.*|.*crash.*)\.exe$',
    re.IGNORECASE,
)


def find_games(base_dir: Path) -> list[dict]:
    games = []
    for entry in sorted(base_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith('.'):
            continue
        candidates = _find_candidates(entry)
        if not candidates:
            continue
        exe = _pick_exe(base_dir, entry.name, candidates)
        games.append({'name': entry.name, 'path': entry, 'exe': exe})
    return games


def detect_exe(game_dir: Path) -> Path | None:
    candidates = _find_candidates(game_dir)
    if not candidates:
        return None
    return _pick_exe(game_dir.parent, game_dir.name, candidates)


def _find_candidates(game_dir: Path) -> list[Path]:
    return [f for f in game_dir.rglob('*.exe') if not EXCLUDE_PATTERN.match(f.name)]


def _pick_exe(base_dir: Path, game_name: str, candidates: list[Path]) -> Path:
    config = _load_config(base_dir)
    if game_name in config:
        override = base_dir / config[game_name]['exe']
        if override.exists():
            return override
    return max(candidates, key=lambda f: f.stat().st_size)


def _load_config(base_dir: Path) -> dict:
    config_file = base_dir / '.launcher.json'
    if not config_file.exists():
        return {}
    try:
        return json.loads(config_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/shaun/winegames && bash test.sh tests/test_scanner.py
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/shaun/winegames
git add scanner.py tests/test_scanner.py
git commit -m "feat: game scanner with exe detection and config override"
```

---

## Task 3: Proton Runner

**Files:**
- Create: `runner.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write the failing tests**

Write to `/home/shaun/winegames/tests/test_runner.py`:

```python
import os
from pathlib import Path
from runner import build_launch_args, build_env


def test_build_launch_args_structure(tmp_path):
    proton = tmp_path / 'proton' / 'proton'
    exe = tmp_path / 'Game' / 'game.exe'
    assert build_launch_args(proton, exe) == [str(proton), 'run', str(exe)]


def test_build_env_sets_compat_path(tmp_path):
    compat = tmp_path / '.compat' / 'Game'
    env = build_env(compat)
    assert env['STEAM_COMPAT_DATA_PATH'] == str(compat)


def test_build_env_clears_client_install_path(tmp_path):
    compat = tmp_path / '.compat' / 'Game'
    env = build_env(compat)
    assert env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] == ''


def test_build_env_inherits_existing_env(tmp_path):
    compat = tmp_path / '.compat' / 'Game'
    env = build_env(compat)
    assert 'PATH' in env
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/shaun/winegames && bash test.sh tests/test_runner.py
```

Expected: `ModuleNotFoundError: No module named 'runner'`

- [ ] **Step 3: Implement runner.py**

Write to `/home/shaun/winegames/runner.py`:

```python
import os
import subprocess
from pathlib import Path


def build_launch_args(proton_bin: Path, exe_path: Path) -> list[str]:
    return [str(proton_bin), 'run', str(exe_path)]


def build_env(compat_path: Path) -> dict:
    env = os.environ.copy()
    env['STEAM_COMPAT_DATA_PATH'] = str(compat_path)
    env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = ''
    return env


def launch(proton_bin: Path, exe_path: Path, compat_path: Path) -> tuple[bool, str]:
    compat_path.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.Popen(
            build_launch_args(proton_bin, exe_path),
            env=build_env(compat_path),
            start_new_session=True,
        )
        return True, ''
    except OSError as e:
        return False, str(e)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/shaun/winegames && bash test.sh tests/test_runner.py
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/shaun/winegames
git add runner.py tests/test_runner.py
git commit -m "feat: proton runner with env and launch helpers"
```

---

## Task 4: Cover Art Module

**Files:**
- Create: `cover.py`
- Create: `tests/test_cover.py`

- [ ] **Step 1: Write the failing tests**

Write to `/home/shaun/winegames/tests/test_cover.py`:

```python
from pathlib import Path
from cover import cover_cache_path, steam_art_url, steam_search_params


def test_cover_cache_path(tmp_path):
    assert cover_cache_path(tmp_path, 'Diablo II') == tmp_path / 'Diablo II.jpg'


def test_cover_cache_path_preserves_spaces(tmp_path):
    assert cover_cache_path(tmp_path, 'Age of Empires II') == tmp_path / 'Age of Empires II.jpg'


def test_steam_art_url():
    assert steam_art_url(12345) == (
        'https://cdn.akamai.steamstatic.com/steam/apps/12345/library_600x900_2x.jpg'
    )


def test_steam_search_params():
    params = steam_search_params('Halo CE')
    assert params['term'] == 'Halo CE'
    assert params['cc'] == 'us'
    assert params['l'] == 'en'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/shaun/winegames && bash test.sh tests/test_cover.py
```

Expected: `ModuleNotFoundError: No module named 'cover'`

- [ ] **Step 3: Implement cover.py**

Write to `/home/shaun/winegames/cover.py`:

```python
from pathlib import Path

import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

_STEAM_SEARCH = 'https://store.steampowered.com/api/storesearch/'
_STEAM_ART = 'https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_600x900_2x.jpg'


def cover_cache_path(cache_dir: Path, game_name: str) -> Path:
    return cache_dir / f'{game_name}.jpg'


def steam_art_url(appid: int) -> str:
    return _STEAM_ART.format(appid=appid)


def steam_search_params(game_name: str) -> dict:
    return {'term': game_name, 'cc': 'us', 'l': 'en'}


class CoverFetcher(QThread):
    cover_ready = pyqtSignal(str, QPixmap)  # game_name, pixmap

    def __init__(self, games: list[dict], cache_dir: Path):
        super().__init__()
        self._games = games
        self._cache_dir = cache_dir

    def run(self):
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        for game in self._games:
            pixmap = self._load(game['name'])
            if pixmap is not None:
                self.cover_ready.emit(game['name'], pixmap)

    def _load(self, name: str) -> QPixmap | None:
        cached = cover_cache_path(self._cache_dir, name)
        if cached.exists():
            px = QPixmap()
            px.load(str(cached))
            return px if not px.isNull() else None
        return self._fetch(name)

    def _fetch(self, name: str) -> QPixmap | None:
        try:
            resp = requests.get(_STEAM_SEARCH, params=steam_search_params(name), timeout=10)
            resp.raise_for_status()
            items = resp.json().get('items', [])
            if not items:
                return None
            appid = items[0]['id']
            img = requests.get(steam_art_url(appid), timeout=10)
            if img.status_code != 200:
                return None
            cover_cache_path(self._cache_dir, name).write_bytes(img.content)
            px = QPixmap()
            px.loadFromData(img.content)
            return px if not px.isNull() else None
        except Exception:
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/shaun/winegames && bash test.sh tests/test_cover.py
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/shaun/winegames
git add cover.py tests/test_cover.py
git commit -m "feat: cover art fetcher with Steam API and disk cache"
```

---

## Task 5: Game Card Widget

**Files:**
- Create: `card.py`

No unit tests for this task — it is a pure PyQt5 widget with no logic outside painting and event forwarding.

- [ ] **Step 1: Implement card.py**

Write to `/home/shaun/winegames/card.py`:

```python
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget

CARD_W = 150
CARD_H = 230
LABEL_H = 40


class GameCard(QWidget):
    clicked = pyqtSignal(dict)

    def __init__(self, game: dict, parent=None):
        super().__init__(parent)
        self._game = game
        self._pixmap: QPixmap | None = None
        self._hovered = False
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.PointingHandCursor)

    def set_cover(self, pixmap: QPixmap):
        self._pixmap = pixmap.scaled(
            CARD_W, CARD_H - LABEL_H,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        img_h = CARD_H - LABEL_H

        # poster area
        if self._pixmap:
            p.drawPixmap(0, 0, CARD_W, img_h, self._pixmap)
        else:
            self._paint_placeholder(p, img_h)

        # label bar
        p.fillRect(0, img_h, CARD_W, LABEL_H, QColor('#1a1a1a'))
        p.setPen(QColor('#5b9bd5' if self._hovered else '#e2e2e2'))
        p.setFont(QFont('sans-serif', 8, QFont.Bold))
        p.drawText(5, img_h, CARD_W - 10, LABEL_H, Qt.AlignLeft | Qt.AlignVCenter, self._game['name'])

        # hover border
        if self._hovered:
            p.setPen(QColor('#5b9bd5'))
            p.drawRect(0, 0, CARD_W - 1, CARD_H - 1)

    def _paint_placeholder(self, p: QPainter, img_h: int):
        p.fillRect(0, 0, CARD_W, img_h, QColor('#1a2a3a'))
        initials = ''.join(w[0].upper() for w in self._game['name'].split()[:2])
        p.setPen(QColor('#5b9bd5'))
        p.setFont(QFont('sans-serif', 28, QFont.Bold))
        p.drawText(0, 0, CARD_W, img_h, Qt.AlignCenter, initials)

    def enterEvent(self, _event):
        self._hovered = True
        self.update()

    def leaveEvent(self, _event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._game)
```

- [ ] **Step 2: Commit**

```bash
cd /home/shaun/winegames
git add card.py
git commit -m "feat: GameCard widget with poster, placeholder, and hover state"
```

---

## Task 6: Main Window

**Files:**
- Create: `launcher.py`

- [ ] **Step 1: Implement launcher.py**

Write to `/home/shaun/winegames/launcher.py`:

```python
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from card import GameCard
from cover import CoverFetcher
from runner import launch
from scanner import find_games

BASE_DIR = Path(__file__).parent
PROTON_BIN = BASE_DIR / 'proton' / 'proton'
COMPAT_DIR = BASE_DIR / '.compat'
COVER_CACHE = BASE_DIR / '.cache' / 'covers'
COLS = 5


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Proton Game Launcher')
        self.setMinimumSize(860, 580)
        self._games: list[dict] = []
        self._cards: dict[str, GameCard] = {}
        self._cover_cache: dict[str, QPixmap] = {}
        self._fetcher: CoverFetcher | None = None
        self._setup_ui()
        self._load_games()

    # ------------------------------------------------------------------ UI

    def _setup_ui(self):
        toolbar = self._make_toolbar()

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet('background: #0d0d0d;')
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setContentsMargins(16, 16, 16, 16)
        self._grid.setSpacing(12)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll = QScrollArea()
        scroll.setWidget(self._grid_widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('background: #0d0d0d; border: none;')

        self.statusBar().setStyleSheet('background: #111; color: #555; font-size: 10px;')

        central = QWidget()
        central.setStyleSheet('background: #0d0d0d;')
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(toolbar)
        lay.addWidget(scroll)
        self.setCentralWidget(central)

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet('background: #161616; border-bottom: 1px solid #2a2a2a;')
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)

        title = QLabel('🎮 Proton Game Launcher')
        title.setStyleSheet('color: #e2e2e2; font-size: 14px; font-weight: bold; letter-spacing: 1px;')

        self._search = QLineEdit()
        self._search.setPlaceholderText('Search games...')
        self._search.setFixedWidth(200)
        self._search.setStyleSheet(
            'background: #222; border: 1px solid #333; color: #ccc; border-radius: 4px; padding: 4px 10px;'
        )
        self._search.textChanged.connect(self._filter_cards)

        refresh = QPushButton('↺ Refresh')
        refresh.setStyleSheet(
            'background: #2a2a2a; color: #888; border: 1px solid #333; border-radius: 4px; padding: 4px 10px;'
        )
        refresh.clicked.connect(self._load_games)

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._search)
        lay.addWidget(refresh)
        return bar

    # ------------------------------------------------------------------ Data

    def _load_games(self):
        if self._fetcher and self._fetcher.isRunning():
            self._fetcher.terminate()
            self._fetcher.wait()

        self._games = find_games(BASE_DIR)
        self._populate_grid()
        self._update_status()
        self._fetch_covers()

    def _populate_grid(self):
        for i in reversed(range(self._grid.count())):
            w = self._grid.itemAt(i).widget()
            if w:
                w.setParent(None)
        self._cards.clear()

        for i, game in enumerate(self._games):
            card = GameCard(game)
            card.clicked.connect(self._on_launch)
            if game['name'] in self._cover_cache:
                card.set_cover(self._cover_cache[game['name']])
            self._cards[game['name']] = card
            self._grid.addWidget(card, i // COLS, i % COLS)

    def _fetch_covers(self):
        self._fetcher = CoverFetcher(self._games, COVER_CACHE)
        self._fetcher.cover_ready.connect(self._on_cover_ready)
        self._fetcher.start()

    def _on_cover_ready(self, name: str, pixmap: QPixmap):
        self._cover_cache[name] = pixmap
        if name in self._cards:
            self._cards[name].set_cover(pixmap)

    def _filter_cards(self, text: str):
        text = text.lower()
        for name, card in self._cards.items():
            card.setVisible(text in name.lower())

    def _update_status(self):
        version_file = PROTON_BIN.parent / 'version'
        version = version_file.read_text().strip() if version_file.exists() else 'Proton-GE not installed'
        self.statusBar().showMessage(f'  {len(self._games)} games    {version}')

    # ------------------------------------------------------------------ Launch

    def _on_launch(self, game: dict):
        if not game['exe']:
            QMessageBox.warning(self, 'No Executable', f"No executable found in '{game['name']}'.")
            return
        if not PROTON_BIN.exists():
            QMessageBox.critical(
                self, 'Proton Not Found',
                'Proton-GE is not installed.\nRun ./run.sh to download it automatically.',
            )
            return
        ok, err = launch(PROTON_BIN, game['exe'], COMPAT_DIR / game['name'])
        if not ok:
            QMessageBox.critical(self, 'Launch Failed', f"Could not launch '{game['name']}':\n{err}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
```

- [ ] **Step 2: Run all tests to verify nothing is broken**

```bash
cd /home/shaun/winegames && bash test.sh
```

Expected: all tests PASS.

- [ ] **Step 3: Smoke-test the launcher visually**

```bash
cd /home/shaun/winegames
mkdir -p "test_game/BinW64"
dd if=/dev/urandom of="test_game/BinW64/game.exe" bs=1M count=1 2>/dev/null
.venv/bin/python launcher.py
```

Expected: window opens, shows one game card with initials placeholder, no crashes.

```bash
rm -rf test_game
```

- [ ] **Step 4: Commit**

```bash
cd /home/shaun/winegames
git add launcher.py
git commit -m "feat: main window with poster grid, search, and launch handler"
```

---

## Task 7: Full Run Script (Proton-GE Download)

This task verifies the complete `run.sh` end-to-end including Proton-GE download, which requires internet access and ~500 MB of disk space.

**Files:**
- Modify: `run.sh` (already written in Task 1 — verify it works end-to-end)

- [ ] **Step 1: Check available disk space**

```bash
df -h /home/shaun/winegames
```

Expected: at least 1 GB free.

- [ ] **Step 2: Run the full script**

```bash
cd /home/shaun/winegames && bash run.sh
```

Expected:
- Prints "Downloading Proton-GE (first run, ~500 MB)..."
- Downloads and extracts to `proton/`
- Launcher window opens
- Status bar shows the Proton-GE version (e.g. `GE-Proton9-20`)

- [ ] **Step 3: Verify proton binary is present**

```bash
ls /home/shaun/winegames/proton/proton
cat /home/shaun/winegames/proton/version
```

Expected: binary exists, version file contains a version string.

- [ ] **Step 4: Second run should skip all setup**

```bash
cd /home/shaun/winegames && bash run.sh
```

Expected: launcher opens immediately with no "first run" messages.

- [ ] **Step 5: Commit final state**

```bash
cd /home/shaun/winegames
git add -A
git status
git commit -m "feat: complete proton game launcher"
```

---

## Full Test Suite

Run this before calling the project done:

```bash
cd /home/shaun/winegames && bash test.sh -v
```

Expected output:
```
tests/test_cover.py::test_cover_cache_path PASSED
tests/test_cover.py::test_cover_cache_path_preserves_spaces PASSED
tests/test_cover.py::test_steam_art_url PASSED
tests/test_cover.py::test_steam_search_params PASSED
tests/test_runner.py::test_build_launch_args_structure PASSED
tests/test_runner.py::test_build_env_sets_compat_path PASSED
tests/test_runner.py::test_build_env_clears_client_install_path PASSED
tests/test_runner.py::test_build_env_inherits_existing_env PASSED
tests/test_scanner.py::test_exclude_pattern_blocks_setup_variants PASSED
tests/test_scanner.py::test_exclude_pattern_allows_game_exe PASSED
tests/test_scanner.py::test_detect_exe_picks_largest PASSED
tests/test_scanner.py::test_detect_exe_excludes_setup_even_if_larger PASSED
tests/test_scanner.py::test_detect_exe_returns_none_when_no_exes PASSED
tests/test_scanner.py::test_detect_exe_returns_none_when_only_excluded PASSED
tests/test_scanner.py::test_detect_exe_finds_exe_in_subdirectory PASSED
tests/test_scanner.py::test_detect_exe_respects_launcher_json_override PASSED
tests/test_scanner.py::test_find_games_skips_hidden_dirs PASSED
tests/test_scanner.py::test_find_games_skips_dirs_without_exe PASSED
tests/test_scanner.py::test_find_games_returns_game_with_exe PASSED
tests/test_scanner.py::test_find_games_sorted_alphabetically PASSED
```
