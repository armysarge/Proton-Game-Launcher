import sys
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from card import GameCard
from cover import CoverFetcher
from runner import launch
from dialog import AddGameDialog
from scanner import find_games, load_manual_games, save_manual_games
from shortcut import create_shortcut

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
        self._games: List[dict] = []
        self._cards: Dict[str, GameCard] = {}
        self._cover_cache: Dict[str, QPixmap] = {}
        self._manual_games: List[dict] = []
        self._fetcher: Optional[CoverFetcher] = None
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
