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
