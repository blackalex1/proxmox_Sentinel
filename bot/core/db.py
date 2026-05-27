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
            
        logging.info("[Database] Таблицы базы данных успешно проверены/созданы с поддержкой трафика.")
        
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

