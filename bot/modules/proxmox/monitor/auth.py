import asyncio
import logging
import os
import re
import datetime

from .state import lxc_auth_history, lxc_name_cache, lxc_state_cache, auth_tailers
from .utils import LogTailer, send_alert_to_admins

def find_auth_log_path(vmid):
    """Определение пути к файлу логов авторизации контейнера на хосте (если они пишутся в файл)."""
    rootfs = f"/var/lib/lxc/{vmid}/rootfs"
    possible_paths = [
        f"{rootfs}/var/log/auth.log",
        f"{rootfs}/var/log/secure",
        f"{rootfs}/var/log/messages"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return None


async def handle_auth_log_line(line, vmid):
    """Парсинг логов аутентификации контейнера/хоста и отправка алертов."""
    try:
        container_name = lxc_name_cache.get(vmid, "Unknown")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        from .auth_parser import parse_auth_line
        event, msg = parse_auth_line(line, vmid, timestamp, container_name)
        if event and msg:
            lxc_auth_history[vmid].append(event)
            await send_alert_to_admins(msg)

    except Exception as e:
        logging.error(f"Ошибка парсинга лога авторизации: {e}")


async def monitor_lxc_auth():
    """Динамический запуск и остановка tailer-ов для авторизаций контейнеров (с поддержкой journalctl)."""
    logging.info("Запущен сервис отслеживания авторизаций LXC и Хоста...")
    
    # 0. Инициализация tailer-а для самого хоста Proxmox VE (vmid=0)
    if 0 not in auth_tailers:
        host_log = None
        for p in ["/var/log/auth.log", "/var/log/secure"]:
            if os.path.exists(p):
                host_log = p
                break
                
        if host_log:
            host_tailer = LogTailer(host_log, handle_auth_log_line, 0)
            auth_tailers[0] = host_tailer
            await host_tailer.start()
            logging.info(f"Запущено файловое отслеживание логов авторизации хоста ({host_log}).")
        else:
            # Резервный вариант для отключения буферизации в journalctl (в режиме follow логи сбрасываются сразу)
            cmd = ["stdbuf", "-oL", "journalctl", "-f", "-n", "0"]
            host_tailer = LogTailer(cmd, handle_auth_log_line, 0)
            auth_tailers[0] = host_tailer
            await host_tailer.start()
            logging.info("Запущено отслеживание логов авторизации хоста через journalctl.")

    while True:
        try:
            # Самолечение: если какой-либо тайлер завершил работу, удаляем его для автоперезапуска
            for vmid in list(auth_tailers.keys()):
                t = auth_tailers[vmid]
                if t.task and t.task.done():
                    logging.warning(f"[Auth Monitor] Тайлер для VMID {vmid} неожиданно завершил работу. Очищаем для автоперезапуска.")
                    auth_tailers.pop(vmid, None)

            # Автоматическая инициализация / перезапуск тайлера хоста (vmid=0)
            if 0 not in auth_tailers:
                host_log = None
                for p in ["/var/log/auth.log", "/var/log/secure"]:
                    if os.path.exists(p):
                        host_log = p
                        break
                if host_log:
                    host_tailer = LogTailer(host_log, handle_auth_log_line, 0)
                    auth_tailers[0] = host_tailer
                    await host_tailer.start()
                    logging.info(f"Запущено файловое отслеживание логов авторизации хоста ({host_log}).")
                else:
                    cmd = ["stdbuf", "-oL", "journalctl", "-f", "-n", "0"]
                    host_tailer = LogTailer(cmd, handle_auth_log_line, 0)
                    auth_tailers[0] = host_tailer
                    await host_tailer.start()
                    logging.info("Запущено отслеживание логов авторизации хоста через journalctl.")

            # Получаем список директорий из /var/lib/lxc
            if not os.path.exists("/var/lib/lxc"):
                await asyncio.sleep(30)
                continue
                
            lxc_dirs = [d for d in os.listdir("/var/lib/lxc") if d.isdigit()]
            
            for d in lxc_dirs:
                vmid = int(d)
                state = lxc_state_cache.get(vmid, "stopped")
                
                # Если контейнер работает и еще не отслеживается
                if state == "running" and vmid not in auth_tailers:
                    # 1. Проверяем наличие классического файла лога auth.log
                    log_path = find_auth_log_path(vmid)
                    
                    if log_path:
                        # Используем файловый tailer (режим совместимости)
                        tailer = LogTailer(log_path, handle_auth_log_line, vmid)
                        auth_tailers[vmid] = tailer
                        await tailer.start()
                    else:
                        # 2. Если файла нет (Debian 12+), стримим логи напрямую через pct exec!
                        cmd = ["pct", "exec", str(vmid), "--", "stdbuf", "-oL", "journalctl", "-f", "-n", "0"]
                        tailer = LogTailer(cmd, handle_auth_log_line, vmid)
                        auth_tailers[vmid] = tailer
                        await tailer.start()
                        logging.info(f"Файл логов не найден. Запущено отслеживание логов через pct exec для LXC {vmid}.")
                        
                # Если контейнер выключен, но tailer активен
                elif state != "running" and vmid in auth_tailers:
                    tailer = auth_tailers.pop(vmid)
                    await tailer.stop()
                    
            # Очищаем tailer-ы удаленных машин (игнорируя хост с vmid == 0)
            active_ids = {int(x) for x in lxc_dirs}
            for vmid in list(auth_tailers.keys()):
                if vmid != 0 and vmid not in active_ids:
                    tailer = auth_tailers.pop(vmid)
                    await tailer.stop()
                    
        except Exception as e:
            logging.error(f"Ошибка в сервисе tailer-ов авторизаций: {e}")
            
        await asyncio.sleep(15)
