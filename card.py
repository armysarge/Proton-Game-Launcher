from typing import Optional

from PyQt5.QtCore import Qt, QRect, pyqtSignal
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
