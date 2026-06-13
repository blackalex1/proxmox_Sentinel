import logging
import json
import time
import datetime
from core.bot import bot
from core.config import settings
from core.messages import get_session_activity_card, get_new_ip_alert, get_client_disconnected_alert

# In-memory cards state: (panel_name, username, protocol) -> card dict
active_activity_cards = {}

def format_card_msg(panel_name, username, protocol, lines, tx, rx):
    return get_session_activity_card(protocol, panel_name, username, tx, rx, lines)

def is_card_active(card, now_time):
    if not card:
        return False
    has_active = False
    for ip, conns in card.get('connections', {}).items():
        if conns:
            has_active = True
            break
    if has_active:
        return True
    last_act = card.get('last_activity_at', card.get('started_at', now_time))
    return now_time - last_act < 900.0


def check_new_ip_and_get_history(username, current_ip, current_timestamp, logs):
    user_logs = []
    for log in logs:
        details_dict = {}
        try:
            if isinstance(log.get("details"), str):
                details_dict = json.loads(log["details"])
            elif isinstance(log.get("details"), dict):
                details_dict = log["details"]
        except Exception:
            pass
            
        log_user = details_dict.get("username") or log.get("username")
        if log_user == username:
            user_logs.append(log)
            
    user_logs.sort(key=lambda x: x["timestamp"], reverse=True)
    
    conns = []
    for log in user_logs:
        if log["timestamp"] >= current_timestamp:
            continue
            
        action = log["action"]
        if action in ("xray_connect", "hysteria_connect"):
            ip = log["target"]
            conn_time = log["timestamp"]
            
            disconnect_time = None
            duration_str = None
            
            for d_log in user_logs:
                d_action = d_log["action"]
                if d_action in ("xray_disconnect", "hysteria_disconnect") and d_log["target"] == ip:
                    if d_log["timestamp"] >= conn_time:
                        if disconnect_time is None or d_log["timestamp"] < disconnect_time:
                            disconnect_time = d_log["timestamp"]
                            try:
                                d_details = json.loads(d_log["details"]) if isinstance(d_log["details"], str) else d_log["details"]
                                duration_str = d_details.get("duration")
                            except Exception:
                                pass
                                
            if disconnect_time and not duration_str:
                diff = int(disconnect_time - conn_time)
                if diff < 0:
                    diff = 0
                if diff < 60:
                    duration_str = f"{diff} сек"
                elif diff < 3600:
                    duration_str = f"{diff // 60} мин {diff % 60} сек"
                else:
                    duration_str = f"{diff // 3600} ч {(diff % 3600) // 60} мин"
            elif not duration_str:
                duration_str = "неизвестно"
                
            conns.append({
                "ip": ip,
                "timestamp": conn_time,
                "duration": duration_str
            })
            if len(conns) >= 5:
                break
                
    if not conns:
        return False, []
        
    prev_ips = {c["ip"] for c in conns}
    is_new_ip = current_ip not in prev_ips
    return is_new_ip, conns


