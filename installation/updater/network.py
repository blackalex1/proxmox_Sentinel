"""Network, Proxy & VPN Rotator Manager for Sentinel Controller Updater."""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from typing import Dict, Optional

from .common import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    RESET,
    YELLOW,
    free_port,
    log_banner,
    log_error,
    log_info,
    log_success,
    log_warn,
)


class NetworkManager:
    """Manages VPN rotator tunnel and external HTTP/SOCKS5 proxy settings for Controller."""

    def __init__(self, project_dir: str, proxy_arg: Optional[str] = None, no_proxy: bool = False, auto_mode: bool = False) -> None:
        self.project_dir = project_dir
        self.custom_proxy: Optional[str] = proxy_arg
        self.no_proxy: bool = no_proxy
        self.auto_mode: bool = auto_mode
        self.use_rotator: bool = True if not (no_proxy or proxy_arg) else False
        self.rotator_proc: Optional[subprocess.Popen] = None
        self.active_proxy_url: Optional[str] = None

        self._init_proxy_from_env()

    def _init_proxy_from_env(self) -> None:
        """Reads PROXY_URL from config or environment if not explicitly set."""
        if not self.custom_proxy and not self.no_proxy:
            env_paths = [
                os.path.join(self.project_dir, "bot", "config", ".env"),
                os.path.join(self.project_dir, ".env"),
                os.path.join(self.project_dir, "config", ".env"),
            ]
            for p in env_paths:
                if os.path.isfile(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith("PROXY_URL="):
                                    val = line.split("=", 1)[1].strip(" '\"")
                                    if val:
                                        self.custom_proxy = val
                                        break
                    except Exception:
                        pass
                if self.custom_proxy:
                    break

    def show_menu(self) -> None:
        """Displays interactive network selection menu if interactive TTY."""
        if not sys.stdin.isatty() or self.auto_mode or self.no_proxy or self.custom_proxy:
            return

        log_banner("🌐 НАСТРОЙКА СЕТИ И ПРОКСИ ДЛЯ ОБНОВЛЕНИЯ КОНТРОЛЛЕРА")
        print("Выберите режим подключения к GitHub для загрузки релизов:")
        print(f"  1) {GREEN}🟢 Автоматический VPN / Прокси ротатор{RESET} [Рекомендуется / По умолчанию]")
        print(f"  2) 🌐 Прямое соединение к GitHub (с авто-фолбэком на CDN-зеркала при блокировке)")
        print(f"  3) 🔌 Использовать существующий HTTP / SOCKS5 прокси\n")

        while True:
            try:
                raw_choice = input(f"Выберите вариант [1-3] (по умолчанию 1): ")
            except (EOFError, KeyboardInterrupt):
                print("")
                raw_choice = "1"

            choice = re.sub(r"[^1-3]", "", raw_choice.strip()) or "1" if raw_choice.strip() == "" else re.sub(r"[^1-3]", "", raw_choice.strip())

            if choice == "1":
                self.use_rotator = True
                self.no_proxy = False
                break
            elif choice == "2":
                self.use_rotator = False
                self.no_proxy = True
                break
            elif choice == "3":
                self.use_rotator = False
                self.no_proxy = False
                while True:
                    p_input = input("Введите адрес прокси (например socks5://127.0.0.1:10808): ").strip()
                    if re.match(r"^(http|https|socks4|socks5|socks5h)://", p_input, re.IGNORECASE):
                        self.custom_proxy = p_input
                        break
                    print(f"{RED}Неверный формат URL прокси. Повторите ввод.{RESET}")
                break

    def setup_network(self) -> Optional[str]:
        """Activates chosen proxy mode or starts automated failover rotator."""
        if self.no_proxy:
            log_info("Используется прямое сетевое подключение к GitHub (с CDN-зеркалами при блокировке).")
            return None

        if self.custom_proxy:
            self.active_proxy_url = self.custom_proxy
            log_info(f"Используется указанный прокси: {self.active_proxy_url}")
            return self.active_proxy_url

        if not self.use_rotator:
            return None

        # Start automated VPN Rotator
        log_info("Запуск Sentinel Proxy Rotator для поиска рабочего VPN...")
        self.cleanup()

        # Find python executable inside bot venv or host
        py_bin = sys.executable
        venv_py = os.path.join(self.project_dir, "bot", "venv", "bin", "python")
        if os.path.isfile(venv_py):
            py_bin = venv_py

        rotator_script = (
            "import sys, os, asyncio\n"
            "bot_dir = os.path.join(os.getcwd(), 'bot')\n"
            "if bot_dir not in sys.path: sys.path.insert(0, bot_dir)\n"
            "from core.proxy_rotator import start_rotator_foreground\n"
            "asyncio.run(start_rotator_foreground(port=10818, auto_rotate=False))\n"
        )

        try:
            extra_kwargs = {}
            if sys.platform != "win32":
                extra_kwargs["preexec_fn"] = os.setsid

            self.rotator_proc = subprocess.Popen(
                [py_bin, "-u", "-c", rotator_script],
                cwd=self.project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                bufsize=1,
                **extra_kwargs
            )
        except Exception as e:
            log_warn(f"Не удалось запустить процесс ротатора: {e}")
            return None

        start_time = time.time()
        timeout = 90.0

        while time.time() - start_time < timeout:
            if self.rotator_proc.poll() is not None:
                log_error("Процесс ротатора завершился до установления соединения.")
                break

            line = self.rotator_proc.stdout.readline() if self.rotator_proc.stdout else ""
            if line:
                line_str = line.strip()
                if "PROXY_READY:" in line_str:
                    self.active_proxy_url = line_str.split("PROXY_READY:", 1)[1].strip()
                    log_success(f"VPN-туннель успешно поднят на {self.active_proxy_url}!")
                    return self.active_proxy_url
                elif any(k in line_str for k in ("[INFO]", "[Failover]", "[singbox]", "Tier", "nodes alive", "Best:", "singbox")):
                    print(f"    {line_str}", flush=True)

            time.sleep(0.05)

        log_warn("Превышено время ожидания ответа от VPN-нод. Продолжаем обновление без ротатора...")
        self.cleanup()
        return None

    def get_env_dict(self) -> Dict[str, str]:
        """Returns environment dictionary configured with the active proxy."""
        env: Dict[str, str] = {}
        if self.active_proxy_url:
            env["http_proxy"] = self.active_proxy_url
            env["https_proxy"] = self.active_proxy_url
            env["all_proxy"] = self.active_proxy_url
            env["HTTP_PROXY"] = self.active_proxy_url
            env["HTTPS_PROXY"] = self.active_proxy_url
            env["ALL_PROXY"] = self.active_proxy_url
        return env

    def cleanup(self) -> None:
        """Terminates any background rotator process and frees proxy ports."""
        if self.rotator_proc:
            try:
                if sys.platform != "win32":
                    try:
                        os.killpg(os.getpgid(self.rotator_proc.pid), signal.SIGTERM)
                    except Exception:
                        self.rotator_proc.terminate()
                else:
                    self.rotator_proc.terminate()
                self.rotator_proc.wait(timeout=1.5)
            except Exception:
                try:
                    if sys.platform != "win32":
                        try:
                            os.killpg(os.getpgid(self.rotator_proc.pid), signal.SIGKILL)
                        except Exception:
                            self.rotator_proc.kill()
                    else:
                        self.rotator_proc.kill()
                except Exception:
                    pass
            self.rotator_proc = None

        try:
            if sys.platform != "win32":
                subprocess.run(["pkill", "-9", "-f", "singbox_failover.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-9", "-f", "xray_failover.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        free_port(10818)
        free_port(10819)
