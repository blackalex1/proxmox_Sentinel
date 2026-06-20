import logging
import json
import time
import datetime
import asyncio
from core.messages import get_new_ip_alert
from core.messages.i18n import _
from core.config import settings

# Очередь для агрегации событий подключений
pending_events = []
digest_task = None

async def check_new_ip_and_get_history(username, current_ip, session_id):
    from core.db import execute_read_one, execute_read_all
    
    row = await execute_read_one(
        "SELECT is_new_ip FROM vpn_sessions WHERE username = ? AND session_id = ?",
        (username, session_id)
    )
    is_new_ip = bool(row["is_new_ip"]) if row else False
    
    rows = await execute_read_all(
        "SELECT ip, connect_time, duration FROM vpn_sessions WHERE username = ? AND ip != ? AND session_id != ? ORDER BY connect_time DESC LIMIT 5",
        (username, current_ip, session_id)
    )
    
    history = []
    for r in rows:
        ip = r["ip"]
        conn_time_str = r["connect_time"]
        duration = r["duration"] or _("spectre", "history_unknown")
        
        try:
            ts = datetime.datetime.strptime(conn_time_str, "%Y-%m-%d %H:%M:%S").timestamp()
        except Exception:
            ts = 0
            
        history.append({
            "ip": ip,
            "timestamp": ts,
            "duration": duration
        })
        
    return is_new_ip, history


async def digest_sender_loop():
    logging.info("[Controller Alerts] Started connection notification digest loop.")
    while True:
        try:
            await asyncio.sleep(30)
            if not pending_events:
                continue
                
            # Забираем накопившиеся события и очищаем очередь
            events = list(pending_events)
            pending_events.clear()
            
            # Группируем события по ключу (username, client_ip, panel_name, protocol)
            grouped = {}
            for ev in events:
                key = (ev["username"], ev["client_ip"], ev["panel_name"], ev["protocol"])
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(ev)
                
            lines = []
            for key, ev_list in grouped.items():
                username, client_ip, panel_name, protocol = key
                
                # Сортируем события внутри группы по времени
                ev_list.sort(key=lambda x: x["timestamp"])
                
                connects = [x for x in ev_list if "connect" in x["action"]]
                disconnects = [x for x in ev_list if "disconnect" in x["action"]]
                
                C = len(connects)
                D = len(disconnects)
                
                last_event = ev_list[-1]
                last_action = last_event["action"]
                
                try:
                    time_str = datetime.datetime.fromtimestamp(last_event["timestamp"]).strftime("%H:%M:%S")
                except Exception:
                    time_str = datetime.datetime.now().strftime("%H:%M:%S")
                
                if C > 1 or D > 1:
                    # Флаппинг / множественные переподключения
                    state = "ПОДКЛЮЧЕН 🟢" if "connect" in last_action else "ОТКЛЮЧЕН 🔴"
                    lines.append(f"• 👤 `{username}` ({client_ip}) @ {panel_name} ({protocol}): {C} переподключений, сейчас {state} [{time_str}]")
                elif C == 1 and D == 0:
                    lines.append(f"• 👤 `{username}` ({client_ip}) @ {panel_name} ({protocol}): ПОДКЛЮЧИЛСЯ 🟢 [{time_str}]")
                elif C == 0 and D == 1:
                    duration_info = f" (Длительность: {last_event['duration_str']})" if last_event.get('duration_str') else ""
                    lines.append(f"• 👤 `{username}` ({client_ip}) @ {panel_name} ({protocol}): ОТКЛЮЧИЛСЯ 🔴 [{time_str}]{duration_info}")
                elif C == 1 and D == 1:
                    # Зашел и вышел в рамках одного окна
                    first_event = ev_list[0]
                    if "connect" in first_event["action"]:
                        duration_info = f" (Длительность: {last_event['duration_str']})" if last_event.get('duration_str') else ""
                        lines.append(f"• 👤 `{username}` ({client_ip}) @ {panel_name} ({protocol}): Зашел и вышел 🔴 [{time_str}]{duration_info}")
                    else:
                        lines.append(f"• 👤 `{username}` ({client_ip}) @ {panel_name} ({protocol}): Переподключился 🟢 [{time_str}]")
                        
            if lines:
                msg_text = "📊 **События подключений (дайджест за 30 сек):**\n\n" + "\n".join(lines)
                
                from .utils import send_rich_message
                for admin_id in settings.admin_ids:
                    try:
                        await send_rich_message(admin_id, msg_text, parse_mode="markdown")
                    except Exception as e:
                        logging.error(f"[Controller Alerts] Error sending digest to admin {admin_id}: {e}")
                        
        except Exception as e:
            logging.error(f"[Controller Alerts] Error in digest loop: {e}")


def start_digest_loop_if_needed():
    global digest_task
    if digest_task is None or digest_task.done():
        digest_task = asyncio.create_task(digest_sender_loop())


