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
                    reason TEXT DEFAULT 'Вручную',
                    PRIMARY KEY (server_ip, dst_ip)
                );
            """)
            try:
                conn.execute("ALTER TABLE temp_bans ADD COLUMN reason TEXT DEFAULT 'Вручную';")
            except sqlite3.OperationalError:
                pass # уже существует
            
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approved_ips (
                    username TEXT,
                    ip TEXT,
                    PRIMARY KEY (username, ip)
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_approved_ips_username ON approved_ips (username);")
            conn.execute("DELETE FROM approved_ips WHERE ip = 'ip' OR (ip NOT LIKE '%.%' AND ip NOT LIKE '%:%');")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS temp_port_bans (
                    server_ip TEXT,
                    client_ip TEXT,
                    port INTEGER,
                    protocol TEXT DEFAULT 'tcp',
                    expire_time TEXT,
                    reason TEXT DEFAULT 'Вручную',
                    PRIMARY KEY (server_ip, client_ip, port, protocol)
                );
            """)
            
        logging.info("database_database_tables_successfully_verified_created_with")
        
        # Миграция из JSON файла при первом запуске
        if os.path.exists(JSON_FILE):
            logging.info("database_old_json_history_file_detected_starting")
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
                                
                logging.info("database_migration_completed_successfully_transferred_records", migrated_count)
                
                # Переименовываем старый JSON файл в бэкап, чтобы не сканировать повторно
                backup_file = JSON_FILE + ".backup"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(JSON_FILE, backup_file)
                logging.info("database_staryy_fayl_istorii_pereimenovan_v", os.path.basename(backup_file))
            except Exception as e:
                logging.error("database_error_migrating_old_history", e)
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
                logging.error("database_error_write_error_query", e, query)
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
            logging.error("database_error_read_error_query", e, query)
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
            logging.error("database_error_row_read_error_query", e, query)
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
        logging.error("database_deserialization_state_error_for", key, e)
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
        logging.error("database_serialization_state_error_for", key, e)
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
                logging.info("whitelist_check_process_is_whitelisted_on_node", process, n)
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
                            logging.info("whitelist_check_connection_matched_rule_on_node", ip, port, entry, n)
                            return True
                else:
                    if entry == ip:
                        logging.info("whitelist_check_ip_matched_rule_on_node", ip, entry, n)
                        return True
                        
    return False


import ipaddress

def is_valid_ip_or_cidr(val: str) -> bool:
    val = (val or "").strip()
    if not val or val == "ip":
        return False
    try:
        ipaddress.ip_address(val)
        return True
    except ValueError:
        pass
    try:
        ipaddress.ip_network(val, strict=False)
        return True
    except ValueError:
        pass
    return False

async def is_ip_approved(username: str, ip: str) -> bool:
    """Проверяет, одобрен ли IP для пользователя (без учета регистра имени пользователя)."""
    if not is_valid_ip_or_cidr(ip):
        return False
    row = await execute_read_one(
        "SELECT 1 FROM approved_ips WHERE LOWER(username) = LOWER(?) AND ip = ?",
        (username, ip)
    )
    return row is not None


async def approve_ip(username: str, ip: str) -> bool:
    """Добавляет IP в список одобренных для пользователя и синхронизирует ТОЛЬКО с теми панелями, где заведен данный клиент."""
    if not is_valid_ip_or_cidr(ip):
        logging.warning(f"Invalid IP '{ip}' passed to approve_ip for {username}")
        return False
    res = await execute_write(
        "INSERT OR IGNORE INTO approved_ips (username, ip) VALUES (?, ?)",
        (username, ip)
    )
    try:
        from core.spectre_client import spectre_manager
        found_clients = await spectre_manager.search_client_all(username)
        target_panel_names = {c.get("panel_name") for c in found_clients if c.get("panel_name")}
        
        # Если клиент найден конкретно на определенных панелях — берем только их, иначе синхронизируем на все
        target_panels = [p for p in spectre_manager.panels.values() if not target_panel_names or p.name in target_panel_names]
        
        for panel in target_panels:
            await panel.request("POST", "/api/security/allow-ip", json={"ip": ip, "email": username})
    except Exception as e:
        logging.error(f"Error syncing allow-ip to panel: {e}")
    return res


async def cleanup_orphaned_approved_ips(active_emails: set) -> int:
    """Удаляет из базы данных бота (approved_ips) удаленных пользователей, которых больше нет на панелях."""
    if not active_emails:
        return 0
    # Приводим к нижнему регистру для надежной сверки
    active_emails_lower = {e.lower() for e in active_emails}
    rows = await execute_read_all("SELECT DISTINCT username FROM approved_ips")
    if not rows:
        return 0
    deleted_count = 0
    for row in rows:
        username = row.get("username") if isinstance(row, dict) else row[0]
        if username and username.lower() not in active_emails_lower:
            await execute_write("DELETE FROM approved_ips WHERE username = ?", (username,))
            deleted_count += 1
            logging.info(f"[Cleanup] Removed orphaned approved_ips for deleted user: {username}")
    return deleted_count


