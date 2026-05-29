import asyncio
import logging
import datetime
import time as pytime
from core.bot import bot
from modules.proxmox.monitor.utils import send_alert_to_admins
from ..history import update_disconnection
from .state import active_activity_cards, is_card_active, save_active_cards_state
from .traffic import get_remote_hysteria_traffic
from .formatter import format_card_msg_async

async def handle_hysteria_disconnect(server, username, client_ip, silent=False):
    """Добавляет событие отключения и длительность к хронологической карточке активности."""
    server_ip = server['ip']
    now_time = pytime.time()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    key = (server_ip, username)
    
    card = active_activity_cards.get(key)
    if not card or not is_card_active(card, now_time):
        if not silent:
            await asyncio.sleep(0.8)
            card = active_activity_cards.get(key)
        
    if card and is_card_active(card, now_time):
        card['last_activity_at'] = now_time
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
                
            # Получаем накопленный трафик из карточки или пытаемся сделать быстрый опрос напоследок
            download_bytes = card.get('download_bytes', 0)
            upload_bytes = card.get('upload_bytes', 0)
            
            if not silent:
                stats = await get_remote_hysteria_traffic(server, username)
                if stats:
                    download_bytes = stats.get("tx", 0)
                    upload_bytes = stats.get("rx", 0)
                    card['download_bytes'] = download_bytes
                    card['upload_bytes'] = upload_bytes
                
            # Завершаем запись сессии в SQLite БД
            await update_disconnection(username, client_ip, duration_str, download_bytes, upload_bytes)
                
        event_line = f"🔴 <code>[{timestamp}]</code> Отключение <code>{client_ip}</code> — {duration_str}"
        card['lines'].append(event_line)
        await save_active_cards_state()
        
        if not silent:
            if not card.get('admin_messages'):
                # Если карточка была создана без отправки сообщения (в бесшумном режиме), шлем разовый алерт о завершении сессии
                msg = (f"🔴 <b>[VPS Hysteria: {server_ip}] Клиент отключился</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code> — {duration_str}\n"
                       f"🕒 Время: <code>{timestamp}</code>")
                await send_alert_to_admins(msg)
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
                        logging.error(f"Не удалось обновить карточку Hysteria при отключении: {e}")
    else:
        if not silent:
            # Если карточки нет в памяти, шлем разовое сообщение об отключении
            msg = (f"🔴 <b>[VPS Hysteria: {server_ip}] Клиент отключился</b>\n\n"
                   f"👤 Пользователь: <code>{username}</code>\n"
                   f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            await send_alert_to_admins(msg)
