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

from core.db import get_state, set_state

async def load_alerts_state():
    """Загружает состояния Hysteria алертов из SQLite при старте бота."""
    global recent_hysteria_violations, recent_remote_traffic_alerts, active_activity_cards
    
    # 1. Загружаем recent_hysteria_violations
    violations = await get_state("recent_hysteria_violations", {})
    recent_hysteria_violations.clear()
    recent_hysteria_violations.update(violations)
    
    # 2. Загружаем recent_remote_traffic_alerts
    alerts = await get_state("recent_remote_traffic_alerts", {})
    recent_remote_traffic_alerts.clear()
    recent_remote_traffic_alerts.update(alerts)
    
    # 3. Загружаем active_activity_cards
    cards = await get_state("active_activity_cards", {})
    active_activity_cards.clear()
    for k, card in cards.items():
        if ":" in k:
            server_ip, username = k.split(":", 1)
            # Десериализуем connections (переводим ISO-строки дат обратно в datetime)
            connections = {}
            for ip, dates in card.get('connections', {}).items():
                connections[ip] = []
                for d_str in dates:
                    try:
                        connections[ip].append(datetime.datetime.fromisoformat(d_str))
                    except Exception:
                        pass
            card['connections'] = connections
            active_activity_cards[(server_ip, username)] = card
            
    logging.info(f"[Hysteria State] Успешно восстановлено сессий: {len(active_activity_cards)}, нарушений: {len(recent_hysteria_violations)}")

async def save_violations_state():
    """Сохраняет recent_hysteria_violations в SQLite."""
    await set_state("recent_hysteria_violations", recent_hysteria_violations)

async def save_traffic_alerts_state():
    """Сохраняет recent_remote_traffic_alerts в SQLite."""
    await set_state("recent_remote_traffic_alerts", recent_remote_traffic_alerts)

async def save_active_cards_state():
    """Сохраняет active_activity_cards в SQLite."""
    serializable_cards = {}
    for (server_ip, username), card in active_activity_cards.items():
        key_str = f"{server_ip}:{username}"
        # Сериализуем connections datetime объекты в ISO-строки
        connections_str = {}
        for ip, dates in card.get('connections', {}).items():
            connections_str[ip] = [d.isoformat() if isinstance(d, datetime.datetime) else d for d in dates]
            
        serializable_card = dict(card)
        serializable_card['connections'] = connections_str
        serializable_cards[key_str] = serializable_card
        
    await set_state("active_activity_cards", serializable_cards)
def is_card_active(card, now_time):
    """Проверяет, активна ли карточка сессии Hysteria.
    Карточка считается активной, если:
    1. У пользователя есть хотя бы одно незакрытое (активное) подключение.
    2. Или с момента последнего события (активности) прошло менее 15 минут (900 сек).
    """
    if not card:
        return False
        
    # Проверяем наличие активных подключений
    has_active = False
    for ip, conns in card.get('connections', {}).items():
        if conns:
            has_active = True
            break
            
    if has_active:
        return True
        
    # Если все отключились, даем карточке "повисеть" 15 минут для группировки переподключений
    last_act = card.get('last_activity_at', card.get('started_at', now_time))
    return now_time - last_act < 900.0


# Кэш параметров API Hysteria для каждого сервера: server_ip -> (port, secret)
hysteria_api_configs = {}

async def discover_hysteria_api_config(server):
    """Автоматически считывает и разбирает /etc/hysteria/config.json на удаленном сервере
    для извлечения порта и секрета Traffic Stats API.
    """
    import json
    ip = server['ip']
    if ip in hysteria_api_configs:
        return hysteria_api_configs[ip]
        
    logging.info(f"[Remote Hysteria {ip}] Попытка автоопределения параметров Traffic Stats API...")
    try:
        from ..ssh import run_remote_ssh_cmd
        success, stdout, stderr = await run_remote_ssh_cmd(server, ["cat", "/etc/hysteria/config.json"])
        if success and stdout:
            data = json.loads(stdout)
            stats = data.get("trafficStats", {})
            listen = stats.get("listen", "")
            secret = stats.get("secret", "")
            
            if listen and secret:
                port = "25413"
                if ":" in listen:
                    port = listen.split(":")[-1]
                
                config = {"port": port, "secret": secret}
                hysteria_api_configs[ip] = config
                logging.info(f"[Remote Hysteria {ip}] Успешно обнаружен API: порт {port}, секрет найден.")
                return config
    except Exception as e:
        logging.warning(f"[Remote Hysteria {ip}] Не удалось разобрать конфиг для автоопределения API: {e}")
        
    return None

