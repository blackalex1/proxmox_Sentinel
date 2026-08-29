"""Direct GitHub Downloader for Sentinel Controller Updater."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import ssl
import subprocess
import sys
import urllib.request
from typing import Any, Dict, Optional

from .common import BOLD, RESET, log_error, log_info, log_success, log_warn


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class Downloader:
    """Handles file downloads, HTTP API requests, and SHA-256 validation directly from GitHub."""

    def __init__(self, proxy_url: Optional[str] = None) -> None:
        self.proxy_url = proxy_url

    def _build_opener(self) -> urllib.request.OpenerDirector:
        """Builds an urllib opener configured with SSL and optional proxy."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        handlers: list = [urllib.request.HTTPSHandler(context=ctx)]
        if self.proxy_url:
            p_dict = {
                "http": self.proxy_url,
                "https": self.proxy_url,
            }
            handlers.append(urllib.request.ProxyHandler(p_dict))

        return urllib.request.build_opener(*handlers)

    def download_file(self, url: str, dest: str, timeout: float = 180.0) -> bool:
        """Downloads a file directly from GitHub to destination path using atomic temp replacement."""
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        tmp_dest = f"{dest}.tmp.{os.getpid()}"

        # 1. Try curl (fast, reliable TLS, redirect follow and proxy support)
        if shutil.which("curl"):
            proxy_candidates = []
            if self.proxy_url:
                p = self.proxy_url
                if p.startswith("socks5://"):
                    p = "socks5h://" + p[len("socks5://"):]
                proxy_candidates.append(p)
                # Also try HTTP inbound port if socks5 on 10818
                if "10818" in p:
                    proxy_candidates.append(p.replace("10818", "10819").replace("socks5h://", "http://").replace("socks5://", "http://"))
            else:
                proxy_candidates.append(None)

            for p_opt in proxy_candidates:
                try:
                    is_interactive = sys.stdout.isatty()
                    progress_flag = "-#" if is_interactive else "-s"
                    curl_cmd = [
                        "curl", progress_flag, "-L", "-k",
                        "--connect-timeout", "10",
                        "--max-time", str(int(timeout)),
                        "--speed-time", "20",
                        "--speed-limit", "500",
                        "--retry", "2",
                        "--retry-delay", "1",
                        "-H", f"User-Agent: {USER_AGENT}",
                        "-o", tmp_dest,
                    ]
                    if p_opt:
                        curl_cmd.extend(["-x", p_opt])
                    else:
                        curl_cmd.extend(["--noproxy", "*"])

                    curl_cmd.append(url)
                    
                    if is_interactive:
                        # Allow curl progress bar to render live to terminal stderr
                        res = subprocess.run(curl_cmd, timeout=timeout + 10.0)
                    else:
                        res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout + 10.0)

                    if res.returncode == 0 and os.path.isfile(tmp_dest) and os.path.getsize(tmp_dest) > 0:
                        size_mb = os.path.getsize(tmp_dest) / (1024 * 1024)
                        if platform.system() != "Windows":
                            try:
                                os.chmod(tmp_dest, 0o755)
                            except Exception:
                                pass
                        os.replace(tmp_dest, dest)
                        log_info(f"  [✓] Загружено: {size_mb:.1f} MB")
                        return True
                    elif hasattr(res, 'stderr') and res.stderr:
                        log_warn(f"  [curl] {res.stderr.strip()}")
                except Exception as e:
                    log_warn(f"  [curl exception] {e}")

        # 2. Fallback to urllib.request
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            opener = self._build_opener()
            with opener.open(req, timeout=timeout) as resp:
                if resp.status == 200:
                    with open(tmp_dest, "wb") as f:
                        shutil.copyfileobj(resp, f)
                    if os.path.isfile(tmp_dest) and os.path.getsize(tmp_dest) > 0:
                        if platform.system() != "Windows":
                            try:
                                os.chmod(tmp_dest, 0o755)
                            except Exception:
                                pass
                        os.replace(tmp_dest, dest)
                        return True
        except Exception:
            return False
        finally:
            if os.path.isfile(tmp_dest):
                try:
                    os.remove(tmp_dest)
                except Exception:
                    pass

        return False

    def download_bytes(self, url: str, timeout: float = 180.0) -> Optional[bytes]:
        """Downloads data from GitHub URL into memory."""
        # 1. Try curl
        if shutil.which("curl"):
            proxy_candidates = []
            if self.proxy_url:
                p = self.proxy_url
                if p.startswith("socks5://"):
                    p = "socks5h://" + p[len("socks5://"):]
                proxy_candidates.append(p)
                if "10818" in p:
                    proxy_candidates.append(p.replace("10818", "10819").replace("socks5h://", "http://").replace("socks5://", "http://"))
            else:
                proxy_candidates.append(None)

            for p_opt in proxy_candidates:
                try:
                    curl_cmd = [
                        "curl", "-sSL", "-k",
                        "--connect-timeout", "10",
                        "--max-time", str(int(timeout)),
                        "--speed-time", "20",
                        "--speed-limit", "500",
                        "--retry", "2",
                        "--retry-delay", "1",
                        "-H", f"User-Agent: {USER_AGENT}",
                    ]
                    if p_opt:
                        curl_cmd.extend(["-x", p_opt])
                    else:
                        curl_cmd.extend(["--noproxy", "*"])

                    curl_cmd.append(url)
                    res = subprocess.run(curl_cmd, capture_output=True, timeout=timeout + 10.0)
                    if res.returncode == 0 and res.stdout and len(res.stdout) > 1024:
                        return res.stdout
                except Exception:
                    pass

        # 2. Fallback to urllib.request
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            opener = self._build_opener()
            with opener.open(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception:
            return None

        return None

    def download_file_with_mirrors(self, direct_url: str, dest_path: str, filename_for_log: str = "") -> bool:
        """Downloads a file directly from GitHub releases."""
        log_name = filename_for_log or os.path.basename(dest_path)
        log_info(f"  ➜ Загрузка {log_name} с GitHub...")
        return self.download_file(direct_url, dest_path, timeout=180.0)

    def download_bytes_with_mirrors(self, direct_url: str, label_for_log: str = "") -> Optional[bytes]:
        """Downloads bytes directly from GitHub releases."""
        if label_for_log:
            log_info(f"  ➜ Загрузка {label_for_log} с GitHub...")
        return self.download_bytes(direct_url, timeout=180.0)

    def fetch_github_api(self, endpoint_url: str, timeout: float = 8.0) -> Optional[Any]:
        """Queries GitHub REST API directly."""
        # 1. Try curl
        if shutil.which("curl"):
            try:
                curl_cmd = [
                    "curl", "-fsSL", "-k",
                    "--connect-timeout", "4",
                    "--max-time", str(int(timeout)),
                    "-H", f"User-Agent: {USER_AGENT}",
                    "-H", "Accept: application/vnd.github.v3+json",
                ]
                if self.proxy_url:
                    p = self.proxy_url
                    if p.startswith("socks5://"):
                        p = "socks5h://" + p[len("socks5://"):]
                    curl_cmd.extend(["-x", p])
                else:
                    curl_cmd.extend(["--noproxy", "*"])

                curl_cmd.append(endpoint_url)
                res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout + 2.0)
                if res.returncode == 0 and res.stdout.strip():
                    return json.loads(res.stdout)
            except Exception:
                pass

        # 2. Try urllib fallback
        try:
            req = urllib.request.Request(
                endpoint_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            opener = self._build_opener()
            with opener.open(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        return None

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Calculates SHA-256 hash of a local file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