async def process_hysteria_audit_event(panel, action, client_ip, log_timestamp, details_str):
    try:
        details = json.loads(details_str)
    except Exception:
        return
        
    username = details.get("username", "Unknown")
    duration_str = details.get("duration", "неизвестно")
    
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
        
    key = (panel_name, username, protocol)
    now_time = time.time()
    
    try:
        timestamp_str = datetime.datetime.fromtimestamp(log_timestamp).strftime("%H:%M:%S")
    except Exception:
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S")

    card = active_activity_cards.get(key)
    
    if action in ("xray_connect", "hysteria_connect"):
        # Check for new IP connection on controller
        try:
            success, res = await panel.get_audit_logs(limit=100)
            if success and res.get("success"):
                logs_list = res.get("logs", [])
                is_new_ip, history = check_new_ip_and_get_history(username, client_ip, log_timestamp, logs_list)
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

        event_line = f"🟢 <code>[{timestamp_str}]</code> Подключение с <code>{client_ip}</code>"
        if card and is_card_active(card, now_time):
            card['lines'].append(event_line)
            card['last_activity_at'] = now_time
            if client_ip not in card['connections']:
                card['connections'][client_ip] = []
            card['connections'][client_ip].append(datetime.datetime.now())
            
            msg_text = format_card_msg(panel_name, username, protocol, card['lines'], tx, rx)
            from .utils import edit_rich_message
            for msg in card['admin_messages']:
                try:
                    await edit_rich_message(chat_id=msg['admin_id'], message_id=msg['message_id'], text=msg_text, parse_mode="markdown")
                except Exception as e:
                    if "message is not modified" not in str(e).lower():
                        logging.error(f"[Controller Alerts] Error editing card: {e}")
        else:
            lines = [event_line]
            connections = {client_ip: [datetime.datetime.now()]}
            msg_text = format_card_msg(panel_name, username, protocol, lines, tx, rx)
            
            admin_messages = []
            from .utils import send_rich_message
            for admin_id in settings.admin_ids:
                try:
                    m = await send_rich_message(admin_id, msg_text, parse_mode="markdown")
                    if m:
                        admin_messages.append({'admin_id': admin_id, 'message_id': m.message_id})
                except Exception as e:
                    logging.error(f"[Controller Alerts] Error sending card to admin {admin_id}: {e}")
                    
            active_activity_cards[key] = {
                'started_at': now_time,
                'last_activity_at': now_time,
                'lines': lines,
                'connections': connections,
                'admin_messages': admin_messages
            }
            
    elif action in ("xray_disconnect", "hysteria_disconnect"):
        if card and is_card_active(card, now_time):
            card['last_activity_at'] = now_time
            
            if "hysteria" in action:
                conn_list = card['connections'].get(client_ip, [])
                if conn_list:
                    conn_time = conn_list.pop(0)
                    duration_sec = int((datetime.datetime.now() - conn_time).total_seconds())
                    if duration_sec < 60:
                        duration_str = f"{duration_sec} сек"
                    elif duration_sec < 3600:
                        duration_str = f"{duration_sec // 60} мин {duration_sec % 60} сек"
                    else:
                        duration_str = f"{duration_sec // 3600} ч {(duration_sec % 3600) // 60} мин"
            else:
                conn_list = card['connections'].get(client_ip, [])
                if conn_list:
                    conn_list.pop(0)
            
            event_line = f"🔴 <code>[{timestamp_str}]</code> Отключение <code>{client_ip}</code> — {duration_str}"
            card['lines'].append(event_line)
            
            msg_text = format_card_msg(panel_name, username, protocol, card['lines'], tx, rx)
            from .utils import edit_rich_message
            for msg in card['admin_messages']:
                try:
                    await edit_rich_message(chat_id=msg['admin_id'], message_id=msg['message_id'], text=msg_text, parse_mode="markdown")
                except Exception as e:
                    if "message is not modified" not in str(e).lower():
                        logging.error(f"[Controller Alerts] Error editing card on disconnect: {e}")
        else:
            from .utils import get_geoip_info
            geoip_info = await get_geoip_info(client_ip)
            msg_text = get_client_disconnected_alert(protocol, panel_name, username, client_ip, timestamp_str, geoip_info=geoip_info)
            from .utils import send_rich_message
            for admin_id in settings.admin_ids:
                try:
                    await send_rich_message(admin_id, msg_text, parse_mode="markdown")
                except Exception as e:
                    logging.error(f"[Controller Alerts] Error sending disconnect message: {e}")

async def update_controller_active_cards_traffic():
    now_time = time.time()
    for (panel_name, username, protocol), card in list(active_activity_cards.items()):
        if not is_card_active(card, now_time):
            continue
        if not card.get('admin_messages'):
            continue
            
        from core.spectre_client import spectre_manager
        panel = None
        for p in spectre_manager.panels.values():
            if p.name == panel_name:
                panel = p
                break
        if not panel:
            continue
            
        success, res = await panel.request("GET", "/api/security/search-client", params={"key": username})
        if success and res.get("success"):
            clients = res.get("clients", [])
            tx, rx = 0, 0
            for item in clients:
                c = item.get("client", {})
                tx += c.get("up", 0)
                rx += c.get("down", 0)
            
            # In database, up is client upload (rx from server perspective), down is download (tx from server perspective)
            msg_text = format_card_msg(panel_name, username, protocol, card['lines'], rx, tx)
            from .utils import edit_rich_message
            for msg in card['admin_messages']:
                try:
                    await edit_rich_message(chat_id=msg['admin_id'], message_id=msg['message_id'], text=msg_text, parse_mode="markdown")
                except Exception as e:
                    if "message is not modified" not in str(e).lower():
                        logging.error(f"[Controller Alerts] Error editing card during traffic poll: {e}")
