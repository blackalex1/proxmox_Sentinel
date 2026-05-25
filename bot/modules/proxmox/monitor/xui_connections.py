import asyncio
import logging
import datetime
import os
import re

from core.config import settings
from .utils import LogTailer, send_alert_to_admins, detect_xui_service

# Активные сессии клиентов: email -> {"last_seen": timestamp, "ip": client_ip}
active_clients = {}

def find_xray_access_log_path(vmid):
    """Поиск пути к access.log контейнера Xray на файловой системе хоста."""
    rootfs = f"/var/lib/lxc/{vmid}/rootfs"
    possible_paths = [
        f"{rootfs}/usr/local/x-ui/access.log",
        f"{rootfs}/var/log/xray/access.log",
        f"{rootfs}/etc/x-ui/xray-access.log"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return None

async def handle_xray_log_line(line):
    """Обработка лог-линий Xray для отслеживания сессий клиентов."""
    try:
        if "email:" not in line:
            return
            
        # Извлекаем email пользователя
        match = re.search(r"email:\s*(\S+)", line)
        if not match:
            return
            
        email = match.group(1).strip()
        now = asyncio.get_event_loop().time()
        
        # Извлекаем IP-адрес клиента
        client_ip = "Неизвестный"
        ip_match = re.search(r"(?:(?:\d{4}[/\-]\d{2}[/\-]\d{2}\s+\d{2}:\d{2}:\d{2})\s+)?(\[[0-9a-fA-F:]+\]|[\d\.]+):(\d+)", line)
        if ip_match:
            client_ip = ip_match.group(1).replace("[", "").replace("]", "")

        # Если пользователь в списке игнорируемых
        if email in settings.vpn_ignore_users:
            active_clients[email] = {"last_seen": now, "ip": client_ip}
            return
            
        if email not in active_clients:
            active_clients[email] = {"last_seen": now, "ip": client_ip}
            timestamp_str = datetime.datetime.now().strftime("%H:%M:%S")
            msg = (f"🟢 <b>Клиент подключился к VPN!</b>\n\n"
                   f"👤 Пользователь: <code>{email}</code>\n"
                   f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                   f"🕒 Время: <code>{timestamp_str}</code>")
            await send_alert_to_admins(msg)
            logging.info(f"Клиент {email} вошел в сеть с IP {client_ip} (активных сессий: {len(active_clients)})")
        else:
            active_clients[email] = {"last_seen": now, "ip": client_ip}
            
    except Exception as e:
        logging.error(f"Ошибка при обработке лог-строки Xray: {e}")

async def monitor_xui_offline_check():
    """Периодический воркер для проверки таймаутов отключения клиентов."""
    logging.info("Запущен фоновый воркер проверки офлайн-таймаутов 3X-UI...")
    while True:
        try:
            await asyncio.sleep(20)
            now = asyncio.get_event_loop().time()
            offline_users = []
            
            for email, data in list(active_clients.items()):
                last_seen = data["last_seen"] if isinstance(data, dict) else data
                client_ip = data["ip"] if isinstance(data, dict) else "Неизвестный"
                
                if now - last_seen > settings.vpn_offline_timeout:
                    offline_users.append((email, client_ip))
                    
            for email, client_ip in offline_users:
                active_clients.pop(email, None)
                
                if email in settings.vpn_ignore_users:
                    logging.info(f"Клиент {email} отключился по таймауту (тихий режим, активных сессий: {len(active_clients)})")
                    continue
                    
                timestamp_str = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🔴 <b>Клиент отключился от VPN</b>\n\n"
                       f"👤 Пользователь: <code>{email}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🕒 Время: <code>{timestamp_str}</code>")
                await send_alert_to_admins(msg)
                logging.info(f"Клиент {email} отключился по таймауту с IP {client_ip} (активных сессий: {len(active_clients)})")
                
        except Exception as e:
            logging.error(f"Ошибка в воркере проверки офлайн-таймаутов: {e}")

def find_xray_access_log_path_inside_container(vmid):
    """Поиск пути к access.log внутри самого LXC контейнера."""
    import subprocess
    import platform
    if platform.system() != 'Linux':
        return None
    possible_paths = [
        "/usr/local/x-ui/access.log",
        "/var/log/xray/access.log",
        "/etc/x-ui/xray-access.log"
    ]
    for p in possible_paths:
        try:
            cmd = ["pct", "exec", str(vmid), "--", "test", "-f", p]
            res = subprocess.run(cmd, capture_output=True, timeout=2)
            if res.returncode == 0:
                return p
        except Exception:
            pass
    return None

async def monitor_xui_connections():
    """Инициализация tailer-а логов Xray на хосте для мониторинга входов/выходов."""
    logging.info("Запуск системы отслеживания подключений 3X-UI через access.log...")
    
    log_path = find_xray_access_log_path(settings.vpn_vmid)
    asyncio.create_task(monitor_xui_offline_check())
    
    if log_path:
        tailer = LogTailer(log_path, handle_xray_log_line)
        await tailer.start()
        logging.info(f"Запущен прямой мониторинг файла логов доступа Xray: {log_path}")
    else:
        container_log_path = find_xray_access_log_path_inside_container(settings.vpn_vmid)
        if container_log_path:
            cmd = ["pct", "exec", str(settings.vpn_vmid), "--", "tail", "-f", "-n", "0", container_log_path]
            tailer = LogTailer(cmd, handle_xray_log_line)
            await tailer.start()
            logging.info(f"Запущен мониторинг access.log через pct exec tail ({container_log_path}) для LXC {settings.vpn_vmid}.")
        else:
            service_name = detect_xui_service(settings.vpn_vmid)
            cmd = ["pct", "exec", str(settings.vpn_vmid), "--", "stdbuf", "-oL", "journalctl", "-u", service_name, "-f", "-n", "0"]
            tailer = LogTailer(cmd, handle_xray_log_line)
            await tailer.start()
            logging.info(f"Файл access.log не найден. Запущено резервное отслеживание через pct exec journalctl ({service_name}) для LXC {settings.vpn_vmid}.")
