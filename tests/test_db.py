import pytest
import os
import tempfile
import sqlite3

# Перехватываем путь к файлу БД и подменяем его временным файлом для тестов
import core.db
ORIGINAL_DB_FILE = core.db.DB_FILE
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
    core.db.DB_FILE = ORIGINAL_DB_FILE
    core.db.init_db()


@pytest.mark.asyncio
async def test_node_segregated_whitelists():
    from core.db import save_node_whitelists, is_whitelisted
    
    # Инициализируем тестовый белый список с разделением по нодам
    whitelists = {
        "global": {
            "processes": ["caddy"],
            "ip_ports": ["1.1.1.1"]
        },
        "vps_1.2.3.4": {
            "processes": ["xray"],
            "ip_ports": ["5.6.7.8:22", "8.8.8.8:*"]
        },
        "lxc_100": {
            "processes": ["nginx"],
            "ip_ports": ["9.9.9.9:80"]
        }
    }
    
    # Сохраняем в БД
    success = await save_node_whitelists(whitelists)
    assert success is True
    
    # 1. Проверяем глобальный белый список
    # Глобальный IP
    assert await is_whitelisted(node="vps_1.2.3.4", ip="1.1.1.1") is True
    assert await is_whitelisted(node="lxc_100", ip="1.1.1.1") is True
    
    # Глобальный процесс
    assert await is_whitelisted(node="vps_1.2.3.4", process="caddy") is True
    assert await is_whitelisted(node="lxc_100", process="caddy") is True
    
    # 2. Проверяем сегрегацию по нодам
    # Процесс xray в белом списке vps_1.2.3.4, но не lxc_100
    assert await is_whitelisted(node="vps_1.2.3.4", process="xray") is True
    assert await is_whitelisted(node="lxc_100", process="xray") is False
    
    # IP 9.9.9.9 на порту 80 в белом списке lxc_100, но не vps_1.2.3.4
    assert await is_whitelisted(node="lxc_100", ip="9.9.9.9", port=80) is True
    assert await is_whitelisted(node="vps_1.2.3.4", ip="9.9.9.9", port=80) is False
    
    # 3. Проверяем разрешение портов (наш ключевой кейс)
    # Доступ к 22 порту на vps_1.2.3.4 разрешен
    assert await is_whitelisted(node="vps_1.2.3.4", ip="5.6.7.8", port=22) is True
    # Доступ к 23 порту на vps_1.2.3.4 должен быть запрещен (забанится)
    assert await is_whitelisted(node="vps_1.2.3.4", ip="5.6.7.8", port=23) is False
    
    # Проверяем wildcard порт (8.8.8.8:*)
    assert await is_whitelisted(node="vps_1.2.3.4", ip="8.8.8.8", port=80) is True
    assert await is_whitelisted(node="vps_1.2.3.4", ip="8.8.8.8", port=443) is True


@pytest.mark.asyncio
async def test_save_vpn_connect_disconnect():
    from core.db import save_vpn_connect, save_vpn_disconnect, execute_read_all, execute_write
    
    # Очищаем таблицу для теста
    await execute_write("DELETE FROM vpn_sessions")
    
    # 1. Первое подключение (новый IP)
    session_id_1 = await save_vpn_connect(
        username="test_user_hist",
        ip="1.2.3.4",
        connect_time_str="2026-06-13 12:00:00",
        tx=1000,
        rx=2000
    )
    assert session_id_1 is not None
    
    # Проверяем, что сессия успешно сохранена
    rows = await execute_read_all("SELECT * FROM vpn_sessions WHERE username = 'test_user_hist'")
    assert len(rows) == 1
    assert rows[0]['session_id'] == session_id_1
    assert rows[0]['is_new_ip'] == 1
    assert rows[0]['download_bytes'] == 1000
    assert rows[0]['upload_bytes'] == 2000
    assert rows[0]['disconnect_time'] is None
    
    # 2. Второе подключение (тот же IP) - не должен быть новым
    session_id_2 = await save_vpn_connect(
        username="test_user_hist",
        ip="1.2.3.4",
        connect_time_str="2026-06-13 12:05:00",
        tx=1500,
        rx=2500
    )
    rows = await execute_read_all("SELECT * FROM vpn_sessions WHERE username = 'test_user_hist' ORDER BY connect_time DESC")
    assert len(rows) == 2
    assert rows[0]['session_id'] == session_id_2
    assert rows[0]['is_new_ip'] == 0 # IP "1.2.3.4" уже встречался для "test_user_hist"
    
    # 3. Отключение последней сессии (12:05:00)
    # Итоговые: tx = 1800 (потребление = 1800 - 1500 = 300), rx = 3000 (потребление = 3000 - 2500 = 500)
    await save_vpn_disconnect(
        username="test_user_hist",
        ip="1.2.3.4",
        disconnect_time_str="2026-06-13 12:10:00",
        tx=1800,
        rx=3000
    )
    
    # Проверяем, что обновилась именно нужная сессия
    session_updated = await execute_read_all("SELECT * FROM vpn_sessions WHERE session_id = ?", (session_id_2,))
    assert len(session_updated) == 1
    assert session_updated[0]['disconnect_time'] == "2026-06-13 12:10:00"
    assert session_updated[0]['duration'] == "5 мин 0 сек" # с 12:05:00 по 12:10:00
    assert session_updated[0]['download_bytes'] == 300
    assert session_updated[0]['upload_bytes'] == 500
    
    # Проверяем, что первая сессия (12:00:00) осталась активной (disconnect_time is None)
    session_first = await execute_read_all("SELECT * FROM vpn_sessions WHERE session_id = ?", (session_id_1,))
    assert session_first[0]['disconnect_time'] is None
    
    # 4. Отключение без активной сессии (резервный сценарий)
    await save_vpn_disconnect(
        username="test_user_hist",
        ip="5.5.5.5", # Другой IP, подключений не было
        disconnect_time_str="2026-06-13 12:15:00",
        tx=999,
        rx=999
    )
    # Должна создаться закрытая сессия с длительностью "неизвестно" и нулевым трафиком
    rows_fallback = await execute_read_all("SELECT * FROM vpn_sessions WHERE username = 'test_user_hist' AND ip = '5.5.5.5'")
    assert len(rows_fallback) == 1
    assert rows_fallback[0]['disconnect_time'] == "2026-06-13 12:15:00"
    assert rows_fallback[0]['duration'] == "неизвестно"
    assert rows_fallback[0]['download_bytes'] == 0
    assert rows_fallback[0]['upload_bytes'] == 0


