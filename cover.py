from pathlib import Path

import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

_STEAM_SEARCH = 'https://store.steampowered.com/api/storesearch/'
_STEAM_ART = 'https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_600x900_2x.jpg'


def cover_cache_path(cache_dir: Path, game_name: str) -> Path:
    return cache_dir / f'{game_name}.jpg'


def steam_art_url(appid: int) -> str:
    return _STEAM_ART.format(appid=appid)


def steam_search_params(game_name: str) -> dict:
    return {'term': game_name, 'cc': 'us', 'l': 'en'}


class CoverFetcher(QThread):
    cover_ready = pyqtSignal(str, QPixmap)  # game_name, pixmap

    def __init__(self, games: list[dict], cache_dir: Path):
        super().__init__()
        self._games = games
        self._cache_dir = cache_dir

    def run(self):
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        for game in self._games:
            pixmap = self._load(game['name'])
            if pixmap is not None:
                self.cover_ready.emit(game['name'], pixmap)

    def _load(self, name: str) -> QPixmap | None:
        cached = cover_cache_path(self._cache_dir, name)
        if cached.exists():
            px = QPixmap()
            px.load(str(cached))
            return px if not px.isNull() else None
        return self._fetch(name)

    def _fetch(self, name: str) -> QPixmap | None:
        try:
            resp = requests.get(_STEAM_SEARCH, params=steam_search_params(name), timeout=10)
            resp.raise_for_status()
            items = resp.json().get('items', [])
            if not items:
                return None
            appid = items[0]['id']
            img = requests.get(steam_art_url(appid), timeout=10)
            if img.status_code != 200:
                return None
            cover_cache_path(self._cache_dir, name).write_bytes(img.content)
            px = QPixmap()
            px.loadFromData(img.content)
            return px if not px.isNull() else None
        except Exception:
            return None
