#!/usr/bin/env python3
import asyncio
import sys
import os

# Добавляем родительскую директорию в sys.path, чтобы импортировать core и modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def get_lang():
    try:
        from core.config import settings
        return settings.bot_language
    except Exception:
        return 'en'

def echo_lang(ru, en):
    return ru if get_lang() == 'ru' else en

def print_lang(ru, en):
    print(echo_lang(ru, en))

def update_env_file(key, value):
    from core.config import base_dir
    env_path = os.path.abspath(os.path.join(base_dir, 'config', '.env'))
    if not os.path.exists(env_path):
        print_lang(f"⚠️ Файл конфигурации не найден по пути: {env_path}", f"⚠️ Configuration file not found at: {env_path}")
        return False
    
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            updated = True
        else:
            new_lines.append(line)
            
    if not updated:
        new_lines.append(f"{key}={value}\n")
        
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print_lang(f"   \033[0;32m✓ Записано в .env: {key}={value}\033[0m", f"   \033[0;32m✓ Saved to .env: {key}={value}\033[0m")
    return True

async def test_router():
    try:
        from core.config import settings
        from modules.router.router import run_router_ssh_cmd
        from modules.router.monitor.rules import setup_router_logging_rules, remove_router_logging_rules
    except Exception as e:
        print_lang(f"\033[0;31m❌ Не удалось импортировать модули проекта: {e}\033[0m", f"\033[0;31m❌ Failed to import project modules: {e}\033[0m")
        return False

    print("\n\033[0;34m==================================================\033[0m")
    print_lang("\033[1;35m       ДИАГНОСТИКА И ПРОВЕРКА УТИЛИТ НА РОУТЕРЕ\033[0m", "\033[1;35m       ROUTER UTILITIES DIAGNOSTICS & VERIFICATION\033[0m")
    print("\033[0;34m==================================================\033[0m")
    print_lang(f"Попытка SSH-подключения к роутеру: \033[1;33m{settings.router_ssh_user}@{settings.router_ssh_host}:{settings.router_ssh_port}\033[0m...", f"Attempting SSH connection to the router: \033[1;33m{settings.router_ssh_user}@{settings.router_ssh_host}:{settings.router_ssh_port}\033[0m...")

    # 1. Проверяем базовое SSH-соединение
    ok, stdout, stderr = await run_router_ssh_cmd("echo 'Aegis Connection Test'")
    if not ok:
        print_lang("\033[0;31m❌ Ошибка подключения по SSH к роутеру!\033[0m", "\033[0;31m❌ SSH connection to router failed!\033[0m")
        print_lang(f"Детали ошибки: {stderr or stdout}", f"Error details: {stderr or stdout}")
        print_lang("\033[1;33m👉 Пожалуйста, проверьте настройки SSH хоста, порта, имени пользователя, пароля или ключа.\033[0m", "\033[1;33m👉 Please check SSH host, port, username, password, or key settings.\033[0m")
        return False

    print_lang("\033[0;32m✓ SSH-подключение успешно установлено!\033[0m", "\033[0;32m✓ SSH connection successfully established!\033[0m")

    # 2. Проверяем наличие conntrack, iptables и nftables
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    
    print_lang("\nПроверка системных утилит на роутере...", "\nChecking system utilities on the router...")
    
    # conntrack
    ok_ct, stdout_ct, _ = await run_router_ssh_cmd(f"{path_prefix}which conntrack")
    conntrack_installed = bool(ok_ct and stdout_ct.strip())
    
    # iptables
    ok_ipt, stdout_ipt, _ = await run_router_ssh_cmd(f"{path_prefix}which iptables")
    iptables_installed = False
    iptables_has_log = False
    if ok_ipt and stdout_ipt.strip():
        # Дополнительно проверяем поддержку цели LOG в ядре
        test_log_cmd = (
            f"{path_prefix}iptables -I FORWARD -p tcp --dport 9999 -j LOG --log-prefix \"AEGIS_TEST: \" && "
            f"{path_prefix}iptables -D FORWARD -p tcp --dport 9999 -j LOG --log-prefix \"AEGIS_TEST: \""
        )
        ok_test, _, _ = await run_router_ssh_cmd(test_log_cmd)
        if ok_test:
            iptables_installed = True
            iptables_has_log = True

    # nftables
    ok_nft, stdout_nft, _ = await run_router_ssh_cmd(f"{path_prefix}which nft")
    nftables_installed = bool(ok_nft and stdout_nft.strip())

    # Вывод статуса утилит
    status_installed = "\033[0;32mУСТАНОВЛЕНО\033[0m" if get_lang() == 'ru' else "\033[0;32mINSTALLED\033[0m"
    status_missing = "\033[0;31mОТСУТСТВУЕТ\033[0m" if get_lang() == 'ru' else "\033[0;31mMISSING\033[0m"

    # Если conntrack отсутствует на OpenWrt, проверяем доступность в репозитории
    ct_pkg_in_repo = False
    ipt_pkg_in_repo = False
    
    if settings.router_type == 'openwrt':
        if not conntrack_installed:
            print_lang("Поиск пакета conntrack-tools в репозитории OpenWrt...", "Searching for conntrack-tools package in OpenWrt repository...")
            ok_pkg, stdout_pkg, _ = await run_router_ssh_cmd(f"{path_prefix}opkg list | grep conntrack-tools || true")
            ct_pkg_in_repo = bool(ok_pkg and stdout_pkg.strip())
            
        if not (iptables_installed or nftables_installed):
            print_lang("Поиск пакета iptables в репозитории OpenWrt...", "Searching for iptables package in OpenWrt repository...")
            ok_pkg_ipt, stdout_pkg_ipt, _ = await run_router_ssh_cmd(f"{path_prefix}opkg list | grep -E '^iptables ' || true")
            ipt_pkg_in_repo = bool(ok_pkg_ipt and stdout_pkg_ipt.strip())

    # Выводим статус с пометкой доступности в репо
    if conntrack_installed:
        print(f" - conntrack : {status_installed}")
    elif ct_pkg_in_repo:
        print_lang(f" - conntrack : {status_missing} \033[1;33m(НО ДОСТУПНО В РЕПОЗИТОРИИ)\033[0m", f" - conntrack : {status_missing} \033[1;33m(BUT AVAILABLE IN REPOSITORY)\033[0m")
    else:
        print(f" - conntrack : {status_missing}")

    if iptables_installed:
        print(f" - iptables   : {status_installed}")
    elif ok_ipt and stdout_ipt.strip() and not iptables_has_log:
        print_lang(f" - iptables   : {status_missing} \033[1;31m(НЕТ ПОДДЕРЖКИ LOG В ЯДРЕ)\033[0m", f" - iptables   : {status_missing} \033[1;31m(NO LOG SUPPORT IN KERNEL)\033[0m")
    elif ipt_pkg_in_repo:
        print_lang(f" - iptables   : {status_missing} \033[1;33m(НО ДОСТУПНО В РЕПОЗИТОРИИ)\033[0m", f" - iptables   : {status_missing} \033[1;33m(BUT AVAILABLE IN REPOSITORY)\033[0m")
    else:
        print(f" - iptables   : {status_missing}")

    if nftables_installed:
        print(f" - nftables   : {status_installed}")

    # 3. Формируем рекомендации
    print_lang("\n\033[1;35mРЕКОМЕНДАЦИИ ПО ВЫБОРУ РЕЖИМА:\033[0m", "\n\033[1;35mMODE RECOMMENDATIONS:\033[0m")
    print_lang("   \033[1;32mconntrack\033[0m - \033[1;32m[РЕКОМЕНДУЕТСЯ / ОПТИМАЛЬНО]\033[0m Работает напрямую с ядром, нагрузка 0%.", "   \033[1;32mconntrack\033[0m - \033[1;32m[RECOMMENDED / OPTIMAL]\033[0m Interacts directly with the kernel, 0% load.")
    print_lang("   \033[1;33miptables\033[0m  - \033[1;31m[МЕНЕЕ ОПТИМАЛЬНО]\033[0m Использует лог-файлы syslog, создает доп. нагрузку на запись логов.", "   \033[1;33miptables\033[0m  - \033[1;31m[LESS OPTIMAL]\033[0m Uses syslog files, generates extra write load.")

    # 4. Выбор режима и автонастройка
    recommended_choice = "conntrack" if conntrack_installed else "iptables"
    print_lang(f"\n👉 Какой режим вы хотите использовать? (conntrack/iptables) [по умолчанию: {recommended_choice}]", f"\n👉 Which mode do you want to use? (conntrack/iptables) [default: {recommended_choice}]")
    try:
        user_choice = input(">> ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        user_choice = ""
    if not user_choice:
        user_choice = recommended_choice

    while user_choice not in ("conntrack", "iptables"):
        print_lang("⚠️ Неверный выбор. Пожалуйста, введите 'conntrack' или 'iptables':", "⚠️ Invalid choice. Please enter 'conntrack' or 'iptables':")
        try:
            user_choice = input(">> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            user_choice = recommended_choice
            break

    # 5. Процедура автоустановки и автонастройки
    if user_choice == "conntrack":
        if not conntrack_installed:
            if settings.router_type == 'openwrt' and ct_pkg_in_repo:
                print_lang("⏳ Запуск обновления репозиториев и установки conntrack-tools...", "⏳ Launching package repository update and conntrack-tools installation...")
                install_ok, install_out, install_err = await run_router_ssh_cmd(f"{path_prefix}opkg update && opkg install conntrack-tools")
                if install_ok:
                    print_lang("\033[0;32m✓ Установка завершена успешно!\033[0m", "\033[0;32m✓ Installation completed successfully!\033[0m")
                    conntrack_installed = True
                else:
                    print_lang(f"\033[0;31m❌ Ошибка установки conntrack-tools:\033[0m {install_err or install_out}", f"\033[0;31m❌ Error installing conntrack-tools:\033[0m {install_err or install_out}")
            elif settings.router_type == 'keenetic':
                print_lang("\n\033[1;33m👉 Пожалуйста, зайдите в веб-интерфейс Keenetic и установите компонент 'Служба conntrack'.\033[0m", "\n\033[1;33m👉 Please open the Keenetic web interface and install the 'Conntrack service' component.\033[0m")
            else:
                print_lang("\n\033[1;33m👉 Пожалуйста, установите утилиту conntrack на ваш роутер вручную.\033[0m", "\n\033[1;33m👉 Please install the conntrack utility on your router manually.\033[0m")

        if conntrack_installed:
            # Финальная проверка работоспособности conntrack
            ok_ct_run, _, _ = await run_router_ssh_cmd(f"{path_prefix}conntrack -L -p tcp -g -h 2>/dev/null || conntrack -h")
            if ok_ct_run:
                print_lang("\033[0;32m✓ conntrack успешно настроен и проверен!\033[0m", "\033[0;32m✓ conntrack successfully configured and verified!\033[0m")
                update_env_file("ROUTER_MONITOR_MODE", "conntrack")
            else:
                print_lang("\033[1;31m⚠️ conntrack установлен, но модуль ядра не отвечает. Проверьте права root на роутере.\033[0m", "\033[1;31m⚠️ conntrack is installed but kernel module is not responding. Check root permissions on the router.\033[0m")
                update_env_file("ROUTER_MONITOR_MODE", "conntrack")
        else:
            print_lang("\033[1;31m⚠️ Не удалось настроить conntrack. Выбран режим conntrack, но утилита отсутствует.\033[0m", "\033[1;31m⚠️ Failed to configure conntrack. conntrack mode is selected but the utility is missing.\033[0m")
            update_env_file("ROUTER_MONITOR_MODE", "conntrack")

    elif user_choice == "iptables":
        # Если выбран iptables, но утилит нет на роутере
        if not (iptables_installed or nftables_installed):
            if settings.router_type == 'openwrt' and ipt_pkg_in_repo:
                print_lang("⏳ Запуск обновления репозиториев и установки iptables...", "⏳ Launching package repository update and iptables installation...")
                install_ok, install_out, install_err = await run_router_ssh_cmd(f"{path_prefix}opkg update && opkg install iptables")
                if install_ok:
                    print_lang("\033[0;32m✓ Установка завершена успешно!\033[0m", "\033[0;32m✓ Installation completed successfully!\033[0m")
                    iptables_installed = True
                else:
                    print_lang(f"\033[0;31m❌ Ошибка установки iptables:\033[0m {install_err or install_out}", f"\033[0;31m❌ Error installing iptables:\033[0m {install_err or install_out}")
            else:
                print_lang("\n\033[1;33m👉 Пожалуйста, установите iptables на ваш роутер вручную.\033[0m", "\n\033[1;33m👉 Please install iptables on your router manually.\033[0m")
                
        # Настройка режима iptables
        print_lang("\033[1;33m💡 Выбран режим iptables (менее оптимально). Записываем настройки...\033[0m", "\033[1;33m💡 Selected iptables mode (less optimal). Saving configuration...\033[0m")
        update_env_file("ROUTER_MONITOR_MODE", "iptables")
        
        # Проверяем работу правил
        original_monitor = settings.router_monitor_enable
        settings.router_monitor_enable = True
        try:
            rules_ok = await setup_router_logging_rules()
            if rules_ok:
                print_lang("\033[0;32m✓ Правила логирования успешно протестированы на роутере!\033[0m", "\033[0;32m✓ Logging rules successfully tested on the router!\033[0m")
                await remove_router_logging_rules()
            else:
                print_lang("\033[1;31m⚠️ Не удалось применить правила логирования на роутере. Проверьте права доступа SSH.\033[0m", "\033[1;31m⚠️ Failed to apply logging rules on the router. Check SSH access permissions.\033[0m")
        except Exception as ex:
            print_lang(f"⚠️ Ошибка проверки правил: {ex}", f"⚠️ Rule verification error: {ex}")
        finally:
            settings.router_monitor_enable = original_monitor

    print("\033[0;34m==================================================\033[0m\n")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_router())
    sys.exit(0 if success else 1)
