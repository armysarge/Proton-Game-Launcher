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
        self._exe_edit.setStyleSheet(_FIELD)
        self._exe_edit.textChanged.connect(self._validate)
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
