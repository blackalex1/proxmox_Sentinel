import logging
import json
import time
import datetime
import asyncio
from core.bot import bot
from core.config import settings
from core.messages import get_session_activity_card, get_new_ip_alert, get_client_disconnected_alert
from core.messages.i18n import _

# In-memory cards state: (panel_name, username, protocol) -> card dict
active_activity_cards = {}

async def trigger_card_edit(card, msg_text):
    if card.get('last_sent_text') == msg_text:
        return
    card['pending_text'] = msg_text
    now = time.time()
    
    if now - card.get('last_edited_at', 0) >= 30.0:
        card['last_edited_at'] = now
        card['pending_text'] = None
        card['last_sent_text'] = msg_text
        
        from .utils import edit_rich_message
        for msg in card['admin_messages']:
            try:
                await edit_rich_message(chat_id=msg['admin_id'], message_id=msg['message_id'], text=msg_text, parse_mode="HTML")
            except Exception as e:
                if "message is not modified" not in str(e).lower():
                    logging.error(f"[Controller Alerts] Error editing card: {e}")
    else:
        if not card.get('edit_task') or card['edit_task'].done():
            async def run_delayed_edit():
                await asyncio.sleep(30.0)
                if card.get('pending_text'):
                    text_to_send = card['pending_text']
                    card['pending_text'] = None
                    card['last_edited_at'] = time.time()
                    card['last_sent_text'] = text_to_send
                    
                    from .utils import edit_rich_message
                    for msg in card['admin_messages']:
                        try:
                            await edit_rich_message(chat_id=msg['admin_id'], message_id=msg['message_id'], text=text_to_send, parse_mode="HTML")
                        except Exception as e:
                            if "message is not modified" not in str(e).lower():
                                logging.error(f"[Controller Alerts] Error in debounced card edit: {e}")
            card['edit_task'] = asyncio.create_task(run_delayed_edit())

def format_card_msg(panel_name, username, protocol, lines, tx, rx):
    return get_session_activity_card(protocol, panel_name, username, tx, rx, lines)

def is_card_active(card, now_time):
    if not card:
        return False
    if not card.get('admin_messages') and not card.get('pending_send'):
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


async def get_traffic_from_api(panel, username):
    db_download, db_upload = 0, 0
    if not panel:
        return 0, 0
    try:
        success, res = await panel.request("GET", "/api/security/search-client", params={"key": username})
        if success and res.get("success") and res.get("clients"):
            for item in res["clients"]:
                c_data = item.get("client", {})
                db_download += c_data.get("down", 0)
                db_upload += c_data.get("up", 0)
    except Exception as e:
        logging.error(f"[Controller Alerts] Error fetching traffic for {username} on panel {panel.name}: {e}")
    return db_download, db_upload


