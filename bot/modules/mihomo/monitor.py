import asyncio
import aiohttp
import logging
import datetime
import re
from core.config import settings
from modules.proxmox.monitor.utils import send_alert_to_admins

async def find_mihomo_connection_id(src_ip, src_port, dst_port):
    """Ищет ID активного соединения в Mihomo по IP/порту источника и порту назначения."""
    try:
        api_url = settings.mihomo_api_url
        headers = {}
        if settings.mihomo_api_secret:
            headers["Authorization"] = f"Bearer {settings.mihomo_api_secret}"
            
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/connections", headers=headers, timeout=2) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    connections = data.get("connections", [])
                    for conn in connections:
                        metadata = conn.get("metadata", {})
                        conn_src_ip = metadata.get("sourceIP", "")
                        conn_src_port = int(metadata.get("sourcePort", 0)) if str(metadata.get("sourcePort", "")).isdigit() else 0
                        conn_dst_port = int(metadata.get("destinationPort", 0)) if str(metadata.get("destinationPort", "")).isdigit() else 0
                        
                        if conn_src_ip == src_ip and conn_src_port == src_port and conn_dst_port == dst_port:
                            return conn.get("id")
    except Exception as e:
        logging.error(f"Ошибка при поиске ID соединения в Mihomo: {e}")
    return None

async def close_mihomo_connection(conn_id):
    """Разрывает активное соединение в Mihomo по его ID."""
    try:
        api_url = settings.mihomo_api_url
        headers = {}
        if settings.mihomo_api_secret:
            headers["Authorization"] = f"Bearer {settings.mihomo_api_secret}"
            
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{api_url}/connections/{conn_id}", headers=headers, timeout=2) as resp:
                if resp.status in (200, 204):
                    return True
    except Exception as e:
        logging.error(f"Ошибка при разрыве соединения {conn_id} в Mihomo: {e}")
    return False

recent_mihomo_violations = {}

