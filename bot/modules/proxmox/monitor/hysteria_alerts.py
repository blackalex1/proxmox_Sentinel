import logging
import json
import time
import datetime
from core.messages import get_new_ip_alert
from core.messages.i18n import _
from core.config import settings

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


async def process_hysteria_audit_event(panel, action, client_ip, log_timestamp, details_str):
    try:
        details = json.loads(details_str)
    except Exception:
        return
        
    username = details.get("username", "Unknown")
    
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

        # Отправляем предупреждение в Telegram ТОЛЬКО если IP новый
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
            
    elif action in ("xray_disconnect", "hysteria_disconnect"):
        # Записываем событие отключения в SQLite БД
        try:
            from core.db import save_vpn_disconnect
            try:
                disc_time_str = datetime.datetime.fromtimestamp(log_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                disc_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await save_vpn_disconnect(username, client_ip, disc_time_str, tx, rx)
        except Exception as db_err:
            logging.error("controller_database_error_saving_disconnection", db_err)


async def update_controller_active_cards_traffic():
    pass
