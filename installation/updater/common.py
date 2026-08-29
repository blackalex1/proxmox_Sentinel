"""Common CLI styles, helpers and port management for Sentinel Controller Updater."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from typing import Dict, List, Optional, Union

# ANSI Color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[0;32m"
BOLD_GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD_RED = "\033[1;31m"
CYAN = "\033[0;36m"
BOLD_CYAN = "\033[1;36m"
MAGENTA = "\033[0;35m"
BLUE = "\033[0;34m"
WHITE = "\033[1;37m"


def log_info(msg: str) -> None:
    print(f"{CYAN}[+]{RESET} {msg}", flush=True)


def log_success(msg: str) -> None:
    print(f"{GREEN}[✓]{RESET} {BOLD_GREEN}{msg}{RESET}", flush=True)


def log_warn(msg: str) -> None:
    print(f"{YELLOW}[!]{RESET} {msg}", flush=True)


def log_error(msg: str) -> None:
    print(f"{RED}[✗]{RESET} {BOLD_RED}{msg}{RESET}", file=sys.stderr, flush=True)


def log_banner(title: str) -> None:
    sep = "=" * 60
    print(f"\n{BOLD_CYAN}{sep}{RESET}")
    print(f"{BOLD_CYAN}{title}{RESET}")
    print(f"{BOLD_CYAN}{sep}{RESET}\n", flush=True)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a TCP port is currently open and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def free_port(port: int) -> None:
    """Forcefully frees a TCP port on Linux/Unix using fuser, lsof or ss."""
    if sys.platform == "win32":
        return

    if not is_port_in_use(port):
        return

    # 1. fuser -k
    if shutil.which("fuser"):
        subprocess.run(["fuser", "-k", f"{port}/tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.3)
        if not is_port_in_use(port):
            return

    # 2. lsof -t -i :port
    if shutil.which("lsof"):
        try:
            pids = subprocess.check_output(["lsof", "-t", f"-i:{port}"], stderr=subprocess.DEVNULL).decode().strip().split()
            for pid in pids:
                if pid and pid.isdigit():
                    subprocess.run(["kill", "-9", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        time.sleep(0.3)
        if not is_port_in_use(port):
            return

    # 3. ss -lptn
    if shutil.which("ss"):
        try:
            out = subprocess.check_output(["ss", "-lptn", f"sport = :{port}"], stderr=subprocess.DEVNULL).decode()
            import re
            pids = re.findall(r"pid=(\d+)", out)
            for pid in pids:
                subprocess.run(["kill", "-9", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def run_command(
    cmd: Union[str, List[str]],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    capture: bool = False,
    check: bool = True,
    shell: bool = False,
) -> subprocess.CompletedProcess:
    """Runs a shell command with proper environment inheritance."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    if isinstance(cmd, str) and not shell:
        import shlex
        cmd = shlex.split(cmd)

    if capture:
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=check,
            shell=shell,
        )
    else:
        return subprocess.run(cmd, cwd=cwd, env=full_env, check=check, shell=shell)
