import asyncio
import logging
import aiohttp
from core.config import settings
from .mihomo_handlers import (
    handle_mihomo_log_line,
    handle_new_mihomo_connection
)
from .ssh_workers import monitor_router_conntrack, monitor_router_syslog, monitor_router_syslog_v2

async def monitor_mihomo_connections():
    """Фоновый воркер для мониторинга трафика роутера через Mihomo API или SSH conntrack/iptables/nftables."""
    mode = getattr(settings, 'mihomo_monitor_mode', 'polling').lower()
    
    # Поддерживаем два основных режима:
    # 1. 'mihomo' (опрос соединений через REST API Mihomo)
    # 2. 'conntrack' (SSH-стрим conntrack ядра Linux роутера)
    if mode == 'mihomo':
        mode = 'polling'
        
    is_ssh_mode = mode in ('conntrack', 'iptables')
    
    # Разрешаем работу conntrack и iptables даже если Mihomo отключен (главное, чтобы был включен SSH)
    if not settings.mihomo_monitor_enable and not (is_ssh_mode and settings.router_ssh_enable):
        return
        
    if mode == 'conntrack':
        await monitor_router_conntrack()
        return
        
    if mode == 'iptables':
        # Вызываем monitor_router_syslog из этого же модуля
        await monitor_router_syslog()
        return
        
    if mode == 'websocket':
        logging.info("Запуск системы отслеживания трафика роутера через Mihomo API (WebSocket)...")
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
            
    else:  # polling
        logging.info("Запуск системы отслеживания трафика роутера через Mihomo API (опрос соединений)...")
        
        api_url = settings.mihomo_api_url
        headers = {}
        if settings.mihomo_api_secret:
            headers["Authorization"] = f"Bearer {settings.mihomo_api_secret}"
            
        previously_seen_connection_ids = set()
        poll_interval = getattr(settings, 'mihomo_poll_interval', 2.0)
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    while True:
                        try:
                            async with session.get(f"{api_url}/connections", headers=headers, timeout=3) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    connections = data.get("connections", [])
                                    
                                    current_active_ids = set()
                                    for conn in connections:
                                        conn_id = conn.get("id")
                                        if not conn_id:
                                            continue
                                        current_active_ids.add(conn_id)
                                        
                                        if conn_id in previously_seen_connection_ids:
                                            continue
                                            
                                        await handle_new_mihomo_connection(conn)
                                        
                                    previously_seen_connection_ids = current_active_ids
                                else:
                                    logging.warning(f"[Mihomo Monitor] Неожиданный статус API при опросе соединений: {resp.status}")
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            logging.warning(f"[Mihomo Monitor] Ошибка при опросе API соединений: {e}")
                            
                        await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.warning(f"[Mihomo Monitor] Ошибка сессии опроса Mihomo API: {e}")
                
            logging.info("[Mihomo Monitor] Переподключение сессии через 10 секунд...")
            await asyncio.sleep(10)
