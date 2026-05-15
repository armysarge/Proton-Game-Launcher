# Game State & Proton Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two-state game card overlays (Starting/Running), a single-game lock preventing a second launch while one is running, and an "Update Proton-GE" option in the ⋮ menu with a modal progress dialog.

**Architecture:** `runner.py` returns the `Popen` object so `launcher.py` can track it via two `QTimer`s — a 5 s single-shot for the Starting→Running transition and a 1 s polling timer for exit detection. Card state is encapsulated in `GameCard.set_state()`. A new `proton_updater.py` owns all GitHub API / download / extract logic as a `QThread`, keeping it testable and Qt-free at the module level.

**Tech Stack:** Python 3.9+, PyQt5, pytest, pathlib, requests, tarfile

---

## File Map

| File | Change |
|------|--------|
| `runner.py` | Modify: `launch()` returns `(Popen \| None, str)` |
| `card.py` | Modify: `_state`, `set_state()`, `_dot_timer`, overlay in `paintEvent`, block clicks |
| `proton_updater.py` | Create: `fetch_latest_release_url()`, `ProtonUpdater(QThread)` |
| `launcher.py` | Modify: game lock timers, updated `_on_launch`, Proton update UI |
| `tests/conftest.py` | Create: session-scoped `qapp` fixture |
| `tests/test_runner.py` | Modify: add 2 tests for `launch()` |
| `tests/test_card_state.py` | Create: 4 tests |
| `tests/test_proton_updater.py` | Create: 3 tests |

---

### Task 1: runner.py — update launch() return type

**Files:**
- Modify: `runner.py`
- Modify: `tests/test_runner.py`

- [ ] **Step 1: Add 2 failing tests to tests/test_runner.py**

Append to the bottom of `tests/test_runner.py`:

```python
import subprocess
from unittest.mock import patch, MagicMock
from runner import launch


def test_launch_returns_popen_on_success(tmp_path):
    mock_proc = MagicMock(spec=subprocess.Popen)
    with patch('runner.subprocess.Popen', return_value=mock_proc):
        proc, err = launch(tmp_path / 'proton', tmp_path / 'game.exe', tmp_path / 'compat')
    assert proc is mock_proc
    assert err == ''


def test_launch_returns_none_on_oserror(tmp_path):
    with patch('runner.subprocess.Popen', side_effect=OSError('exec failed')):
        proc, err = launch(tmp_path / 'proton', tmp_path / 'game.exe', tmp_path / 'compat')
    assert proc is None
    assert err != ''
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_runner.py::test_launch_returns_popen_on_success tests/test_runner.py::test_launch_returns_none_on_oserror -v
```

Expected: both tests FAIL — `launch` currently returns `(bool, str)`, not `(Popen, str)`.

- [ ] **Step 3: Replace runner.py**

Replace the entire contents of `/home/shaun/proton-launcher/runner.py`:

```python
import os
import subprocess
from pathlib import Path
from typing import Optional


def build_launch_args(proton_bin: Path, exe_path: Path) -> list[str]:
    return [str(proton_bin), 'run', str(exe_path)]


def build_env(compat_path: Path) -> dict:
    env = os.environ.copy()
    env['STEAM_COMPAT_DATA_PATH'] = str(compat_path)
    env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = ''
    return env


def launch(
    proton_bin: Path, exe_path: Path, compat_path: Path
) -> tuple[Optional[subprocess.Popen], str]:
    compat_path.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.Popen(
            build_launch_args(proton_bin, exe_path),
            env=build_env(compat_path),
            start_new_session=True,
        )
        return proc, ''
    except OSError as e:
        return None, str(e)
```

- [ ] **Step 4: Run new tests to verify they pass**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_runner.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 34 tests PASS (32 existing + 2 new).

- [ ] **Step 6: Commit**

```bash
cd /home/shaun/proton-launcher && git add runner.py tests/test_runner.py && git commit -m "feat: return Popen from launch() for process tracking"
```

---

### Task 2: card.py — state management and overlays

**Files:**
- Modify: `card.py`
- Create: `tests/conftest.py`
- Create: `tests/test_card_state.py`

- [ ] **Step 1: Create tests/conftest.py**

Create `/home/shaun/proton-launcher/tests/conftest.py`:

```python
import pytest
from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope='session')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
```

- [ ] **Step 2: Create tests/test_card_state.py**

Create `/home/shaun/proton-launcher/tests/test_card_state.py`:

