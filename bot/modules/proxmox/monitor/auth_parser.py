import re

def parse_auth_line(line: str, vmid: int, timestamp: str, container_name: str):
    """Парсинг логов аутентификации контейнера/хоста.
    Возвращает кортеж (event_dict, alert_message) или (None, None).
    """
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
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        emoji_str = "🖥" if vmid == 0 else "🔒"
        
        msg = (f"{emoji_str} <b>Успешный вход в Proxmox Web GUI!</b>\n\n"
               f"📦 Назначение: <b>{target_str}</b>\n"
               f"👤 Пользователь: <code>{user}</code>\n"
               f"🌐 IP-адрес: <code>WEB_GUI</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
        return event, msg

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
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        
        msg = (f"❌ <b>ОШИБКА АВТОРИЗАЦИИ в Proxmox Web GUI!</b>\n\n"
               f"📦 Назначение: <b>{target_str}</b>\n"
               f"👤 Попытка входа под: <code>{user}</code>\n"
               f"🌐 IP-адрес: <code>{ip}</code>\n"
               f"📝 Причина: <code>{reason}</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
        return event, msg
    
    # 1. Успешный вход по SSH
    ssh_ok_match = re.search(r"sshd(?:-session)?\[(\d+)\]: Accepted (password|publickey) for (\S+) from (\S+) port (\d+)", line)
    if ssh_ok_match:
        pid_str, method, user, ip, port = ssh_ok_match.groups()
        pid = int(pid_str)
        event = {
            'time': timestamp,
            'type': 'SUCCESS',
            'user': user,
            'ip': ip,
            'pid': pid,
            'msg': f"Вход через {method} (порт {port})"
        }
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        title_str = "🖥 <b>Успешная SSH авторизация на Хосте!</b>" if vmid == 0 else "🔒 <b>Успешная SSH авторизация в LXC!</b>"
        
        msg = (f"{title_str}\n\n"
               f"📦 Назначение: <b>{target_str}</b>\n"
               f"👤 Пользователь: <code>{user}</code>\n"
               f"🌐 IP-адрес: <code>{ip}</code>\n"
               f"🔑 Метод: <b>{method}</b>\n"
               f"🕒 Время: <code>{timestamp}</code>")
        return event, msg

    # 2. Неудачный вход по SSH (пароль или публичный ключ)
    ssh_fail_match = re.search(r"sshd(?:-session)?\[\d+\]: Failed (password|publickey) for (?:invalid user )?(\S+) from (\S+) port (\d+)", line)
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
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        title_str = "❌ <b>ОШИБКА SSH АВТОРИЗАЦИИ на Хосте!</b>" if vmid == 0 else "❌ <b>ОШИБКА АВТОРИЗАЦИИ в LXC!</b>"
        
        msg = (f"{title_str}\n\n"
               f"📦 Назначение: <b>{target_str}</b>\n"
               f"👤 Попытка входа под: <code>{user}</code>\n"
               f"🌐 IP-адрес: <code>{ip}</code>\n"
               f"🔑 Способ: <b>{method_ru}</b>\n"
               f"🕒 Время: <code>{timestamp}</code>")
        return event, msg

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
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        title_str = "💻 <b>Выполнение SUDO-команды на Хосте!</b>" if vmid == 0 else "🛠 <b>Выполнение SUDO-команды в LXC!</b>"
        
        msg = (f"{title_str}\n\n"
               f"📦 Назначение: <b>{target_str}</b>\n"
               f"👤 Пользователь: <code>{user}</code> (от имени <code>{run_as}</code>)\n"
               f"💻 Команда:\n<code>{command}</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
        return event, msg

    return None, None
