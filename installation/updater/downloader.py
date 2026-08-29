"""Unified Network Downloader & Mirror Manager for Sentinel Updater."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import ssl
import subprocess
import urllib.request
from typing import Any, Dict, List, Optional, Union

from .common import BOLD, RESET, log_error, log_info, log_success, log_warn


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CDN_MIRRORS = [
    "",  # Direct GitHub
    "https://ghfast.top/",
    "https://gh-proxy.com/",
    "https://gh.ddlc.top/",
    "https://ghproxy.net/",
]


class Downloader:
    """Handles file downloads, HTTP API requests, CDN mirror failover, and SHA-256 validation."""

    def __init__(self, proxy_url: Optional[str] = None) -> None:
        self.proxy_url = proxy_url
        self.direct_blocked = False

    def _build_opener(self) -> urllib.request.OpenerDirector:
        """Builds an urllib opener configured with SSL ignore and optional proxy."""
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

    def download_file(self, url: str, dest: str, timeout: float = 30.0) -> bool:
        """Downloads a single URL directly to dest path using atomic temp file replacement."""
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        tmp_dest = f"{dest}.tmp.{os.getpid()}"

        # 1. Try curl (fastest, robust Cloudflare & TLS 1.3 support)
        if shutil.which("curl"):
            try:
                curl_cmd = [
                    "curl", "-fsSL", "-k",
                    "--connect-timeout", "4",
                    "--max-time", str(int(timeout)),
                    "-H", f"User-Agent: {USER_AGENT}",
                    "-o", tmp_dest,
                ]
                if self.proxy_url:
                    p = self.proxy_url
                    if p.startswith("socks5://"):
                        p = "socks5h://" + p[len("socks5://"):]
                    curl_cmd.extend(["-x", p])
                else:
                    curl_cmd.extend(["--noproxy", "*"])

                curl_cmd.append(url)
                res = subprocess.run(curl_cmd, capture_output=True, timeout=timeout + 3.0)
                if res.returncode == 0 and os.path.isfile(tmp_dest) and os.path.getsize(tmp_dest) > 0:
                    if platform.system() != "Windows":
                        try:
                            os.chmod(tmp_dest, 0o755)
                        except Exception:
                            pass
                    os.replace(tmp_dest, dest)
                    return True
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

    def download_bytes(self, url: str, timeout: float = 30.0) -> Optional[bytes]:
        """Downloads data from URL into memory."""
        # 1. Try curl
        if shutil.which("curl"):
            try:
                curl_cmd = [
                    "curl", "-fsSL", "-k",
                    "--connect-timeout", "4",
                    "--max-time", str(int(timeout)),
                    "-H", f"User-Agent: {USER_AGENT}",
                ]
                if self.proxy_url:
                    p = self.proxy_url
                    if p.startswith("socks5://"):
                        p = "socks5h://" + p[len("socks5://"):]
                    curl_cmd.extend(["-x", p])
                else:
                    curl_cmd.extend(["--noproxy", "*"])

                curl_cmd.append(url)
                res = subprocess.run(curl_cmd, capture_output=True, timeout=timeout + 3.0)
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
        """Downloads a file with automated failover across direct GitHub and CDN mirrors."""
        mirrors = list(CDN_MIRRORS)
        if self.direct_blocked and mirrors[0] == "":
            mirrors = mirrors[1:] + [""]

        for prefix in mirrors:
            full_url = f"{prefix}{direct_url}" if prefix else direct_url
            source_label = "Официальный GitHub" if not prefix else f"CDN-зеркало ({prefix.split('/')[2]})"

            log_name = filename_for_log or os.path.basename(dest_path)
            log_info(f"  ➜ Попытка загрузки {log_name} из {source_label}...")

            ok = self.download_file(full_url, dest_path, timeout=30.0)
            if ok and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 0:
                return True

            if not prefix:
                self.direct_blocked = True

        return False

    def download_bytes_with_mirrors(self, direct_url: str, label_for_log: str = "") -> Optional[bytes]:
        """Downloads in-memory data with automated failover across CDN mirrors."""
        mirrors = list(CDN_MIRRORS)
        if self.direct_blocked and mirrors[0] == "":
            mirrors = mirrors[1:] + [""]

        for prefix in mirrors:
            full_url = f"{prefix}{direct_url}" if prefix else direct_url
            source_label = "Официальный GitHub" if not prefix else f"CDN-зеркало ({prefix.split('/')[2]})"

            if label_for_log:
                log_info(f"  ➜ Загрузка {label_for_log} из {source_label}...")

            data = self.download_bytes(full_url, timeout=30.0)
            if data and len(data) > 1024:
                return data

            if not prefix:
                self.direct_blocked = True

        return None

    def fetch_github_api(self, endpoint_url: str, timeout: float = 6.0) -> Optional[Any]:
        """Queries GitHub REST API endpoints with mirror failover and JSON decoding."""
        api_urls = [
            endpoint_url,
            f"https://ghfast.top/{endpoint_url}",
            f"https://gh-proxy.com/{endpoint_url}",
            f"https://gh.ddlc.top/{endpoint_url}",
            f"https://ghproxy.net/{endpoint_url}",
        ]

        for url in api_urls:
            # 1. Try curl
            if shutil.which("curl"):
                try:
                    curl_cmd = [
                        "curl", "-fsSL", "-k",
                        "--connect-timeout", "3",
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

                    curl_cmd.append(url)
                    res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout + 2.0)
                    if res.returncode == 0 and res.stdout.strip():
                        return json.loads(res.stdout)
                except Exception:
                    pass

            # 2. Try urllib fallback
            try:
                req = urllib.request.Request(
                    url,
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
                continue

        return None

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Calculates SHA-256 hash of a local file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
