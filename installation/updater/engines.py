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
from .downloader import Downloader


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
        self.downloader = Downloader(proxy_url=proxy_url)

        os.makedirs(self.bin_dir, exist_ok=True)

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
        data = self.downloader.fetch_github_api(f"https://api.github.com/repos/{repo}/releases/latest")
        if isinstance(data, dict):
            tag = data.get("tag_name")
            if tag:
                return tag
        return None

    def download_singbox(self, tag: Optional[str] = None) -> bool:
        """Downloads and installs Sing-box proxy engine binary into bot/bin/."""
        if not tag:
            tag = self.fetch_latest_release("SagerNet/sing-box")
            if not tag:
                tag = input("Не удалось определить версию Sing-box с GitHub. Введите тег версии (например v1.13.20): ").strip()
                if not tag:
                    log_error("Версия Sing-box не указана.")
                    return False

        if not tag.startswith("v") and not tag.startswith("V"):
            tag = "v" + tag

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
        data = self.downloader.download_bytes_with_mirrors(direct_url, label_for_log=filename)
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
                    try:
                        os.chmod(target_bin, 0o755)
                    except Exception:
                        pass
                log_success(f"Sing-box {tag} успешно установлен -> {target_bin}")
                return True
        except Exception as e:
            log_error(f"Ошибка распаковки Sing-box: {e}")
            return False

        return False

    def download_xray(self, tag: Optional[str] = None) -> bool:
        """Downloads and installs Xray-core proxy engine binary into bot/bin/."""
        if not tag:
            tag = self.fetch_latest_release("XTLS/Xray-core")
            if not tag:
                tag = input("Не удалось определить версию Xray-core с GitHub. Введите тег версии (например v26.3.27): ").strip()
                if not tag:
                    log_error("Версия Xray-core не указана.")
                    return False

        if not tag.startswith("v") and not tag.startswith("V"):
            tag = "v" + tag

        os_name, _, arch_xray = self._get_platform_info()
        log_info(f"Загрузка Xray-core {BOLD}{tag}{RESET} для {os_name}/{arch_xray}...")

        if os_name == "windows":
            filename = f"Xray-windows-{arch_xray}.zip"
        elif os_name == "darwin":
            filename = f"Xray-macos-{arch_xray}.zip"
        else:
            filename = f"Xray-linux-{arch_xray}.zip"

        direct_url = f"https://github.com/XTLS/Xray-core/releases/download/{tag}/{filename}"
        data = self.downloader.download_bytes_with_mirrors(direct_url, label_for_log=filename)
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

        sb_latest = self.fetch_latest_release("SagerNet/sing-box")
        xray_latest = self.fetch_latest_release("XTLS/Xray-core")

        log_banner("🚀  ВЫБОР PROXY / VPN ДВИЖКА (FAILOVER МОСТ)")
        sb_display = f"{GREEN}{sb_cur}{RESET}" if sb_cur else f"{RED}Не установлен{RESET}"
        xray_display = f"{GREEN}{xray_cur}{RESET}" if xray_cur else f"{RED}Не установлен{RESET}"

        sb_latest_disp = f"{CYAN}{sb_latest}{RESET}" if sb_latest else f"{YELLOW}Не определена{RESET}"
        xray_latest_disp = f"{CYAN}{xray_latest}{RESET}" if xray_latest else f"{YELLOW}Не определена{RESET}"

        print(f"📌 Текущее состояние:")
        print(f"  • Sing-box:  {sb_display} (Последняя на GitHub: {sb_latest_disp})")
        print(f"  • Xray-core: {xray_display} (Последняя на GitHub: {xray_latest_disp})")
        print("=" * 60)

        is_sb_installed = bool(sb_cur)
        default_choice = "4" if is_sb_installed else "1"

        sb_opt_label = f"Sing-box ({sb_latest})" if sb_latest else "Sing-box"
        xray_opt_label = f"Xray-core ({xray_latest})" if xray_latest else "Xray-core"

        if not is_sb_installed:
            print(f"  1) 🟢 Установить {sb_opt_label} [Рекомендуется / По умолчанию]")
            print(f"  2) 🟢 Установить {xray_opt_label}")
            print(f"  3) 🌐 Установить оба движка ({sb_opt_label} + {xray_opt_label})")
            print(f"  4) ⏹️  Пропустить установку движков")
        else:
            print(f"  1) 🔄 Обновить / переустановить {sb_opt_label}")
            print(f"  2) 🔄 Обновить / переустановить {xray_opt_label}")
            print(f"  3) 🌐 Установить / обновить оба движка")
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
