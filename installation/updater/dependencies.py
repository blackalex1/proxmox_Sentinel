"""Python Dependencies & Virtual Environment Manager for Sentinel Controller."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Dict, Optional

from .common import (
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    log_error,
    log_info,
    log_success,
    log_warn,
    run_command,
)


class DependencyManager:
    """Manages Python virtual environments and package installations (uv / pip)."""

    def __init__(self, project_dir: str, proxy_url: Optional[str] = None) -> None:
        self.project_dir = project_dir
        self.venv_dir = os.path.join(project_dir, "bot", "venv")
        self.requirements_path = os.path.join(project_dir, "bot", "requirements.txt")
        self.proxy_url = proxy_url

    def _ensure_venv(self) -> str:
        """Ensures virtual environment exists, creating one if needed."""
        py_bin = os.path.join(self.venv_dir, "bin", "python")
        if sys.platform == "win32":
            py_bin = os.path.join(self.venv_dir, "Scripts", "python.exe")

        if not os.path.isfile(py_bin):
            log_info(f"Создание виртуального окружения Python: {self.venv_dir}...")
            os.makedirs(os.path.dirname(self.venv_dir), exist_ok=True)
            run_command([sys.executable, "-m", "venv", self.venv_dir], cwd=self.project_dir, check=True)

        return py_bin

    def update_dependencies(self) -> bool:
        """Updates Python dependencies using uv (fast) or pip."""
        if not os.path.isfile(self.requirements_path):
            log_warn(f"Файл {self.requirements_path} не найден. Пропуск обновления зависимостей.")
            return True

        py_bin = self._ensure_venv()

        log_info("Обновление зависимостей Python (bot/requirements.txt)...")

        env_dict: Dict[str, str] = {}
        if self.proxy_url:
            env_dict["http_proxy"] = self.proxy_url
            env_dict["https_proxy"] = self.proxy_url
            env_dict["HTTP_PROXY"] = self.proxy_url
            env_dict["HTTPS_PROXY"] = self.proxy_url

        # Check for uv binary
        uv_bin = shutil.which("uv")
        if not uv_bin:
            for cand in [
                os.path.expanduser("~/.local/bin/uv"),
                os.path.expanduser("~/.cargo/bin/uv"),
                "/root/.local/bin/uv",
                "/usr/local/bin/uv",
            ]:
                if os.path.isfile(cand):
                    uv_bin = cand
                    break

        if uv_bin:
            try:
                log_info(f"Использование uv для быстрой установки зависимостей ({uv_bin})...")
                # Avoid unnecessary --upgrade queries on direct connection to prevent PyPI timeouts
                uv_cmd = [
                    uv_bin, "pip", "install",
                    "--python", self.venv_dir,
                    "-r", self.requirements_path
                ]
                if not self.proxy_url:
                    uv_cmd.extend(["--extra-index-url", "https://mirror.yandex.ru/pypi/simple"])

                res = run_command(
                    uv_cmd,
                    cwd=self.project_dir,
                    env=env_dict,
                    check=False,
                )
                if res.returncode == 0:
                    log_success("Зависимости Python успешно обновлены через uv!")
                    return True
            except Exception as e:
                log_warn(f"Сбой установки через uv: {e}. Переключение на стандартный pip...")

        # Fallback to pip
        pip_bin = os.path.join(self.venv_dir, "bin", "pip")
        if sys.platform == "win32":
            pip_bin = os.path.join(self.venv_dir, "Scripts", "pip.exe")

        pip_cmd = [pip_bin] if os.path.isfile(pip_bin) else [py_bin, "-m", "pip"]

        try:
            pip_args = pip_cmd + ["install", "--default-timeout=15", "-r", self.requirements_path]
            if not self.proxy_url:
                pip_args.extend(["--extra-index-url", "https://mirror.yandex.ru/pypi/simple"])

            res = run_command(pip_args, cwd=self.project_dir, env=env_dict, check=False)
            if res.returncode == 0:
                log_success("Зависимости Python успешно обновлены через pip!")
                return True
            else:
                log_error("Ошибка при обновлении зависимостей через pip.")
                return False
        except Exception as e:
            log_error(f"Не удалось обновить зависимости Python: {e}")
            return False
