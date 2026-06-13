import re
from core.messages import (
    get_pve_web_login_alert,
    get_pve_web_fail_alert,
    get_ssh_login_alert,
    get_ssh_fail_alert,
    get_sudo_alert,
    get_ssh_close_alert
)

async def parse_auth_line(line: str, vmid: int, timestamp: str, container_name: str):
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
        msg = get_pve_web_login_alert(target_str, user, timestamp, line)
        return event, msg

    # 0.1. Ошибка входа в Proxmox Web GUI (pvedaemon)
    pve_fail_match = re.search(r"pvedaemon\[\d+\]: authentication failure; rhost=(?:::ffff:)?(\S+) user=(\S+) msg=(.*)", line)
    if pve_fail_match:
        ip, user, reason = pve_fail_match.groups()
        from .utils import get_geoip_info
        geoip_info = await get_geoip_info(ip)
        event = {
            'time': timestamp,
            'type': 'FAILED',
            'user': user,
            'ip': ip,
            'msg': f"Ошибка Web GUI: {reason}"
        }
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        msg = get_pve_web_fail_alert(target_str, user, ip, reason, timestamp, line, geoip_info=geoip_info)
        return event, msg
    
    # 1. Успешный вход по SSH
    ssh_ok_match = re.search(r"sshd(?:-session)?\[(\d+)\]: Accepted (password|publickey) for (\S+) from (\S+) port (\d+)(?: ssh2: \S+ (\S+))?", line)
    if ssh_ok_match:
        pid_str, method, user, ip, port, fingerprint = ssh_ok_match.groups()
        from .utils import get_geoip_info
        geoip_info = await get_geoip_info(ip)
        pid = int(pid_str)
        event = {
            'time': timestamp,
            'type': 'SUCCESS',
            'user': user,
            'ip': ip,
            'pid': pid,
            'msg': f"Вход через {method} (порт {port})"
        }
        if fingerprint:
            event['fingerprint'] = fingerprint
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        emoji_str = "🖥" if vmid == 0 else "🔒"
        title_str = "Успешная SSH авторизация на Хосте!" if vmid == 0 else "Успешная SSH авторизация в LXC!"
        
        msg = get_ssh_login_alert(title_str, emoji_str, target_str, user, ip, method, fingerprint, timestamp, line, geoip_info=geoip_info)
        return event, msg

    # 2. Неудачный вход по SSH (пароль или публичный ключ)
    ssh_fail_match = re.search(r"sshd(?:-session)?\[\d+\]: Failed (password|publickey) for (?:invalid user )?(\S+) from (\S+) port (\d+)", line)
    if ssh_fail_match:
        method, user, ip, port = ssh_fail_match.groups()
        from .utils import get_geoip_info
        geoip_info = await get_geoip_info(ip)
        method_ru = "Неверный пароль" if method == "password" else "Неверный SSH-ключ"
        event = {
            'time': timestamp,
            'type': 'FAILED',
            'user': user,
            'ip': ip,
            'msg': f"{method_ru} (порт {port})"
        }
        
        target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
        emoji_str = "🖥" if vmid == 0 else "🔒"
        title_str = "ОШИБКА SSH АВТОРИЗАЦИИ на Хосте!" if vmid == 0 else "ОШИБКА АВТОРИЗАЦИИ в LXC!"
        
        msg = get_ssh_fail_alert(title_str, emoji_str, target_str, user, ip, method_ru, timestamp, line, geoip_info=geoip_info)
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
        emoji_str = "🖥" if vmid == 0 else "🔒"
        title_str = "Выполнение SUDO-команды на Хосте!" if vmid == 0 else "Выполнение SUDO-команды в LXC!"
        
        msg = get_sudo_alert(title_str, emoji_str, target_str, user, run_as, command, timestamp, line)
        return event, msg

    # 5. SSH сессия закрыта (Connection closed / session closed)
    if "sshd" in line and "[preauth]" not in line:
        # 5.1 Connection closed
        conn_close = re.search(r"sshd(?:-session)?\[(\d+)\]: Connection closed by user (\S+) (\S+) port (\d+)", line)
        if conn_close:
            pid_str, user, ip, port = conn_close.groups()
            pid = int(pid_str)
            event = {
                'time': timestamp,
                'type': 'CLOSE',
                'user': user,
                'ip': ip,
                'pid': pid,
                'msg': f"SSH соединение закрыто (порт {port})"
            }
            target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
            msg = get_ssh_close_alert(target_str, user, ip, timestamp, line)
            return event, msg

        # 5.2 pam_unix session closed
        pam_close = re.search(r"sshd(?:-session)?\[(\d+)\]: pam_unix\(sshd:session\): session closed for user (\S+)", line)
        if pam_close:
            pid_str, user = pam_close.groups()
            pid = int(pid_str)
            event = {
                'time': timestamp,
                'type': 'CLOSE',
                'user': user,
                'pid': pid,
                'msg': f"SSH сессия закрыта для {user}"
            }
            target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
            msg = get_ssh_close_alert(target_str, user, None, timestamp, line)
            return event, msg

    return None, None
