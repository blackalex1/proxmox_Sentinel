import asyncio
import logging

from core.config import settings
from .resources import monitor_lxc_resources
from .auth import monitor_lxc_auth
from .traffic import monitor_lxc_traffic
from .traffic.firewall import monitor_expired_bans
from .xui_connections import monitor_xui_connections
from .xui_panel import monitor_xui_panel_logins
from .remote import monitor_remote_server

async def start_all_lxc_monitors():
    """Инициализация и запуск всех фоновых асинхронных задач мониторинга LXC и удаленных серверов."""
    # 0. Запускаем фоновый Garbage Collector для очистки просроченных временных блокировок
    asyncio.create_task(monitor_expired_bans())
    
    # 1. Запускаем опрос ресурсов
    asyncio.create_task(monitor_lxc_resources())
    
    # 2. Запускаем tailer-watcher авторизаций
    asyncio.create_task(monitor_lxc_auth())
    
    # 3. Запускаем перехват трафика через iptables LOG
    asyncio.create_task(monitor_lxc_traffic())
    
    # 4. Запускаем отслеживание подключений 3X-UI через access.log
    asyncio.create_task(monitor_xui_connections())
    
    # 4b. Запускаем отслеживание входов в веб-панель 3X-UI
    asyncio.create_task(monitor_xui_panel_logins())
    
    # 5. Запускаем мониторинг удаленного сервера, если включен в конфиге
    if settings.remote_monitor_enable:
        asyncio.create_task(monitor_remote_server())
        logging.info("Мониторинг удаленного сервера запущен!")
        
    logging.info("Все службы LXC мониторинга успешно запущены в фоне!")



