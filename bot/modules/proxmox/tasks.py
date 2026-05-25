import asyncio
import logging
from core.bot import bot
from core.config import settings
from modules.proxmox.api import proxmox

# Кэш для мониторинга
offline_nodes_cache = set()

async def monitor_nodes():
    """Фоновая задача для алерта о падении нод"""
    while True:
        try:
            if settings.admin_ids:
                nodes = proxmox.get_nodes()
                
                for node in nodes:
                    node_name = node['node']
                    is_offline = (node['status'] != "online")
                    
                    if is_offline:
                        if node_name not in offline_nodes_cache:
                            offline_nodes_cache.add(node_name)
                            for admin_id in settings.admin_ids:
                                try:
                                    await bot.send_message(
                                        admin_id, 
                                        f"⚠️ <b>АЛЕРТ!</b> Сервер <b>{node_name}</b> отключен или недоступен (статус: {node['status']})!", 
                                        parse_mode="HTML"
                                    )
                                except:
                                    pass
                    else:
                        if node_name in offline_nodes_cache:
                            offline_nodes_cache.remove(node_name)
                            for admin_id in settings.admin_ids:
                                try:
                                    await bot.send_message(
                                        admin_id, 
                                        f"✅ <b>ВОССТАНОВЛЕНИЕ:</b> Сервер <b>{node_name}</b> снова в сети!", 
                                        parse_mode="HTML"
                                    )
                                except:
                                    pass
        except Exception as e:
            logging.error(f"Ошибка в фоновом мониторинге Proxmox: {e}")
            
        await asyncio.sleep(60)

