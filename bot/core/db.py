import os
import sqlite3
import json
import logging
import asyncio
from typing import Dict, List, Tuple, Optional

# Находим корневой каталог проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
# bot/core/db.py -> bot/config/vpn_history.db
DB_FILE = os.path.abspath(os.path.join(current_dir, '../config/vpn_history.db'))
JSON_FILE = os.path.abspath(os.path.join(current_dir, '../config/vpn_connections_history.json'))

# Глобальная блокировка для синхронизации записи в SQLite
_db_lock = asyncio.Lock()

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Включаем WAL режим для параллельного чтения и быстрой записи
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    """Инициализирует таблицы БД и запускает автоматическую миграцию старых данных."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vpn_sessions (
                    session_id TEXT,
                    username TEXT,
                    ip TEXT,
                    connect_time TEXT,
                    disconnect_time TEXT,
                    duration TEXT,
                    is_new_ip INTEGER,
                    download_bytes INTEGER DEFAULT 0,
                    upload_bytes INTEGER DEFAULT 0,
                    PRIMARY KEY (username, session_id)
                );
            """)
            
            # Автоматическая миграция: добавляем новые колонки для трафика, если их нет
            try:
                conn.execute("ALTER TABLE vpn_sessions ADD COLUMN download_bytes INTEGER DEFAULT 0;")
            except sqlite3.OperationalError:
                pass # уже существует
            try:
                conn.execute("ALTER TABLE vpn_sessions ADD COLUMN upload_bytes INTEGER DEFAULT 0;")
            except sqlite3.OperationalError:
                pass # уже существует

            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_username ON vpn_sessions (username);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_ip ON vpn_sessions (ip);")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temp_bans (
                    server_ip TEXT,
                    dst_ip TEXT,
                    expire_time TEXT,
                    PRIMARY KEY (server_ip, dst_ip)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ips_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attacker_ip TEXT,
                    tunnel_name TEXT,
                    attacker_email TEXT,
                    reaction_time TEXT,
                    timestamp TEXT
                );
            """)
            
        logging.info("[Database] Таблицы базы данных успешно проверены/созданы с поддержкой трафика и инцидентов.")
        
        # Миграция из JSON файла при первом запуске
        if os.path.exists(JSON_FILE):
            logging.info("[Database] Обнаружен старый файл истории JSON. Запуск миграции...")
            try:
                with open(JSON_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                migrated_count = 0
                with conn:
                    for username, sessions in history.items():
                        for s in sessions:
                            # Проверяем, существует ли уже эта сессия
                            cursor = conn.execute(
                                "SELECT 1 FROM vpn_sessions WHERE username = ? AND session_id = ?",
                                (username, str(s['session_id']))
                            )
                            if not cursor.fetchone():
                                conn.execute("""
                                    INSERT INTO vpn_sessions (session_id, username, ip, connect_time, disconnect_time, duration, is_new_ip)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    str(s['session_id']),
                                    username,
                                    s.get('ip'),
                                    s.get('connect_time'),
                                    s.get('disconnect_time'),
                                    s.get('duration'),
                                    1 if s.get('is_new_ip') else 0
                                ))
                                migrated_count += 1
                                
                logging.info(f"[Database] Миграция успешно завершена! Перенесено {migrated_count} записей.")
                
                # Переименовываем старый JSON файл в бэкап, чтобы не сканировать повторно
                backup_file = JSON_FILE + ".backup"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(JSON_FILE, backup_file)
                logging.info(f"[Database] Старый файл истории переименован в {os.path.basename(backup_file)}")
            except Exception as e:
                logging.error(f"[Database] Ошибка при миграции старой истории: {e}")
    finally:
        conn.close()

# Запускаем инициализацию при импорте модуля
init_db()

# --- Асинхронные обертки для операций БД ---

