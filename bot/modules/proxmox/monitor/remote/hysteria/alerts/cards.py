import logging
import datetime
import time as pytime
from core.bot import bot
from core.config import settings
from modules.proxmox.monitor.utils import send_alert_to_admins
from ..history import log_connection
from .state import active_activity_cards, is_card_active, save_active_cards_state
from .formatter import format_card_msg_async

async def handle_hysteria_connect(server, username, client_ip, silent=False):
    """Добавляет новое подключение к хронологической карточке (создает новую или обновляет текущую)."""
    server_ip = server['ip']
    now_time = pytime.time()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    key = (server_ip, username)
    
    # Записываем сессию во всеобщую историю SQLite и проверяем смену IP
    session_id, recent_prev, is_new_ip = await log_connection(username, client_ip)
    
    # СЦЕНАРИЙ БЕЗОПАСНОСТИ: Если обнаружен НОВЫЙ IP-адрес, шлем отдельное тревожное сообщение (🚨)
    if is_new_ip:
        if silent:
            # В бесшумном режиме просто создаем карточку без отправки Telegram сообщения
            lines = [f"🟢 <code>[{timestamp}]</code> Подключение с <code>{client_ip}</code> ⚠️ <b>[НОВЫЙ IP]</b>"]
            connections = {client_ip: [datetime.datetime.now()]}
            active_activity_cards[key] = {
                'admin_messages': [],
                'started_at': now_time,
                'last_activity_at': now_time,
                'lines': lines,
                'connections': connections
            }
            await save_active_cards_state()
            return

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
        for admin_id in settings.admin_ids:
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
                'last_activity_at': now_time,
                'lines': lines,
                'connections': connections
            }
            await save_active_cards_state()
        return

    # ОБЫЧНЫЙ СЦЕНАРИЙ (Стабильный IP): Добавляем к хронологической карте
    event_line = f"🟢 <code>[{timestamp}]</code> Подключение с <code>{client_ip}</code>"
    
    card = active_activity_cards.get(key)
    # Если карточка активна, просто редактируем её
    if card and is_card_active(card, now_time):
        card['lines'].append(event_line)
        card['last_activity_at'] = now_time
        if client_ip not in card['connections']:
            card['connections'][client_ip] = []
        card['connections'][client_ip].append(datetime.datetime.now())
        await save_active_cards_state()
        
        if not silent:
            if not card.get('admin_messages'):
                # Если карточка была создана без отправки сообщения (в бесшумном режиме), шлем новое
                msg = await format_card_msg_async(server, username, card['lines'], card=card)
                sent_messages = []
                for admin_id in settings.admin_ids:
                    try:
                        m = await bot.send_message(admin_id, msg, parse_mode="HTML")
                        sent_messages.append({'admin_id': admin_id, 'message_id': m.message_id})
                    except Exception:
                        pass
                card['admin_messages'] = sent_messages
                await save_active_cards_state()
            else:
                msg = await format_card_msg_async(server, username, card['lines'], card=card)
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
            
        if silent:
            active_activity_cards[key] = {
                'admin_messages': [],
                'started_at': now_time,
                'last_activity_at': now_time,
                'lines': lines,
                'connections': connections
            }
            await save_active_cards_state()
            return

        msg = await format_card_msg_async(server, username, lines)
        sent_messages = []
        for admin_id in settings.admin_ids:
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
                'last_activity_at': now_time,
                'lines': lines,
                'connections': connections
            }
            await save_active_cards_state()
