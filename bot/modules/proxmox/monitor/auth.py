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
        
        # 0. Успешный вход в Proxmox Web GUI (pvedaemon)
        pve_ok_match = re.search(r"pvedaemon\[\d+\]: <(\S+)> successful auth for user '(\S+)'", line)
        if pve_ok_match:
            realm_user, user = pve_ok_match.groups()
            event = {
                'time': timestamp,
                'type': 'SUCCESS',
                'user': user,
                'ip': 'WEB_GUI',
                'msg': "Вход в Proxmox VE Web GUI"
            }
            lxc_auth_history[vmid].append(event)
            
            target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
            emoji_str = "🖥" if vmid == 0 else "🔒"
            
            msg = (f"{emoji_str} <b>Успешный вход в Proxmox Web GUI!</b>\n\n"
                   f"📦 Назначение: <b>{target_str}</b>\n"
                   f"👤 Пользователь: <code>{user}</code>\n"
                   f"🌐 IP-адрес: <code>WEB_GUI</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            
            await send_alert_to_admins(msg)
            return

        # 0.1. Ошибка входа в Proxmox Web GUI (pvedaemon)
        pve_fail_match = re.search(r"pvedaemon\[\d+\]: authentication failure; rhost=(?:::ffff:)?(\S+) user=(\S+) msg=(.*)", line)
        if pve_fail_match:
            ip, user, reason = pve_fail_match.groups()
            event = {
                'time': timestamp,
                'type': 'FAILED',
                'user': user,
                'ip': ip,
                'msg': f"Ошибка Web GUI: {reason}"
            }
            lxc_auth_history[vmid].append(event)
            
            target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
            
            msg = (f"❌ <b>ОШИБКА АВТОРИЗАЦИИ в Proxmox Web GUI!</b>\n\n"
                   f"📦 Назначение: <b>{target_str}</b>\n"
                   f"👤 Попытка входа под: <code>{user}</code>\n"
                   f"🌐 IP-адрес: <code>{ip}</code>\n"
                   f"📝 Причина: <code>{reason}</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            
            await send_alert_to_admins(msg)
            return
        
        # 1. Успешный вход по SSH
        ssh_ok_match = re.search(r"sshd\[\d+\]: Accepted (password|publickey) for (\S+) from (\S+) port (\d+)", line)
        if ssh_ok_match:
            method, user, ip, port = ssh_ok_match.groups()
            event = {
                'time': timestamp,
                'type': 'SUCCESS',
                'user': user,
                'ip': ip,
                'msg': f"Вход через {method} (порт {port})"
            }
            lxc_auth_history[vmid].append(event)
            
            target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
            title_str = "🖥 <b>Успешная SSH авторизация на Хосте!</b>" if vmid == 0 else "🔒 <b>Успешная SSH авторизация в LXC!</b>"
            
            msg = (f"{title_str}\n\n"
                   f"📦 Назначение: <b>{target_str}</b>\n"
                   f"👤 Пользователь: <code>{user}</code>\n"
                   f"🌐 IP-адрес: <code>{ip}</code>\n"
                   f"🔑 Метод: <b>{method}</b>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            
            await send_alert_to_admins(msg)
            return

        # 2. Неудачный вход по SSH (пароль или публичный ключ)
        ssh_fail_match = re.search(r"sshd\[\d+\]: Failed (password|publickey) for (?:invalid user )?(\S+) from (\S+) port (\d+)", line)
        if ssh_fail_match:
            method, user, ip, port = ssh_fail_match.groups()
            method_ru = "Неверный пароль" if method == "password" else "Неверный SSH-ключ"
            event = {
                'time': timestamp,
                'type': 'FAILED',
                'user': user,
                'ip': ip,
                'msg': f"{method_ru} (порт {port})"
            }
            lxc_auth_history[vmid].append(event)
            
            target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
            title_str = "❌ <b>ОШИБКА SSH АВТОРИЗАЦИИ на Хосте!</b>" if vmid == 0 else "❌ <b>ОШИБКА АВТОРИЗАЦИИ в LXC!</b>"
            
            msg = (f"{title_str}\n\n"
                   f"📦 Назначение: <b>{target_str}</b>\n"
                   f"👤 Попытка входа под: <code>{user}</code>\n"
                   f"🌐 IP-адрес: <code>{ip}</code>\n"
                   f"🔑 Способ: <b>{method_ru}</b>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            
            await send_alert_to_admins(msg)
            return

        # 3. Выполнение команд через SUDO
        sudo_match = re.search(r"sudo:\s+(\S+)\s+:.*?USER=(\S+)\s+;.*?COMMAND=(.*)", line)
        if sudo_match:
            user, run_as, command = sudo_match.groups()
            event = {
                'time': timestamp,
                'type': 'SUDO',
                'user': user,
                'ip': 'LOCAL',
                'msg': f"sudo [{run_as}]: {command[:50]}"
            }
            lxc_auth_history[vmid].append(event)
            
            target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
            title_str = "💻 <b>Выполнение SUDO-команды на Хосте!</b>" if vmid == 0 else "🛠 <b>Выполнение SUDO-команды в LXC!</b>"
            
            msg = (f"{title_str}\n\n"
                   f"📦 Назначение: <b>{target_str}</b>\n"
                   f"👤 Пользователь: <code>{user}</code> (от имени <code>{run_as}</code>)\n"
                   f"💻 Команда:\n<code>{command}</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            
            await send_alert_to_admins(msg)
            return

    except Exception as e:
        logging.error(f"Ошибка парсинга лога авторизации: {e}")


async def monitor_lxc_auth():
    """Динамический запуск и остановка tailer-ов для авторизаций контейнеров (с поддержкой journalctl)."""
    logging.info("Запущен сервис отслеживания авторизаций LXC и Хоста...")
    
    # 0. Инициализация tailer-а для самого хоста Proxmox VE (vmid=0)
    if 0 not in auth_tailers:
        cmd = ["journalctl", "-f", "-n", "0"]
        host_tailer = LogTailer(cmd, handle_auth_log_line, 0)
        auth_tailers[0] = host_tailer
        await host_tailer.start()
        logging.info("Запущено отслеживание логов авторизации хоста (sshd, sudo, pvedaemon) через journalctl.")

    while True:
        try:
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
                        cmd = ["pct", "exec", str(vmid), "--", "journalctl", "-f", "-n", "0"]
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