async def execute_write(query: str, params: tuple = ()) -> bool:
    """Выполняет команду записи (INSERT/UPDATE/DELETE) в потокобезопасном режиме."""
    async with _db_lock:
        def _write():
            conn = get_db_connection()
            try:
                with conn:
                    conn.execute(query, params)
                return True
            except Exception as e:
                logging.error(f"[Database Error] Ошибка записи: {e} | Query: {query}")
                return False
            finally:
                conn.close()
        return await asyncio.to_thread(_write)

async def execute_read_all(query: str, params: tuple = ()) -> List[dict]:
    """Выполняет чтение списка строк."""
    def _read():
        conn = get_db_connection()
        try:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"[Database Error] Ошибка чтения: {e} | Query: {query}")
            return []
        finally:
            conn.close()
    return await asyncio.to_thread(_read)

async def execute_read_one(query: str, params: tuple = ()) -> Optional[dict]:
    """Выполняет чтение одной строки."""
    def _read():
        conn = get_db_connection()
        try:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"[Database Error] Ошибка чтения строки: {e} | Query: {query}")
            return None
        finally:
            conn.close()
    return await asyncio.to_thread(_read)


async def get_state(key: str, default=None):
    """Считывает сериализованный JSON-объект состояния из БД по ключу."""
    row = await execute_read_one("SELECT value FROM bot_state WHERE key = ?", (key,))
    if not row:
        return default
    try:
        return json.loads(row['value'])
    except Exception as e:
        logging.error(f"[Database] Ошибка десериализации состояния для '{key}': {e}")
        return default


async def set_state(key: str, value) -> bool:
    """Записывает сериализованный JSON-объект состояния в БД по ключу."""
    try:
        val_str = json.dumps(value, ensure_ascii=False)
        return await execute_write(
            "INSERT OR REPLACE INTO bot_state (key, value) VALUES (?, ?)",
            (key, val_str)
        )
    except Exception as e:
        logging.error(f"[Database] Ошибка сериализации состояния для '{key}': {e}")
        return False

