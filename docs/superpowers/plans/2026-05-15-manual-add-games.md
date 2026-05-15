# Manual Add Games Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "+ Add Game" button to the launcher toolbar that lets users browse to a game folder anywhere on the filesystem, set a name and exe, and persist the entry — plus a per-card remove button for manually-added games.

**Architecture:** Manually-added games are stored in `games.json` at the launcher root. Two new functions in `scanner.py` handle I/O. A new `dialog.py` provides the Add Game dialog. `card.py` gains an `is_manual` flag that renders a badge and × remove button. `launcher.py` merges auto-detected and manual games, wires the dialog, and handles removal.

**Tech Stack:** Python 3.8+, PyQt5, pytest, pathlib, json

---

## File Map

| File | Change |
|------|--------|
| `scanner.py` | Add `load_manual_games`, `save_manual_games` |
| `dialog.py` | Create: `AddGameDialog(QDialog)` |
| `card.py` | Add `is_manual` param, `remove_requested` signal, badge + × button rendering |
| `launcher.py` | Add `_manual_games` state, merge load, Add Game button, `_on_add_game`, `_on_remove_game` |
| `tests/test_scanner.py` | Add 4 tests for new scanner functions |

---

### Task 1: scanner.py — load and save manual games

**Files:**
- Modify: `scanner.py`
- Test: `tests/test_scanner.py`

- [ ] **Step 1: Write the failing tests**

First, add these two imports to the top of `tests/test_scanner.py`, on the line after the existing imports:

```python
from pathlib import Path
from scanner import load_manual_games, save_manual_games
```

Then add these four test functions at the bottom of `tests/test_scanner.py`:

```python
def test_load_manual_games_valid(tmp_path):
    (tmp_path / 'games.json').write_text(json.dumps([
        {'name': 'Halo CE', 'path': '/games/Halo CE', 'exe': '/games/Halo CE/halo.exe'}
    ]))
    result = load_manual_games(tmp_path)
    assert len(result) == 1
    assert result[0]['name'] == 'Halo CE'
    assert result[0]['path'] == Path('/games/Halo CE')
    assert result[0]['exe'] == Path('/games/Halo CE/halo.exe')


def test_load_manual_games_missing_file(tmp_path):
    assert load_manual_games(tmp_path) == []


def test_load_manual_games_malformed_json(tmp_path):
    (tmp_path / 'games.json').write_text('not valid json')
    assert load_manual_games(tmp_path) == []


def test_save_load_roundtrip(tmp_path):
    games = [{'name': 'Diablo II', 'path': Path('/games/D2'), 'exe': Path('/games/D2/Diablo II.exe')}]
    save_manual_games(tmp_path, games)
    result = load_manual_games(tmp_path)
    assert result[0]['name'] == 'Diablo II'
    assert result[0]['path'] == Path('/games/D2')
    assert result[0]['exe'] == Path('/games/D2/Diablo II.exe')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_scanner.py::test_load_manual_games_valid tests/test_scanner.py::test_load_manual_games_missing_file tests/test_scanner.py::test_load_manual_games_malformed_json tests/test_scanner.py::test_save_load_roundtrip -v
```

Expected: 4 failures — `ImportError: cannot import name 'load_manual_games'`

- [ ] **Step 3: Implement the two functions in scanner.py**

Add these two functions at the bottom of `scanner.py` (after `_load_config`):

```python
def load_manual_games(base_dir: Path) -> list[dict]:
    games_file = base_dir / 'games.json'
    if not games_file.exists():
        return []
    try:
        entries = json.loads(games_file.read_text())
        return [
            {
                'name': e['name'],
                'path': Path(e['path']),
                'exe': Path(e['exe']),
            }
            for e in entries
        ]
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return []


def save_manual_games(base_dir: Path, games: list[dict]) -> None:
    games_file = base_dir / 'games.json'
    entries = [
        {'name': g['name'], 'path': str(g['path']), 'exe': str(g['exe'])}
        for g in games
    ]
    games_file.write_text(json.dumps(entries, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_scanner.py -v
```

Expected: all 16 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/shaun/proton-launcher && git add scanner.py tests/test_scanner.py && git commit -m "feat: add load_manual_games and save_manual_games to scanner"
```

---

### Task 2: card.py — is_manual flag, remove button, badge

**Files:**
- Modify: `card.py`

- [ ] **Step 1: Update imports and add REMOVE_BTN constant**

Replace the imports block at the top of `card.py`:

```python
from typing import Optional