async def check_and_send_card_delayed(key, session_id):
    await asyncio.sleep(5.0)
    
    from core.db import execute_read_one
    try:
        row = await execute_read_one(
            "SELECT connect_time, disconnect_time, download_bytes, upload_bytes FROM vpn_sessions WHERE session_id = ?",
            (session_id,)
        )
    except Exception as e:
        logging.error(f"[Controller Alerts] Error querying session {session_id} in delay task: {e}")
        row = None

    is_noise = False
    if row and row["disconnect_time"] is not None:
        try:
            conn_dt = datetime.datetime.strptime(row["connect_time"], "%Y-%m-%d %H:%M:%S")
            disc_dt = datetime.datetime.strptime(row["disconnect_time"], "%Y-%m-%d %H:%M:%S")
            duration_sec = int((disc_dt - conn_dt).total_seconds())
        except Exception:
            duration_sec = 0
        tx_diff = row["download_bytes"] or 0
        rx_diff = row["upload_bytes"] or 0
        
        if duration_sec <= 3 and tx_diff == 0 and rx_diff == 0:
            is_noise = True

    card = active_activity_cards.get(key)
    if not card:
        return

    panel_name, username, protocol = key

    if is_noise:
        card['lines'] = [l for l in card['lines'] if l.get('session_id') != session_id]
        
        if not card['lines']:
            active_activity_cards.pop(key, None)
            return
            
        if not card.get('pending_send', True):
            from core.spectre_client import spectre_manager
            panel = None
            for p in spectre_manager.panels.values():
                if p.name == panel_name:
                    panel = p
                    break
            tx, rx = await get_traffic_from_api(panel, username)
            msg_text = format_card_msg(panel_name, username, protocol, [l['text'] for l in card['lines']], tx, rx)
            await trigger_card_edit(card, msg_text)
    else:
        if card.get('pending_send', True):
            card['pending_send'] = False
            
            from core.spectre_client import spectre_manager
            panel = None
            for p in spectre_manager.panels.values():
                if p.name == panel_name:
                    panel = p
                    break
            tx, rx = await get_traffic_from_api(panel, username)
            msg_text = format_card_msg(panel_name, username, protocol, [l['text'] for l in card['lines']], tx, rx)
            
            admin_messages = []
            from .utils import send_rich_message
            for admin_id in settings.admin_ids:
                try:
                    m = await send_rich_message(admin_id, msg_text, parse_mode="HTML")
                    if m:
                        admin_messages.append({'admin_id': admin_id, 'message_id': m.message_id})
                except Exception as e:
                    logging.error(f"[Controller Alerts] Error sending card to admin {admin_id}: {e}")
            
            card['admin_messages'] = admin_messages
            card['last_sent_text'] = msg_text


