import json
import re
from pathlib import Path

EXCLUDE_PATTERN = re.compile(
    r'^(unins.*|setup.*|install.*|.*redist.*|unitycrashhandler.*'
    r'|dxsetup.*|dotnetfx.*)\.exe$',
    re.IGNORECASE,
)


def find_games(base_dir: Path) -> list[dict]:
    games = []
    for entry in sorted(base_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith('.'):
            continue
        candidates = _find_candidates(entry)
        if not candidates:
            continue
        exe = _pick_exe(base_dir, entry.name, candidates)
        games.append({'name': entry.name, 'path': entry, 'exe': exe})
    return games


def detect_exe(game_dir: Path) -> Path | None:
    candidates = _find_candidates(game_dir)
    if not candidates:
        return None
    return _pick_exe(game_dir.parent, game_dir.name, candidates)


def _find_candidates(game_dir: Path) -> list[Path]:
    return [f for f in game_dir.rglob('*.exe') if not EXCLUDE_PATTERN.match(f.name)]


def _pick_exe(base_dir: Path, game_name: str, candidates: list[Path]) -> Path:
    config = _load_config(base_dir)
    if game_name in config:
        override_rel = config[game_name].get('exe')
        if override_rel:
            override = base_dir / override_rel
            if override.exists():
                return override
    return max(candidates, key=lambda f: f.stat().st_size)


def _load_config(base_dir: Path) -> dict:
    config_file = base_dir / '.launcher.json'
    if not config_file.exists():
        return {}
    try:
        return json.loads(config_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_manual_games(base_dir: Path) -> list[dict]:
    games_file = base_dir / 'games.json'
    if not games_file.exists():
        return []
    try:
        entries = json.loads(games_file.read_text())
        return [
            {
                'name': e['name'],
                'path': Path(e['path']),
                'exe': Path(e['exe']),
            }
            for e in entries
        ]
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return []


def save_manual_games(base_dir: Path, games: list[dict]) -> None:
    games_file = base_dir / 'games.json'
    entries = [
        {'name': g['name'], 'path': str(g['path']), 'exe': str(g['exe'])}
        for g in games
    ]
    games_file.write_text(json.dumps(entries, indent=2))
