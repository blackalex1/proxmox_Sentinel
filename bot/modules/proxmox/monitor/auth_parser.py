from typing import Tuple, Optional, Dict, Any
from core.messages import (
    get_pve_web_login_alert,
    get_pve_web_fail_alert,
    get_ssh_login_alert,
    get_ssh_fail_alert,
    get_sudo_alert,
    get_ssh_close_alert
)
from core import sentinel_core_bridge
from .utils import get_geoip_info

async def parse_auth_line(line: str, vmid: int, timestamp: str, container_name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Парсинг логов аутентификации контейнера/хоста через Go-ядро sentinel_core.
    Возвращает кортеж (event_dict, alert_message) или (None, None).
    """
    core_ev = sentinel_core_bridge.parse_auth_line(line)
    if not core_ev:
        return None, None

    ev_type = core_ev.get("type")
    user = core_ev.get("user") or "unknown"
    ip = core_ev.get("source_ip") or ""
    pid = core_ev.get("pid")
    port = core_ev.get("port") or 0
    auth_method = core_ev.get("auth_method") or ""
    fingerprint = core_ev.get("key_fingerprint") or ""
    command = core_ev.get("command") or ""
    run_as = core_ev.get("run_as") or "root"
    reason = core_ev.get("reason") or ""

    target_str = "Хост Proxmox VE" if vmid == 0 else f"LXC {vmid} ({container_name})"
    emoji_str = "🖥" if vmid == 0 else "🔒"

    # 1. Proxmox VE Web GUI login
    if ev_type == "PVE_WEB_LOGIN":
        event = {
            'time': timestamp,
            'type': 'SUCCESS',
            'user': user,
            'ip': 'WEB_GUI',
            'msg': "Вход в Proxmox VE Web GUI"
        }
        msg = get_pve_web_login_alert(target_str, user, timestamp, line)
        return event, msg

    # 2. Proxmox VE Web GUI failure
    if ev_type == "PVE_WEB_FAIL":
        geoip_info = await get_geoip_info(ip) if ip else None
        event = {
            'time': timestamp,
            'type': 'FAILED',
            'user': user,
            'ip': ip,
            'msg': f"Ошибка Web GUI: {reason}"
        }
        msg = get_pve_web_fail_alert(target_str, user, ip, reason, timestamp, line, geoip_info=geoip_info)
        return event, msg

    # 3. SSH Successful login
    if ev_type == "SSH_LOGIN":
        geoip_info = await get_geoip_info(ip) if ip else None
        event = {
            'time': timestamp,
            'type': 'SUCCESS',
            'user': user,
            'ip': ip,
            'pid': pid,
            'msg': f"Вход через {auth_method} (порт {port})"
        }
        if fingerprint:
            event['fingerprint'] = fingerprint

        title_str = "Успешная SSH авторизация на Хосте!" if vmid == 0 else "Успешная SSH авторизация в LXC!"
        msg = get_ssh_login_alert(title_str, emoji_str, target_str, user, ip, auth_method, fingerprint, timestamp, line, geoip_info=geoip_info)
        return event, msg

    # 4. SSH Failed login
    if ev_type == "SSH_FAILED_AUTH":
        geoip_info = await get_geoip_info(ip) if ip else None
        method_ru = "Неверный пароль" if auth_method == "password" else "Неверный SSH-ключ"
        event = {
            'time': timestamp,
            'type': 'FAILED',
            'user': user,
            'ip': ip,
            'msg': f"{method_ru} (порт {port})"
        }
        title_str = "ОШИБКА SSH АВТОРИЗАЦИИ на Хосте!" if vmid == 0 else "ОШИБКА АВТОРИЗАЦИИ в LXC!"
        msg = get_ssh_fail_alert(title_str, emoji_str, target_str, user, ip, method_ru, timestamp, line, geoip_info=geoip_info)
        return event, msg

    # 5. SUDO execution
    if ev_type == "SUDO_EXEC":
        event = {
            'time': timestamp,
            'type': 'SUDO',
            'user': user,
            'ip': 'LOCAL',
            'msg': f"sudo [{run_as}]: {command[:50]}"
        }
        title_str = "Выполнение SUDO-команды на Хосте!" if vmid == 0 else "Выполнение SUDO-команды в LXC!"
        msg = get_sudo_alert(title_str, emoji_str, target_str, user, run_as, command, timestamp, line)
        return event, msg

    # 6. SSH Logout / Closed session
    if ev_type == "SSH_LOGOUT":
        event = {
            'time': timestamp,
            'type': 'CLOSE',
            'user': user,
            'ip': ip,
            'pid': pid,
            'msg': f"SSH соединение закрыто (порт {port})" if port else f"SSH сессия закрыта для {user}"
        }
        msg = get_ssh_close_alert(target_str, user, ip if ip else None, timestamp, line)
        return event, msg

    return None, None
