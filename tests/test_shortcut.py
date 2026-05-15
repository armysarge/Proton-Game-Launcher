from pathlib import Path
import shortcut as sc


def test_desktop_content_fields(tmp_path):
    content = sc._desktop_content(tmp_path)
    assert content.startswith('[Desktop Entry]\n')
    assert 'Name=Proton Game Launcher' in content
    assert f'Exec=bash "{tmp_path / "run.sh"}"' in content
    assert 'Icon=applications-games' in content
    assert 'Type=Application' in content
    assert 'Categories=Game;' in content
    assert 'Terminal=false' in content


def test_create_shortcut_desktop_only(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, '_DESKTOP_DIR', tmp_path / 'Desktop')
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=True, app_menu=False)
    assert ok
    assert err == ''
    assert (tmp_path / 'Desktop' / sc.DESKTOP_FILE_NAME).exists()
    assert not (tmp_path / 'apps' / sc.DESKTOP_FILE_NAME).exists()


def test_create_shortcut_app_menu_only(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, '_DESKTOP_DIR', tmp_path / 'Desktop')
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=False, app_menu=True)
    assert ok
    assert err == ''
    assert not (tmp_path / 'Desktop' / sc.DESKTOP_FILE_NAME).exists()
    assert (tmp_path / 'apps' / sc.DESKTOP_FILE_NAME).exists()


def test_create_shortcut_both(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, '_DESKTOP_DIR', tmp_path / 'Desktop')
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=True, app_menu=True)
    assert ok
    assert err == ''
    assert (tmp_path / 'Desktop' / sc.DESKTOP_FILE_NAME).exists()
    assert (tmp_path / 'apps' / sc.DESKTOP_FILE_NAME).exists()


def test_create_shortcut_write_failure(tmp_path, monkeypatch):
    desktop_dir = tmp_path / 'Desktop'
    desktop_dir.mkdir()
    desktop_dir.chmod(0o444)  # read-only — write will fail
    monkeypatch.setattr(sc, '_DESKTOP_DIR', desktop_dir)
    monkeypatch.setattr(sc, '_APP_MENU_DIR', tmp_path / 'apps')
    ok, err = sc.create_shortcut(tmp_path, desktop=True, app_menu=False)
    assert not ok
    assert err != ''
    desktop_dir.chmod(0o755)  # restore for cleanup


def test_desktop_content_exec_quotes_path_with_spaces(tmp_path):
    spaced = tmp_path / 'my games' / 'proton-launcher'
    content = sc._desktop_content(spaced)
    assert f'Exec=bash "{spaced / "run.sh"}"' in content
