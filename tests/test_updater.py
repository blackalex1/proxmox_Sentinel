"""Tests for Modular Sentinel Controller Updater."""

import os
import pytest
from unittest.mock import MagicMock, patch

from updater.core.downloader import Downloader
from updater.core.sentinel_core import SentinelCoreManager
from updater.controller.engines import ProxyEngineManager
from updater.core.git import GitManager


def test_downloader_compute_sha256(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("sentinel-core-test", encoding="utf-8")
    h = Downloader.compute_sha256(str(f))
    assert isinstance(h, str)
    assert len(h) == 64


def test_core_manager_platform_info():
    mgr = SentinelCoreManager(bin_dir=".")
    os_name, arch, ext = mgr._get_platform_info()
    assert os_name in ("windows", "linux", "darwin")
    assert arch in ("amd64", "arm64", "armv7")
    assert ext in (".dll", ".so", ".dylib")


def test_proxy_engine_manager_platform_info():
    mgr = ProxyEngineManager(bin_dir=".")
    os_name, arch_sb, arch_xray = mgr._get_platform_info()
    assert os_name in ("windows", "linux", "darwin")
    assert arch_sb in ("amd64", "arm64", "armv7", "386")
    assert arch_xray in ("64", "arm64-v8a", "arm32-v7a", "32")


def test_downloader_fetch_github_api():
    downloader = Downloader()
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = '{"tag_name": "v0.0.1"}'
    with patch("shutil.which", return_value="curl"), patch("subprocess.run", return_value=mock_proc):
        res = downloader.fetch_github_api("https://api.github.com/repos/test/releases/latest")
        assert res == {"tag_name": "v0.0.1"}
