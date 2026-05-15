# Game State & Proton Update — Design Spec

**Date:** 2026-05-15
**Project:** Proton Game Launcher

## Overview

Three interrelated features:
1. **Update Proton-GE** — ⋮ menu action downloads and installs the latest Proton-GE release via a modal progress dialog.
2. **Game lock** — while a game is launching or running, all other cards are non-interactive.
3. **Card loading states** — the active game card shows a visual overlay indicating `Starting…` or `● Running`.

---

## Architecture

| File | Change |
|------|--------|
| `proton_updater.py` | Create: `fetch_latest_release_url()`, `ProtonUpdater(QThread)` |
| `runner.py` | Modify: `launch()` returns `(Popen \| None, str)` |
| `card.py` | Modify: `set_state()`, `_state`, `_dot_count`, `_dot_timer`, updated `paintEvent` and `mousePressEvent` |
| `launcher.py` | Modify: `_running_game`, `_running_proc`, `_start_timer`, `_poll_timer`, `_on_update_proton`, updated `_on_launch` |
| `tests/test_proton_updater.py` | Create: 3 tests |
| `tests/test_runner.py` | Create: 2 tests |
| `tests/test_card_state.py` | Create: 4 tests + `conftest.py` QApplication fixture |

---

## Components

### `proton_updater.py` — new file

**`fetch_latest_release_url(api_url: str) -> tuple[str, str]`**

Standalone function. Takes the GitHub releases API URL as a parameter (injectable for testing). Returns `(download_url, version_string)` where `download_url` is the `.tar.gz` asset URL and `version_string` is the release tag name.

Raises `RuntimeError` if:
- Network request fails (`requests.RequestException`)
- No `.tar.gz` asset found in the release

**`ProtonUpdater(QThread)`**

Constructor: `ProtonUpdater(proton_dir: Path)`

Signals:
- `progress = pyqtSignal(str)` — status message string
- `finished = pyqtSignal(bool, str)` — `(success, version_or_error)`

`run()` sequence:
1. Emit `progress("Checking for latest release…")`
2. Call `fetch_latest_release_url(GITHUB_API_URL)` — on `RuntimeError`, emit `finished(False, str(e))` and return
3. Emit `progress(f"Downloading {tarball_name}…")`
4. Stream-download tarball with `requests.get(url, stream=True)`, chunk size 1 MB; emit `progress(f"Downloading… {mb:.0f} MB")` every 10 MB
5. Save tarball to a temp file (`tempfile.NamedTemporaryFile`)
6. Emit `progress("Extracting…")`
7. `shutil.rmtree(proton_dir)` then `proton_dir.mkdir()`; extract tarball with `tarfile.open`, stripping the top-level directory component from each member path (`Path(member.name).parts[1:]`)
8. Emit `finished(True, version)`
9. On any `OSError` or `RuntimeError` during steps 4–7: emit `finished(False, str(e))`

Module-level constant:
```python
GITHUB_API_URL = 'https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest'
```

---

### `runner.py` — modified

`launch()` return type changes from `tuple[bool, str]` to `tuple[Optional[subprocess.Popen], str]`.

- On success: returns `(process, '')`
- On `OSError`: returns `(None, str(e))`

---

### `card.py` — modified

**New fields:**
- `_state: str = 'normal'` — one of `'normal'`, `'starting'`, `'running'`
- `_dot_count: int = 0` — cycles 0–3 for dot animation
- `_dot_timer: QTimer` — 400 ms interval, connected to `_tick_dots`; only running when state is `'starting'`

**New methods:**
- `set_state(state: str)` — sets `_state`, updates cursor (`Qt.ForbiddenCursor` for non-normal, `Qt.PointingHandCursor` for normal), starts/stops `_dot_timer`, calls `update()`
- `_tick_dots()` — increments `_dot_count % 4`, calls `update()`

**`paintEvent` additions** (drawn after poster, before label bar):

For `'starting'` and `'running'`, draw a semi-transparent dark overlay over the poster area:
```
fillRect(0, 0, CARD_W, img_h, QColor(0, 0, 0, 160))
```

Then draw centered text:
- `'starting'`: white text, `"Starting" + "." * _dot_count`
- `'running'`: green (`#7ec87e`) text, `"● Running"`

Font: `sans-serif`, 9pt, bold. Text rect: full poster area, `Qt.AlignCenter`.

**`mousePressEvent`:** if `_state != 'normal'`, return without emitting `clicked` or `remove_requested`.

