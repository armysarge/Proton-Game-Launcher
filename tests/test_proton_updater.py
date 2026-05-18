import pytest
import requests
from unittest.mock import patch, MagicMock
from proton_updater import fetch_latest_release_url


FAKE_RESPONSE = {
    'tag_name': 'GE-Proton9-27',
    'assets': [
        {
            'name': 'GE-Proton9-27.tar.gz',
            'browser_download_url': 'https://example.com/GE-Proton9-27.tar.gz',
        },
        {
            'name': 'GE-Proton9-27.sha512sum',
            'browser_download_url': 'https://example.com/GE-Proton9-27.sha512sum',
        },
    ],
}


def test_fetch_latest_release_url_returns_url_and_version():
    mock_resp = MagicMock()
    mock_resp.json.return_value = FAKE_RESPONSE
    with patch('proton_updater.requests.get', return_value=mock_resp):
        url, version = fetch_latest_release_url('https://fake-api')
    assert url == 'https://example.com/GE-Proton9-27.tar.gz'
    assert version == 'GE-Proton9-27'


def test_fetch_latest_release_url_no_tarball_raises():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'tag_name': 'GE-Proton9-27',
        'assets': [
            {
                'name': 'GE-Proton9-27.sha512sum',
                'browser_download_url': 'https://example.com/sha512',
            },
        ],
    }
    with patch('proton_updater.requests.get', return_value=mock_resp):
        with pytest.raises(RuntimeError, match='No .tar.gz'):
            fetch_latest_release_url('https://fake-api')


def test_fetch_latest_release_url_network_error_raises():
    with patch('proton_updater.requests.get', side_effect=requests.RequestException('timeout')):
        with pytest.raises(RuntimeError, match='Network error'):
            fetch_latest_release_url('https://fake-api')