async def handle_mihomo_log_line(payload):
    """
    Разбор лог-строк Mihomo/Clash.
    Пример: "[TCP] 192.168.1.50:52627 --> 51.159.186.137:22 match Direct"
    """
    try:
        # IPv4/IPv6 regexp для захвата протокола, источника и назначения
        match = re.search(r"\[(TCP|UDP)\]\s+(\[[0-9a-fA-F:]+\]|[\d\.]+):(\d+)\s+-->\s+(\[[0-9a-fA-F:]+\]|[\w\.\-]+):(\d+)", payload)
        if not match:
            return
            
        proto = match.group(1)
        src_ip = match.group(2).replace("[", "").replace("]", "")
        src_port = int(match.group(3))
        dst_host = match.group(4).replace("[", "").replace("]", "")
        dst_port = int(match.group(5))
        
        # 1. Проверяем, идет ли запрос на чувствительный порт
        is_sensitive = dst_port in settings.monitor_lxc_ports_sensitive
        if not is_sensitive:
            return
            
        import time as pytime
        curr_time = pytime.time()
        
        # 2. Обработка автоматического бана (Auto-Ban)
        if settings.router_ssh_enable and settings.mihomo_auto_ban:
            if src_ip not in recent_mihomo_violations:
                recent_mihomo_violations[src_ip] = []
            recent_mihomo_violations[src_ip].append(curr_time)
            
            # Очищаем нарушения старше 10 минут (600 секунд)
            recent_mihomo_violations[src_ip] = [t for t in recent_mihomo_violations[src_ip] if curr_time - t <= 600]
            
            if len(recent_mihomo_violations[src_ip]) >= settings.mihomo_max_violations:
                recent_mihomo_violations[src_ip] = []  # Сбрасываем счетчик после бана
                
                from .router import ban_router_ip
                success, desc = await ban_router_ip(src_ip)
                if success:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🟢 Разблокировать IP на роутере", callback_data=f"mihomo_unblock:{src_ip}")]
                    ])
                    
                    msg = (f"🛑 <b>[Router Security: Auto-Block] Устройство заблокировано автоматически!</b>\n\n"
                           f"👤 <b>Заблокированный IP:</b> <code>{src_ip}</code>\n"
                           f"🎯 <b>Причина:</b> Превышен лимит сетевых нарушений ({settings.mihomo_max_violations}+ попыток доступа к чувствительным портам за 10 минут).\n"
                           f"🧭 <b>Последняя цель:</b> <code>{dst_host}:{dst_port}</code> ({proto})\n"
                           f"🕒 <b>Время блокировки:</b> <code>{timestamp}</code>")
                           
                    await send_alert_to_admins(msg, reply_markup=kb)
                    logging.warning(f"[Mihomo Auto-Ban] Устройство {src_ip} автоматически забанено на роутере!")
                    return
            
        # 3. Троттлинг одинаковых предупреждений (в пределах 15 секунд)
        from modules.proxmox.monitor.state import lxc_alert_throttle
        
        throttle_key = (f"router_{src_ip}", 'threat', 'sensitive_port', dst_host, dst_port)
        last_alert = lxc_alert_throttle.get(throttle_key, 0)
        if curr_time - last_alert < 15:
            return
        lxc_alert_throttle[throttle_key] = curr_time
        
        # 3. Пытаемся найти ID активного соединения в Mihomo для предоставления кнопки разрыва
        conn_id = await find_mihomo_connection_id(src_ip, src_port, dst_port)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        if conn_id:
            buttons.append([InlineKeyboardButton(text="⚡️ Разорвать соединение", callback_data=f"mihomo_kill:{conn_id}")])
            
        if settings.router_ssh_enable:
            buttons.append([InlineKeyboardButton(text="🛑 Заблокировать IP на роутере", callback_data=f"mihomo_block:{src_ip}")])
            
        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        
        # 4. Отправляем алерт безопасности в Telegram
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        msg = (f"🚨 <b>[Router Security: Mihomo] Обнаружен доступ к чувствительному порту!</b>\n\n"
               f"🌐 Протокол: <code>{proto}</code>\n"
               f"👤 Устройство (Источник): <code>{src_ip}:{src_port}</code>\n"
               f"🎯 Назначение: <code>{dst_host}:{dst_port}</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
               
        await send_alert_to_admins(msg, reply_markup=kb)
        logging.warning(f"[Mihomo IPS] Устройство {src_ip} обратилось к чувствительному порту {dst_host}:{dst_port}")
        
    except Exception as e:
        logging.error(f"Ошибка при обработке строки логов Mihomo: {e}")

async def monitor_mihomo_connections():
    """Фоновый воркер для подключения по WebSocket к REST API роутера Mihomo."""
    if not settings.mihomo_monitor_enable:
        return
        
    logging.info("Запуск системы отслеживания трафика роутера через Mihomo API...")
    
    # Формируем URL для WebSocket
    # http://192.168.1.1:9090 -> ws://192.168.1.1:9090/logs
    api_url = settings.mihomo_api_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{api_url}/logs?level=info"
    if settings.mihomo_api_secret:
        ws_url += f"&token={settings.mihomo_api_secret}"
        
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if settings.mihomo_api_secret:
                    headers["Authorization"] = f"Bearer {settings.mihomo_api_secret}"
                    
                async with session.ws_connect(ws_url, headers=headers, timeout=10) as ws:
                    logging.info(f"[Mihomo Monitor] Успешно подключено по WebSocket к {ws_url}")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            import json
                            try:
                                data = json.loads(msg.data)
                                payload = data.get("payload", "")
                                if payload:
                                    await handle_mihomo_log_line(payload)
                            except json.JSONDecodeError:
                                # Если пришел сырой текст
                                await handle_mihomo_log_line(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            logging.warning(f"[Mihomo Monitor] WebSocket соединение закрыто: {msg.type}")
                            break
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.warning(f"[Mihomo Monitor] Ошибка подключения по WebSocket к роутеру: {e}")
            
        logging.info("[Mihomo Monitor] Переподключение через 15 секунд...")
        await asyncio.sleep(15)
