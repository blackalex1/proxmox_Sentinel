#!/usr/bin/env python3
import os
import sys
import datetime
import asyncio

# Add parent directory to sys.path to enable importing core and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import refactored modules from setup_modules package
from setup_modules.utils import (
    RED, GREEN, YELLOW, BLUE, CYAN, NC,
    print_header, print_success, print_warning, print_error, print_info,
    modify_env_value, restart_bot_service, get_lang, echo_lang
)
from setup_modules.checks import (
    check_systemd_service, check_sysctl, get_running_containers, get_running_vms
)
from setup_modules.cases import (
    test_host_ips, benchmark_ips_latency, test_container_ips, test_remote_vps,
    test_router_monitoring
)
from setup_modules.diagnostics import (
    verify_journal_logging, test_journal_streaming
)

async def main():
    test_start_time = datetime.datetime.now()
    if os.name != 'nt' and os.geteuid() != 0:
        print_error(echo_lang(
            "Этот скрипт должен быть запущен с правами ROOT (sudo), чтобы управлять pct и проверять сокеты!",
            "This script must be run with ROOT (sudo) privileges to manage pct and verify sockets!"
        ))
        sys.exit(1)
        
    print_header(echo_lang(
        "PVE Aegis IPS - Локальная диагностика и активный тест",
        "PVE Aegis IPS - Local Diagnostics & Active Test"
    ))
    print_info(echo_lang("Инициализация настроек бота...", "Initializing bot settings..."))
    
    try:
        from core.config import settings
        from modules.router.router import unban_router_ip
    except Exception as e:
        print_error(echo_lang(
            f"Не удалось загрузить core.config или модули роутера: {e}",
            f"Failed to load core.config or router modules: {e}"
        ))
        sys.exit(1)

    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
    
    # Извлекаем IP хоста Proxmox
    host_ip = None
    if settings.proxmox_host:
        host_ip = settings.proxmox_host.split(':')[0]
    
    if not host_ip:
        try:
            import socket
            host_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            host_ip = "127.0.0.1"

    print_info(echo_lang(
        f"Определен IP-адрес хоста Proxmox: {host_ip}",
        f"Detected Proxmox host IP address: {host_ip}"
    ))
    print_info(echo_lang(
        f"Активный IPS_PROCESS_WHITELIST из конфигурации: {settings.ips_process_whitelist}",
        f"Active IPS_PROCESS_WHITELIST from configuration: {settings.ips_process_whitelist}"
    ))
    
    # 1. Вносим хост и временное имя скрипта в белый список, затем перезапускаем бота
    host_whitelist_modified = False
    cmdline_whitelist_modified = False
    
    if host_ip:
        host_whitelist_modified = modify_env_value(env_path, "TRUSTED_ADMIN_IPS", host_ip, remove=False)
        cmdline_whitelist_modified = modify_env_value(env_path, "IPS_TEMP_WHITELIST_CMDLINE", "test_ips.py", remove=False)
        
        if host_whitelist_modified or cmdline_whitelist_modified:
            await restart_bot_service()
            
            # 2. Пытаемся разбанить хост на роутере перед тестами
            print_info(echo_lang(
                f"Снимаем возможные блокировки для {host_ip} на роутере...",
                f"Removing possible blocks for {host_ip} on the router..."
            ))
            try:
                success, desc = await unban_router_ip(host_ip)
                if success:
                    print_success(echo_lang(
                        f"Запрос на разбан отправлен: {desc}",
                        f"Unban request sent: {desc}"
                    ))
                else:
                    print_warning(echo_lang(
                        f"Не удалось разбанить на роутере: {desc}",
                        f"Failed to unban on the router: {desc}"
                    ))
            except Exception as ex:
                print_error(echo_lang(
                    f"Ошибка при попытке разбанить хост на роутере: {ex}",
                    f"Error trying to unban host on router: {ex}"
                ))

    try:
        # Запуск диагностики логов ядра
        await verify_journal_logging()
        await test_journal_streaming()
            
        # Check environments
        service_active = await check_systemd_service()
        sysctl_ok = await check_sysctl()
        
        if not service_active:
            print_warning(echo_lang(
                "Служба бота неактивна. Запустите бота, чтобы он перехватывал логи!",
                "Bot service is inactive. Start the bot to capture logs!"
            ))
            
        results = {}
        
        # 1. Test Host
        host_ok = await test_host_ips()
        results[echo_lang("Хост Proxmox VE (vmid=0)", "Proxmox VE Host (vmid=0)")] = host_ok
        
        latency_ms = None
        if host_ok:
            latency_ms = await benchmark_ips_latency()
        
        # 2. Test LXC Containers
        running_lxcs = await get_running_containers()
        for vmid, name in running_lxcs:
            if vmid in settings.ips_lxc_whitelist:
                print_info(echo_lang(
                    f"LXC {vmid} находится в белом списке (IPS Whitelist). Пропускаем тест.",
                    f"LXC {vmid} is whitelisted (IPS Whitelist). Skipping test."
                ))
                results[f"LXC {vmid} ({name})"] = "WHITELISTED"
                continue
                
            lxc_ok = await test_container_ips(vmid, name)
            results[f"LXC {vmid} ({name})"] = lxc_ok
            
        # 3. List VMs (Informational)
        running_vms = await get_running_vms()
        if running_vms:
            print_header(echo_lang("Ограничения архитектуры (Виртуальные машины)", "Architecture Limits (Virtual Machines)"))
            print_warning(echo_lang("Обнаружены запущенные QEMU VMs. Они НЕ защищаются PVE Aegis.", "Running QEMU VMs detected. They are NOT protected by PVE Aegis."))
            print_info(echo_lang(
                "Виртуальные машины (QEMU/KVM) полностью изолированы на уровне оборудования.",
                "Virtual machines (QEMU/KVM) are fully isolated at the hardware level."
            ))
            print_info(echo_lang(
                "Бот контролирует только процессы контейнеров LXC и самого Хоста.",
                "The bot only monitors LXC container processes and the Host itself."
            ))
            
        # 4. Test Remote Servers
        if settings.remote_servers:
            print_header(echo_lang("Тестирование удаленных VPS серверов", "Testing Remote VPS Servers"))
            for server in settings.remote_servers:
                vps_ok = await test_remote_vps(server)
                results[f"VPS {server['ip']}"] = vps_ok
                
        # 5. Test Router Monitoring
        if settings.router_monitor_enable:
            router_ok = await test_router_monitoring(settings)
            results[echo_lang("Роутер через SSH", "Router via SSH")] = router_ok
                
        # Print Summary Table
        print_header(echo_lang("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ", "TESTING RESULTS SUMMARY TABLE"))
        all_ok = True
        for target, status in results.items():
            if status == "WHITELISTED":
                status_str = f"{YELLOW}" + echo_lang("ПРОПУЩЕНО (РАЗРЕШЕНО / БЕЛЫЙ СПИСОК)", "SKIPPED (ALLOWED / WHITELIST)") + f"{NC}"
            elif status == "SKIPPED":
                status_str = f"{YELLOW}" + echo_lang("ПРОПУЩЕНО (НЕТ КЛЮЧА SSH / НЕ НАСТРОЕНО)", "SKIPPED (NO SSH KEY / NOT CONFIGURED)") + f"{NC}"
            elif "Роутер" in target or "Router" in target:
                status_str = f"{GREEN}" + echo_lang("УСПЕШНО (ПОДКЛЮЧЕНО)", "SUCCESS (CONNECTED)") + f"{NC}" if status else f"{RED}" + echo_lang("СБОЙ (ПРОБЛЕМА ПОДКЛЮЧЕНИЯ/УТИЛИТ)", "FAILED (CONNECTION/UTILITIES PROBLEM)") + f"{NC}"
            else:
                status_str = f"{GREEN}" + echo_lang("РАБОТАЕТ (ЗАБЛОКИРОВАНО)", "WORKING (BLOCKED)") + f"{NC}" if status else f"{RED}" + echo_lang("НЕ СРАБОТАЛО (НЕТ БЛОКИРОВКИ)", "FAILED (NO BLOCK)") + f"{NC}"
            print(f" - {target:<35} : {status_str}")
            if status is False:
                all_ok = False
                
        if latency_ms is not None:
            latency_label = echo_lang("Быстродействие (время реакции)", "Latency (response time)")
            print(f" - {latency_label:<35} : {GREEN}{latency_ms:.2f} ms{NC}")
            
        print("\n" + "="*60)
        if all_ok:
            print(f"{GREEN}✓ " + echo_lang("Все тесты активной защиты (IPS) успешно пройдены!", "All active protection (IPS) tests passed successfully!") + f"{NC}")
            print_lang("Проверьте ваш Telegram-клиент: там должны появиться алерты блокировки.", "Check your Telegram client: block alerts should appear there.")
        else:
            print(f"{RED}❌ " + echo_lang("Некоторые тесты не прошли.", "Some tests failed.") + f"{NC}")
            print_lang("Возможные причины:", "Possible reasons:")
            print_lang(
                " 1. Бот не запущен (sudo systemctl start proxmox-lxc-bot.service).",
                " 1. Bot is not running (sudo systemctl start proxmox-lxc-bot.service)."
            )
            print_lang(
                " 2. Не настроен Сетевой экран (Firewall) in PVE для LXC.",
                " 2. Firewall is not configured in PVE for LXC."
            )
            print_lang(
                " 3. Вы тестируете контейнер из белого списка.",
                " 3. You are testing a whitelisted container."
            )
            print_lang(
                " 4. В системе не установлены правила iptables.",
                " 4. iptables rules are not installed in the system."
            )
            
            print_header(echo_lang(
                "Диагностический дамп логов службы бота (journalctl)",
                "Diagnostic dump of bot service logs (journalctl)"
            ))
            try:
                since_time_str = test_start_time.strftime("%Y-%m-%d %H:%M:%S")
                proc = await asyncio.create_subprocess_exec(
                    "journalctl", "-u", "proxmox-lxc-bot.service", "--since", since_time_str, "--no-pager",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout_bytes, _ = await proc.communicate()
                logs = stdout_bytes.decode('utf-8', errors='ignore')
                
                keywords = ["Traffic Monitor", "is_local_bot_process", "Local IPS", "ss -atnup", "proc_name", "whitelist", "recent_bot_ports"]
                for line in logs.splitlines():
                    if any(kw in line for kw in keywords) or "WARNING" in line or "ERROR" in line:
                        print(line)
            except Exception as e:
                print_error(echo_lang(
                    f"Не удалось получить логи из journalctl: {e}",
                    f"Failed to retrieve logs from journalctl: {e}"
                ))
        print("="*60 + "\n")

    finally:
        # Восстанавливаем исходный белый список
        need_restart = False
        if host_whitelist_modified and host_ip:
            print_header(echo_lang(
                "Очистка настроек после теста (TRUSTED_ADMIN_IPS)",
                "Cleaning up settings after test (TRUSTED_ADMIN_IPS)"
            ))
            modify_env_value(env_path, "TRUSTED_ADMIN_IPS", host_ip, remove=True)
            need_restart = True
            
        if cmdline_whitelist_modified:
            print_header(echo_lang(
                "Очистка настроек после теста (IPS_TEMP_WHITELIST_CMDLINE)",
                "Cleaning up settings after test (IPS_TEMP_WHITELIST_CMDLINE)"
            ))
            modify_env_value(env_path, "IPS_TEMP_WHITELIST_CMDLINE", "test_ips.py", remove=True)
            need_restart = True
            
        if need_restart:
            await restart_bot_service()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(echo_lang("\nТест прерван пользователем.", "\nTest interrupted by user."))