async def log_ips_incident(attacker_ip: str, tunnel_name: str, attacker_email: str, reaction_time: str) -> bool:
    """Записывает инцидент IPS в базу данных."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return await execute_write(
        "INSERT INTO ips_incidents (attacker_ip, tunnel_name, attacker_email, reaction_time, timestamp) VALUES (?, ?, ?, ?, ?)",
        (attacker_ip, tunnel_name, attacker_email, reaction_time, timestamp)
    )

async def get_node_whitelists() -> dict:
    """Возвращает все белые списки нод."""
    return await get_state("ips_node_whitelists", {})

async def save_node_whitelists(whitelists: dict) -> bool:
    """Сохраняет все белые списки нод."""
    return await set_state("ips_node_whitelists", whitelists)

async def is_whitelisted(node: str, ip: Optional[str] = None, port: Optional[int] = None, process: Optional[str] = None) -> bool:
    """
    Проверяет, находится ли IP:Порт или Процесс в белом списке для данной ноды или глобально.
    """
    whitelists = await get_node_whitelists()
    
    # Проверяем конкретную ноду и глобальную ноду
    nodes_to_check = ["global", node]
    
    for n in nodes_to_check:
        wl = whitelists.get(n, {})
        
        # Проверяем процессы
        if process:
            proc_wl = wl.get("processes", [])
            if process.lower().strip() in [p.lower().strip() for p in proc_wl]:
                logging.info(f"[Whitelist Check] Процесс {process} находится в белом списке ноды {n}")
                return True
                
        # Проверяем IP и Порт
        if ip:
            ip_port_wl = wl.get("ip_ports", [])
            for entry in ip_port_wl:
                entry = entry.strip()
                if ":" in entry:
                    entry_ip, entry_port = entry.rsplit(":", 1)
                    if entry_ip == ip:
                        if entry_port == "*" or (port is not None and str(entry_port) == str(port)):
                            logging.info(f"[Whitelist Check] Соединение {ip}:{port} совпало с правилом {entry} на ноде {n}")
                            return True
                else:
                    if entry == ip:
                        logging.info(f"[Whitelist Check] IP {ip} совпал с правилом {entry} на ноде {n}")
                        return True
                        
    return False


async def save_vpn_connect(username: str, ip: str, connect_time_str: str, tx: int, rx: int) -> str:
    """
    Сохраняет событие подключения к VPN в базу данных.
    Проверяет, является ли данный IP новым для этого пользователя.
    Возвращает сгенерированный session_id.
    """
    import uuid
    # 1. Проверяем, встречался ли IP ранее для этого пользователя
    row = await execute_read_one(
        "SELECT 1 FROM vpn_sessions WHERE username = ? AND ip = ? LIMIT 1",
        (username, ip)
    )
    is_new_ip = 0 if row else 1
    
    # 2. Генерируем уникальный session_id
    session_id = str(uuid.uuid4())
    
    # 3. Записываем в базу данных
    await execute_write(
        "INSERT INTO vpn_sessions (session_id, username, ip, connect_time, disconnect_time, duration, is_new_ip, download_bytes, upload_bytes) VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?)",
        (session_id, username, ip, connect_time_str, is_new_ip, tx, rx)
    )
    logging.info(f"[Database] Зарегистрировано подключение: {username} ({ip}), session_id: {session_id}")
    return session_id


async def save_vpn_disconnect(username: str, ip: str, disconnect_time_str: str, tx: int, rx: int):
    """
    Обновляет сессию VPN информацией о времени отключения, длительности и потреблении трафика.
    """
    # 1. Ищем последнюю активную сессию пользователя с этого IP
    session = await execute_read_one(
        "SELECT session_id, connect_time, download_bytes, upload_bytes FROM vpn_sessions WHERE username = ? AND ip = ? AND disconnect_time IS NULL ORDER BY connect_time DESC LIMIT 1",
        (username, ip)
    )
    
    if session:
        session_id = session['session_id']
        connect_time_str = session['connect_time']
        initial_tx = session['download_bytes'] or 0
        initial_rx = session['upload_bytes'] or 0
        
        # Расчет потребленного трафика за сессию (положительные значения)
        diff_tx = max(0, tx - initial_tx)
        diff_rx = max(0, rx - initial_rx)
        
        # Расчет длительности
        try:
            import datetime
            conn_dt = datetime.datetime.strptime(connect_time_str, "%Y-%m-%d %H:%M:%S")
            disc_dt = datetime.datetime.strptime(disconnect_time_str, "%Y-%m-%d %H:%M:%S")
            duration_sec = int((disc_dt - conn_dt).total_seconds())
        except Exception:
            duration_sec = 0
            
        if duration_sec < 60:
            duration_str = f"{duration_sec} сек"
        elif duration_sec < 3600:
            duration_str = f"{duration_sec // 60} мин {duration_sec % 60} сек"
        else:
            duration_str = f"{duration_sec // 3600} ч {(duration_sec % 3600) // 60} мин"
            
        await execute_write(
            "UPDATE vpn_sessions SET disconnect_time = ?, duration = ?, download_bytes = ?, upload_bytes = ? WHERE username = ? AND session_id = ?",
            (disconnect_time_str, duration_str, diff_tx, diff_rx, username, session_id)
        )
        logging.info(f"[Database] Зарегистрировано отключение: {username} ({ip}), использовано {diff_tx} tx / {diff_rx} rx, session_id: {session_id}")
    else:
        # Резервный вариант: если сессия не найдена (пропустили подключение), создаем завершенную с нулевым трафиком
        import uuid
        session_id = str(uuid.uuid4())
        
        row = await execute_read_one(
            "SELECT 1 FROM vpn_sessions WHERE username = ? AND ip = ? LIMIT 1",
            (username, ip)
        )
        is_new_ip = 0 if row else 1
        duration_str = "неизвестно"
        
        await execute_write(
            "INSERT INTO vpn_sessions (session_id, username, ip, connect_time, disconnect_time, duration, is_new_ip, download_bytes, upload_bytes) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)",
            (session_id, username, ip, disconnect_time_str, disconnect_time_str, duration_str, is_new_ip)
        )
        logging.info(f"[Database] Зарегистрировано отключение (без подключения): {username} ({ip}), session_id: {session_id}")



