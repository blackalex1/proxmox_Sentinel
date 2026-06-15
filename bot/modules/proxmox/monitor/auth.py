import asyncio
import logging
import os
import re
import datetime
import time
from collections import deque

from .state import lxc_auth_history, lxc_name_cache, lxc_state_cache, auth_tailers
from .utils import LogTailer, send_alert_to_admins

# rolling-буфер для дедупликации закрытия SSH сессий: (vmid, key_type, value, timestamp)
recent_closed_events = deque(maxlen=200)

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
        event, msg = await parse_auth_line(line, vmid, timestamp, container_name)
        if event and msg:
            if event.get('type') == 'CLOSE':
                pid = event.get('pid')
                user = event.get('user')
                ip = event.get('ip')
                now = time.time()
                
                # Проверяем на дубликаты за последние 3 секунды
                is_duplicate = False
                for v, ktype, val, ts in list(recent_closed_events):
                    if v == vmid and now - ts < 3.0:
                        if pid and ktype == 'pid' and val == pid:
                            is_duplicate = True
                            break
                        if user and user != 'root' and ktype == 'user' and val == user:
                            is_duplicate = True
                            break
                        if ip and ktype == 'ip' and val == ip:
                            is_duplicate = True
                            break
                            
                if is_duplicate:
                    return
                
                # Добавляем в буфер
                if pid:
                    recent_closed_events.append((vmid, 'pid', pid, now))
                if user and user != 'root':
                    recent_closed_events.append((vmid, 'user', user, now))
                if ip:
                    recent_closed_events.append((vmid, 'ip', ip, now))
                
                user_str = user or 'unknown'
                target_key = "local" if vmid == 0 else f"lxc_{vmid}"
                logging.info("ssh_close_ssh-sessiya_dlya_na_pid_uspeshno", user_str, target_key, pid)
                
            lxc_auth_history[vmid].append(event)
            
            # Если это успешный вход по SSH, добавляем кнопку сброса сессии
            reply_markup = None
            if event.get('type') == 'SUCCESS' and 'pid' in event and 'WEB_GUI' not in event.get('ip', ''):
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                target_key = "local" if vmid == 0 else f"lxc_{vmid}"
                sshd_pid = event['pid']
                kb = [[InlineKeyboardButton(text="❌ Сбросить SSH-сессию", callback_data=f"termssh:{target_key}:{sshd_pid}")]]
                
                # Если вход выполнен по ключу, кэшируем его в БД и добавляем кнопку бана
                if 'fingerprint' in event:
                    from core.db import get_state, set_state
                    cache = await get_state("ssh_key_cache", {})
                    cache[f"{target_key}:{sshd_pid}"] = [event['fingerprint'], event.get('user', 'root')]
                    await set_state("ssh_key_cache", cache)
                    kb.append([InlineKeyboardButton(text="🚫 Заблокировать SSH-ключ", callback_data=f"bankey:{target_key}:{sshd_pid}")])
                
                reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
                
            await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=reply_markup)

    except Exception as e:
        logging.error("error_parsing_authorization_log", e)


async def monitor_lxc_auth():
    """Динамический запуск и остановка tailer-ов для авторизаций контейнеров (с поддержкой journalctl)."""
    logging.info("lxc_and_host_authorization_tracking_service_started")
    
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
            logging.info("zapuscheno_faylovoe_otslezhivanie_logov_avtorizatsii_khosta", host_log)
        else:
            # Резервный вариант для отключения буферизации в journalctl (в режиме follow логи сбрасываются сразу)
            cmd = ["stdbuf", "-oL", "journalctl", "-f", "-n", "0"]
            host_tailer = LogTailer(cmd, handle_auth_log_line, 0)
            auth_tailers[0] = host_tailer
            await host_tailer.start()
            logging.info("host_authorization_log_tracking_via_journalctl_started")

    while True:
        try:
            # Самолечение: если какой-либо тайлер завершил работу, удаляем его для автоперезапуска
            for vmid in list(auth_tailers.keys()):
                t = auth_tailers[vmid]
                if t.task and t.task.done():
                    logging.warning("auth_monitor_tailer_for_vmid_unexpectedly_terminated", vmid)
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
                    logging.info("zapuscheno_faylovoe_otslezhivanie_logov_avtorizatsii_khosta", host_log)
                else:
                    cmd = ["stdbuf", "-oL", "journalctl", "-f", "-n", "0"]
                    host_tailer = LogTailer(cmd, handle_auth_log_line, 0)
                    auth_tailers[0] = host_tailer
                    await host_tailer.start()
                    logging.info("host_authorization_log_tracking_via_journalctl_started")

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
                        logging.info("log_file_not_found_started_log_tracking", vmid)
                        
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
            logging.error("error_in_authorization_tailers_service", e)
            
        await asyncio.sleep(15)
