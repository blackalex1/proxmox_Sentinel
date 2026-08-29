"""Tests for Modular Sentinel Controller Updater."""

import os
import pytest
from unittest.mock import MagicMock, patch

from installation.updater.downloader import Downloader
from installation.updater.core import CoreManager
from installation.updater.engines import ProxyEngineManager
from installation.updater.git import GitManager


def test_downloader_compute_sha256(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("sentinel-core-test", encoding="utf-8")
    h = Downloader.compute_sha256(str(f))
    assert isinstance(h, str)
    assert len(h) == 64


def test_core_manager_platform_info():
    mgr = CoreManager(project_dir=".")
    os_name, arch, ext = mgr._get_platform_info()
    assert os_name in ("windows", "linux", "darwin")
    assert arch in ("amd64", "arm64", "armv7")
    assert ext in (".dll", ".so", ".dylib")


def test_proxy_engine_manager_platform_info():
    mgr = ProxyEngineManager(project_dir=".")
    os_name, arch_sb, arch_xray = mgr._get_platform_info()
    assert os_name in ("windows", "linux", "darwin")
    assert arch_sb in ("amd64", "arm64", "armv7", "386")
    assert arch_xray in ("64", "arm64-v8a", "arm32-v7a", "32")


def test_downloader_fetch_github_api():
    downloader = Downloader()
    mock_data = {"tag_name": "v0.0.1", "assets": [{"name": "sentinel-core-linux-amd64", "digest": "sha256:abcd"}]}
    with patch.object(downloader, "download_bytes", return_value=None):
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = '{"tag_name": "v0.0.1"}'
            mock_run.return_value = mock_proc
            res = downloader.fetch_github_api("https://api.github.com/repos/test/releases/latest")
            assert res == {"tag_name": "v0.0.1"}
