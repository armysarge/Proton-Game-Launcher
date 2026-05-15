import os
from pathlib import Path
from runner import build_launch_args, build_env


def test_build_launch_args_structure(tmp_path):
    proton = tmp_path / 'proton' / 'proton'
    exe = tmp_path / 'Game' / 'game.exe'
    assert build_launch_args(proton, exe) == [str(proton), 'run', str(exe)]


def test_build_env_sets_compat_path(tmp_path):
    compat = tmp_path / '.compat' / 'Game'
    env = build_env(compat)
    assert env['STEAM_COMPAT_DATA_PATH'] == str(compat)


def test_build_env_clears_client_install_path(tmp_path):
    compat = tmp_path / '.compat' / 'Game'
    env = build_env(compat)
    assert env['STEAM_COMPAT_CLIENT_INSTALL_PATH'] == ''


def test_build_env_inherits_existing_env(tmp_path):
    compat = tmp_path / '.compat' / 'Game'
    env = build_env(compat)
    assert 'PATH' in env
