from pathlib import Path

DESKTOP_FILE_NAME = 'proton-game-launcher.desktop'
_DESKTOP_DIR = Path.home() / 'Desktop'
_APP_MENU_DIR = Path.home() / '.local' / 'share' / 'applications'


def create_shortcut(launcher_dir: Path, desktop: bool, app_menu: bool) -> tuple[bool, str]:
    content = _desktop_content(launcher_dir)
    errors = []
    if desktop:
        ok, err = _write_file(_DESKTOP_DIR / DESKTOP_FILE_NAME, content)
        if not ok:
            errors.append(f'Desktop: {err}')
    if app_menu:
        ok, err = _write_file(_APP_MENU_DIR / DESKTOP_FILE_NAME, content)
        if not ok:
            errors.append(f'App menu: {err}')
    if errors:
        return False, '\n'.join(errors)
    return True, ''


def _desktop_content(launcher_dir: Path) -> str:
    run_sh = launcher_dir / 'run.sh'
    return (
        '[Desktop Entry]\n'
        'Name=Proton Game Launcher\n'
        'Comment=Run Windows games via Proton-GE\n'
        f'Exec=bash {run_sh}\n'
        'Icon=applications-games\n'
        'Type=Application\n'
        'Categories=Game;\n'
        'Terminal=false\n'
    )


def _write_file(path: Path, content: str) -> tuple[bool, str]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return True, ''
    except OSError as e:
        return False, str(e)
