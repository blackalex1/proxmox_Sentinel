#!/usr/bin/env python3
import asyncio
import sys
import os

# Добавляем родительскую директорию в sys.path, чтобы импортировать core и modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def update_env_file(key, value):
    from core.config import base_dir
    env_path = os.path.abspath(os.path.join(base_dir, 'config', '.env'))
    if not os.path.exists(env_path):
        print(f"⚠️ Файл конфигурации не найден по пути: {env_path}")
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
        # Добавляем перед пустыми строками или в конец
        new_lines.append(f"{key}={value}\n")
        
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"   \033[0;32m✓ Записано в .env: {key}={value}\033[0m")
    return True

async def test_router():
    try:
        from core.config import settings
        from modules.router.router import run_router_ssh_cmd
        from modules.router.monitor.rules import setup_router_logging_rules, remove_router_logging_rules
    except Exception as e:
        print(f"\033[0;31m❌ Не удалось импортировать модули проекта: {e}\033[0m")
        return False

    print("\n\033[0;34m==================================================\033[0m")
    print("\033[1;35m       ДИАГНОСТИКА И ПРОВЕРКА УТИЛИТ НА РОУТЕРЕ\033[0m")
    print("\033[0;34m==================================================\033[0m")
    print(f"Попытка SSH-подключения к роутеру: \033[1;33m{settings.router_ssh_user}@{settings.router_ssh_host}:{settings.router_ssh_port}\033[0m...")

    # 1. Проверяем базовое SSH-соединение
    ok, stdout, stderr = await run_router_ssh_cmd("echo 'Aegis Connection Test'")
    if not ok:
        print(f"\033[0;31m❌ Ошибка подключения по SSH к роутеру!\033[0m")
        print(f"Детали ошибки: {stderr or stdout}")
        print("\033[1;33m👉 Пожалуйста, проверьте настройки SSH хоста, порта, имени пользователя, пароля или ключа.\033[0m")
        return False

    print("\033[0;32m✓ SSH-подключение успешно установлено!\033[0m")

    # 2. Проверяем наличие conntrack, iptables и nftables
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    
    print("\nПроверка системных утилит на роутере...")
    
    # conntrack
    ok_ct, stdout_ct, _ = await run_router_ssh_cmd(f"{path_prefix}which conntrack")
    conntrack_installed = bool(ok_ct and stdout_ct.strip())
    
    # iptables
    ok_ipt, stdout_ipt, _ = await run_router_ssh_cmd(f"{path_prefix}which iptables")
    iptables_installed = bool(ok_ipt and stdout_ipt.strip())

    # nftables
    ok_nft, stdout_nft, _ = await run_router_ssh_cmd(f"{path_prefix}which nft")
    nftables_installed = bool(ok_nft and stdout_nft.strip())

    # Вывод статуса утилит в требуемом пользователем формате
    status_installed = "\033[0;32mУСТАНОВЛЕНО\033[0m"
    status_missing = "\033[0;31mОТСУТСТВУЕТ\033[0m"

    # Если conntrack отсутствует на OpenWrt, проверяем доступность в репозитории
    ct_pkg_in_repo = False
    ipt_pkg_in_repo = False
    
    if settings.router_type == 'openwrt':
        if not conntrack_installed:
            print("Поиск пакета conntrack-tools в репозитории OpenWrt...")
            ok_pkg, stdout_pkg, _ = await run_router_ssh_cmd(f"{path_prefix}opkg list | grep conntrack-tools || true")
            ct_pkg_in_repo = bool(ok_pkg and stdout_pkg.strip())
            
        if not (iptables_installed or nftables_installed):
            print("Поиск пакета iptables в репозитории OpenWrt...")
            ok_pkg_ipt, stdout_pkg_ipt, _ = await run_router_ssh_cmd(f"{path_prefix}opkg list | grep -E '^iptables ' || true")
            ipt_pkg_in_repo = bool(ok_pkg_ipt and stdout_pkg_ipt.strip())

    # Выводим статус с пометкой доступности в репо
    if conntrack_installed:
        print(f" - conntrack : {status_installed}")
    elif ct_pkg_in_repo:
        print(f" - conntrack : {status_missing} \033[1;33m(НО ДОСТУПНО В РЕПОЗИТОРИИ)\033[0m")
    else:
        print(f" - conntrack : {status_missing}")

    if iptables_installed:
        print(f" - iptables   : {status_installed}")
    elif ipt_pkg_in_repo:
        print(f" - iptables   : {status_missing} \033[1;33m(НО ДОСТУПНО В РЕПОЗИТОРИИ)\033[0m")
    else:
        print(f" - iptables   : {status_missing}")

    if nftables_installed:
        print(f" - nftables   : {status_installed}")

    # 3. Формируем рекомендации
    print("\n\033[1;35mРЕКОМЕНДАЦИИ ПО ВЫБОРУ РЕЖИМА:\033[0m")
    print("   \033[1;32mconntrack\033[0m - \033[1;32m[РЕКОМЕНДУЕТСЯ / ОПТИМАЛЬНО]\033[0m Работает напрямую с ядром, нагрузка 0%.")
    print("   \033[1;33miptables\033[0m  - \033[1;31m[МЕНЕЕ ОПТИМАЛЬНО]\033[0m Использует лог-файлы syslog, создает доп. нагрузку на запись логов.")

    # 4. Выбор режима и автонастройка
    recommended_choice = "conntrack" if conntrack_installed else "iptables"
    print(f"\n👉 Какой режим вы хотите использовать? (conntrack/iptables) [по умолчанию: {recommended_choice}]")
    try:
        user_choice = input(">> ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        user_choice = ""
    if not user_choice:
        user_choice = recommended_choice

    while user_choice not in ("conntrack", "iptables"):
        print("⚠️ Неверный выбор. Пожалуйста, введите 'conntrack' или 'iptables':")
        try:
            user_choice = input(">> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            user_choice = recommended_choice
            break

    # 5. Процедура автоустановки и автонастройки
    if user_choice == "conntrack":
        if not conntrack_installed:
            if settings.router_type == 'openwrt' and ct_pkg_in_repo:
                print("⏳ Запуск обновления репозиториев и установки conntrack-tools...")
                install_ok, install_out, install_err = await run_router_ssh_cmd(f"{path_prefix}opkg update && opkg install conntrack-tools")
                if install_ok:
                    print("\033[0;32m✓ Установка завершена успешно!\033[0m")
                    conntrack_installed = True
                else:
                    print(f"\033[0;31m❌ Ошибка установки conntrack-tools:\033[0m {install_err or install_out}")
            elif settings.router_type == 'keenetic':
                print("\n\033[1;33m👉 Пожалуйста, зайдите в веб-интерфейс Keenetic и установите компонент 'Служба conntrack'.\033[0m")
            else:
                print("\n\033[1;33m👉 Пожалуйста, установите утилиту conntrack на ваш роутер вручную.\033[0m")

        if conntrack_installed:
            # Финальная проверка работоспособности conntrack
            ok_ct_run, _, _ = await run_router_ssh_cmd(f"{path_prefix}conntrack -L -p tcp -g -h 2>/dev/null || conntrack -h")
            if ok_ct_run:
                print("\033[0;32m✓ conntrack успешно настроен и проверен!\033[0m")
                update_env_file("ROUTER_MONITOR_MODE", "conntrack")
            else:
                print("\033[1;31m⚠️ conntrack установлен, но модуль ядра не отвечает. Проверьте права root на роутере.\033[0m")
                update_env_file("ROUTER_MONITOR_MODE", "conntrack")
        else:
            print("\033[1;31m⚠️ Не удалось настроить conntrack. Выбран режим conntrack, но утилита отсутствует.\033[0m")
            update_env_file("ROUTER_MONITOR_MODE", "conntrack")

    elif user_choice == "iptables":
        # Если выбран iptables, но утилит нет на роутере
        if not (iptables_installed or nftables_installed):
            if settings.router_type == 'openwrt' and ipt_pkg_in_repo:
                print("⏳ Запуск обновления репозиториев и установки iptables...")
                install_ok, install_out, install_err = await run_router_ssh_cmd(f"{path_prefix}opkg update && opkg install iptables")
                if install_ok:
                    print("\033[0;32m✓ Установка завершена успешно!\033[0m")
                    iptables_installed = True
                else:
                    print(f"\033[0;31m❌ Ошибка установки iptables:\033[0m {install_err or install_out}")
            else:
                print("\n\033[1;33m👉 Пожалуйста, установите iptables на ваш роутер вручную.\033[0m")
                
        # Настройка режима iptables
        print("\033[1;33m💡 Выбран режим iptables (менее оптимально). Записываем настройки...\033[0m")
        update_env_file("ROUTER_MONITOR_MODE", "iptables")
        
        # Проверяем работу правил
        original_monitor = settings.router_monitor_enable
        settings.router_monitor_enable = True
        try:
            rules_ok = await setup_router_logging_rules()
            if rules_ok:
                print("\033[0;32m✓ Правила логирования успешно протестированы на роутере!\033[0m")
                await remove_router_logging_rules()
            else:
                print("\033[1;31m⚠️ Не удалось применить правила логирования на роутере. Проверьте права доступа SSH.\033[0m")
        except Exception as ex:
            print(f"⚠️ Ошибка проверки правил: {ex}")
        finally:
            settings.router_monitor_enable = original_monitor

    print("\033[0;34m==================================================\033[0m\n")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_router())
    sys.exit(0 if success else 1)
