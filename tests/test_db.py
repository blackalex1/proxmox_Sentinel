import pytest
import os
import tempfile
import sqlite3

# Перехватываем путь к файлу БД и подменяем его временным файлом для тестов
import core.db
temp_db_fd, temp_db_path = tempfile.mkstemp()
core.db.DB_FILE = temp_db_path
core.db.init_db()

@pytest.mark.asyncio
async def test_sqlite_db_operations():
    from core.db import execute_write, execute_read_all, execute_read_one
    
    # Очищаем таблицу для тестов
    await execute_write("DELETE FROM vpn_sessions")
    
    # 1. Проверяем запись сессии
    success = await execute_write(
        "INSERT INTO vpn_sessions (session_id, username, ip, connect_time, disconnect_time, duration, is_new_ip) VALUES (?, ?, ?, ?, NULL, NULL, ?)",
        ("0", "test_user", "192.168.1.10", "2026-05-25 00:00:00", 0)
    )
    assert success is True
    
    # 2. Проверяем чтение одной строки
    row = await execute_read_one("SELECT * FROM vpn_sessions WHERE username = ?", ("test_user",))
    assert row is not None
    assert row['username'] == 'test_user'
    assert row['ip'] == '192.168.1.10'
    assert row['disconnect_time'] is None
    
    # 3. Проверяем обновление строки (disconnect)
    upd_success = await execute_write(
        "UPDATE vpn_sessions SET disconnect_time = ?, duration = ? WHERE username = ? AND session_id = ?",
        ("2026-05-25 00:10:00", "10 мин", "test_user", "0")
    )
    assert upd_success is True
    
    # 4. Проверяем чтение обновленной строки
    updated_row = await execute_read_one("SELECT * FROM vpn_sessions WHERE username = ?", ("test_user",))
    assert updated_row['disconnect_time'] == "2026-05-25 00:10:00"
    assert updated_row['duration'] == "10 мин"

@pytest.mark.asyncio
async def test_hysteria_history_sqlite():
    from modules.proxmox.monitor.remote.hysteria.history import log_connection, update_disconnection, load_history
    
    # Очищаем таблицу для тестов
    from core.db import execute_write
    await execute_write("DELETE FROM vpn_sessions")
    
    # Записываем первое подключение
    session_id, recent_prev, is_new_ip = await log_connection("test_user", "1.1.1.1")
    assert session_id == "0"
    assert is_new_ip is False
    assert len(recent_prev) == 0
    
    # Закрываем сессию с указанием байтов трафика (100 MB скачано, 50 MB загружено)
    await update_disconnection("test_user", "1.1.1.1", "5 сек", 104857600, 52428800)
    
    # Загружаем историю и проверяем сохраненные байты трафика
    history = await load_history()
    assert history["test_user"][0]["download_bytes"] == 104857600
    assert history["test_user"][0]["upload_bytes"] == 52428800
    
    # Записываем второе подключение с новым IP
    session_id2, recent_prev2, is_new_ip2 = await log_connection("test_user", "2.2.2.2")
    assert session_id2 == "1"
    assert is_new_ip2 is True
    assert len(recent_prev2) == 1
    assert recent_prev2[0]['ip'] == '1.1.1.1'
    assert recent_prev2[0]['duration'] == '5 сек'

@pytest.mark.asyncio
async def test_bot_state_and_temp_bans():
    from core.db import get_state, set_state, execute_write, execute_read_one
    
    # 1. Тестируем get_state / set_state
    test_dict = {"a": 1, "b": [2, 3], "c": {"d": "test"}}
    save_success = await set_state("test_state_key", test_dict)
    assert save_success is True
    
    loaded_dict = await get_state("test_state_key")
    assert loaded_dict == test_dict
    
    # Несуществующий ключ возвращает default
    non_existent = await get_state("non_existent_key", default="fallback")
    assert non_existent == "fallback"
    
    # 2. Тестируем таблицу temp_bans
    await execute_write("DELETE FROM temp_bans")
    await execute_write(
        "INSERT INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
        ("local", "192.168.1.50", "2026-05-25T12:00:00")
    )
    
    row = await execute_read_one("SELECT * FROM temp_bans WHERE dst_ip = ?", ("192.168.1.50",))
    assert row is not None
    assert row['server_ip'] == 'local'
    assert row['expire_time'] == '2026-05-25T12:00:00'


# Чистим временные файлы после тестов
def teardown_module(module):
    try:
        os.close(temp_db_fd)
        os.remove(temp_db_path)
    except Exception:
        pass
