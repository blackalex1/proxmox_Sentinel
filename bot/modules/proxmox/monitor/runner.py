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
    
    # 8. Запускаем фоновый опрос аудит-логов панелей для перехвата и оповещения об IPS авто-блокировках
    asyncio.create_task(monitor_panel_audit_logs(), name="monitor_panel_audit_logs")
    
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


async def monitor_panel_audit_logs():
    """
    Периодически опрашивает логи аудита всех панелей Spectre Panel и пересылает
    уведомления об авто-блокировках IPS-Sentinel администраторам в Telegram.
    """
    from core.spectre_client import spectre_manager
    from core.bot import bot
    import time
    
    # Хранит последний обработанный ID лога для каждой панели
    last_log_ids = {}
    
    logging.info("[Audit Monitor] Запущен фоновый мониторинг логов аудита панелей.")
    
    # Даем немного времени на стартовое обнаружение панелей
    await asyncio.sleep(10)
    
    # Инициализируем начальные ID, чтобы не спамить старыми алертами при перезапуске бота
    for p_key, panel in list(spectre_manager.panels.items()):
        try:
            success, res = await panel.get_audit_logs(limit=1)
            if success and res.get("success") and res.get("logs"):
                last_log_ids[p_key] = res["logs"][0]["id"]
        except Exception:
            pass
            
    while True:
        try:
            panels = list(spectre_manager.panels.items())
            for p_key, panel in panels:
                try:
                    success, res = await panel.get_audit_logs(limit=20)
                    if not success or not res.get("success"):
                        continue
                        
                    logs = res.get("logs", [])
                    if not logs:
                        continue
                        
                    # Сортируем логи по возрастанию ID (от старых к новым)
                    logs.sort(key=lambda x: x["id"])
                    
                    prev_max_id = last_log_ids.get(p_key, 0)
                    new_max_id = prev_max_id
                    
                    for log in logs:
                        log_id = log["id"]
                        if log_id <= prev_max_id:
                            continue
                            
                        new_max_id = max(new_max_id, log_id)
                        
                        # Фильтруем события авто-блокировки и успешных авторизаций
                        is_ips_block = (
                            log.get("username") == "IPS-Sentinel" or
                            "IPS-Sentinel" in str(log.get("details")) or
                            "IPS Auto-blocked" in str(log.get("details"))
                        )
                        is_login_success = log.get("action") in ["login_success", "login_telegram_success"]
                        
                        if is_ips_block:
                            email = log.get("target") or "unknown"
                            details = log.get("details") or ""
                            timestamp_val = log.get("timestamp")
                            try:
                                import datetime
                                time_str = datetime.datetime.fromtimestamp(timestamp_val).strftime("%H:%M:%S")
                            except Exception:
                                time_str = datetime.datetime.now().strftime("%H:%M:%S")
                                
                            msg = (f"🛑 <b>[IPS: Авто-блокировка на {panel.name}]</b>\n\n"
                                   f"👤 Пользователь: <code>{email}</code>\n"
                                   f"ℹ️ Причина: <b>{details}</b>\n"
                                   f"🕒 Время: <code>{time_str}</code>")
                                   
                            # Отправляем алерт всем администраторам контроллера
                            for admin_id in settings.admin_ids:
                                try:
                                    await bot.send_message(chat_id=admin_id, text=msg, parse_mode="HTML")
                                except Exception as e:
                                    logging.error(f"[Audit Monitor] Не удалось отправить алерт админу {admin_id}: {e}")
                                    
                        elif is_login_success:
                            username = log.get("username") or "unknown"
                            ip = log.get("target") or "unknown"
                            details = log.get("details") or ""
                            timestamp_val = log.get("timestamp")
                            try:
                                import datetime
                                time_str = datetime.datetime.fromtimestamp(timestamp_val).strftime("%H:%M:%S")
                            except Exception:
                                time_str = datetime.datetime.now().strftime("%H:%M:%S")
                                
                            msg = (f"🔑 <b>[Вход выполнен на {panel.name}]</b>\n\n"
                                   f"👤 Логин: <code>{username}</code>\n"
                                   f"🌐 IP-адрес: <code>{ip}</code>\n"
                                   f"ℹ️ Детали: <b>{details}</b>\n"
                                   f"🕒 Время: <code>{time_str}</code>")
                                   
                            # Отправляем алерт всем администраторам контроллера
                            for admin_id in settings.admin_ids:
                                try:
                                    await bot.send_message(chat_id=admin_id, text=msg, parse_mode="HTML")
                                except Exception as e:
                                    logging.error(f"[Audit Monitor] Не удалось отправить алерт админу {admin_id}: {e}")
                                    
                    last_log_ids[p_key] = new_max_id
                except Exception as panel_err:
                    logging.debug(f"[Audit Monitor] Ошибка опроса панели {panel.name}: {panel_err}")
        except Exception as e:
            logging.error(f"[Audit Monitor] Ошибка в цикле мониторинга аудит-логов: {e}")
            
        await asyncio.sleep(10)