async def process_hysteria_audit_event(panel, action, client_ip, log_timestamp, details_str):
    # Запускаем фоновый цикл при первом получении события
    start_digest_loop_if_needed()

    try:
        details = json.loads(details_str)
    except Exception:
        return
        
    username = details.get("username", "Unknown")
    duration_str = details.get("duration", _("spectre", "history_unknown"))
    
    panel_name = panel.name
    protocol = "Xray" if "xray" in action else "Hysteria"
    
    # Получаем актуальный совокупный трафик из базы панели
    db_download, db_upload = 0, 0
    success, res = await panel.request("GET", "/api/security/search-client", params={"key": username})
    if success and res.get("success") and res.get("clients"):
        for item in res["clients"]:
            c_data = item.get("client", {})
            db_download += c_data.get("down", 0)
            db_upload += c_data.get("up", 0)
        tx = db_download
        rx = db_upload
    else:
        # Резервный фолбек на данные из лога события
        tx = details.get("tx", 0)
        rx = details.get("rx", 0)
        if protocol == "Xray":
            tx, rx = rx, tx  # Swap: tx becomes client download, rx becomes client upload
            
    now_time = time.time()
    is_too_old = (now_time - log_timestamp) > 180.0
    
    try:
        timestamp_str = datetime.datetime.fromtimestamp(log_timestamp).strftime("%H:%M:%S")
    except Exception:
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S")

    if action in ("xray_connect", "hysteria_connect"):
        session_id = None
        # Записываем событие подключения в SQLite БД
        try:
            from core.db import save_vpn_connect
            try:
                conn_time_str = datetime.datetime.fromtimestamp(log_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                conn_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session_id = await save_vpn_connect(username, client_ip, conn_time_str, tx, rx)
        except Exception as db_err:
            logging.error("controller_database_error_saving_connection", db_err)

        # Критические алерты о НОВОМ IP отправляем мгновенно
        if session_id and not is_too_old:
            try:
                is_new_ip, history = await check_new_ip_and_get_history(username, client_ip, session_id)
                if is_new_ip:
                    from .utils import get_geoip_info
                    geoip_info = await get_geoip_info(client_ip)
                    alert_text = get_new_ip_alert(protocol, panel_name, username, client_ip, timestamp_str, history, geoip_info=geoip_info)
                    from .utils import send_rich_message
                    for admin_id in settings.admin_ids:
                        try:
                            await send_rich_message(admin_id, alert_text, parse_mode="markdown")
                        except Exception as e:
                            logging.error(f"[Controller Alerts] Error sending new IP alert to admin {admin_id}: {e}")
            except Exception as e:
                logging.error(f"[Controller Alerts] Error checking new IP: {e}")

        # Добавляем событие в очередь дайджеста
        pending_events.append({
            "timestamp": log_timestamp,
            "panel_name": panel_name,
            "username": username,
            "protocol": protocol,
            "action": action,
            "client_ip": client_ip,
            "duration_str": None,
            "tx": tx,
            "rx": rx
        })
            
    elif action in ("xray_disconnect", "hysteria_disconnect"):
        # Записываем событие отключения в SQLite БД
        duration_sec, diff_tx, diff_rx = 0, 0, 0
        try:
            from core.db import save_vpn_disconnect
            try:
                disc_time_str = datetime.datetime.fromtimestamp(log_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                disc_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            res_tuple = await save_vpn_disconnect(username, client_ip, disc_time_str, tx, rx)
            if isinstance(res_tuple, tuple) and len(res_tuple) == 3:
                duration_sec, diff_tx, diff_rx = res_tuple
        except Exception as db_err:
            logging.error("controller_database_error_saving_disconnection", db_err)

        # Фильтр шума/флаппинга: если сессия длилась <= 3 сек и не передала трафика (0 байт)
        if duration_sec <= 3 and diff_tx == 0 and diff_rx == 0:
            # Удаляем соответствующее событие подключения из очереди дайджеста
            for i, ev in enumerate(list(pending_events)):
                if ev["username"] == username and ev["client_ip"] == client_ip and "connect" in ev["action"]:
                    pending_events.pop(i)
                    break
            # Выходим сразу, не добавляя дисконнект в очередь дайджеста
            return

        # Вычисляем длительность для дайджеста
        duration_val = _("spectre", "history_unknown")
        if "hysteria" in action:
            # Для Hysteria пробуем получить длительность
            duration_val = duration_str
        
        # Добавляем событие в очередь дайджеста
        pending_events.append({
            "timestamp": log_timestamp,
            "panel_name": panel_name,
            "username": username,
            "protocol": protocol,
            "action": action,
            "client_ip": client_ip,
            "duration_str": duration_val,
            "tx": tx,
            "rx": rx
        })


async def update_controller_active_cards_traffic():
    pass
