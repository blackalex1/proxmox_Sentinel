import asyncio
import logging
import datetime
import time as pytime
from core.bot import bot
from core.config import settings
from modules.proxmox.monitor.utils import send_alert_to_admins

from .history import log_connection, update_disconnection
from .ips import block_remote_hysteria_user

# Нарушения пользователей Hysteria: username -> list of timestamps
recent_hysteria_violations = {}

# Память для троттлинга алертов трафика удаленного VPS (IP -> timestamp)
recent_remote_traffic_alerts = {}

# Активные карточки хронологии сессий: (server_ip, username) -> dict
active_activity_cards = {}

def format_card_msg(server_ip, username, lines):
    # Показываем последние 15 строк хронологии событий
    displayed_lines = lines[-15:]
    timeline = "\n".join(displayed_lines)
    if len(lines) > 15:
        timeline = "<i>... показать ещё ...</i>\n" + timeline
        
    text = (
        f"📊 <b>[VPS Hysteria: {server_ip}] Активность сессии</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Пользователь:</b> <code>{username}</code>\n\n"
        f"📋 <b>Хронология событий:</b>\n"
        f"{timeline}"
    )
    return text

async def handle_hysteria_connect(server, username, client_ip):
    """Добавляет новое подключение к хронологической карточке (создает новую или обновляет текущую)."""
    server_ip = server['ip']
    now_time = pytime.time()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    key = (server_ip, username)
    
    # Записываем сессию во всеобщую историю SQLite и проверяем смену IP
    session_id, recent_prev, is_new_ip = await log_connection(username, client_ip)
    
    # СЦЕНАРИЙ БЕЗОПАСНОСТИ: Если обнаружен НОВЫЙ IP-адрес, шлем отдельное тревожное сообщение (🚨)
    if is_new_ip:
        msg = (f"🚨 <b>[VPS Hysteria Security: {server_ip}] Обнаружено подключение с нового IP!</b>\n\n"
               f"👤 <b>Пользователь:</b> <code>{username}</code>\n"
               f"🌐 <b>Новый IP-адрес:</b> <code>{client_ip}</code> ⚠️ <b>[ВНИМАНИЕ]</b>\n"
               f"🕒 <b>Время:</b> <code>{timestamp}</code>")
               
        if recent_prev:
            history_lines = []
            for s in recent_prev:
                try:
                    dt = datetime.datetime.strptime(s['connect_time'], "%Y-%m-%d %H:%M:%S")
                    date_str = dt.strftime("%d.%m %H:%M")
                except Exception:
                    date_str = s['connect_time']
                history_lines.append(f"• <code>{s['ip']}</code> ({date_str}) — {s['duration']}")
            msg += f"\n\n📋 <b>Предыдущие подключения (для сравнения):</b>\n" + "\n".join(history_lines)
            
        sent_messages = []
        for admin_id in ADMIN_IDS:
            try:
                m = await bot.send_message(admin_id, msg, parse_mode="HTML")
                sent_messages.append({
                    'admin_id': admin_id,
                    'message_id': m.message_id
                })
            except Exception as e:
                logging.error(f"Не удалось отправить алерт о новом IP Hysteria админу {admin_id}: {e}")
                
        if sent_messages:
            # Создаем новую изолированную карточку активности под этот новый IP-адрес
            lines = [f"🟢 <code>[{timestamp}]</code> Подключение с <code>{client_ip}</code> ⚠️ <b>[НОВЫЙ IP]</b>"]
            connections = {client_ip: [datetime.datetime.now()]}
            active_activity_cards[key] = {
                'admin_messages': sent_messages,
                'started_at': now_time,
                'lines': lines,
                'connections': connections
            }
        return

    # ОБЫЧНЫЙ СЦЕНАРИЙ (Стабильный IP): Добавляем к хронологической карте
    event_line = f"🟢 <code>[{timestamp}]</code> Подключение с <code>{client_ip}</code>"
    
    card = active_activity_cards.get(key)
    # Если карточка активна и создана менее 5 минут назад, просто редактируем её
    if card and now_time - card['started_at'] < 300.0:
        card['lines'].append(event_line)
        if client_ip not in card['connections']:
            card['connections'][client_ip] = []
        card['connections'][client_ip].append(datetime.datetime.now())
        
        msg = format_card_msg(server_ip, username, card['lines'])
        for s in card['admin_messages']:
            try:
                await bot.edit_message_text(
                    chat_id=s['admin_id'],
                    message_id=s['message_id'],
                    text=msg,
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Не удалось обновить карточку Hysteria для админа {s['admin_id']}: {e}")
    else:
        # Создаем новую карточку активности
        lines = [event_line]
        connections = {client_ip: [datetime.datetime.now()]}
        
        if recent_prev:
            history_lines = []
            for s in recent_prev:
                try:
                    dt = datetime.datetime.strptime(s['connect_time'], "%Y-%m-%d %H:%M:%S")
                    date_str = dt.strftime("%d.%m %H:%M")
                except Exception:
                    date_str = s['connect_time']
                history_lines.append(f"• <code>{s['ip']}</code> ({date_str}) — {s['duration']}")
            lines.append(f"\n📋 <b>Предыдущие подключения:</b>\n" + "\n".join(history_lines))
        else:
            lines.append(f"\n📋 <i>Это первое зафиксированное подключение пользователя.</i>")
            
        msg = format_card_msg(server_ip, username, lines)
        sent_messages = []
        for admin_id in ADMIN_IDS:
            try:
                m = await bot.send_message(admin_id, msg, parse_mode="HTML")
                sent_messages.append({
                    'admin_id': admin_id,
                    'message_id': m.message_id
                })
            except Exception as e:
                logging.error(f"Не удалось отправить новую карточку Hysteria админу {admin_id}: {e}")
                
        if sent_messages:
            active_activity_cards[key] = {
                'admin_messages': sent_messages,
                'started_at': now_time,
                'lines': lines,
                'connections': connections
            }

async def handle_hysteria_disconnect(server, username, client_ip):
    """Добавляет событие отключения и длительность к хронологической карточке активности."""
    server_ip = server['ip']
    now_time = pytime.time()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    key = (server_ip, username)
    
    card = active_activity_cards.get(key)
    if not card or now_time - card['started_at'] > 300.0:
        await asyncio.sleep(0.8)
        card = active_activity_cards.get(key)
        
    if card and now_time - card['started_at'] < 300.0:
        duration_str = "неизвестно"
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
                
            # Завершаем запись сессии в SQLite БД
            await update_disconnection(username, client_ip, duration_str)
                
        event_line = f"🔴 <code>[{timestamp}]</code> Отключение <code>{client_ip}</code> — {duration_str}"
        card['lines'].append(event_line)
        
        msg = format_card_msg(server_ip, username, card['lines'])
        for s in card['admin_messages']:
            try:
                await bot.edit_message_text(
                    chat_id=s['admin_id'],
                    message_id=s['message_id'],
                    text=msg,
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.error(f"Не удалось обновить карточку Hysteria при отключении: {e}")
    else:
        # Если карточки нет в памяти, шлем разовое сообщение об отключении
        msg = (f"🔴 <b>[VPS Hysteria: {server_ip}] Клиент отключился</b>\n\n"
               f"👤 Пользователь: <code>{username}</code>\n"
               f"🌐 IP-адрес: <code>{client_ip}</code>\n"
               f"🕒 Время: <code>{timestamp}</code>")
        await send_alert_to_admins(msg)
