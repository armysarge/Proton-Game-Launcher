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
