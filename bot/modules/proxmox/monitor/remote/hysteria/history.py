import datetime
import logging
from core.db import execute_write, execute_read_all, execute_read_one

async def load_history() -> dict:
    """Обеспечивает обратную совместимость: выгружает всю историю из SQLite в формате старого словаря."""
    try:
        rows = await execute_read_all("SELECT * FROM vpn_sessions ORDER BY connect_time ASC")
        history = {}
        for r in rows:
            username = r['username']
            if username not in history:
                history[username] = []
            history[username].append({
                'session_id': r['session_id'],
                'ip': r['ip'],
                'connect_time': r['connect_time'],
                'disconnect_time': r['disconnect_time'],
                'duration': r['duration'],
                'is_new_ip': bool(r['is_new_ip'])
            })
        return history
    except Exception as e:
        logging.error(f"Ошибка load_history из SQLite: {e}")
        return {}

async def save_history(history: dict):
    """Метод-заглушка для обратной совместимости (теперь запись идет атомарно в SQLite)."""
    pass

async def log_connection(username: str, client_ip: str) -> tuple:
    """Записывает начало сессии в SQLite и возвращает (session_id, recent_prev, is_new_ip)."""
    # 1. Получаем 3 предыдущих завершенных сессии
    prev_rows = await execute_read_all(
        "SELECT * FROM vpn_sessions WHERE username = ? AND disconnect_time IS NOT NULL ORDER BY connect_time DESC LIMIT 3",
        (username,)
    )
    recent_prev = []
    for r in prev_rows:
        recent_prev.append({
            'session_id': r['session_id'],
            'ip': r['ip'],
            'connect_time': r['connect_time'],
            'disconnect_time': r['disconnect_time'],
            'duration': r['duration'],
            'is_new_ip': bool(r['is_new_ip'])
        })

    # 2. Проверяем на изменение IP по сравнению с прошлым подключением
    is_new_ip = False
    last_row = await execute_read_one(
        "SELECT ip FROM vpn_sessions WHERE username = ? AND disconnect_time IS NOT NULL ORDER BY connect_time DESC LIMIT 1",
        (username,)
    )
    if last_row and last_row['ip'] != client_ip:
        is_new_ip = True

    # 3. Вычисляем ID следующей сессии (просто количество записей этого пользователя)
    count_row = await execute_read_one(
        "SELECT COUNT(*) as cnt FROM vpn_sessions WHERE username = ?",
        (username,)
    )
    session_id = str(count_row['cnt'] if count_row else 0)

    # 4. Вставляем новую активную сессию
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await execute_write(
        """
        INSERT INTO vpn_sessions (session_id, username, ip, connect_time, disconnect_time, duration, is_new_ip)
        VALUES (?, ?, ?, ?, NULL, NULL, ?)
        """,
        (session_id, username, client_ip, now_str, 1 if is_new_ip else 0)
    )

    return session_id, recent_prev, is_new_ip

async def update_disconnection(username: str, client_ip: str, duration_str: str) -> bool:
    """Обновляет время отключения и длительность последней активной сессии в SQLite."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Используем ROWID подзапрос, чтобы точечно обновить последнюю по времени активную сессию
    query = """
        UPDATE vpn_sessions 
        SET disconnect_time = ?, duration = ? 
        WHERE ROWID = (
            SELECT ROWID FROM vpn_sessions 
            WHERE username = ? AND ip = ? AND disconnect_time IS NULL 
            ORDER BY connect_time DESC LIMIT 1
        )
    """
    return await execute_write(query, (now_str, duration_str, username, client_ip))