---

### `launcher.py` — modified

**New fields (in `__init__`):**
- `_running_game: Optional[str] = None`
- `_running_proc: Optional[subprocess.Popen] = None`
- `_start_timer: QTimer` — single-shot, 5000 ms, connected to `_on_game_running`
- `_poll_timer: QTimer` — repeating, 1000 ms, connected to `_poll_game_proc`

**Updated `_on_launch`:**
1. If `_running_game is not None`: show `QMessageBox.information` "A game is already running" and return
2. Call `launch(PROTON_BIN, game['exe'], COMPAT_DIR / game['name'])` — returns `(proc, err)`
3. If `proc is None`: show error as before
4. On success: `self._cards[game['name']].set_state('starting')`, set `_running_game` and `_running_proc`, start `_start_timer` and `_poll_timer`

**New `_on_game_running()`:**
- `self._cards[self._running_game].set_state('running')` (guard: if `_running_game` still set)

**New `_poll_game_proc()`:**
- If `_running_proc` and `_running_proc.poll() is not None`:
  - Stop `_poll_timer` and `_start_timer`
  - If `_running_game in self._cards`: `self._cards[self._running_game].set_state('normal')` (guard against Refresh rebuilding cards mid-game)
  - Set `_running_game = None`, `_running_proc = None`

**Updated `_make_toolbar`** — add "Update Proton-GE…" action to `self._more_menu`:
```python
update_action = self._more_menu.addAction('Update Proton-GE…')
update_action.triggered.connect(self._on_update_proton)
```
Store `self._update_action = update_action`. In `_on_launch`, disable it when game starts: `self._update_action.setEnabled(False)`. In `_poll_game_proc`, re-enable it when game exits: `self._update_action.setEnabled(True)`.

**New `_on_update_proton()`:**
- Creates a modal `QDialog` (no close button: `dlg.setWindowFlag(Qt.WindowCloseButtonHint, False)`)
- Contains: `QLabel` status text, indeterminate `QProgressBar` (no min/max set, calls `setRange(0, 0)`)
- Creates `ProtonUpdater(BASE_DIR / 'proton')`, connects signals:
  - `progress` → updates label text
  - `finished` → closes dialog; on success: `_update_status()` + `QMessageBox.information`; on failure: `QMessageBox.critical`
- Starts updater thread, then calls `dlg.exec_()`

---

## Error Handling

- **Network failure during update:** `ProtonUpdater` emits `finished(False, error_message)` — modal closes, `QMessageBox.critical` shown.
- **Extraction failure:** same path.
- **Game already running when another clicked:** `QMessageBox.information` shown, no state change.
- **Game exits before 5 s "Starting" window:** `_poll_timer` fires, detects exit, stops `_start_timer` before it fires, resets state.

---

## Testing

### `tests/conftest.py` (new or append)

```python
import pytest
from PyQt5.QtWidgets import QApplication

@pytest.fixture(scope='session')
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
```

### `tests/test_proton_updater.py` (new)

- `test_fetch_latest_release_url_returns_url_and_version` — mock `requests.get` with a fake API response containing one `.tar.gz` asset; assert correct URL and version returned
- `test_fetch_latest_release_url_no_tarball_raises` — mock response with no `.tar.gz` asset; assert `RuntimeError` raised
- `test_fetch_latest_release_url_network_error_raises` — mock `requests.get` to raise `requests.RequestException`; assert `RuntimeError` raised

### `tests/test_runner.py` (new)

- `test_launch_returns_popen_on_success` — mock `subprocess.Popen`; assert returns `(mock_proc, '')`
- `test_launch_returns_none_on_oserror` — mock `Popen` to raise `OSError`; assert returns `(None, non_empty_str)`

### `tests/test_card_state.py` (new)

All tests use `qapp` fixture.

- `test_card_default_state_is_normal` — new `GameCard` has `_state == 'normal'`
- `test_set_state_starting_blocks_click` — set state `'starting'`, call `mousePressEvent` with left button; assert `clicked` signal not emitted
- `test_set_state_running_blocks_click` — same for `'running'`
- `test_set_state_normal_allows_click` — set state `'normal'`, call `mousePressEvent`; assert `clicked` emitted once

---

## Out of Scope

- Checking if Proton-GE is already the latest version before downloading.
- Cancelling an in-progress download.
- Per-game compat data path selection.
- Detecting game window visibility to drive `'starting'` → `'running'` transition (time-based 5 s is sufficient).
