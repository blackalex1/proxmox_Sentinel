"""Master Orchestrator Entrypoint for Sentinel Controller Modular Updater."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time

from .common import (
    BOLD,
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    YELLOW,
    log_banner,
    log_error,
    log_info,
    log_success,
    log_warn,
)
from .core import CoreManager
from .dependencies import DependencyManager
from .engines import ProxyEngineManager
from .git import GitManager
from .network import NetworkManager
from .service import ServiceManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sentinel Controller Modular Updater")
    parser.add_argument("--proxy", type=str, help="Specify an HTTP or SOCKS5 proxy URL (e.g. socks5://127.0.0.1:10808)")
    parser.add_argument("--no-proxy", action="store_true", help="Force direct connection without VPN rotator or proxy")
    parser.add_argument("--auto", action="store_true", help="Non-interactive automated update mode")
    parser.add_argument("--core-version", type=str, help="Specific sentinel-core version/tag to install")
    parser.add_argument("--force-core", action="store_true", help="Force core reinstallation even if up to date")
    parser.add_argument("--bootstrapped", action="store_true", help="Indicates update.sh already performed bootstrap git fetch")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(project_root)

    log_banner("🔄 ОБНОВЛЕНИЕ SENTINEL CONTROLLER")

    try:
        head_proc = subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "--short", "HEAD"], cwd=project_root, capture_output=True, text=True)
        recent_proc = subprocess.run(["git", "-c", "safe.directory=*", "log", "-n", "3", "--pretty=format:  • \033[1;33m%h\033[0m %s \033[2m(%cr)\033[0m"], cwd=project_root, capture_output=True, text=True)
        if head_proc.returncode == 0 and head_proc.stdout.strip():
            print(f"📌 Текущая ревизия контроллера: {BOLD}{head_proc.stdout.strip()}{RESET}")
        if recent_proc.returncode == 0 and recent_proc.stdout.strip():
            print(f"📝 Последние изменения:\n{recent_proc.stdout.strip()}\n")
    except Exception:
        pass

    # 0. Sync Git Codebase (only if not already bootstrapped by update.sh)
    if not args.bootstrapped:
        git_mgr = GitManager(project_dir=project_root)
        updated = git_mgr.update_codebase(silent_if_uptodate=True)
        if updated:
            log_info("Перезапуск обновленного апдейтера...")
            os.execv(sys.executable, [sys.executable, "-m", "installation.updater.main", "--bootstrapped"] + sys.argv[1:])

    network_mgr = NetworkManager(
        project_dir=project_root,
        proxy_arg=args.proxy,
        no_proxy=args.no_proxy,
        auto_mode=args.auto,
    )

    def _signal_handler(signum, frame):
        print(f"\n{YELLOW}[!] Процесс прерван пользователем. Выполняется очистка ресурсов...{RESET}")
        network_mgr.cleanup()
        sys.exit(130)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        # 1. Network & Proxy Setup
        network_mgr.show_menu()
        active_proxy = network_mgr.setup_network()

        # 2. Manage Sentinel-Core Binaries & Libraries
        core_mgr = CoreManager(
            project_dir=project_root,
            proxy_url=active_proxy,
            auto_mode=args.auto,
            force=args.force_core,
        )

        target_ver = args.core_version or core_mgr.select_version()
        if target_ver:
            core_ok = core_mgr.download_core(target_ver)
            if not core_ok:
                log_warn("Не удалось обновить некоторые компоненты ядра. Продолжаем развертывание...")

        # 4. Manage Sing-box & Xray-core Proxy Engines
        engine_mgr = ProxyEngineManager(
            project_dir=project_root,
            proxy_url=active_proxy,
            auto_mode=args.auto,
        )
        engine_mgr.manage_engines()

        # 5. Update Python Dependencies (bot/requirements.txt)
        dep_mgr = DependencyManager(project_dir=project_root, proxy_url=active_proxy)
        dep_mgr.update_dependencies()

        # 6. Register / Restart Systemd Service
        service_mgr = ServiceManager(project_dir=project_root)
        service_mgr.register_and_restart_service()

        # 7. Success Banner
        log_banner("✅ ОБНОВЛЕНИЕ SENTINEL CONTROLLER УСПЕШНО ЗАВЕРШЕНО!")
        print(f"{GREEN}Все компоненты, ядро и служба контроллера успешно обновлены и перезапущены.{RESET}\n")

        # 7. Live Follow Logs Stream (-f)
        if sys.stdin.isatty() and not args.auto:
            print(f"{CYAN}📡 Подключение к живому потоку логов службы ({BOLD}journalctl -u proxmox-lxc-bot -f -n 25{RESET}{CYAN})...{RESET}")
            print(f"{YELLOW}(Нажмите Ctrl+C для выхода из режима просмотра логов){RESET}\n")
            service_mgr.stream_live_logs()
            print(f"\n{GREEN}[✓] Просмотр логов завершен. Служба контроллера продолжает работать в фоне.{RESET}\n")

        return 0

    except Exception as e:
        log_error(f"Критическая ошибка в процессе обновления: {e}")
        return 1
    finally:
        network_mgr.cleanup()


if __name__ == "__main__":
    sys.exit(main())
