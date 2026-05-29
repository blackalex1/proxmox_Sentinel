import asyncio
import logging
import datetime
import json
import re
from core.config import settings
from modules.proxmox.monitor.utils import send_alert_to_admins

from .alerts.cards import handle_hysteria_connect
from .alerts.disconnect import handle_hysteria_disconnect
from .alerts.state import (
    recent_hysteria_violations,
    recent_remote_traffic_alerts,
    save_violations_state,
    save_traffic_alerts_state
)
from .ips import block_remote_hysteria_user, unblock_remote_hysteria_user

async def handle_remote_hysteria_line(line, server=None, silent=False):
    """Парсинг JSON логов подключений и TCP-ошибок Hysteria 2."""
    if not server:
        return
    try:
        if "client connected" in line:
            match = re.search(r"client connected\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                
                if username in settings.vpn_ignore_users:
                    return
                    
                await handle_hysteria_connect(server, username, client_ip, silent=silent)
                if not silent:
                    logging.info(f"[Remote Hysteria {server['ip']}] Client {username} connected from {client_ip}")

        elif "client disconnected" in line:
            match = re.search(r"client disconnected\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                
                if username in settings.vpn_ignore_users:
                    return
                    
                await handle_hysteria_disconnect(server, username, client_ip, silent=silent)
                if not silent:
                    logging.info(f"[Remote Hysteria {server['ip']}] Client {username} disconnected")

        elif "TCP error" in line:
            if silent:
                return
            match = re.search(r"TCP error\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                req_addr = data.get("reqAddr", "")
                err_msg = data.get("error", "")
                
                if not req_addr or username in settings.vpn_ignore_users:
                    return
                    
                if ":" in req_addr:
                    req_host, req_port_str = req_addr.rsplit(":", 1)
                    req_port = int(req_port_str) if req_port_str.isdigit() else 0
                else:
                    req_host = req_addr
                    req_port = 0
                    
                is_sensitive = req_port in [22, 3389, 3306, 5432, 27017, 8006]
                is_whitelisted = req_port in [80, 443, 53, 123] or not req_port
                
                now = asyncio.get_event_loop().time()
                throttle_key = f"{server['ip']}_{username}_{req_port}"
                
                if is_sensitive:
                    import time as pytime
                    curr_time = pytime.time()
                    if username not in recent_hysteria_violations:
                        recent_hysteria_violations[username] = []
                    recent_hysteria_violations[username].append(curr_time)
                    
                    recent_hysteria_violations[username] = [t for t in recent_hysteria_violations[username] if curr_time - t <= 600]
                    await save_violations_state()
                    
                    last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                    is_throttled = now - last_alert < 30
                    
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    if len(recent_hysteria_violations[username]) >= 3:
                        recent_hysteria_violations[username] = []
                        await save_violations_state()
                        block_success = await block_remote_hysteria_user(server, username)
                        
                        if block_success:
                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🔓 Разблокировать пользователя", callback_data=f"unblock_hysteria:{username}:{server['ip']}")]
                            ])
                            
                            block_msg = (f"🛑 <b>[Hysteria Auto-Block: {server['ip']}] Пользователь заблокирован!</b>\n\n"
                                         f"👤 Пользователь: <code>{username}</code>\n"
                                         f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                                         f"🎯 Причина: Превышен лимит сетевых нарушений (3+ попыток сканирования чувствительных портов за 10 минут).\n"
                                         f"🕒 Время блокировки: <code>{timestamp}</code>")
                            await send_alert_to_admins(block_msg, reply_markup=kb)
                            return
                    
                    if not is_throttled:
                        recent_remote_traffic_alerts[throttle_key] = now
                        await save_traffic_alerts_state()
                        msg = (f"🚨 <b>[VPS Hysteria Security: {server['ip']}] Попытка доступа к чувствительному порту!</b>\n\n"
                               f"👤 Пользователь: <code>{username}</code>\n"
                               f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                               f"🎯 Целевой хост: <code>{req_host}:{req_port}</code>\n"
                               f"ℹ️ Ошибка: <i>{err_msg}</i>\n"
                               f"🕒 Время: <code>{timestamp}</code>")
                        await send_alert_to_admins(msg)
                elif not is_whitelisted and settings.alert_vpn_client_unusual_ports:
                    last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                    if now - last_alert < 60:
                        return
                    recent_remote_traffic_alerts[throttle_key] = now
                    await save_traffic_alerts_state()
                    
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    msg = (f"⚠️ <b>[VPS Hysteria Warning: {server['ip']}] Нетипичный исходящий порт VPN-клиента</b>\n\n"
                           f"👤 Пользователь: <code>{username}</code>\n"
                           f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                           f"🎯 Назначение: <code>{req_host}:{req_port}</code>\n"
                           f"ℹ️ Ошибка: <i>{err_msg}</i>\n"
                           f"🕒 Время: <code>{timestamp}</code>")
                    await send_alert_to_admins(msg)
    except Exception as e:
        logging.error(f"Ошибка при разборе лог-линии Hysteria 2 на {server['ip']}: {e}")