from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget

CARD_W = 150
CARD_H = 230
LABEL_H = 40
REMOVE_BTN = QRect(CARD_W - 26, 6, 20, 20)
```

- [ ] **Step 2: Update the GameCard class definition**

Replace the entire `GameCard` class with:

```python
class GameCard(QWidget):
    clicked = pyqtSignal(dict)
    remove_requested = pyqtSignal(str)

    def __init__(self, game: dict, is_manual: bool = False, parent=None):
        super().__init__(parent)
        self._game = game
        self._is_manual = is_manual
        self._pixmap: Optional[QPixmap] = None
        self._hovered = False
        self._remove_hovered = False
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.PointingHandCursor)
        if is_manual:
            self.setMouseTracking(True)

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

        # remove button — manual cards, hover only
        if self._is_manual and self._hovered:
            p.setBrush(QColor('#c0392b' if self._remove_hovered else '#8b2020'))
            p.setPen(Qt.NoPen)
            p.drawEllipse(REMOVE_BTN)
            p.setPen(QColor('#ffffff'))
            p.setFont(QFont('sans-serif', 11, QFont.Bold))
            p.drawText(REMOVE_BTN, Qt.AlignCenter, '×')

        # label bar
        p.fillRect(0, img_h, CARD_W, LABEL_H, QColor('#1a1a1a'))

        # manual badge
        if self._is_manual:
            bw, bh = 42, 14
            bx = CARD_W - bw - 4
            by = img_h + (LABEL_H - bh) // 2
            p.setBrush(QColor('#1a3a1a'))
            p.setPen(QColor('#2a6a2a'))
            p.drawRoundedRect(bx, by, bw, bh, 3, 3)
            p.setPen(QColor('#5a9a5a'))
            p.setFont(QFont('sans-serif', 7))
            p.drawText(bx, by, bw, bh, Qt.AlignCenter, 'manual')

        # game name
        name_w = CARD_W - 10 - (50 if self._is_manual else 0)
        p.setPen(QColor('#5b9bd5' if self._hovered else '#e2e2e2'))
        p.setFont(QFont('sans-serif', 8, QFont.Bold))
        fm = p.fontMetrics()
        elided = fm.elidedText(self._game.get('name', ''), Qt.ElideRight, name_w)
        p.drawText(5, img_h, name_w, LABEL_H, Qt.AlignLeft | Qt.AlignVCenter, elided)

        # hover border
        if self._hovered:
            p.setBrush(Qt.NoBrush)
            p.setPen(QColor('#5b9bd5'))
            p.drawRect(1, 1, CARD_W - 2, CARD_H - 2)

        p.end()

    def _paint_placeholder(self, p: QPainter, img_h: int):
        p.fillRect(0, 0, CARD_W, img_h, QColor('#1a2a3a'))
        initials = ''.join(w[0].upper() for w in self._game.get('name', '').split()[:2])
        p.setPen(QColor('#5b9bd5'))
        p.setFont(QFont('sans-serif', 28, QFont.Bold))
        p.drawText(0, 0, CARD_W, img_h, Qt.AlignCenter, initials)

    def enterEvent(self, _event):
        self._hovered = True
        self.update()

    def leaveEvent(self, _event):
        self._hovered = False
        self._remove_hovered = False
        self.update()

    def mouseMoveEvent(self, event):
        if self._is_manual and self._hovered:
            hovered = REMOVE_BTN.contains(event.pos())
            if hovered != self._remove_hovered:
                self._remove_hovered = hovered
                self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._is_manual and REMOVE_BTN.contains(event.pos()):
                self.remove_requested.emit(self._game.get('name', ''))
            else:
                self.clicked.emit(self._game)
```

- [ ] **Step 3: Run the existing test suite to confirm no regressions**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 16 tests PASS (card.py has no unit tests — visual changes are manual verification only)

- [ ] **Step 4: Commit**

```bash
cd /home/shaun/proton-launcher && git add card.py && git commit -m "feat: add is_manual flag, remove button, and badge to GameCard"
```

---

### Task 3: dialog.py — AddGameDialog

**Files:**
- Create: `dialog.py`

- [ ] **Step 1: Create dialog.py**

Create `/home/shaun/proton-launcher/dialog.py` with this content:

```python
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout,
)

