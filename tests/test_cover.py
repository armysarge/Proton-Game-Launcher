from pathlib import Path
from cover import cover_cache_path, steam_art_url, steam_search_params


def test_cover_cache_path(tmp_path):
    assert cover_cache_path(tmp_path, 'Diablo II') == tmp_path / 'Diablo II.jpg'


def test_cover_cache_path_preserves_spaces(tmp_path):
    assert cover_cache_path(tmp_path, 'Age of Empires II') == tmp_path / 'Age of Empires II.jpg'


def test_steam_art_url():
    assert steam_art_url(12345) == (
        'https://cdn.akamai.steamstatic.com/steam/apps/12345/library_600x900_2x.jpg'
    )


def test_steam_search_params():
    params = steam_search_params('Halo CE')
    assert params['term'] == 'Halo CE'
    assert params['cc'] == 'us'
    assert params['l'] == 'en'
