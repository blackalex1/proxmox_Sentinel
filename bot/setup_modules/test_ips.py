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
    modify_env_value, restart_bot_service
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
        print_error("Этот скрипт должен быть запущен с правами ROOT (sudo), чтобы управлять pct и проверять сокеты!")
        sys.exit(1)
        
    print_header("PVE Aegis IPS - Локальная диагностика и активный тест")
    print_info("Инициализация настроек бота...")
    
    try:
        from core.config import settings
        from modules.router.router import unban_router_ip
    except Exception as e:
        print_error(f"Не удалось загрузить core.config или модули роутера: {e}")
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

    print_info(f"Определен IP-адрес хоста Proxmox: {host_ip}")
    print_info(f"Активный IPS_PROCESS_WHITELIST из конфигурации: {settings.ips_process_whitelist}")
    
    # 1. Вносим хост и временное имя скрипта в белый список, затем перезапускаем бота
    host_whitelist_modified = False
    cmdline_whitelist_modified = False
    
    if host_ip:
        host_whitelist_modified = modify_env_value(env_path, "TRUSTED_ADMIN_IPS", host_ip, remove=False)
        cmdline_whitelist_modified = modify_env_value(env_path, "IPS_TEMP_WHITELIST_CMDLINE", "test_ips.py", remove=False)
        
        if host_whitelist_modified or cmdline_whitelist_modified:
            await restart_bot_service()
            
            # 2. Пытаемся разбанить хост на роутере перед тестами
            print_info(f"Снимаем возможные блокировки для {host_ip} на роутере...")
            try:
                success, desc = await unban_router_ip(host_ip)
                if success:
                    print_success(f"Запрос на разбан отправлен: {desc}")
                else:
                    print_warning(f"Не удалось разбанить на роутере: {desc}")
            except Exception as ex:
                print_error(f"Ошибка при попытке разбанить хост на роутере: {ex}")

    try:
        # Запуск диагностики логов ядра
        await verify_journal_logging()
        await test_journal_streaming()
            
        # Check environments
        service_active = await check_systemd_service()
        sysctl_ok = await check_sysctl()
        
        if not service_active:
            print_warning("Служба бота неактивна. Запустите бота, чтобы он перехватывал логи!")
            
        results = {}
        
        # 1. Test Host
        host_ok = await test_host_ips()
        results["Хост Proxmox VE (vmid=0)"] = host_ok
        
        latency_ms = None
        if host_ok:
            latency_ms = await benchmark_ips_latency()
        
        # 2. Test LXC Containers
        running_lxcs = await get_running_containers()
        for vmid, name in running_lxcs:
            if vmid in settings.ips_lxc_whitelist:
                print_info(f"LXC {vmid} находится в белом списке (IPS Whitelist). Пропускаем тест.")
                results[f"LXC {vmid} ({name})"] = "WHITELISTED"
                continue
                
            lxc_ok = await test_container_ips(vmid, name)
            results[f"LXC {vmid} ({name})"] = lxc_ok
            
        # 3. List VMs (Informational)
        running_vms = await get_running_vms()
        if running_vms:
            print_header("Ограничения архитектуры (Виртуальные машины)")
            print_warning("Обнаружены запущенные QEMU VMs. Они НЕ защищаются PVE Aegis.")
            print_info("Виртуальные машины (QEMU/KVM) полностью изолированы на уровне оборудования.")
            print_info("Бот контролирует только процессы контейнеров LXC и самого Хоста.")
            
        # 4. Test Remote Servers
        if settings.remote_servers:
            print_header("Тестирование удаленных VPS серверов")
            for server in settings.remote_servers:
                vps_ok = await test_remote_vps(server)
                results[f"VPS {server['ip']}"] = vps_ok
                
        # 5. Test Router Monitoring
        if settings.router_monitor_enable:
            router_ok = await test_router_monitoring(settings)
            results["Роутер через SSH"] = router_ok
                
        # Print Summary Table
        print_header("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        all_ok = True
        for target, status in results.items():
            if status == "WHITELISTED":
                status_str = f"{YELLOW}ПРОПУЩЕНО (РАЗРЕШЕНО / БЕЛЫЙ СПИСОК){NC}"
            elif status == "SKIPPED":
                status_str = f"{YELLOW}ПРОПУЩЕНО (НЕТ КЛЮЧА SSH / НЕ НАСТРОЕНО){NC}"
            elif "Роутер" in target:
                status_str = f"{GREEN}УСПЕШНО (ПОДКЛЮЧЕНО){NC}" if status else f"{RED}СБОЙ (ПРОБЛЕМА ПОДКЛЮЧЕНИЯ/УТИЛИТ){NC}"
            else:
                status_str = f"{GREEN}РАБОТАЕТ (ЗАБЛОКИРОВАНО){NC}" if status else f"{RED}НЕ СРАБОТАЛО (НЕТ БЛОКИРОВКИ){NC}"
            print(f" - {target:<35} : {status_str}")
            if status is False:
                all_ok = False
                
        if latency_ms is not None:
            print(f" - {'Быстродействие (время реакции)':<35} : {GREEN}{latency_ms:.2f} мс{NC}")
            
        print("\n" + "="*60)
        if all_ok:
            print(f"{GREEN}✓ Все тесты активной защиты (IPS) успешно пройдены!{NC}")
            print("Проверьте ваш Telegram-клиент: там должны появиться алерты блокировки.")
        else:
            print(f"{RED}❌ Некоторые тесты не прошли.{NC}")
            print("Возможные причины:")
            print(" 1. Бот не запущен (sudo systemctl start proxmox-lxc-bot.service).")
            print(" 2. Не настроен Сетевой экран (Firewall) in PVE для LXC.")
            print(" 3. Вы тестируете контейнер из белого списка.")
            print(" 4. В системе не установлены правила iptables.")
            
            print_header("Диагностический дамп логов службы бота (journalctl)")
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
                print_error(f"Не удалось получить логи из journalctl: {e}")
        print("="*60 + "\n")

    finally:
        # Восстанавливаем исходный белый список
        need_restart = False
        if host_whitelist_modified and host_ip:
            print_header("Очистка настроек после теста (TRUSTED_ADMIN_IPS)")
            modify_env_value(env_path, "TRUSTED_ADMIN_IPS", host_ip, remove=True)
            need_restart = True
            
        if cmdline_whitelist_modified:
            print_header("Очистка настроек после теста (IPS_TEMP_WHITELIST_CMDLINE)")
            modify_env_value(env_path, "IPS_TEMP_WHITELIST_CMDLINE", "test_ips.py", remove=True)
            need_restart = True
            
        if need_restart:
            await restart_bot_service()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nТест прерван пользователем.")
