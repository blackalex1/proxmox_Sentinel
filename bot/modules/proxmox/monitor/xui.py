import asyncio
import logging
import datetime
import os
import re

from core.config import VPN_VMID, VPN_OFFLINE_TIMEOUT, VPN_IGNORE_USERS
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
        
        # Извлекаем IP-адрес клиента (поддерживаем разные форматы дат и времени)
        client_ip = "Неизвестный"
        ip_match = re.search(r"(?:(?:\d{4}[/\-]\d{2}[/\-]\d{2}\s+\d{2}:\d{2}:\d{2})\s+)?(\[[0-9a-fA-F:]+\]|[\d\.]+):(\d+)", line)
        if ip_match:
            client_ip = ip_match.group(1).replace("[", "").replace("]", "")


        # Если пользователь в списке игнорируемых — просто тихо обновляем время активности
        if email in VPN_IGNORE_USERS:
            active_clients[email] = {"last_seen": now, "ip": client_ip}
            return
            
        # Если пользователя не было в активных сессиях — он только что вошел!
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
            # Если уже активен — просто обновляем время последней активности и IP (тихо)
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
                
                if now - last_seen > VPN_OFFLINE_TIMEOUT:
                    offline_users.append((email, client_ip))
                    
            for email, client_ip in offline_users:
                # Удаляем из активных
                active_clients.pop(email, None)
                
                # Если пользователь в списке игнорируемых — отключаем тихо
                if email in VPN_IGNORE_USERS:
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
    
    # 1. Находим лог-файл доступа Xray на файловой системе хоста
    log_path = find_xray_access_log_path(VPN_VMID)
    
    # 2. Запускаем фоновый воркер проверки таймаутов
    asyncio.create_task(monitor_xui_offline_check())
    
    if log_path:
        # Используем быстрый файловый LogTailer прямо на хосте
        tailer = LogTailer(log_path, handle_xray_log_line)
        await tailer.start()
        logging.info(f"Запущен прямой мониторинг файла логов доступа Xray: {log_path}")
    else:
        # 3. Если на хосте путь не найден (например, из-за ZFS/LVM-thin), 
        # пытаемся найти файл внутри самого контейнера и запустить tail -f через pct exec!
        container_log_path = find_xray_access_log_path_inside_container(VPN_VMID)
        if container_log_path:
            cmd = ["pct", "exec", str(VPN_VMID), "--", "tail", "-f", "-n", "0", container_log_path]
            tailer = LogTailer(cmd, handle_xray_log_line)
            await tailer.start()
            logging.info(f"Запущен мониторинг access.log через pct exec tail ({container_log_path}) для LXC {VPN_VMID}.")
        else:
            # Резервный вариант: если файл не найден, стримим логи через pct exec из journalctl
            service_name = detect_xui_service(VPN_VMID)
            cmd = ["pct", "exec", str(VPN_VMID), "--", "journalctl", "-u", service_name, "-f", "-n", "0"]
            tailer = LogTailer(cmd, handle_xray_log_line)
            await tailer.start()
            logging.info(f"Файл access.log не найден. Запущено резервное отслеживание через pct exec journalctl ({service_name}) для LXC {VPN_VMID}.")


# Память для предотвращения дублирования входов в панель 3X-UI: (username, log_timestamp) -> IP
recent_panel_logins = {}

async def handle_xui_panel_log_line(line):
    """Парсинг логов веб-панели 3X-UI для обнаружения входов в админку с дедупликацией IP."""
    try:
        if "logged in successfully" not in line:
            return
            
        # Извлекаем таймстамп лога (первые 19 символов, например "2026/05/23 20:51:27")
        log_ts = "unknown"
        ts_match = re.match(r"^(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})", line)
        if ts_match:
            log_ts = ts_match.group(1)
            
        # Извлекаем имя пользователя
        username = "Unknown"
        user_match = re.search(r"X-UI:\s*(\S+)\s+logged in", line)
        if user_match:
            username = user_match.group(1).strip()
        else:
            # Резервный поиск
            user_match = re.search(r"(\S+)\s+logged in successfully", line)
            if user_match:
                username = user_match.group(1).strip()
                
        # Извлекаем IP-адрес
        ip_address = None
        ip_match = re.search(r"Ip Address:\s*([\d\.\:a-fA-F]+)", line)
        if ip_match:
            ip_address = ip_match.group(1).strip()
            
        cache_key = (username, log_ts)
        
        if ip_address:
            # Если строка содержит IP-адрес, мы сразу шлем алерт и записываем в кэш
            recent_panel_logins[cache_key] = ip_address
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            msg = (f"🔑 <b>[3X-UI Web Panel] Успешный вход в панель!</b>\n\n"
                   f"👤 Администратор: <code>{username}</code>\n"
                   f"🌐 IP-адрес: <code>{ip_address}</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            await send_alert_to_admins(msg)
            logging.info(f"[3X-UI Panel Login] Admin {username} logged in from {ip_address}")
        else:
            # Если строка НЕ содержит IP-адрес, ждем 0.5 сек, давая прийти строке с IP
            await asyncio.sleep(0.5)
            
            # Проверяем, не был ли уже отправлен алерт с IP-адресом для этого входа
            if cache_key in recent_panel_logins:
                # Уже отправили алерт с IP, этот дубликат без IP игнорируем!
                return
                
            # Если за полсекунды строка с IP так и не пришла, шлем алерт с IP "Неизвестный"
            recent_panel_logins[cache_key] = "Неизвестный"
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            msg = (f"🔑 <b>[3X-UI Web Panel] Успешный вход в панель!</b>\n\n"
                   f"👤 Администратор: <code>{username}</code>\n"
                   f"🌐 IP-адрес: <code>Неизвестный</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            await send_alert_to_admins(msg)
            logging.info(f"[3X-UI Panel Login] Admin {username} logged in (IP address not logged)")
            
        # Ограничиваем размер кэша
        if len(recent_panel_logins) > 50:
            for k in list(recent_panel_logins.keys())[:20]:
                recent_panel_logins.pop(k, None)
                
    except Exception as e:
        logging.error(f"Ошибка при обработке лог-линии панели X-UI: {e}")


async def monitor_xui_panel_logins():
    """Фоновый воркер для мониторинга входов в веб-панель 3X-UI."""
    import platform
    if platform.system() != 'Linux':
        return
        
    logging.info("Запуск системы отслеживания входов в веб-панель 3X-UI...")
    try:
        service_name = detect_xui_service(VPN_VMID)
        cmd = ["pct", "exec", str(VPN_VMID), "--", "journalctl", "-u", service_name, "-f", "-n", "0"]
        tailer = LogTailer(cmd, handle_xui_panel_log_line)
        await tailer.start()
        logging.info(f"Запущен мониторинг входов 3X-UI Panel через journalctl для LXC {VPN_VMID}.")
    except Exception as e:
        logging.error(f"Ошибка при запуске мониторинга входов 3X-UI Panel: {e}")