from scanner import detect_exe

_FIELD = 'background: #222; border: 1px solid #333; color: #ccc; border-radius: 4px; padding: 4px 8px;'
_BTN   = 'background: #2a2a2a; color: #888; border: 1px solid #333; border-radius: 4px; padding: 4px 10px;'
_LABEL = 'color: #888; font-size: 11px;'


class AddGameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Game')
        self.setMinimumWidth(440)
        self.setStyleSheet('background: #1a1a1a; color: #e2e2e2;')
        self._result: Optional[dict] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Folder
        folder_lbl = QLabel('Game Folder')
        folder_lbl.setStyleSheet(_LABEL)
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText('/home/you/Games/My Game')
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setStyleSheet(_FIELD)
        folder_browse = QPushButton('Browse…')
        folder_browse.setStyleSheet(_BTN)
        folder_browse.clicked.connect(self._browse_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self._folder_edit)
        folder_row.addWidget(folder_browse)

        # Name
        name_lbl = QLabel('Game Name')
        name_lbl.setStyleSheet(_LABEL)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText('My Game')
        self._name_edit.setStyleSheet(_FIELD)
        self._name_edit.textChanged.connect(self._validate)

        # Exe
        exe_lbl = QLabel('Executable')
        exe_lbl.setStyleSheet(_LABEL)
        self._exe_edit = QLineEdit()
        self._exe_edit.setPlaceholderText('(auto-detected after choosing folder)')
        self._exe_edit.setReadOnly(True)
        self._exe_edit.setStyleSheet(_FIELD)
        exe_browse = QPushButton('Browse…')
        exe_browse.setStyleSheet(_BTN)
        exe_browse.clicked.connect(self._browse_exe)
        exe_row = QHBoxLayout()
        exe_row.addWidget(self._exe_edit)
        exe_row.addWidget(exe_browse)

        # Error
        self._error_lbl = QLabel('')
        self._error_lbl.setStyleSheet('color: #c0392b; font-size: 11px;')

        # Buttons
        self._add_btn = QPushButton('Add Game')
        self._add_btn.setEnabled(False)
        self._add_btn.setStyleSheet(
            'background: #2a4a2a; color: #7ec87e; border: 1px solid #3a6a3a;'
            ' border-radius: 4px; padding: 6px 14px;'
        )
        self._add_btn.clicked.connect(self._on_accept)
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setStyleSheet(
            'background: #222; color: #888; border: 1px solid #333;'
            ' border-radius: 4px; padding: 6px 14px;'
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._add_btn)

        layout.addWidget(folder_lbl)
        layout.addLayout(folder_row)
        layout.addWidget(name_lbl)
        layout.addWidget(self._name_edit)
        layout.addWidget(exe_lbl)
        layout.addLayout(exe_row)
        layout.addWidget(self._error_lbl)
        layout.addLayout(btn_row)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 'Select Game Folder', str(Path.home())
        )
        if not folder:
            return
        self._folder_edit.setText(folder)
        self._name_edit.setText(Path(folder).name)
        exe = detect_exe(Path(folder))
        self._exe_edit.setText(str(exe) if exe else '')
        self._validate()

    def _browse_exe(self):
        start = self._folder_edit.text() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Executable', start, 'Executables (*.exe)'
        )
        if path:
            self._exe_edit.setText(path)
            self._validate()

    def _validate(self):
        folder = self._folder_edit.text().strip()
        name = self._name_edit.text().strip()
        exe = self._exe_edit.text().strip()

        if not folder:
            self._error_lbl.setText('')
            self._add_btn.setEnabled(False)
            return
        if not Path(folder).is_dir():
            self._error_lbl.setText('Folder does not exist.')
            self._add_btn.setEnabled(False)
            return
        if not name:
            self._error_lbl.setText('Game name is required.')
            self._add_btn.setEnabled(False)
            return
        if not exe or not Path(exe).is_file():
            self._error_lbl.setText('Select a valid executable.')
            self._add_btn.setEnabled(False)
            return
        self._error_lbl.setText('')
        self._add_btn.setEnabled(True)

    def _on_accept(self):
        self._result = {
            'name': self._name_edit.text().strip(),
            'path': Path(self._folder_edit.text().strip()),
            'exe': Path(self._exe_edit.text().strip()),
        }
        self.accept()

    def game(self) -> Optional[dict]:
        return self._result
