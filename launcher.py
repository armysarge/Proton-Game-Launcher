import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from card import GameCard
from cover import CoverFetcher
from runner import launch
from dialog import AddGameDialog
from scanner import find_games, load_manual_games, save_manual_games
from shortcut import create_shortcut
from proton_updater import ProtonUpdater

VCRUN_PACKAGES = [
    (
        'vcrun2022',
        'VC++ 2015–2022 (recommended)',
        [('https://aka.ms/vs/17/release/vc_redist.x64.exe', 'vc_redist.x64.exe')],
    ),
    (
        'vcrun2019',
        'VC++ 2019',
        [('https://aka.ms/vs/16/release/vc_redist.x64.exe', 'vc_redist2019.x64.exe')],
    ),
    (
        'vcrun2017',
        'VC++ 2017',
        [('https://aka.ms/vs/15/release/vc_redist.x64.exe', 'vc_redist2017.x64.exe')],
    ),
]

BASE_DIR = Path(__file__).parent
PROTON_BIN = BASE_DIR / 'proton' / 'proton'
COMPAT_DIR = BASE_DIR / '.compat'
COVER_CACHE = BASE_DIR / '.cache' / 'covers'
COLS = 5


class VcrunInstaller(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, label: str, installers: list, compat_path: Path, proton_bin: Path, parent=None):
        super().__init__(parent)
        self._label = label
        self._installers = installers  # list of (url, filename)
        self._compat_path = compat_path
        self._proton_bin = proton_bin

    def run(self):
        import os
        import tempfile
        import urllib.request
        import shutil as _shutil

        tmp_dir = Path(tempfile.mkdtemp(prefix='proton-vcrun-'))
        try:
            env = os.environ.copy()
            env['STEAM_COMPAT_DATA_PATH'] = str(self._compat_path)
            env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = ''
            env['PROTON_USE_WOW64'] = '1'

            for url, filename in self._installers:
                dest = tmp_dir / filename
                self.progress.emit(f'Downloading {filename}…')
                try:
                    urllib.request.urlretrieve(url, dest)
                except Exception as e:
                    self.finished.emit(False, f'Download failed: {e}')
                    return

                self.progress.emit(f'Running {filename}…')
                result = subprocess.run(
                    [str(self._proton_bin), 'run', str(dest), '/install', '/quiet', '/norestart'],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                if result.returncode not in (0, 3010):  # 3010 = reboot required but OK
                    self.finished.emit(False, result.stderr.strip() or result.stdout.strip() or f'Exit code {result.returncode}')
                    return

            self.finished.emit(True, self._label)
        finally:
            _shutil.rmtree(tmp_dir, ignore_errors=True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Proton Game Launcher')
        self.setMinimumSize(860, 580)
        self._games: List[dict] = []
        self._cards: Dict[str, GameCard] = {}
        self._cover_cache: Dict[str, QPixmap] = {}
        self._manual_games: List[dict] = []
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

        add_game = QPushButton('+ Add Game')
        add_game.setStyleSheet(
            'background: #1a3a1a; color: #7ec87e; border: 1px solid #2a5a2a;'
            ' border-radius: 4px; padding: 4px 10px;'
        )
        add_game.clicked.connect(self._on_add_game)

        self._more_menu = QMenu(bar)
        self._more_menu.setStyleSheet(
            'QMenu { background: #222; color: #ccc; border: 1px solid #333; padding: 4px; }'
            'QMenu::item { padding: 4px 16px; }'
            'QMenu::item:selected { background: #2a4a2a; }'
        )
        shortcut_action = self._more_menu.addAction('Create Desktop Shortcut…')
        shortcut_action.triggered.connect(self._on_create_shortcut)
        self._update_action = self._more_menu.addAction('Update Proton-GE…')
        self._update_action.triggered.connect(self._on_update_proton)

        more_btn = QPushButton('⋮')
        more_btn.setStyleSheet(
            'background: #2a2a2a; color: #888; border: 1px solid #333;'
            ' border-radius: 4px; padding: 4px 10px; font-size: 14px;'
        )
        more_btn.clicked.connect(
            lambda: self._more_menu.exec_(more_btn.mapToGlobal(more_btn.rect().bottomLeft()))
        )

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._search)
        lay.addWidget(refresh)
        lay.addWidget(add_game)
        lay.addWidget(more_btn)
        return bar

    # ------------------------------------------------------------------ Data

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

    def _populate_grid(self):
        for i in reversed(range(self._grid.count())):
            w = self._grid.itemAt(i).widget()
            if w:
                w.setParent(None)
        self._cards.clear()

        for i, game in enumerate(self._games):
            card = GameCard(game, is_manual=game.get('manual', False))
            card.clicked.connect(self._on_launch)
            card.remove_requested.connect(self._on_remove_game)
            card.install_runtime_requested.connect(self._on_install_runtime)
            card.delete_requested.connect(self._on_delete_game)
            if game['name'] in self._cover_cache:
                card.set_cover(self._cover_cache[game['name']])
            self._cards[game['name']] = card
            self._grid.addWidget(card, i // COLS, i % COLS)

    def _fetch_covers(self):
        if not self._games:
            return
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

    def closeEvent(self, event):
        if self._fetcher and self._fetcher.isRunning():
            self._fetcher.terminate()
            self._fetcher.wait()
        super().closeEvent(event)

    # ------------------------------------------------------------------ Launch

    def _on_add_game(self):
        dlg = AddGameDialog(self)
        if dlg.exec_() != AddGameDialog.Accepted:
            return
        g = dlg.game()
        if g is None:
            return
        existing_names = {game['name'] for game in self._games}
        if g['name'] in existing_names:
            QMessageBox.warning(self, 'Duplicate Name',
                f"A game named '{g['name']}' already exists.")
            return
        updated = self._manual_games + [
            {'name': g['name'], 'path': g['path'], 'exe': g['exe']}
        ]
        try:
            save_manual_games(BASE_DIR, updated)
        except OSError as e:
            QMessageBox.critical(self, 'Save Failed', f'Could not save games.json:\n{e}')
            return
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
        self._load_games()

    def _on_delete_game(self, game: dict):
        if self._running_game == game['name']:
            QMessageBox.information(self, 'Game Running',
                f"'{game['name']}' is currently running and cannot be deleted.")
            return
        path = Path(game['path'])
        reply = QMessageBox.warning(
            self, 'Delete Game',
            f"Permanently delete '{game['name']}'?\n\nThis will remove the entire folder:\n{path}\n\n"
            'This cannot be undone.',
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            shutil.rmtree(path)
        except OSError as e:
            QMessageBox.critical(self, 'Delete Failed', f"Could not delete '{game['name']}':\n{e}")
            return
        if game.get('manual', False):
            updated = [g for g in self._manual_games if g['name'] != game['name']]
            try:
                save_manual_games(BASE_DIR, updated)
            except OSError as e:
                QMessageBox.critical(self, 'Save Failed', f'Could not save games.json:\n{e}')
        self._cover_cache.pop(game['name'], None)
        self._load_games()

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

    def _on_install_runtime(self, game: dict):
        dlg = QDialog(self)
        dlg.setWindowTitle('Install C++ Runtime')
        dlg.setStyleSheet('background: #1a1a1a; color: #e2e2e2;')
        dlg.setMinimumWidth(380)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel(f'Select a Visual C++ runtime to install\ninto the prefix for <b>{game["name"]}</b>:')
        lbl.setStyleSheet('color: #ccc;')

        combo = QComboBox()
        combo.setStyleSheet(
            'background: #222; color: #ccc; border: 1px solid #333;'
            ' border-radius: 4px; padding: 4px 8px;'
        )
        for _pkg, label, installers in VCRUN_PACKAGES:
            combo.addItem(label, (label, installers))

        status_lbl = QLabel('')
        status_lbl.setStyleSheet('color: #888; font-size: 10px;')

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        progress_bar.setVisible(False)
        progress_bar.setStyleSheet(
            'QProgressBar { background: #222; border: 1px solid #333;'
            ' border-radius: 4px; height: 12px; }'
            'QProgressBar::chunk { background: #2a5a2a; }'
        )

        install_btn = QPushButton('Install')
        install_btn.setStyleSheet(
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
        btn_row.addWidget(install_btn)

        layout.addWidget(lbl)
        layout.addWidget(combo)
        layout.addWidget(status_lbl)
        layout.addWidget(progress_bar)
        layout.addLayout(btn_row)

        cancel_btn.clicked.connect(dlg.reject)

        def _do_install():
            label, installers = combo.currentData()
            install_btn.setEnabled(False)
            cancel_btn.setEnabled(False)
            combo.setEnabled(False)
            progress_bar.setVisible(True)

            compat_path = COMPAT_DIR / game['name']
            compat_path.mkdir(parents=True, exist_ok=True)

            installer = VcrunInstaller(
                label, installers, compat_path, PROTON_BIN, parent=dlg
            )

            def _on_progress(msg):
                status_lbl.setText(msg)

            def _on_done(ok, msg):
                progress_bar.setVisible(False)
                dlg.accept()
                if ok:
                    QMessageBox.information(
                        self, 'Runtime Installed',
                        f'{msg} installed successfully for {game["name"]}.',
                    )
                else:
                    QMessageBox.critical(self, 'Install Failed', f'Could not install runtime:\n{msg}')

            installer.progress.connect(_on_progress)
            installer.finished.connect(_on_done)
            installer.start()

        install_btn.clicked.connect(_do_install)
        dlg.exec_()

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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