```python
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMouseEvent
from card import GameCard

GAME = {'name': 'Test Game', 'path': '/games/Test', 'exe': '/games/Test/test.exe'}


def _left_click():
    return QMouseEvent(
        QMouseEvent.MouseButtonPress,
        QPoint(75, 100),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )


def test_card_default_state_is_normal(qapp):
    card = GameCard(GAME)
    assert card._state == 'normal'


def test_set_state_starting_blocks_click(qapp):
    card = GameCard(GAME)
    card.set_state('starting')
    received = []
    card.clicked.connect(received.append)
    card.mousePressEvent(_left_click())
    assert received == []


def test_set_state_running_blocks_click(qapp):
    card = GameCard(GAME)
    card.set_state('running')
    received = []
    card.clicked.connect(received.append)
    card.mousePressEvent(_left_click())
    assert received == []


def test_set_state_normal_allows_click(qapp):
    card = GameCard(GAME)
    card.set_state('normal')
    received = []
    card.clicked.connect(received.append)
    card.mousePressEvent(_left_click())
    assert len(received) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_card_state.py -v
```

Expected: all 4 tests FAIL — `GameCard` has no `_state` attribute and no `set_state` method.

- [ ] **Step 4: Replace card.py**

Replace the entire contents of `/home/shaun/proton-launcher/card.py`:

```python
from typing import Optional

from PyQt5.QtCore import Qt, QRect, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QWidget

CARD_W = 150
CARD_H = 230
LABEL_H = 40
REMOVE_BTN = QRect(CARD_W - 26, 6, 20, 20)


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
        self._state: str = 'normal'
        self._dot_count: int = 0
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(400)
        self._dot_timer.timeout.connect(self._tick_dots)
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

    def set_state(self, state: str):
        self._state = state
        if state == 'starting':
            self._dot_count = 0
            self._dot_timer.start()
            self.setCursor(Qt.ForbiddenCursor)
        elif state == 'running':
            self._dot_timer.stop()
            self.setCursor(Qt.ForbiddenCursor)
        else:
            self._dot_timer.stop()
            self.setCursor(Qt.PointingHandCursor)
        self.update()

    def _tick_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
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

        # state overlay
        if self._state in ('starting', 'running'):
            p.fillRect(0, 0, CARD_W, img_h, QColor(0, 0, 0, 160))
            p.setFont(QFont('sans-serif', 9, QFont.Bold))
            if self._state == 'starting':
                p.setPen(QColor('#ffffff'))
                text = 'Starting' + '.' * self._dot_count
            else:
                p.setPen(QColor('#7ec87e'))
                text = '● Running'
            p.drawText(0, 0, CARD_W, img_h, Qt.AlignCenter, text)

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
        if self._is_manual:
            hovered = REMOVE_BTN.contains(event.pos())
            if hovered != self._remove_hovered:
                self._remove_hovered = hovered
                self.update()

    def mousePressEvent(self, event):
        if self._state != 'normal':
            return
        if event.button() == Qt.LeftButton:
            if self._is_manual and REMOVE_BTN.contains(event.pos()):
                self.remove_requested.emit(self._game.get('name', ''))
            else:
                self.clicked.emit(self._game)
```

- [ ] **Step 5: Run new tests to verify they pass**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_card_state.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Run full suite to confirm no regressions**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 38 tests PASS (34 existing + 4 new).

- [ ] **Step 7: Commit**

```bash
cd /home/shaun/proton-launcher && git add card.py tests/conftest.py tests/test_card_state.py && git commit -m "feat: add starting/running state overlays to GameCard"
```

---

### Task 3: proton_updater.py — download and extract module

**Files:**
- Create: `proton_updater.py`
- Create: `tests/test_proton_updater.py`

- [ ] **Step 1: Create tests/test_proton_updater.py**

Create `/home/shaun/proton-launcher/tests/test_proton_updater.py`:

