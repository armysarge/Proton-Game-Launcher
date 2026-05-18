import shutil
import tarfile
import tempfile
from pathlib import Path

import requests
from PyQt5.QtCore import QThread, pyqtSignal

GITHUB_API_URL = 'https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest'


def fetch_latest_release_url(api_url: str) -> tuple[str, str]:
    try:
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f'Network error: {e}') from e
    version = data.get('tag_name', '')
    for asset in data.get('assets', []):
        if asset.get('name', '').endswith('.tar.gz'):
            return asset['browser_download_url'], version
    raise RuntimeError('No .tar.gz asset found in latest release')


class ProtonUpdater(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, proton_dir: Path, parent=None):
        super().__init__(parent)
        self._proton_dir = proton_dir

    def run(self):
        tmp_path = None
        try:
            self.progress.emit('Checking for latest release…')
            url, version = fetch_latest_release_url(GITHUB_API_URL)
            tarball_name = url.split('/')[-1]

            self.progress.emit(f'Downloading {tarball_name}…')
            resp = requests.get(url, stream=True, timeout=60)
            resp.raise_for_status()

            downloaded_bytes = 0
            last_reported_10mb = 0
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    tmp_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    bucket = downloaded_bytes // (10 * 1024 * 1024)
                    if bucket > last_reported_10mb:
                        last_reported_10mb = bucket
                        self.progress.emit(
                            f'Downloading… {downloaded_bytes / (1024 * 1024):.0f} MB'
                        )

            self.progress.emit('Extracting…')
            if self._proton_dir.exists():
                shutil.rmtree(self._proton_dir)
            self._proton_dir.mkdir(parents=True)
            with tarfile.open(tmp_path) as tf:
                for member in tf.getmembers():
                    parts = Path(member.name).parts
                    if len(parts) <= 1:
                        continue
                    member.name = str(Path(*parts[1:]))
                    tf.extract(member, self._proton_dir)

            self.finished.emit(True, version)

        except (OSError, RuntimeError, requests.RequestException) as e:
            self.finished.emit(False, str(e))
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