async def sync_approved_ips_to_panels():
    """Синхронизирует одобренные IP с панелями (двусторонняя синхронизация) и очищает мусор."""
    try:
        from core.spectre_client import spectre_manager
        if not spectre_manager.panels:
            return

        # 1. Получаем список всех существующих клиентов со всех панелей с привязкой к панели
        all_clients = await spectre_manager.search_client_all("")
        client_panels_map = {}
        active_emails = set()
        reachable_panels = set()
        
        for c in all_clients:
            c_info = c.get("client") or {}
            email = c.get("email") or c_info.get("email")
            p_name = c.get("panel_name")
            if p_name:
                reachable_panels.add(p_name)
            if email:
                active_emails.add(email)
                if p_name:
                    for p in spectre_manager.panels.values():
                        if p.name == p_name:
                            client_panels_map.setdefault(email.lower(), set()).add(p)
                
                # Импортируем allowed_ips с панели в локальную базу бота
                allowed_ips_str = c_info.get("allowed_ips") or c_info.get("allowedIps") or ""
                if allowed_ips_str:
                    for panel_ip in allowed_ips_str.split(","):
                        panel_ip = panel_ip.strip()
                        if panel_ip and is_valid_ip_or_cidr(panel_ip):
                            await execute_write(
                                "INSERT OR IGNORE INTO approved_ips (username, ip) VALUES (?, ?)",
                                (email, panel_ip)
                            )

        # 2. Очищаем устаревший мусор ТОЛЬКО если ВСЕ зарегистрированные панели ответили без ошибок!
        total_configured_panels = len(spectre_manager.panels)
        if active_emails and len(reachable_panels) >= total_configured_panels:
            await cleanup_orphaned_approved_ips(active_emails)

        # 3. Синхронизируем оставшиеся одобренные IP ТОЛЬКО на те панели, где этот клиент реально заведен!
        rows = await execute_read_all("SELECT username, ip FROM approved_ips")
        if not rows:
            return

        synced_count = 0
        for r in rows:
            username = r.get("username") if isinstance(r, dict) else r[0]
            ip = r.get("ip") if isinstance(r, dict) else r[1]
            if not username or not ip or not is_valid_ip_or_cidr(ip):
                continue
            target_panels = client_panels_map.get(username.lower(), set())
            # Если карту привязок еще не составили или панель не определена, перестраховываемся
            if not target_panels:
                target_panels = set(spectre_manager.panels.values())

            for panel in target_panels:
                try:
                    res_ok, res = await panel.request("POST", "/api/security/allow-ip", json={"ip": ip, "email": username})
                    if res_ok and isinstance(res, dict) and res.get("success"):
                        synced_count += 1
                except Exception as e:
                    logging.error(f"Error syncing approved IP {ip} for {username} to panel {panel.name}: {e}")
        if synced_count > 0:
            logging.info(f"[IP Sync] Successfully synced {synced_count} approved IP addresses to target panels.")
    except Exception as e:
        logging.error(f"Error in sync_approved_ips_to_panels: {e}")


async def save_vpn_connect(username: str, ip: str, connect_time_str: str, tx: int, rx: int) -> str:
    """
    Сохраняет событие подключения к VPN в базу данных.
    Проверяет, является ли данный IP новым для этого пользователя.
    Возвращает сгенерированный session_id.
    """
    import uuid
    # 1. Проверяем, одобрен ли IP
    is_approved = await is_ip_approved(username, ip)
    is_new_ip = 0 if is_approved else 1
    
    # 2. Генерируем уникальный session_id
    session_id = str(uuid.uuid4())
    
    # 3. Записываем в базу данных
    await execute_write(
        "INSERT INTO vpn_sessions (session_id, username, ip, connect_time, disconnect_time, duration, is_new_ip, download_bytes, upload_bytes) VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?)",
        (session_id, username, ip, connect_time_str, is_new_ip, tx, rx)
    )
    logging.info("[Database] Connection registered: %s (%s), is_approved=%s, is_new_ip=%s, session_id=%s", username, ip, is_approved, is_new_ip, session_id)
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
        is_noise = (duration_sec <= 3 and diff_tx == 0 and diff_rx == 0)
        if not is_noise:
            logging.info("database_disconnection_registered_used_tx_rx", username, ip, diff_tx, diff_rx, session_id)
        return session_id, duration_sec, diff_tx, diff_rx
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
        logging.info("database_disconnection_registered_without_connection_session_id", username, ip, session_id)
        return session_id, 0, 0, 0


async def get_client_cumulative_traffic(username: str) -> tuple[int, int]:
    """Возвращает совокупный исторический трафик (download, upload) пользователя из базы бота."""
    if not username:
        return 0, 0
    try:
        row = await execute_read_one(
            "SELECT SUM(download_bytes) as total_down, SUM(upload_bytes) as total_up FROM vpn_sessions WHERE username = ?",
            (username,)
        )
        if row and (row.get('total_down') or row.get('total_up')):
            return int(row.get('total_down') or 0), int(row.get('total_up') or 0)
    except Exception:
        pass
    return 0, 0



