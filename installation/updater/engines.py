"""Sing-box & Xray-core Proxy Engine Manager for Sentinel Controller."""

from __future__ import annotations

import io
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from typing import Optional, Tuple

from .common import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    YELLOW,
    log_banner,
    log_error,
    log_info,
    log_success,
    log_warn,
)


class ProxyEngineManager:
    """Manages version detection, downloading and updating Sing-box and Xray-core proxy engines."""

    def __init__(
        self,
        project_dir: str,
        proxy_url: Optional[str] = None,
        auto_mode: bool = False,
    ) -> None:
        self.project_dir = project_dir
        self.bin_dir = os.path.join(project_dir, "bot", "bin")
        self.proxy_url = proxy_url
        self.auto_mode = auto_mode
        self.direct_github_blocked = False

        os.makedirs(self.bin_dir, exist_ok=True)

    def _build_opener(self) -> urllib.request.OpenerDirector:
        """Constructs an HTTP/HTTPS opener with proxy and SSL configuration."""
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

    def _get_platform_info(self) -> Tuple[str, str, str]:
        """Detects OS, Arch for singbox, and Arch for xray."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        os_name = "linux"
        if "darwin" in system:
            os_name = "darwin"
        elif "windows" in system:
            os_name = "windows"

        arch_singbox = "amd64"
        arch_xray = "64"

        if "aarch64" in machine or "arm64" in machine:
            arch_singbox = "arm64"
            arch_xray = "arm64-v8a"
        elif "armv7" in machine or "armhf" in machine:
            arch_singbox = "armv7"
            arch_xray = "arm32-v7a"
        elif "x86_64" in machine or "amd64" in machine:
            arch_singbox = "amd64"
            arch_xray = "64"

        return os_name, arch_singbox, arch_xray

    def get_installed_versions(self) -> Tuple[Optional[str], Optional[str]]:
        """Returns installed versions: (singbox_version, xray_version)."""
        sb_ver = None
        xray_ver = None

        # Sing-box
        sb_bin = os.path.join(self.bin_dir, "sing-box.exe" if platform.system() == "Windows" else "sing-box")
        if os.path.isfile(sb_bin):
            if platform.system() != "Windows":
                try:
                    os.chmod(sb_bin, 0o755)
                except Exception:
                    pass
            try:
                out = subprocess.check_output([sb_bin, "version"], stderr=subprocess.STDOUT, timeout=3).decode()
                m = re.search(r"sing-box version\s+([v\d\.\-]+)", out, re.IGNORECASE)
                if m:
                    sb_ver = m.group(1)
                else:
                    first_line = out.strip().split("\n")[0]
                    sb_ver = first_line.split()[2] if len(first_line.split()) > 2 else "установлен"
            except Exception:
                sb_ver = "установлен"

        # Xray-core
        xray_bin = os.path.join(self.bin_dir, "xray.exe" if platform.system() == "Windows" else "xray")
        if os.path.isfile(xray_bin):
            if platform.system() != "Windows":
                try:
                    os.chmod(xray_bin, 0o755)
                except Exception:
                    pass
            try:
                out = subprocess.check_output([xray_bin, "version"], stderr=subprocess.STDOUT, timeout=3).decode()
                m = re.search(r"Xray\s+([v\d\.\-]+)", out, re.IGNORECASE)
                if m:
                    xray_ver = m.group(1)
                else:
                    first_line = out.strip().split("\n")[0]
                    xray_ver = first_line.split()[1] if len(first_line.split()) > 1 else "установлен"
            except Exception:
                xray_ver = "установлен"

        return sb_ver, xray_ver

    def fetch_latest_release(self, repo: str) -> Optional[str]:
        """Queries GitHub API to find the latest release tag for a repository."""
        api_urls = [
            f"https://api.github.com/repos/{repo}/releases/latest",
            f"https://ghfast.top/https://api.github.com/repos/{repo}/releases/latest",
            f"https://gh-proxy.com/https://api.github.com/repos/{repo}/releases/latest",
            f"https://ghproxy.net/https://api.github.com/repos/{repo}/releases/latest",
        ]

        for url in api_urls:
            # 1. Try curl
            if shutil.which("curl"):
                try:
                    curl_cmd = [
                        "curl", "-fsSL", "-k",
                        "--connect-timeout", "4",
                        "--max-time", "8",
                        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "-H", "Accept: application/vnd.github.v3+json",
                    ]
                    if self.proxy_url:
                        p = self.proxy_url
                        if p.startswith("socks5://"):
                            p = "socks5h://" + p[len("socks5://"):]
                        curl_cmd.extend(["-x", p])
                    curl_cmd.append(url)
                    res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10.0)
                    if res.returncode == 0 and res.stdout.strip():
                        data = json.loads(res.stdout)
                        tag = data.get("tag_name")
                        if tag:
                            return tag
                except Exception:
                    pass

            # 2. Try urllib fallback
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                opener = self._build_opener()
                with opener.open(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        tag = data.get("tag_name")
                        if tag:
                            return tag
            except Exception:
                continue

        return None

    def _download_bytes(self, url: str) -> Optional[bytes]:
        """Downloads bytes from URL using curl or urllib fallback."""
        if shutil.which("curl"):
            try:
                curl_cmd = [
                    "curl", "-fsSL", "-k",
                    "--connect-timeout", "6",
                    "--max-time", "120",
                    "--retry", "1",
                    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ]
                if self.proxy_url:
                    p = self.proxy_url
                    if p.startswith("socks5://"):
                        p = "socks5h://" + p[len("socks5://"):]
                    curl_cmd.extend(["-x", p])
                curl_cmd.append(url)
                res = subprocess.run(curl_cmd, capture_output=True, timeout=125.0)
                if res.returncode == 0 and res.stdout and len(res.stdout) > 1024:
                    return res.stdout
            except Exception:
                pass

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            )
            opener = self._build_opener()
            with opener.open(req, timeout=35.0) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception:
            return None
        return None

    def _download_with_mirrors(self, direct_url: str) -> Optional[bytes]:
        """Downloads data with mirror failovers."""
        mirrors = [
            "",
            "https://gh-proxy.com/",
            "https://ghfast.top/",
            "https://gh.ddlc.top/",
            "https://ghproxy.net/",
        ]

        if self.direct_github_blocked and mirrors[0] == "":
            mirrors = mirrors[1:] + [""]

        for prefix in mirrors:
            full_url = f"{prefix}{direct_url}" if prefix else direct_url
            label = "Официальный GitHub" if not prefix else f"CDN-зеркало ({prefix.split('/')[2]})"
            log_info(f"  ➜ Загрузка из {label}...")
            data = self._download_bytes(full_url)
            if data and len(data) > 1024:
                return data
            if not prefix:
                self.direct_github_blocked = True

        return None

    def download_singbox(self, tag: Optional[str] = None) -> bool:
        """Downloads and installs Sing-box proxy engine binary into bot/bin/."""
        if not tag:
            tag = self.fetch_latest_release("SagerNet/sing-box") or "v1.11.4"

        clean_ver = tag.lstrip("v")
        os_name, arch_sb, _ = self._get_platform_info()

        log_info(f"Загрузка Sing-box {BOLD}{tag}{RESET} для {os_name}/{arch_sb}...")

        if os_name == "windows":
            filename = f"sing-box-{clean_ver}-windows-{arch_sb}.zip"
        elif os_name == "darwin":
            filename = f"sing-box-{clean_ver}-darwin-{arch_sb}.tar.gz"
        else:
            filename = f"sing-box-{clean_ver}-linux-{arch_sb}.tar.gz"

        direct_url = f"https://github.com/SagerNet/sing-box/releases/download/{tag}/{filename}"
        data = self._download_with_mirrors(direct_url)
        if not data:
            log_error(f"Не удалось загрузить архив Sing-box {filename}")
            return False

        target_bin = os.path.join(self.bin_dir, "sing-box.exe" if os_name == "windows" else "sing-box")

        try:
            if filename.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    for member in zf.namelist():
                        if member.endswith("sing-box") or member.endswith("sing-box.exe"):
                            with zf.open(member) as src, open(target_bin, "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            break
            else:
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                    for member in tf.getmembers():
                        if member.name.endswith("sing-box") or member.name.endswith("sing-box.exe"):
                            f = tf.extractfile(member)
                            if f:
                                with open(target_bin, "wb") as dst:
                                    shutil.copyfileobj(f, dst)
                                break

            if os.path.isfile(target_bin) and os.path.getsize(target_bin) > 0:
                if os_name != "windows":
                    os.chmod(target_bin, 0o755)
                log_success(f"Sing-box {tag} успешно установлен -> {target_bin}")
                return True
        except Exception as e:
            log_error(f"Ошибка распаковки Sing-box: {e}")
            return False

        return False

    def download_xray(self, tag: Optional[str] = None) -> bool:
        """Downloads and installs Xray-core proxy engine binary into bot/bin/."""
        if not tag:
            tag = self.fetch_latest_release("XTLS/Xray-core") or "v1.8.24"

        os_name, _, arch_xray = self._get_platform_info()
        log_info(f"Загрузка Xray-core {BOLD}{tag}{RESET} для {os_name}/{arch_xray}...")

        if os_name == "windows":
            filename = f"Xray-windows-{arch_xray}.zip"
        elif os_name == "darwin":
            filename = f"Xray-macos-{arch_xray}.zip"
        else:
            filename = f"Xray-linux-{arch_xray}.zip"

        direct_url = f"https://github.com/XTLS/Xray-core/releases/download/{tag}/{filename}"
        data = self._download_with_mirrors(direct_url)
        if not data:
            log_error(f"Не удалось загрузить архив Xray-core {filename}")
            return False

        target_bin = os.path.join(self.bin_dir, "xray.exe" if os_name == "windows" else "xray")

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for member in zf.namelist():
                    base = os.path.basename(member)
                    if base in ["xray", "xray.exe", "geoip.dat", "geosite.dat"]:
                        target_file = os.path.join(self.bin_dir, base)
                        with zf.open(member) as src, open(target_file, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        if base in ["xray", "xray.exe"] and os_name != "windows":
                            os.chmod(target_file, 0o755)

            if os.path.isfile(target_bin) and os.path.getsize(target_bin) > 0:
                log_success(f"Xray-core {tag} успешно установлен -> {target_bin}")
                return True
        except Exception as e:
            log_error(f"Ошибка распаковки Xray-core: {e}")
            return False

        return False

    def manage_engines(self) -> None:
        """Interactive or automated menu for managing Sing-box and Xray-core proxy engines."""
        sb_cur, xray_cur = self.get_installed_versions()

        # In non-interactive auto mode: ensure at least Sing-box is installed
        if not sys.stdin.isatty() or self.auto_mode:
            if not sb_cur:
                log_info("Sing-box не обнаружен. Автоматическая загрузка...")
                self.download_singbox()
            return

        sb_latest = self.fetch_latest_release("SagerNet/sing-box") or "v1.11.4"
        xray_latest = self.fetch_latest_release("XTLS/Xray-core") or "v1.8.24"

        log_banner("🚀  ВЫБОР PROXY / VPN ДВИЖКА (FAILOVER МОСТ)")
        sb_display = f"{GREEN}{sb_cur}{RESET}" if sb_cur else f"{RED}Не установлен{RESET}"
        xray_display = f"{GREEN}{xray_cur}{RESET}" if xray_cur else f"{RED}Не установлен{RESET}"

        print(f"📌 Текущее состояние:")
        print(f"  • Sing-box:  {sb_display} (Последняя: {CYAN}{sb_latest}{RESET})")
        print(f"  • Xray-core: {xray_display} (Последняя: {CYAN}{xray_latest}{RESET})")
        print("=" * 60)

        is_sb_installed = bool(sb_cur)
        default_choice = "4" if is_sb_installed else "1"

        if not is_sb_installed:
            print(f"  1) 🟢 Установить Sing-box ({sb_latest}) [Рекомендуется / По умолчанию]")
            print(f"  2) 🟢 Установить Xray-core ({xray_latest})")
            print(f"  3) 🌐 Установить оба движка (Sing-box + Xray-core)")
            print(f"  4) ⏹️  Пропустить установку движков")
        else:
            print(f"  1) 🔄 Обновить / переустановить Sing-box ({sb_latest})")
            print(f"  2) 🔄 Обновить / переустановить Xray-core ({xray_latest})")
            print(f"  3) 🌐 Установить / обновить оба движка (Sing-box + Xray-core)")
            print(f"  4) ⏹️  Оставить текущие версии [По умолчанию / Пропустить]")

        while True:
            try:
                raw = input(f"Выберите вариант [1-4] (по умолчанию {default_choice}): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("")
                raw = default_choice
            choice = re.sub(r"[^1-4]", "", raw) or default_choice

            if choice == "1":
                self.download_singbox(sb_latest)
                break
            elif choice == "2":
                self.download_xray(xray_latest)
                break
            elif choice == "3":
                self.download_singbox(sb_latest)
                self.download_xray(xray_latest)
                break
            elif choice == "4":
                log_info("Обновление прокси-движков пропущено.")
                break
