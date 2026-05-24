import asyncio
import logging
import json
import datetime
import re
from core.config import VPN_IGNORE_USERS, ALERT_VPN_CLIENT_UNUSUAL_PORTS
from modules.proxmox.monitor.utils import send_alert_to_admins
from .ssh import run_remote_ssh_cmd, get_ssh_base_cmd

# Нарушения пользователей Hysteria: username -> list of timestamps
recent_hysteria_violations = {}

# Память для троттлинга алертов трафика удаленного VPS (IP -> timestamp)
recent_remote_traffic_alerts = {}

async def block_remote_hysteria_user(server, username):
    """Блокирует пользователя Hysteria на конкретном удаленном VPS через MongoDB и сбрасывает сессию."""
    eval_str = f"db.users.updateOne({{_id: '{username}'}}, {{\\$set: {{blocked: true}}}})"
    db_cmd = [f"mongosh blitz_panel --quiet --eval \"{eval_str}\""]
    success, stdout, stderr = await run_remote_ssh_cmd(server, db_cmd)
    if success:
        logging.info(f"[Hysteria IPS {server['ip']}] Пользователь {username} успешно заблокирован в MongoDB.")
        
        kick_script = (
            'import json, urllib.request; '
            'cfg = json.load(open("/etc/hysteria/config.json")); '
            'ts = cfg.get("trafficStats", {}); '
            'secret = ts.get("secret", ""); '
            'port = ts.get("listen", "").split(":")[-1]; '
            'req = urllib.request.Request(f"http://127.0.0.1:{port}/kick", '
            f'data=json.dumps(["{username}"]).encode(), '
            'headers={"Authorization": secret, "Content-Type": "application/json"}, method="POST"); '
            'urllib.request.urlopen(req)'
        )
        kick_cmd = [f"python3 -c '{kick_script}'"]
        kick_success, _, kick_err = await run_remote_ssh_cmd(server, kick_cmd)
        if kick_success:
            logging.info(f"[Hysteria IPS {server['ip']}] Активные сессии пользователя {username} успешно сброшены.")
        else:
            logging.warning(f"[Hysteria IPS {server['ip']}] Не удалось сбросить активные сессии {username}: {kick_err}")
    else:
        logging.error(f"[Hysteria IPS {server['ip']}] Не удалось заблокировать {username} на VPS: {stderr}")
    return success

async def unblock_remote_hysteria_user(server, username):
    """Разблокирует пользователя Hysteria на конкретном удаленном VPS через MongoDB."""
    if not server:
        logging.error(f"[Hysteria IPS] Разблокировка невозможна: сервер не передан.")
        return False
        
    eval_str = f"db.users.updateOne({{_id: '{username}'}}, {{\\$set: {{blocked: false}}}})"
    cmd = [f"mongosh blitz_panel --quiet --eval \"{eval_str}\""]
    success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
    if success:
        logging.info(f"[Hysteria IPS {server['ip']}] Пользователь {username} успешно разблокирован в MongoDB.")
    else:
        logging.error(f"[Hysteria IPS {server['ip']}] Не удалось разблокировать {username}: {stderr}")
    return success

async def handle_remote_hysteria_line(line, server=None):
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
                
                if username in VPN_IGNORE_USERS:
                    return
                    
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🟢 <b>[VPS Hysteria: {server['ip']}] Клиент подключился!</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🕒 Время: <code>{timestamp}</code>")
                await send_alert_to_admins(msg)
                logging.info(f"[Remote Hysteria {server['ip']}] Client {username} connected from {client_ip}")

        elif "client disconnected" in line:
            match = re.search(r"client disconnected\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                
                if username in VPN_IGNORE_USERS:
                    return
                    
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🔴 <b>[VPS Hysteria: {server['ip']}] Клиент отключился</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🕒 Время: <code>{timestamp}</code>")
                await send_alert_to_admins(msg)
                logging.info(f"[Remote Hysteria {server['ip']}] Client {username} disconnected")

        elif "TCP error" in line:
            match = re.search(r"TCP error\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                req_addr = data.get("reqAddr", "")
                err_msg = data.get("error", "")
                
                if not req_addr or username in VPN_IGNORE_USERS:
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
                    
                    last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                    is_throttled = now - last_alert < 30
                    
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    if len(recent_hysteria_violations[username]) >= 3:
                        recent_hysteria_violations[username] = []
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
                        msg = (f"🚨 <b>[VPS Hysteria Security: {server['ip']}] Попытка доступа к чувствительному порту!</b>\n\n"
                               f"👤 Пользователь: <code>{username}</code>\n"
                               f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                               f"🎯 Целевой хост: <code>{req_host}:{req_port}</code>\n"
                               f"ℹ️ Ошибка: <i>{err_msg}</i>\n"
                               f"🕒 Время: <code>{timestamp}</code>")
                        await send_alert_to_admins(msg)
                elif not is_whitelisted and ALERT_VPN_CLIENT_UNUSUAL_PORTS:
                    last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                    if now - last_alert < 60:
                        return
                    recent_remote_traffic_alerts[throttle_key] = now
                    
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
