"""Sentinel-Core & Proxy Engines Downloader and Manager for Sentinel Controller."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from typing import Dict, List, Optional, Tuple

from .common import (
    BOLD,
    CYAN,
    DIM,
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


class CoreManager:
    """Manages querying GitHub releases, downloading binaries & shared libraries, and verifying digests."""

    REPO = "blackalex1/sentinel-core"

    def __init__(self, project_dir: str, proxy_url: Optional[str] = None, auto_mode: bool = False, force: bool = False) -> None:
        self.project_dir = project_dir
        self.bin_dir = os.path.join(project_dir, "bot", "bin")
        self.proxy_url = proxy_url
        self.auto_mode = auto_mode
        self.force = force
        self.direct_github_blocked = False

        os.makedirs(self.bin_dir, exist_ok=True)

    def _get_installed_version(self) -> Tuple[bool, str]:
        """Detects currently installed core version via binary CLI or C-shared library FFI."""
        exe_path = os.path.join(self.bin_dir, "sentinel-core")
        if platform.system() == "Windows":
            exe_path += ".exe"

        if os.path.isfile(exe_path):
            if platform.system() != "Windows":
                try:
                    os.chmod(exe_path, 0o755)
                except Exception:
                    pass
            for arg in ["version", "--version", "-v"]:
                try:
                    out = subprocess.check_output([exe_path, arg], stderr=subprocess.STDOUT, timeout=3).decode().strip()
                    match = re.search(r"v\d+\.\d+(\.\d+)?(-[a-zA-Z0-9.]+)?", out)
                    if match:
                        return True, match.group(0)
                    if out:
                        return True, out
                except Exception:
                    continue

        # Try shared library FFI
        _, _, ext = self._get_platform_info()
        so_path = os.path.join(self.bin_dir, f"libsentinel-core{ext}")
        if not os.path.isfile(so_path):
            so_path = os.path.join(self.bin_dir, "libsentinel-core.so")

        if os.path.isfile(so_path):
            try:
                ffi_cmd = [
                    sys.executable, "-c",
                    f'import ctypes, re; lib = ctypes.CDLL("{so_path}"); lib.SentinelGetEngineVersion.restype = ctypes.c_char_p; v = lib.SentinelGetEngineVersion().decode("utf-8").strip(); print("v" + v if re.match(r"^\\d+\\.\\d+", v) else v)'
                ]
                v_out = subprocess.check_output(ffi_cmd, stderr=subprocess.DEVNULL, timeout=2).decode().strip()
                if v_out:
                    return True, v_out
            except Exception:
                pass
            return True, "Установлена (.so найдена)"

        return False, "Не установлена"

    def _fetch_releases(self) -> Tuple[str, str, str]:
        """Queries GitHub API (via proxy or mirrors) and returns (stable_ver, prerelease_ver, latest_any)."""
        log_info(f"Опрос GitHub Releases для {self.REPO}...")

        api_urls = [
            f"https://api.github.com/repos/{self.REPO}/releases",
            f"https://gh-proxy.com/https://api.github.com/repos/{self.REPO}/releases",
            f"https://ghfast.top/https://api.github.com/repos/{self.REPO}/releases",
            f"https://gh.ddlc.top/https://api.github.com/repos/{self.REPO}/releases",
        ]

        for url in api_urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Sentinel-Controller-Updater/1.0",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                opener = self._build_opener()
                with opener.open(req, timeout=6.0) as resp:
                    if resp.status == 200:
                        data = resp.read().decode("utf-8")
                        releases = json.loads(data)
                        if not releases or not isinstance(releases, list):
                            continue

                        stable = next((r["tag_name"] for r in releases if not r.get("prerelease")), "")
                        prerelease = releases[0]["tag_name"] if releases[0].get("prerelease") else ""
                        latest_any = releases[0]["tag_name"]
                        return stable, prerelease, latest_any
            except Exception:
                continue

        # Fallback to curl if available
        if shutil.which("curl"):
            for url in api_urls:
                try:
                    curl_cmd = ["curl", "-fsSL", "-k", "--connect-timeout", "4", "--max-time", "8", "-H", "User-Agent: Sentinel-Controller-Updater/1.0", "-H", "Accept: application/vnd.github.v3+json"]
                    if self.proxy_url:
                        p = self.proxy_url
                        if p.startswith("socks5://"):
                            p = "socks5h://" + p[len("socks5://"):]
                        curl_cmd.extend(["-x", p])
                    curl_cmd.append(url)
                    res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=9.0)
                    if res.returncode == 0 and res.stdout.strip():
                        releases = json.loads(res.stdout)
                        if isinstance(releases, list) and len(releases) > 0:
                            stable = next((r["tag_name"] for r in releases if not r.get("prerelease")), "")
                            prerelease = releases[0]["tag_name"] if releases[0].get("prerelease") else ""
                            latest_any = releases[0]["tag_name"]
                            return stable, prerelease, latest_any
                except Exception:
                    continue

        # Fallback to git ls-remote via mirrors
        if shutil.which("git"):
            remotes = [
                f"https://github.com/{self.REPO}.git",
                f"https://ghfast.top/https://github.com/{self.REPO}.git",
                f"https://gh-proxy.com/https://github.com/{self.REPO}.git",
                f"https://ghproxy.net/https://github.com/{self.REPO}.git",
            ]
            for remote in remotes:
                try:
                    cmd = ["git", "-c", "http.connectTimeout=4", "-c", "http.timeout=8", "ls-remote", "--tags", remote]
                    env = os.environ.copy()
                    if self.proxy_url:
                        env["http_proxy"] = self.proxy_url
                        env["https_proxy"] = self.proxy_url
                        env["all_proxy"] = self.proxy_url
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=9.0, env=env)
                    if res.returncode == 0 and res.stdout.strip():
                        tags = []
                        for line in res.stdout.splitlines():
                            parts = line.strip().split()
                            if len(parts) == 2 and "refs/tags/" in parts[1]:
                                raw_t = parts[1].split("refs/tags/")[1]
                                if not raw_t.endswith("^{}"):
                                    tags.append(raw_t)
                        if tags:
                            def _ver_key(v: str):
                                nums = [int(x) for x in re.findall(r"\d+", v)]
                                return nums or [0]
                            tags.sort(key=_ver_key, reverse=True)
                            stable = next((t for t in tags if not any(x in t.lower() for x in ["beta", "alpha", "rc", "dev", "pre"])), "")
                            prerelease = next((t for t in tags if any(x in t.lower() for x in ["beta", "alpha", "rc", "dev", "pre"])), "")
                            latest_any = tags[0]
                            return stable, prerelease, latest_any
                except Exception:
                    continue

        return "", "", ""

    def select_version(self) -> Optional[str]:
        """Runs the interactive or automated version selector."""
        is_installed, current_ver = self._get_installed_version()
        stable_ver, prerelease_ver, latest_any = self._fetch_releases()

        fallback_default = "v0.0.1"
        current_tag_match = re.search(r"v\d+\.\d+(\.\d+)?(-[a-zA-Z0-9.]+)?", current_ver)
        if current_tag_match:
            fallback_default = current_tag_match.group(0)

        # Non-interactive automated mode
        if not sys.stdin.isatty() or self.auto_mode:
            target = stable_ver or prerelease_ver or latest_any or fallback_default
            if not self.force and is_installed and target in current_ver:
                log_info(f"Текущая версия ядра ({current_ver}) уже актуальна ({target}). Обновление не требуется.")
                return None
            return target

        log_banner("🛡️  ВЫБОР ВЕРСИИ ЯДРА SENTINEL-CORE")
        print(f"📌 Текущая версия:              {BOLD}{current_ver}{RESET}")
        print(f"🟢 Последняя стабильная (Stable): {GREEN}{stable_ver or fallback_default}{RESET}")
        print(f"🟡 Пре-релиз / Бета (Pre-release): {YELLOW}{prerelease_ver or 'Отсутствует'}{RESET}")
        print("=" * 60)

        current_tag = current_tag_match.group(0) if current_tag_match else ""
        is_up_to_date = bool(is_installed and (stable_ver or fallback_default) and current_tag == (stable_ver or fallback_default))

        if prerelease_ver and stable_ver:
            if not is_up_to_date:
                default_choice = "1"
                print(f"  1) 🟢 Установить стабильную версию ({stable_ver}) [Рекомендуется / По умолчанию]")
                print(f"  2) 🟡 Установить пре-релиз / бету ({prerelease_ver}) [Экспериментальная]")
                print(f"  3) ⏹️  Оставить текущую версию (пропустить)")
            else:
                default_choice = "3"
                print(f"  1) 🟢 Переустановить стабильную версию ({stable_ver})")
                print(f"  2) 🟡 Установить пре-релиз / бету ({prerelease_ver}) [Экспериментальная]")
                print(f"  3) ⏹️  Оставить текущую версию ({stable_ver}) [По умолчанию / Актуально]")
            print(f"  4) ✏️  Ввести тег/версию вручную")

            while True:
                try:
                    raw = input(f"Выберите вариант [1-4] (по умолчанию {default_choice}): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("")
                    raw = default_choice
                choice = re.sub(r"[^1-4]", "", raw) or default_choice
                if choice == "1":
                    return stable_ver
                elif choice == "2":
                    return prerelease_ver
                elif choice == "3":
                    log_info("Обновление ядра пропущено.")
                    return None
                elif choice == "4":
                    while True:
                        custom_tag = input(f"Введите точный тег версии (например {fallback_default}): ").strip()
                        if custom_tag:
                            if not custom_tag.startswith("v"):
                                custom_tag = "v" + custom_tag
                            return custom_tag
        else:
            active_ver = stable_ver or latest_any or fallback_default
            if not is_up_to_date:
                default_choice = "1"
                print(f"  1) 🟢 Установить последнюю версию ({active_ver}) [Рекомендуется / По умолчанию]")
                print(f"  2) ⏹️  Оставить текущую версию (пропустить)")
            else:
                default_choice = "2"
                print(f"  1) 🟢 Переустановить версию ({active_ver})")
                print(f"  2) ⏹️  Оставить текущую версию ({active_ver}) [По умолчанию / Актуально]")
            print(f"  3) ✏️  Ввести тег/версию вручную")

            while True:
                try:
                    raw = input(f"Выберите вариант [1-3] (по умолчанию {default_choice}): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("")
                    raw = default_choice
                choice = re.sub(r"[^1-3]", "", raw) or default_choice
                if choice == "1":
                    return active_ver
                elif choice == "2":
                    log_info("Обновление ядра пропущено.")
                    return None
                elif choice == "3":
                    while True:
                        custom_tag = input("Введите точный тег версии (например v0.0.8): ").strip()
                        if custom_tag:
                            if not custom_tag.startswith("v"):
                                custom_tag = "v" + custom_tag
                            return custom_tag

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
        """Detects OS, Arch, and dynamic library extension."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        os_name = "linux"
        if "darwin" in system:
            os_name = "darwin"
        elif "windows" in system:
            os_name = "windows"

        arch = "amd64"
        if "aarch64" in machine or "arm64" in machine:
            arch = "arm64"
        elif "arm" in machine:
            arch = "armv7"
        elif "x86_64" in machine or "amd64" in machine:
            arch = "amd64"

        ext = ".so"
        if os_name == "windows":
            ext = ".dll"
        elif os_name == "darwin":
            ext = ".dylib"

        return os_name, arch, ext

    def _download_file(self, url: str, dest: str) -> bool:
        """Downloads a single file from URL to destination path using atomic temp replacement."""
        tmp_dest = f"{dest}.tmp.{os.getpid()}"
        
        # 1. Try curl if available (handles Cloudflare, HTTP/2, redirects and SNI reliably)
        if shutil.which("curl"):
            try:
                curl_cmd = [
                    "curl", "-fsSL", "-k",
                    "--connect-timeout", "6",
                    "--max-time", "60",
                    "--retry", "1",
                    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
                res = subprocess.run(curl_cmd, capture_output=True, timeout=65.0)
                if res.returncode == 0 and os.path.isfile(tmp_dest) and os.path.getsize(tmp_dest) > 0:
                    if os.name != "nt":
                        os.chmod(tmp_dest, 0o755)
                    os.replace(tmp_dest, dest)
                    return True
            except Exception:
                pass

        # 2. Fallback to urllib.request
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            )
            opener = self._build_opener()
            with opener.open(req, timeout=30.0) as resp:
                if resp.status == 200:
                    with open(tmp_dest, "wb") as f:
                        shutil.copyfileobj(resp, f)
                    if os.path.isfile(tmp_dest) and os.path.getsize(tmp_dest) > 0:
                        if os.name != "nt":
                            os.chmod(tmp_dest, 0o755)
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

    def _download_with_fallback(self, base_url: str, dest_path: str, filename: str) -> bool:
        """Downloads a file with automatic failover to CDN proxy mirrors."""
        mirror_prefixes = [
            "",  # Direct GitHub
            "https://ghfast.top/",
            "https://gh-proxy.com/",
            "https://gh.ddlc.top/",
            "https://ghproxy.net/",
        ]

        for prefix in mirror_prefixes:
            full_url = f"{prefix}{base_url}" if prefix else base_url
            source_label = "Официальный GitHub" if not prefix else f"CDN-зеркало ({prefix.split('/')[2]})"

            log_info(f"  ➜ Попытка загрузки {filename} из {source_label}...")
            ok = self._download_file(full_url, dest_path)
            if ok and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 0:
                return True

            if not prefix:
                self.direct_github_blocked = True

        return False

    def _compute_sha256(self, file_path: str) -> str:
        """Calculates SHA-256 hash of a local file."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def _fetch_release_digests(self, tag: str) -> Dict[str, str]:
        """Fetches native asset SHA-256 digests from GitHub release metadata."""
        api_urls = [
            f"https://api.github.com/repos/{self.REPO}/releases/tags/{tag}",
            f"https://gh-proxy.com/https://api.github.com/repos/{self.REPO}/releases/tags/{tag}",
            f"https://ghfast.top/https://api.github.com/repos/{self.REPO}/releases/tags/{tag}",
            f"https://gh.ddlc.top/https://api.github.com/repos/{self.REPO}/releases/tags/{tag}",
        ]
        if tag == "latest":
            api_urls = [f"https://api.github.com/repos/{self.REPO}/releases/latest"] + [f"{m}https://api.github.com/repos/{self.REPO}/releases/latest" for m in ["https://gh-proxy.com/", "https://ghfast.top/", "https://gh.ddlc.top/"]]

        for url in api_urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Sentinel-Controller-Updater/1.0",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                opener = self._build_opener()
                with opener.open(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        checksum_map: Dict[str, str] = {}
                        for a in data.get("assets", []):
                            name = a.get("name")
                            digest = a.get("digest", "")
                            if name and digest:
                                if ":" in digest:
                                    digest = digest.split(":", 1)[1]
                                checksum_map[name] = digest
                        if checksum_map:
                            return checksum_map
            except Exception:
                continue
        return {}

    def download_core(self, tag: str) -> bool:
        """Downloads sentinel-core binary, shared library, and C-header."""
        log_info(f"Загрузка компонентов Sentinel-Core версии {BOLD}{tag}{RESET}...")

        os_name, arch, lib_ext = self._get_platform_info()
        base_release_url = f"https://github.com/{self.REPO}/releases/download/{tag}"

        # Fetch native SHA-256 digests directly from GitHub Release metadata
        checksum_map = self._fetch_release_digests(tag)

        exe_suffix = ".exe" if os_name == "windows" else ""
        bin_asset = f"sentinel-core-{os_name}-{arch}{exe_suffix}"
        lib_asset = f"libsentinel-core-{os_name}-{arch}{lib_ext}"
        header_asset = "sentinel-core.h"

        target_bin = os.path.join(self.bin_dir, f"sentinel-core{exe_suffix}")
        target_lib = os.path.join(self.bin_dir, f"libsentinel-core{lib_ext}")
        target_header = os.path.join(self.bin_dir, header_asset)

        # Download Binary
        bin_ok = self._download_with_fallback(f"{base_release_url}/{bin_asset}", target_bin, bin_asset)
        if bin_ok:
            if os_name != "windows":
                os.chmod(target_bin, 0o755)
            if bin_asset in checksum_map:
                actual = self._compute_sha256(target_bin)
                if actual.lower() == checksum_map[bin_asset].lower():
                    log_success(f"SHA-256 проверен ({actual[:16]}...)")
                else:
                    log_warn(f"Несовпадение SHA-256 для {bin_asset}!")
            log_success(f"Успешно установлен {bin_asset} -> {target_bin}")
        else:
            log_error(f"Не удалось загрузить бинарник {bin_asset}")

        # Download Shared Library
        lib_ok = self._download_with_fallback(f"{base_release_url}/{lib_asset}", target_lib, lib_asset)
        if lib_ok:
            if os_name != "windows":
                os.chmod(target_lib, 0o755)
            if lib_asset in checksum_map:
                actual = self._compute_sha256(target_lib)
                if actual.lower() == checksum_map[lib_asset].lower():
                    log_success(f"SHA-256 проверен ({actual[:16]}...)")
                else:
                    log_warn(f"Несовпадение SHA-256 для {lib_asset}!")
            log_success(f"Успешно установлен {lib_asset} -> {target_lib}")
        else:
            log_warn(f"Shared library {lib_asset} не была загружена.")

        # Download Header
        header_ok = self._download_with_fallback(f"{base_release_url}/{header_asset}", target_header, header_asset)
        if header_ok:
            log_success(f"Успешно установлен {header_asset} -> {target_header}")

        return bin_ok
