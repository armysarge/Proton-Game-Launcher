import os
import subprocess
from pathlib import Path
from typing import Optional


def build_launch_args(proton_bin: Path, exe_path: Path) -> list[str]:
    return [str(proton_bin), 'run', str(exe_path)]


def build_env(compat_path: Path) -> dict:
    env = os.environ.copy()
    env['STEAM_COMPAT_DATA_PATH'] = str(compat_path)
    env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] = ''
    return env


def launch(
    proton_bin: Path, exe_path: Path, compat_path: Path
) -> tuple[Optional[subprocess.Popen], str]:
    compat_path.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.Popen(
            build_launch_args(proton_bin, exe_path),
            env=build_env(compat_path),
            start_new_session=True,
        )
        return proc, ''
    except OSError as e:
        return None, str(e)