async def check_new_ip_and_get_history(username, current_ip, session_id):
    from core.db import execute_read_one, execute_read_all
    
    # 1. Читаем статус новизны IP из созданной сессии
    row = await execute_read_one(
        "SELECT is_new_ip FROM vpn_sessions WHERE username = ? AND session_id = ?",
        (username, session_id)
    )
    is_new_ip = bool(row["is_new_ip"]) if row else False
    
    # 2. Получаем историю предыдущих подключений с других IP
    # Исключаем текущую сессию по session_id
    rows = await execute_read_all(
        "SELECT ip, connect_time, duration FROM vpn_sessions WHERE username = ? AND ip != ? AND session_id != ? ORDER BY connect_time DESC LIMIT 5",
        (username, current_ip, session_id)
    )
    
    history = []
    import datetime
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
    duration_str = details.get("duration", _("spectre", "history_unknown"))
    
    panel_name = panel.name
    protocol = "Xray" if "xray" in action else "Hysteria"
    
    # Получаем актуальный совокупный трафик из базы панели
    tx, rx = await get_traffic_from_api(panel, username)
    if tx == 0 and rx == 0:
        # Резервный фолбек на данные из лога события
        tx = details.get("tx", 0)
        rx = details.get("rx", 0)
        if protocol == "Xray":
            tx, rx = rx, tx  # Swap: tx becomes client download, rx becomes client upload
        
    key = (panel_name, username, protocol)
    now_time = time.time()
    is_too_old = (now_time - log_timestamp) > 180.0
    
    try:
        timestamp_str = datetime.datetime.fromtimestamp(log_timestamp).strftime("%H:%M:%S")
    except Exception:
        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S")

    card = active_activity_cards.get(key)
    
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

        # Check for new IP connection on controller using bot database
        if session_id and not is_too_old:
            try:
                is_new_ip, history = await check_new_ip_and_get_history(username, client_ip, session_id)
                if is_new_ip:
                    from .utils import get_geoip_info
                    geoip_info = await get_geoip_info(client_ip)
                    alert_text = get_new_ip_alert(protocol, panel_name, username, client_ip, timestamp_str, history, geoip_info=geoip_info)
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=_("spectre", "btn_approve_ip"), callback_data=f"approve_ip:{username}:{client_ip}")]
                    ])
                    from .utils import send_rich_message
                    for admin_id in settings.admin_ids:
                        try:
                            await send_rich_message(admin_id, alert_text, parse_mode="HTML", reply_markup=kb)
                        except Exception as e:
                            logging.error(f"[Controller Alerts] Error sending new IP alert to admin {admin_id}: {e}")
            except Exception as e:
                logging.error(f"[Controller Alerts] Error checking new IP: {e}")

        event_line = _("spectre", "timeline_connect", timestamp=timestamp_str, ip=client_ip)
        
        if card and is_card_active(card, now_time):
            card['lines'].append({
                'session_id': session_id,
                'text': event_line,
                'type': 'connect'
            })
            card['last_activity_at'] = now_time
            if client_ip not in card['connections']:
                card['connections'][client_ip] = []
            card['connections'][client_ip].append(datetime.datetime.now())
            
            # Start background task to process send/noise checks after delay
            asyncio.create_task(check_and_send_card_delayed(key, session_id))
            
            if not is_too_old and not card.get('pending_send', True):
                msg_text = format_card_msg(panel_name, username, protocol, [l['text'] for l in card['lines']], tx, rx)
                await trigger_card_edit(card, msg_text)
        else:
            lines = [{
                'session_id': session_id,
                'text': event_line,
                'type': 'connect'
            }]
            connections = {client_ip: [datetime.datetime.now()]}
            
            active_activity_cards[key] = {
                'started_at': now_time,
                'last_activity_at': now_time,
                'last_edited_at': time.time(),
                'lines': lines,
                'connections': connections,
                'admin_messages': [],
                'pending_send': True
            }
            # Start background task to process send/noise checks after delay
            asyncio.create_task(check_and_send_card_delayed(key, session_id))
            
    elif action in ("xray_disconnect", "hysteria_disconnect"):
        # Записываем событие отключения в SQLite БД
        try:
            from core.db import save_vpn_disconnect
            try:
                disc_time_str = datetime.datetime.fromtimestamp(log_timestamp).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                disc_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            res_tuple = await save_vpn_disconnect(username, client_ip, disc_time_str, tx, rx)
            session_id, duration_sec, diff_tx, diff_rx = res_tuple
        except Exception as db_err:
            logging.error("controller_database_error_saving_disconnection", db_err)
            session_id, duration_sec, diff_tx, diff_rx = None, 0, 0, 0

        is_noise = (duration_sec <= 3 and diff_tx == 0 and diff_rx == 0)
        if is_noise:
            # Noise disconnect is ignored completely
            return

        if card and is_card_active(card, now_time):
            card['last_activity_at'] = now_time
            
            if "hysteria" in action:
                conn_list = card['connections'].get(client_ip, [])
                if conn_list:
                    conn_time = conn_list.pop(0)
                    duration_sec_calc = int((datetime.datetime.now() - conn_time).total_seconds())
                    if duration_sec_calc < 60:
                        duration_str = _("spectre", "duration_sec", val=duration_sec_calc)
                    elif duration_sec_calc < 3600:
                        duration_str = _("spectre", "duration_min_sec", min=duration_sec_calc // 60, sec=duration_sec_calc % 60)
                    else:
                        duration_str = _("spectre", "duration_hour_min", hour=duration_sec_calc // 3600, min=(duration_sec_calc % 3600) // 60)
            else:
                conn_list = card['connections'].get(client_ip, [])
                if conn_list:
                    conn_list.pop(0)
            
            event_line = _("spectre", "timeline_disconnect", timestamp=timestamp_str, ip=client_ip, duration=duration_str)
            card['lines'].append({
                'session_id': session_id,
                'text': event_line,
                'type': 'disconnect'
            })
            
            if not is_too_old and not card.get('pending_send', True):
                msg_text = format_card_msg(panel_name, username, protocol, [l['text'] for l in card['lines']], tx, rx)
                await trigger_card_edit(card, msg_text)
        else:
            if not is_too_old:
                from .utils import get_geoip_info
                geoip_info = await get_geoip_info(client_ip)
                msg_text = get_client_disconnected_alert(protocol, panel_name, username, client_ip, timestamp_str, geoip_info=geoip_info)
                from .utils import send_rich_message
                for admin_id in settings.admin_ids:
                    try:
                        await send_rich_message(admin_id, msg_text, parse_mode="HTML")
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
            
        tx, rx = await get_traffic_from_api(panel, username)
        msg_text = format_card_msg(panel_name, username, protocol, [l['text'] for l in card['lines']], tx, rx)
        await trigger_card_edit(card, msg_text)
