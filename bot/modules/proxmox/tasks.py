import asyncio
import logging
from core.bot import bot
from core.config import settings
from modules.proxmox.api import proxmox
from core.messages import get_node_offline_alert, get_node_online_alert

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
                                    from modules.proxmox.monitor import send_rich_message
                                    msg = get_node_offline_alert(node_name, node['status'])
                                    await send_rich_message(
                                        admin_id, 
                                        msg, 
                                        parse_mode="markdown"
                                    )
                                except:
                                    pass
                    else:
                        if node_name in offline_nodes_cache:
                            offline_nodes_cache.remove(node_name)
                            for admin_id in settings.admin_ids:
                                try:
                                    from modules.proxmox.monitor import send_rich_message
                                    msg = get_node_online_alert(node_name)
                                    await send_rich_message(
                                        admin_id, 
                                        msg, 
                                        parse_mode="markdown"
                                    )
                                except:
                                    pass
        except Exception as e:
            logging.error(f"Ошибка в фоновом мониторинге Proxmox: {e}")
            
        await asyncio.sleep(60)