```python
import pytest
import requests
from unittest.mock import patch, MagicMock
from proton_updater import fetch_latest_release_url


FAKE_RESPONSE = {
    'tag_name': 'GE-Proton9-27',
    'assets': [
        {
            'name': 'GE-Proton9-27.tar.gz',
            'browser_download_url': 'https://example.com/GE-Proton9-27.tar.gz',
        },
        {
            'name': 'GE-Proton9-27.sha512sum',
            'browser_download_url': 'https://example.com/GE-Proton9-27.sha512sum',
        },
    ],
}


def test_fetch_latest_release_url_returns_url_and_version():
    mock_resp = MagicMock()
    mock_resp.json.return_value = FAKE_RESPONSE
    with patch('proton_updater.requests.get', return_value=mock_resp):
        url, version = fetch_latest_release_url('https://fake-api')
    assert url == 'https://example.com/GE-Proton9-27.tar.gz'
    assert version == 'GE-Proton9-27'


def test_fetch_latest_release_url_no_tarball_raises():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'tag_name': 'GE-Proton9-27',
        'assets': [
            {
                'name': 'GE-Proton9-27.sha512sum',
                'browser_download_url': 'https://example.com/sha512',
            },
        ],
    }
    with patch('proton_updater.requests.get', return_value=mock_resp):
        with pytest.raises(RuntimeError, match='No .tar.gz'):
            fetch_latest_release_url('https://fake-api')


def test_fetch_latest_release_url_network_error_raises():
    with patch('proton_updater.requests.get', side_effect=requests.RequestException('timeout')):
        with pytest.raises(RuntimeError, match='Network error'):
            fetch_latest_release_url('https://fake-api')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_proton_updater.py -v
```

Expected: 3 failures — `ModuleNotFoundError: No module named 'proton_updater'`.

- [ ] **Step 3: Create proton_updater.py**

Create `/home/shaun/proton-launcher/proton_updater.py`:

```python
import shutil
import tarfile
import tempfile
from pathlib import Path

import requests
from PyQt5.QtCore import QThread, pyqtSignal

GITHUB_API_URL = 'https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest'


def fetch_latest_release_url(api_url: str) -> tuple[str, str]:
    try:
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f'Network error: {e}') from e
    version = data.get('tag_name', '')
    for asset in data.get('assets', []):
        if asset.get('name', '').endswith('.tar.gz'):
            return asset['browser_download_url'], version
    raise RuntimeError('No .tar.gz asset found in latest release')


class ProtonUpdater(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, proton_dir: Path, parent=None):
        super().__init__(parent)
        self._proton_dir = proton_dir

    def run(self):
        tmp_path = None
        try:
            self.progress.emit('Checking for latest release…')
            url, version = fetch_latest_release_url(GITHUB_API_URL)
            tarball_name = url.split('/')[-1]

            self.progress.emit(f'Downloading {tarball_name}…')
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            downloaded_bytes = 0
            last_reported_10mb = 0
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    tmp_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    bucket = downloaded_bytes // (10 * 1024 * 1024)
                    if bucket > last_reported_10mb:
                        last_reported_10mb = bucket
                        self.progress.emit(
                            f'Downloading… {downloaded_bytes / (1024 * 1024):.0f} MB'
                        )

            self.progress.emit('Extracting…')
            if self._proton_dir.exists():
                shutil.rmtree(self._proton_dir)
            self._proton_dir.mkdir(parents=True)
            with tarfile.open(tmp_path) as tf:
                for member in tf.getmembers():
                    parts = Path(member.name).parts
                    if len(parts) <= 1:
                        continue
                    member.name = str(Path(*parts[1:]))
                    tf.extract(member, self._proton_dir)

            self.finished.emit(True, version)

        except (OSError, RuntimeError, requests.RequestException) as e:
            self.finished.emit(False, str(e))
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
```

- [ ] **Step 4: Run new tests to verify they pass**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_proton_updater.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 41 tests PASS (38 existing + 3 new).

- [ ] **Step 6: Commit**

```bash
cd /home/shaun/proton-launcher && git add proton_updater.py tests/test_proton_updater.py && git commit -m "feat: add ProtonUpdater thread and fetch_latest_release_url"
```

---

### Task 4: launcher.py — game lock + Proton update UI

**Files:**
- Modify: `launcher.py`

No new unit tests — this task wires together modules from Tasks 1–3 into the Qt UI. Verify by running the full test suite (no regressions), then run the app to confirm visually.

- [ ] **Step 1: Update PyQt5 QtCore import**

In `launcher.py`, replace:
```python
from PyQt5.QtCore import Qt
```
With:
```python
from PyQt5.QtCore import Qt, QTimer
```

- [ ] **Step 2: Update PyQt5 QtWidgets import**

In `launcher.py`, replace:
```python
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)
```
With:
```python
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)
```

- [ ] **Step 3: Add proton_updater import**

After `from shortcut import create_shortcut`, add:
```python
from proton_updater import ProtonUpdater
```

- [ ] **Step 4: Add game-tracking fields and timers to __init__**

