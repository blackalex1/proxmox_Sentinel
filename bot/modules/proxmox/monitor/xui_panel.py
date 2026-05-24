import asyncio
import logging
import datetime
import re

from core.config import VPN_VMID
from .utils import LogTailer, send_alert_to_admins, detect_xui_service

# Память для предотвращения дублирования входов в панель 3X-UI: (username, ip) -> last_notification_time
recent_panel_logins = {}

async def handle_xui_panel_log_line(line):
    """Парсинг логов веб-панели 3X-UI для обнаружения входов в админку с дедупликацией IP."""
    try:
        if "logged in successfully" not in line or "Ip Address:" not in line:
            return
            
        # Извлекаем имя пользователя
        username = "Unknown"
        user_match = re.search(r"X-UI:\s*(\S+)\s+logged in", line)
        if user_match:
            username = user_match.group(1).strip()
        else:
            user_match = re.search(r"(\S+)\s+logged in successfully", line)
            if user_match:
                username = user_match.group(1).strip()
                
        # Извлекаем IP-адрес
        ip_address = "Неизвестный"
        ip_match = re.search(r"Ip Address:\s*([\d\.\:a-fA-F]+)", line)
        if ip_match:
            ip_address = ip_match.group(1).strip()
            
        import time
        cache_key = (username, ip_address)
        now_ts = time.time()
        
        # Коллаун 10 секунд для предотвращения спама при быстрых повторных входах/запросах от бота
        if cache_key in recent_panel_logins:
            last_time = recent_panel_logins[cache_key]
            if now_ts - last_time < 10:
                return
                
        recent_panel_logins[cache_key] = now_ts
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg = (f"🔑 <b>[3X-UI Web Panel] Успешный вход в панель!</b>\n\n"
               f"👤 Администратор: <code>{username}</code>\n"
               f"🌐 IP-адрес: <code>{ip_address}</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
        await send_alert_to_admins(msg)
        logging.info(f"[3X-UI Panel Login] Admin {username} logged in from {ip_address}")
        
        if len(recent_panel_logins) > 50:
            # Очищаем устаревшие записи
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
        cmd = ["pct", "exec", str(VPN_VMID), "--", "stdbuf", "-oL", "journalctl", "-u", service_name, "-f", "-n", "0"]
        tailer = LogTailer(cmd, handle_xui_panel_log_line)
        await tailer.start()
        logging.info(f"Запущен мониторинг входов 3X-UI Panel через journalctl для LXC {VPN_VMID}.")
    except Exception as e:
        logging.error(f"Ошибка при запуске мониторинга входов 3X-UI Panel: {e}")
