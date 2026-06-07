import asyncio
import logging

from core.config import settings
from .resources import monitor_lxc_resources
from .auth import monitor_lxc_auth
from .traffic import monitor_lxc_traffic
from .traffic.garbage import monitor_expired_bans
from .remote import monitor_remote_server

async def start_all_lxc_monitors():
    """Инициализация и запуск всех фоновых асинхронных задач мониторинга LXC и удаленных серверов."""
    from modules.router.monitor.core import monitor_router_connections
    
    # 0. Запускаем фоновый Garbage Collector для очистки просроченных временных блокировок
    asyncio.create_task(monitor_expired_bans(), name="monitor_expired_bans")
    
    # 1. Запускаем опрос ресурсов
    asyncio.create_task(monitor_lxc_resources(), name="monitor_lxc_resources")
    
    # 2. Запускаем tailer-watcher авторизаций
    asyncio.create_task(monitor_lxc_auth(), name="monitor_lxc_auth")
    
    # 3. Запускаем перехват трафика через iptables LOG
    asyncio.create_task(monitor_lxc_traffic(), name="monitor_lxc_traffic")
    
    # 4. Запускаем автообнаружение панелей Spectre Panel
    from core.spectre_client import spectre_manager
    try:
        await spectre_manager.discover_panels()
    except Exception as e:
        logging.error(f"Ошибка стартового автообнаружения Spectre Panel: {e}")
    asyncio.create_task(spectre_manager.start_discovery_loop(), name="spectre_discovery_loop")
    
    # 5. Запускаем мониторинг удаленного сервера, если включен в конфиге
    if settings.remote_monitor_enable:
        asyncio.create_task(monitor_remote_server(), name="monitor_remote_server")
        from .remote.resources import monitor_remote_resources
        asyncio.create_task(monitor_remote_resources(), name="monitor_remote_resources")
        logging.info("Мониторинг удаленного сервера запущен!")
        
    # 6. Запускаем мониторинг роутера (SSH conntrack/syslog), если включен в конфиге
    if settings.router_monitor_enable:
        asyncio.create_task(monitor_router_connections(), name="monitor_router_connections")
        logging.info(f"Мониторинг роутера запущен (режим: {settings.router_monitor_mode})!")
        
    # 7. Запускаем фоновый планировщик автоматических бэкапов
    asyncio.create_task(start_auto_backup_scheduler(), name="auto_backup_scheduler")
    
    logging.info("Все службы LXC мониторинга успешно запущены в фоне!")


async def start_auto_backup_scheduler():
    """
    Фоновый планировщик ежедневных автоматических бэкапов в 3:00 AM.
    """
    import datetime
    from core.spectre_client import spectre_manager
    from aiogram.types import BufferedInputFile
    from core.bot import bot
    
    logging.info("[Backup Scheduler] Запущен фоновый планировщик бэкапов.")
    last_backup_date = None
    
    while True:
        try:
            now = datetime.datetime.now()
            # Проверяем время (3:00 AM)
            if now.hour == 3 and now.minute == 0:
                current_date = now.date()
                if last_backup_date != current_date:
                    logging.info("[Backup Scheduler] Время 3:00 AM, запуск автоматического резервного копирования...")
                    
                    panels = list(spectre_manager.panels.values())
                    if not panels:
                        logging.warning("[Backup Scheduler] Нет обнаруженных панелей для создания бэкапа.")
                    else:
                        for panel in panels:
                            try:
                                logging.info(f"[Backup Scheduler] Создание бэкапа для панели {panel.name}...")
                                success, res = await panel.request("GET", "/api/security/backup")
                                if success and res.get("success") and "dump" in res:
                                    dump_data = res["dump"]
                                    file_bytes = dump_data.encode("utf-8")
                                    timestamp = int(datetime.datetime.now().timestamp())
                                    
                                    # Отправляем файл администраторам
                                    for admin_id in settings.admin_ids:
                                        try:
                                            document = BufferedInputFile(
                                                file_bytes, 
                                                filename=f"auto_backup_{panel.identifier}_{timestamp}.json"
                                            )
                                            await bot.send_document(
                                                admin_id,
                                                document,
                                                caption=f"📥 <b>Автоматический бэкап Spectre Panel</b>\nСервер: <code>{panel.name}</code>",
                                                parse_mode="HTML"
                                            )
                                        except Exception as e:
                                            logging.error(f"Не удалось отправить бэкап админу {admin_id}: {e}")
                                else:
                                    error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
                                    logging.error(f"[Backup Scheduler] Не удалось создать авто-бэкап для {panel.name}: {error_info}")
                            except Exception as panel_err:
                                logging.error(f"[Backup Scheduler] Ошибка при бэкапе панели {panel.name}: {panel_err}")
                                
                    last_backup_date = current_date
        except Exception as e:
            logging.error(f"[Backup Scheduler] Исключение в планировщике бэкапов: {e}")
            
        await asyncio.sleep(60)



