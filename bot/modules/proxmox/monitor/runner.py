import asyncio
import logging

from core.config import settings
from core.messages import get_ips_autoblock_alert_audit, get_login_success_alert, get_spectre_2fa_alert
from .utils import send_alert_to_admins
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
    
    # 9. Запускаем фоновый мониторинг файлов 2fa.log панелей для мгновенного подтверждения 2FA
    asyncio.create_task(monitor_panel_2fa_logs(), name="monitor_panel_2fa_logs")
    
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
    Фоновый мониторинг логов аудита всех подключенных панелей Spectre Panel.
    Опрашивает эндпоинт /api/security/audit-logs каждые 10 секунд и отправляет
    уведомления об IPS-блокировках и успешных авторизациях.
    """
    from core.spectre_client import spectre_manager
    from core.bot import bot
    
    last_log_ids = {}
    logging.info("[Audit Monitor] Запущен фоновый мониторинг логов аудита панелей.")
    traffic_update_counter = 0
    
    while True:
        try:
            for p_key, panel in list(spectre_manager.panels.items()):
                
                # При первом запуске инициализируем ID последнего лога, чтобы не слать старые алерты
                if p_key not in last_log_ids:
                    success, res = await panel.get_audit_logs(limit=1)
                    if success and res.get("success") and res.get("logs"):
                        last_log_ids[p_key] = res["logs"][0]["id"]
                    else:
                        last_log_ids[p_key] = 0
                    continue
                    
                # Запрашиваем новые логи
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
                        is_client_event = log.get("action") in ("xray_connect", "xray_disconnect", "hysteria_connect", "hysteria_disconnect")
                        
                        if is_ips_block:
                            email = log.get("target") or "unknown"
                            details = log.get("details") or ""
                            timestamp_val = log.get("timestamp")
                            try:
                                import datetime
                                time_str = datetime.datetime.fromtimestamp(timestamp_val).strftime("%H:%M:%S")
                            except Exception:
                                time_str = datetime.datetime.now().strftime("%H:%M:%S")
                                
                            msg = get_ips_autoblock_alert_audit(panel.name, email, details, time_str)
                            
                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"unban_tunnel:{email}")]
                            ])
                                   
                            # Отправляем алерт всем администраторам контроллера
                            try:
                                await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=keyboard)
                            except Exception as e:
                                logging.error(f"[Audit Monitor] Не удалось отправить алерт: {e}")
                                    
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
                                
                            from modules.proxmox.monitor.utils import get_geoip_info
                            geoip_info = await get_geoip_info(ip)
                            msg = get_login_success_alert(panel.name, username, ip, details, time_str, geoip_info=geoip_info)
                                   
                            # Отправляем алерт всем администраторам контроллера
                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(text="❌ Сбросить сессию", callback_data=f"ctrl_term_sess:{p_key}:{username}:{ip}"),
                                    InlineKeyboardButton(text="🔑 Сбросить пароль", callback_data=f"ctrl_reset_pwd:{p_key}:{username}")
                                ]
                            ])
                            try:
                                await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=kb)
                            except Exception as e:
                                logging.error(f"[Audit Monitor] Не удалось отправить алерт: {e}")
                        
                        elif is_client_event:
                            try:
                                from .hysteria_alerts import process_hysteria_audit_event
                                await process_hysteria_audit_event(
                                    panel=panel,
                                    action=log.get("action"),
                                    client_ip=log.get("target"),
                                    log_timestamp=log.get("timestamp"),
                                    details_str=log.get("details")
                                )
                            except Exception as ex:
                                logging.error(f"[Audit Monitor] Ошибка обработки события клиента: {ex}")
                                    
                    last_log_ids[p_key] = new_max_id
                except Exception as panel_err:
                    logging.debug(f"[Audit Monitor] Ошибка опроса панели {panel.name}: {panel_err}")
        except Exception as e:
            logging.error(f"[Audit Monitor] Ошибка в цикле мониторинга аудит-логов: {e}")
            
        traffic_update_counter += 1
        if traffic_update_counter >= 3:
            traffic_update_counter = 0
            try:
                from .hysteria_alerts import update_controller_active_cards_traffic
                await update_controller_active_cards_traffic()
            except Exception as ex:
                logging.error(f"[Audit Monitor] Ошибка при обновлении трафика активных карточек: {ex}")
                
        await asyncio.sleep(10)


async def monitor_panel_2fa_logs():
    """
    Фоновый мониторинг файлов 2fa.log всех панелей Spectre Panel.
    Стримит события создания 2FA-запросов и отправляет алерты администраторам.
    """
    from core.spectre_client import spectre_manager
    from core.bot import bot
    from modules.proxmox.monitor.utils import LogTailer
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    import time
    import datetime
    
    active_tailers = {}
    
    logging.info("[2FA Monitor] Запущен фоновый мониторинг 2fa.log панелей.")
    
    async def handle_2fa_line(line, panel=None):
        if not panel:
            return
        import json
        try:
            data = json.loads(line.strip())
        except Exception:
            return
            
        if data.get("status") != "PENDING":
            return
            
        username = data.get("username")
        client_ip = data.get("client_ip")
        tg_token = data.get("token")
        timestamp = data.get("timestamp")
        
        try:
            log_time = float(timestamp)
            if time.time() - log_time > 120:
                return
            time_str = datetime.datetime.fromtimestamp(log_time).strftime("%H:%M:%S")
        except (ValueError, TypeError, Exception):
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            
        from modules.proxmox.monitor.utils import get_geoip_info
        geoip_info = await get_geoip_info(client_ip)
        msg_text = get_spectre_2fa_alert(panel.name, username, client_ip, time_str, geoip_info=geoip_info)
            
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, разрешить", callback_data=f"tg_2fa_approve:{tg_token}"),
                InlineKeyboardButton(text="❌ Заблокировать IP", callback_data=f"tg_2fa_block:{tg_token}")
            ]
        ])
        
        try:
            await send_alert_to_admins(msg_text, parse_mode="markdown", reply_markup=kb)
        except Exception as e:
            logging.error(f"[2FA Monitor] Не удалось отправить 2FA алерт: {e}")

    while True:
        try:
            panels = list(spectre_manager.panels.items())
            current_keys = set()
            
            for p_key, panel in panels:
                if not panel.env_path:
                    continue
                current_keys.add(p_key)
                
                # Check if tailer task has ended/crashed, and clean it up to allow restart
                if p_key in active_tailers:
                    tailer = active_tailers[p_key]
                    if tailer.task and tailer.task.done():
                        logging.warning(f"[2FA Monitor] Tailer task for {p_key} was terminated. Removing from active tailers to restart.")
                        active_tailers.pop(p_key)
                
                if p_key not in active_tailers:
                    log_path = panel.env_path.replace(".env", "2fa.log")
                    
                    if panel.source_type == "lxc":
                        cmd = ["pct", "exec", str(panel.identifier), "--", "tail", "-F", "-n", "0", log_path]
                        tailer = LogTailer(cmd, handle_2fa_line, panel)
                        active_tailers[p_key] = tailer
                        await tailer.start()
                    elif panel.source_type == "vps":
                        from modules.proxmox.monitor.remote.ssh import get_ssh_base_cmd
                        server = None
                        for s in settings.remote_servers:
                            if s.get('ip') == panel.identifier:
                                server = s
                                break
                        if server:
                            ssh_base = get_ssh_base_cmd(server)
                            cmd = ssh_base + ["tail", "-F", "-n", "0", log_path]
                            tailer = LogTailer(cmd, handle_2fa_line, panel)
                            active_tailers[p_key] = tailer
                            await tailer.start()
                            
            for p_key in list(active_tailers.keys()):
                if p_key not in current_keys:
                    tailer = active_tailers.pop(p_key)
                    await tailer.stop()
                    
        except Exception as e:
            logging.error(f"[2FA Monitor] Ошибка в цикле мониторинга 2fa.log: {e}")
            
        await asyncio.sleep(15)