In `__init__`, replace:
```python
        self._fetcher: Optional[CoverFetcher] = None
        self._setup_ui()
```
With:
```python
        self._fetcher: Optional[CoverFetcher] = None
        self._running_game: Optional[str] = None
        self._running_proc = None
        self._start_timer = QTimer(self)
        self._start_timer.setSingleShot(True)
        self._start_timer.setInterval(5000)
        self._start_timer.timeout.connect(self._on_game_running)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_game_proc)
        self._setup_ui()
```

- [ ] **Step 5: Add _update_action to _make_toolbar**

In `_make_toolbar`, replace:
```python
        shortcut_action = self._more_menu.addAction('Create Desktop Shortcut…')
        shortcut_action.triggered.connect(self._on_create_shortcut)
```
With:
```python
        shortcut_action = self._more_menu.addAction('Create Desktop Shortcut…')
        shortcut_action.triggered.connect(self._on_create_shortcut)
        self._update_action = self._more_menu.addAction('Update Proton-GE…')
        self._update_action.triggered.connect(self._on_update_proton)
```

- [ ] **Step 6: Replace _on_launch**

Replace the entire `_on_launch` method:
```python
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
```
With:
```python
    def _on_launch(self, game: dict):
        if self._running_game is not None:
            QMessageBox.information(self, 'Game Running',
                f"'{self._running_game}' is already running.")
            return
        if not game['exe']:
            QMessageBox.warning(self, 'No Executable', f"No executable found in '{game['name']}'.")
            return
        if not PROTON_BIN.exists():
            QMessageBox.critical(
                self, 'Proton Not Found',
                'Proton-GE is not installed.\nRun ./run.sh to download it automatically.',
            )
            return
        proc, err = launch(PROTON_BIN, game['exe'], COMPAT_DIR / game['name'])
        if proc is None:
            QMessageBox.critical(self, 'Launch Failed', f"Could not launch '{game['name']}':\n{err}")
            return
        self._running_game = game['name']
        self._running_proc = proc
        self._update_action.setEnabled(False)
        if game['name'] in self._cards:
            self._cards[game['name']].set_state('starting')
        self._start_timer.start()
        self._poll_timer.start()
```

- [ ] **Step 7: Add _on_game_running and _poll_game_proc**

Add these two methods after `_on_launch`:

```python
    def _on_game_running(self):
        if self._running_game and self._running_game in self._cards:
            self._cards[self._running_game].set_state('running')

    def _poll_game_proc(self):
        if self._running_proc and self._running_proc.poll() is not None:
            self._poll_timer.stop()
            self._start_timer.stop()
            if self._running_game and self._running_game in self._cards:
                self._cards[self._running_game].set_state('normal')
            self._running_game = None
            self._running_proc = None
            self._update_action.setEnabled(True)
```

- [ ] **Step 8: Add _on_update_proton**

Add this method after `_on_create_shortcut`:

```python
    def _on_update_proton(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('Update Proton-GE')
        dlg.setStyleSheet('background: #1a1a1a; color: #e2e2e2;')
        dlg.setMinimumWidth(380)
        dlg.setWindowFlag(Qt.WindowCloseButtonHint, False)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        status_lbl = QLabel('Starting update…')
        status_lbl.setStyleSheet('color: #ccc;')

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        progress_bar.setStyleSheet(
            'QProgressBar { background: #222; border: 1px solid #333;'
            ' border-radius: 4px; height: 12px; }'
            'QProgressBar::chunk { background: #2a5a2a; }'
        )

        layout.addWidget(status_lbl)
        layout.addWidget(progress_bar)

        updater = ProtonUpdater(BASE_DIR / 'proton', parent=dlg)

        def _on_progress(msg: str):
            status_lbl.setText(msg)

        def _on_finished(ok: bool, msg: str):
            dlg.accept()
            if ok:
                self._update_status()
                QMessageBox.information(self, 'Update Complete',
                    f'Proton-GE updated to {msg}.')
            else:
                QMessageBox.critical(self, 'Update Failed',
                    f'Could not update Proton-GE:\n{msg}')

        updater.progress.connect(_on_progress)
        updater.finished.connect(_on_finished)
        updater.start()
        dlg.exec_()
```

- [ ] **Step 9: Run full suite to confirm no regressions**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 41 tests PASS.

- [ ] **Step 10: Commit**

```bash
cd /home/shaun/proton-launcher && git add launcher.py && git commit -m "feat: game lock with Starting/Running states and Update Proton-GE menu action"
```