async def get_remote_hysteria_traffic(server, username):
    """Запрашивает из Traffic Stats API текущий трафик (tx/rx) для конкретного пользователя."""
    import json
    try:
        config = await discover_hysteria_api_config(server)
        if not config:
            return None
            
        port = config["port"]
        secret = config["secret"]
        
        from ..ssh import run_remote_ssh_cmd
        cmd = ["curl", "-s", "-H", f"'Authorization: {secret}'", f"http://127.0.0.1:{port}/traffic"]
        
        success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
        if success and stdout:
            data = json.loads(stdout)
            user_stats = data.get(username)
            if user_stats:
                return user_stats
    except Exception as e:
        logging.warning(f"[Remote Hysteria {server['ip']}] Не удалось получить трафик для {username}: {e}")
    return None

async def format_card_msg_async(server, username, lines, card=None):
    """Форматирует сообщение карточки активности Hysteria 2 с добавлением данных по трафику."""
    displayed_lines = lines[-15:]
    timeline = "\n".join(displayed_lines)
    if len(lines) > 15:
        timeline = "<i>... показать ещё ...</i>\n" + timeline
        
    traffic_str = ""
    stats = await get_remote_hysteria_traffic(server, username)
    tx = None
    rx = None
    if stats:
        tx = stats.get("tx", 0)
        rx = stats.get("rx", 0)
        if card:
            card['download_bytes'] = tx
            card['upload_bytes'] = rx
    elif card and card.get('download_bytes') is not None:
        tx = card.get('download_bytes')
        rx = card.get('upload_bytes')
        
    if tx is not None and rx is not None:
        def format_bytes(b):
            if b < 1024:
                return f"{b} B"
            elif b < 1024 * 1024:
                return f"{b / 1024:.2f} KB"
            elif b < 1024 * 1024 * 1024:
                return f"{b / (1024 * 1024):.2f} MB"
            else:
                return f"{b / (1024 * 1024 * 1024):.2f} GB"
                
        # В Hysteria tx — это то, что отправлено клиенту (скачано им), rx — принято от клиента (загружено им)
        download = format_bytes(tx)
        upload = format_bytes(rx)
        traffic_str = f"📥 <b>Скачано:</b> <code>{download}</code> | 📤 <b>Загружено:</b> <code>{upload}</code>\n\n"
        
    text = (
        f"📊 <b>[VPS Hysteria: {server['ip']}] Активность сессии</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Пользователь:</b> <code>{username}</code>\n\n"
        f"{traffic_str}"
        f"📋 <b>Хронология событий:</b>\n"
        f"{timeline}"
    )
    return text

async def poll_active_hysteria_traffic():
    """Фоновый периодический опрос API Hysteria для обновления трафика в активных карточках."""
    while True:
        try:
            await asyncio.sleep(60) # опрашиваем раз в минуту
            
            from core.config import settings
            if not settings.remote_servers:
                continue
                
            for server in settings.remote_servers:
                server_ip = server['ip']
                
                for (srv_ip, username), card in list(active_activity_cards.items()):
                    if srv_ip != server_ip:
                        continue
                        
                    import time as pytime
                    now_time = pytime.time()
                    if not is_card_active(card, now_time):
                        continue
                        
                    # Если карточка создана в бесшумном режиме (нет Telegram-сообщений), пропускаем опрос
                    if not card.get('admin_messages'):
                        continue
                        
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
                            if "message is not modified" not in str(e).lower():
                                logging.error(f"Не удалось обновить трафик в карточке Hysteria: {e}")
        except Exception as e:
            logging.error(f"Ошибка в фоновом опросе трафика Hysteria: {e}")

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