```

- [ ] **Step 2: Run the test suite to confirm no regressions**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 16 tests PASS

- [ ] **Step 3: Commit**

```bash
cd /home/shaun/proton-launcher && git add dialog.py && git commit -m "feat: add AddGameDialog for manually adding games"
```

---

### Task 4: launcher.py — wire everything together

**Files:**
- Modify: `launcher.py`

- [ ] **Step 1: Update imports at the top of launcher.py**

Replace:
```python
from scanner import find_games
```
With:
```python
from dialog import AddGameDialog
from scanner import find_games, load_manual_games, save_manual_games
```

- [ ] **Step 2: Add _manual_games to __init__**

In `MainWindow.__init__`, add `self._manual_games` after `self._cover_cache`:

```python
self._games: List[dict] = []
self._cards: Dict[str, GameCard] = {}
self._cover_cache: Dict[str, QPixmap] = {}
self._manual_games: List[dict] = []
self._fetcher: Optional[CoverFetcher] = None
```

- [ ] **Step 3: Add "+ Add Game" button to _make_toolbar**

In `_make_toolbar`, add an `add_game` button after `refresh` is defined and connect it. Replace the end of `_make_toolbar` (the `lay.addWidget` lines and return) with:

```python
        add_game = QPushButton('+ Add Game')
        add_game.setStyleSheet(
            'background: #1a3a1a; color: #7ec87e; border: 1px solid #2a5a2a;'
            ' border-radius: 4px; padding: 4px 10px;'
        )
        add_game.clicked.connect(self._on_add_game)

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._search)
        lay.addWidget(refresh)
        lay.addWidget(add_game)
        return bar
```

- [ ] **Step 4: Update _load_games to merge auto-detected and manual games**

Replace the entire `_load_games` method:

```python
    def _load_games(self):
        if self._fetcher and self._fetcher.isRunning():
            self._fetcher.terminate()
            self._fetcher.wait()

        auto = find_games(BASE_DIR)
        self._manual_games = load_manual_games(BASE_DIR)

        auto_names = {g['name'] for g in auto}
        manual_tagged = [
            {**g, 'manual': True}
            for g in self._manual_games
            if g['name'] not in auto_names
        ]
        self._games = auto + manual_tagged
        self._populate_grid()
        self._update_status()
        self._fetch_covers()
```

- [ ] **Step 5: Update _populate_grid to pass is_manual and connect remove signal**

Replace the `for i, game in enumerate(self._games):` loop inside `_populate_grid`:

```python
        for i, game in enumerate(self._games):
            card = GameCard(game, is_manual=game.get('manual', False))
            card.clicked.connect(self._on_launch)
            card.remove_requested.connect(self._on_remove_game)
            if game['name'] in self._cover_cache:
                card.set_cover(self._cover_cache[game['name']])
            self._cards[game['name']] = card
            self._grid.addWidget(card, i // COLS, i % COLS)
```

- [ ] **Step 6: Add _on_add_game and _on_remove_game methods**

Add both methods after `_on_launch` in `launcher.py`:

```python
    def _on_add_game(self):
        dlg = AddGameDialog(self)
        if dlg.exec_() != AddGameDialog.Accepted:
            return
        g = dlg.game()
        updated = self._manual_games + [
            {'name': g['name'], 'path': g['path'], 'exe': g['exe']}
        ]
        try:
            save_manual_games(BASE_DIR, updated)
        except OSError as e:
            QMessageBox.critical(self, 'Save Failed', f'Could not save games.json:\n{e}')
            return
        self._manual_games = updated
        self._load_games()

    def _on_remove_game(self, name: str):
        reply = QMessageBox.question(
            self, 'Remove Game',
            f"Remove '{name}' from launcher? Files will not be deleted.",
            QMessageBox.Yes | QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return
        updated = [g for g in self._manual_games if g['name'] != name]
        try:
            save_manual_games(BASE_DIR, updated)
        except OSError as e:
            QMessageBox.critical(self, 'Save Failed', f'Could not save games.json:\n{e}')
            return
        self._manual_games = updated
        self._load_games()
```

- [ ] **Step 7: Run the full test suite**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 16 tests PASS

- [ ] **Step 8: Commit**

```bash
cd /home/shaun/proton-launcher && git add launcher.py && git commit -m "feat: wire manual add/remove games into launcher"
```
