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


import subprocess
from unittest.mock import patch, MagicMock
from runner import launch


def test_launch_returns_popen_on_success(tmp_path):
    mock_proc = MagicMock(spec=subprocess.Popen)
    with patch('runner.subprocess.Popen', return_value=mock_proc):
        proc, err = launch(tmp_path / 'proton', tmp_path / 'game.exe', tmp_path / 'compat')
    assert proc is mock_proc
    assert err == ''


def test_launch_returns_none_on_oserror(tmp_path):
    with patch('runner.subprocess.Popen', side_effect=OSError('exec failed')):
        proc, err = launch(tmp_path / 'proton', tmp_path / 'game.exe', tmp_path / 'compat')
    assert proc is None
    assert err != ''
