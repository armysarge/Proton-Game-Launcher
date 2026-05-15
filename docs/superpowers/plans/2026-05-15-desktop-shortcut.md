# Desktop Shortcut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a ⋮ overflow menu to the launcher toolbar that writes a `proton-game-launcher.desktop` file to the user's Desktop, app menu, or both.

**Architecture:** A new `shortcut.py` module owns `.desktop` file generation and writing (pure logic, no Qt, fully testable). `launcher.py` adds a ⋮ toolbar button that opens a `QMenu`, which triggers an inline `QDialog` with two checkboxes for location selection.

**Tech Stack:** Python 3.8+, PyQt5, pytest, pathlib

---

## File Map

| File | Change |
|------|--------|
| `shortcut.py` | Create: `create_shortcut`, `_desktop_content`, `_write_file` |
| `launcher.py` | Add ⋮ toolbar button + `QMenu` + `_on_create_shortcut` dialog |
| `tests/test_shortcut.py` | Create: 5 tests |

---

### Task 1: shortcut.py — create_shortcut function

**Files:**
- Create: `shortcut.py`
- Test: `tests/test_shortcut.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_shortcut.py`:

```python
from pathlib import Path
import shortcut as sc


def test_desktop_content_fields(tmp_path):
    content = sc._desktop_content(tmp_path)
    assert 'Name=Proton Game Launcher' in content
    assert f'Exec=bash {tmp_path / "run.sh"}' in content
    assert 'Icon=applications-games' in content
    assert 'Type=Application' in content
    assert 'Categories=Game;' in content
    assert 'Terminal=false' in content


def test_create_shortcut_desktop_only(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, '_DESKTOP_DIR', tmp_path / 'Desktop')
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=True, app_menu=False)
    assert ok
    assert err == ''
    assert (tmp_path / 'Desktop' / sc.DESKTOP_FILE_NAME).exists()
    assert not (tmp_path / 'apps' / sc.DESKTOP_FILE_NAME).exists()


def test_create_shortcut_app_menu_only(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, '_DESKTOP_DIR', tmp_path / 'Desktop')
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=False, app_menu=True)
    assert ok
    assert err == ''
    assert not (tmp_path / 'Desktop' / sc.DESKTOP_FILE_NAME).exists()
    assert (tmp_path / 'apps' / sc.DESKTOP_FILE_NAME).exists()


def test_create_shortcut_both(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, '_DESKTOP_DIR', tmp_path / 'Desktop')
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=True, app_menu=True)
    assert ok
    assert err == ''
    assert (tmp_path / 'Desktop' / sc.DESKTOP_FILE_NAME).exists()
    assert (tmp_path / 'apps' / sc.DESKTOP_FILE_NAME).exists()


def test_create_shortcut_write_failure(tmp_path, monkeypatch):
    desktop_dir = tmp_path / 'Desktop'
    desktop_dir.mkdir()
    desktop_dir.chmod(0o444)  # read-only — write will fail
    monkeypatch.setattr(sc, '_DESKTOP_DIR', desktop_dir)
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=True, app_menu=False)
    assert not ok
    assert err != ''
    desktop_dir.chmod(0o755)  # restore for cleanup
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_shortcut.py -v
```

Expected: 5 failures — `ModuleNotFoundError: No module named 'shortcut'`

- [ ] **Step 3: Create shortcut.py**

Create `/home/shaun/proton-launcher/shortcut.py`:

```python
from pathlib import Path

DESKTOP_FILE_NAME = 'proton-game-launcher.desktop'
_DESKTOP_DIR = Path.home() / 'Desktop'
_APP_MENU_DIR = Path.home() / '.local' / 'share' / 'applications'


def create_shortcut(launcher_dir: Path, desktop: bool, app_menu: bool) -> tuple[bool, str]:
    content = _desktop_content(launcher_dir)
    errors = []
    if desktop:
        ok, err = _write_file(_DESKTOP_DIR / DESKTOP_FILE_NAME, content)
        if not ok:
            errors.append(f'Desktop: {err}')
    if app_menu:
        ok, err = _write_file(_APP_MENU_DIR / DESKTOP_FILE_NAME, content)
        if not ok:
            errors.append(f'App menu: {err}')
    if errors:
        return False, '\n'.join(errors)
    return True, ''


def _desktop_content(launcher_dir: Path) -> str:
    run_sh = launcher_dir / 'run.sh'
    return (
        '[Desktop Entry]\n'
        'Name=Proton Game Launcher\n'
        'Comment=Run Windows games via Proton-GE\n'
        f'Exec=bash {run_sh}\n'
        'Icon=applications-games\n'
        'Type=Application\n'
        'Categories=Game;\n'
        'Terminal=false\n'
    )


def _write_file(path: Path, content: str) -> tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return True, ''
    except OSError as e:
        return False, str(e)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest tests/test_shortcut.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 31 tests PASS (26 existing + 5 new)

- [ ] **Step 6: Commit**

```bash
cd /home/shaun/proton-launcher && git add shortcut.py tests/test_shortcut.py && git commit -m "feat: add create_shortcut for desktop .desktop file generation"
```

---

### Task 2: launcher.py — ⋮ menu and shortcut dialog

**Files:**
- Modify: `launcher.py`

- [ ] **Step 1: Add new imports to launcher.py**

In the PyQt5 imports block, add `QCheckBox`, `QDialog`, `QMenu`:

```python
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)
```

Also add the shortcut import after the existing local imports:

```python
from shortcut import create_shortcut
```

- [ ] **Step 2: Add the ⋮ button to _make_toolbar**

In `_make_toolbar`, replace the end of the method (the `lay.addWidget` lines and `return bar`) with:

```python
        menu = QMenu(bar)
        menu.setStyleSheet(
            'QMenu { background: #222; color: #ccc; border: 1px solid #333; padding: 4px; }'
            'QMenu::item { padding: 4px 16px; }'
            'QMenu::item:selected { background: #2a4a2a; }'
        )
        shortcut_action = menu.addAction('Create Desktop Shortcut…')
        shortcut_action.triggered.connect(self._on_create_shortcut)

        more_btn = QPushButton('⋮')
        more_btn.setStyleSheet(
            'background: #2a2a2a; color: #888; border: 1px solid #333;'
            ' border-radius: 4px; padding: 4px 10px; font-size: 14px;'
        )
        more_btn.clicked.connect(
            lambda: menu.exec_(more_btn.mapToGlobal(more_btn.rect().bottomLeft()))
        )

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._search)
        lay.addWidget(refresh)
        lay.addWidget(add_game)
        lay.addWidget(more_btn)
        return bar
```

- [ ] **Step 3: Add _on_create_shortcut method to launcher.py**

Add this method after `_on_remove_game`:

```python
    def _on_create_shortcut(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('Create Desktop Shortcut')
        dlg.setStyleSheet('background: #1a1a1a; color: #e2e2e2;')
        dlg.setMinimumWidth(340)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel('Create shortcut for Proton Game Launcher:')
        lbl.setStyleSheet('color: #ccc;')

        desktop_cb = QCheckBox('Desktop  (~/Desktop/)')
        desktop_cb.setChecked(True)
        desktop_cb.setStyleSheet('color: #ccc;')

        app_menu_cb = QCheckBox('App menu  (~/.local/share/applications/)')
        app_menu_cb.setChecked(True)
        app_menu_cb.setStyleSheet('color: #ccc;')

        create_btn = QPushButton('Create')
        create_btn.setStyleSheet(
            'background: #1a3a1a; color: #7ec87e; border: 1px solid #2a5a2a;'
            ' border-radius: 4px; padding: 6px 14px;'
        )
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setStyleSheet(
            'background: #222; color: #888; border: 1px solid #333;'
            ' border-radius: 4px; padding: 6px 14px;'
        )

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(create_btn)

        layout.addWidget(lbl)
        layout.addWidget(desktop_cb)
        layout.addWidget(app_menu_cb)
        layout.addLayout(btn_row)

        def _update_btn():
            create_btn.setEnabled(desktop_cb.isChecked() or app_menu_cb.isChecked())

        desktop_cb.toggled.connect(_update_btn)
        app_menu_cb.toggled.connect(_update_btn)
        cancel_btn.clicked.connect(dlg.reject)

        def _do_create():
            ok, err = create_shortcut(
                BASE_DIR, desktop_cb.isChecked(), app_menu_cb.isChecked()
            )
            if ok:
                QMessageBox.information(dlg, 'Shortcut Created', 'Shortcut created successfully.')
                dlg.accept()
            else:
                QMessageBox.critical(dlg, 'Error', f'Could not create shortcut:\n{err}')

        create_btn.clicked.connect(_do_create)
        dlg.exec_()
```

- [ ] **Step 4: Run the full test suite**

```bash
cd /home/shaun/proton-launcher && .venv/bin/pytest -v
```

Expected: all 31 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/shaun/proton-launcher && git add launcher.py && git commit -m "feat: add ⋮ menu with Create Desktop Shortcut to launcher toolbar"
```
