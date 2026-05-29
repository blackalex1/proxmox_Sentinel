import logging
import datetime
from core.db import get_state, set_state

# Нарушения пользователей Hysteria: username -> list of timestamps
recent_hysteria_violations = {}

# Память для троттлинга алертов трафика удаленного VPS (IP -> timestamp)
recent_remote_traffic_alerts = {}

# Активные карточки хронологии сессий: (server_ip, username) -> dict
active_activity_cards = {}

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
