import json
import pytest
from pathlib import Path
from scanner import find_games, detect_exe, EXCLUDE_PATTERN


def test_exclude_pattern_blocks_setup_variants():
    assert EXCLUDE_PATTERN.match('setup.exe')
    assert EXCLUDE_PATTERN.match('Setup.exe')
    assert EXCLUDE_PATTERN.match('setup64.exe')
    assert EXCLUDE_PATTERN.match('unins000.exe')
    assert EXCLUDE_PATTERN.match('UnityCrashHandler64.exe')
    assert EXCLUDE_PATTERN.match('vcredist_x64.exe')
    assert EXCLUDE_PATTERN.match('dotnetfx35.exe')
    assert EXCLUDE_PATTERN.match('dxsetup.exe')
    assert EXCLUDE_PATTERN.match('installer.exe')
    assert EXCLUDE_PATTERN.match('msredist.exe')


def test_exclude_pattern_allows_game_exe():
    assert not EXCLUDE_PATTERN.match('game.exe')
    assert not EXCLUDE_PATTERN.match('Halo.exe')
    assert not EXCLUDE_PATTERN.match('Diablo II.exe')


def test_detect_exe_picks_largest(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'small.exe').write_bytes(b'x' * 100)
    (game / 'large.exe').write_bytes(b'x' * 1000)
    assert detect_exe(game) == game / 'large.exe'


def test_detect_exe_excludes_setup_even_if_larger(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'setup.exe').write_bytes(b'x' * 2000)
    (game / 'game.exe').write_bytes(b'x' * 100)
    assert detect_exe(game) == game / 'game.exe'


def test_detect_exe_returns_none_when_no_exes(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    assert detect_exe(game) is None


def test_detect_exe_returns_none_when_only_excluded(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'setup.exe').write_bytes(b'x' * 100)
    assert detect_exe(game) is None


def test_detect_exe_finds_exe_in_subdirectory(tmp_path):
    game = tmp_path / 'TestGame'
    sub = game / 'bin'
    sub.mkdir(parents=True)
    (sub / 'game.exe').write_bytes(b'x' * 500)
    assert detect_exe(game) == sub / 'game.exe'


def test_detect_exe_respects_launcher_json_override(tmp_path):
    game = tmp_path / 'TestGame'
    game.mkdir()
    (game / 'main.exe').write_bytes(b'x' * 1000)
    (game / 'alt.exe').write_bytes(b'x' * 100)
    config = {'TestGame': {'exe': 'TestGame/alt.exe'}}
    (tmp_path / '.launcher.json').write_text(json.dumps(config))
    assert detect_exe(game) == game / 'alt.exe'


def test_find_games_skips_hidden_dirs(tmp_path):
    hidden = tmp_path / '.venv'
    hidden.mkdir()
    (hidden / 'python.exe').write_bytes(b'x' * 100)
    assert find_games(tmp_path) == []


def test_find_games_skips_dirs_without_exe(tmp_path):
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'readme.txt').write_text('hello')
    assert find_games(tmp_path) == []


def test_find_games_returns_game_with_exe(tmp_path):
    game = tmp_path / 'Diablo II'
    game.mkdir()
    exe = game / 'Diablo II.exe'
    exe.write_bytes(b'x' * 1000)
    games = find_games(tmp_path)
    assert len(games) == 1
    assert games[0]['name'] == 'Diablo II'
    assert games[0]['path'] == game
    assert games[0]['exe'] == exe


def test_find_games_sorted_alphabetically(tmp_path):
    for name in ['Zork', 'Aardvark', 'Monkey Island']:
        d = tmp_path / name
        d.mkdir()
        (d / 'game.exe').write_bytes(b'x')
    names = [g['name'] for g in find_games(tmp_path)]
    assert names == sorted(names)
