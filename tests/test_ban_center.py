import pytest
import os
import tempfile
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Перехватываем путь к файлу БД и подменяем его временным файлом для тестов
import core.db
ORIGINAL_DB_FILE = core.db.DB_FILE
temp_db_fd, temp_db_path = tempfile.mkstemp()
core.db.DB_FILE = temp_db_path
core.db.init_db()

@pytest.mark.asyncio
async def test_verify_env_configuration():
    from core.env_verifier import verify_env_configuration
    
    # Подменяем настройки
    with patch('core.config.settings.admin_ids', []), \
         patch('core.config.settings.proxmox_host', ''), \
         patch('core.config.settings.xui_host', ''), \
         patch('core.config.settings.ansible_playbooks_dir', ''), \
         patch('core.config.settings.router_ssh_enable', False), \
         patch('core.config.settings.remote_monitor_enable', False), \
         patch('logging.warning') as mock_warn, \
         patch('logging.info') as mock_info:
        
        verify_env_configuration()
        # Должно быть выведено предупреждение
        assert mock_warn.called
        # Проверяем, что логгер предупредил о нехватке параметров
        warnings = [call[0][0] for call in mock_warn.call_args_list]
        assert any("В конфигурации .env не хватает следующих параметров" in w for w in warnings)

@pytest.mark.asyncio
async def test_unban_local_ip():
    from modules.proxmox.monitor.traffic.firewall import unban_local_ip, active_local_blocks
    from core.db import execute_write, execute_read_one
    
    # 1. Добавляем запись в БД и активную задачу
    await execute_write("DELETE FROM temp_bans")
    await execute_write(
        "INSERT INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
        ("local", "192.168.1.99", "2026-05-25T12:00:00")
    )
    
    mock_task = MagicMock()
    active_local_blocks["192.168.1.99"] = mock_task
    
    # 2. Вызываем unban_local_ip с моканьем subprocess
    mock_proc = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    
    with patch('asyncio.create_subprocess_shell', return_value=mock_proc) as mock_shell:
        success, desc = await unban_local_ip("192.168.1.99")
        
        assert success is True
        assert "Блокировка на хосте Proxmox снята" in desc
        # Задача должна быть отменена и удалена из памяти
        mock_task.cancel.assert_called_once()
        assert "192.168.1.99" not in active_local_blocks
        
        # subprocess_shell должен быть вызван для удаления из OUTPUT и FORWARD
        assert mock_shell.call_count == 2
        calls = [call[0][0] for call in mock_shell.call_args_list]
        assert any("iptables -D OUTPUT -d 192.168.1.99" in c for c in calls)
        assert any("iptables -D FORWARD -d 192.168.1.99" in c for c in calls)
        
        # Запись в БД должна быть удалена
        row = await execute_read_one("SELECT * FROM temp_bans WHERE dst_ip = ?", ("192.168.1.99",))
        assert row is None

@pytest.mark.asyncio
async def test_unban_remote_ip():
    from modules.proxmox.monitor.remote.traffic.firewall import unban_remote_ip, active_remote_blocks
    from core.db import execute_write, execute_read_one
    
    await execute_write("DELETE FROM temp_bans")
    await execute_write(
        "INSERT INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
        ("198.51.100.42", "192.168.1.99", "2026-05-25T12:00:00")
    )
    
    mock_task = MagicMock()
    active_remote_blocks[("198.51.100.42", "192.168.1.99")] = mock_task
    
    server = {"ip": "198.51.100.42", "user": "root", "key": "key_path"}
    
    with patch('modules.proxmox.monitor.remote.traffic.firewall.run_remote_ssh_cmd', AsyncMock(return_value=(True, "", ""))) as mock_ssh:
        success, desc = await unban_remote_ip(server, "192.168.1.99")
        
        assert success is True
        assert "Блокировка на VPS 198.51.100.42 снята" in desc
        mock_task.cancel.assert_called_once()
        assert ("198.51.100.42", "192.168.1.99") not in active_remote_blocks
        
        # Проверяем вызов SSH
        mock_ssh.assert_called_once()
        args = mock_ssh.call_args[0]
        assert args[0] == server
        assert "iptables -D OUTPUT -d 192.168.1.99" in args[1][0]
        
        # Запись в БД должна быть удалена
        row = await execute_read_one("SELECT * FROM temp_bans WHERE dst_ip = ?", ("192.168.1.99",))
        assert row is None

@pytest.mark.asyncio
async def test_render_ban_center_empty():
    from core.handlers.ban_center import render_ban_center
    from core.db import execute_write
    
    await execute_write("DELETE FROM temp_bans")
    
    text, reply_markup = await render_ban_center(None)
    assert "Активных блокировок в системе нет" in text
    # Должна быть кнопка возврата в меню
    assert len(reply_markup.inline_keyboard) == 1
    assert reply_markup.inline_keyboard[0][0].callback_data == "main_menu"

@pytest.mark.asyncio
async def test_render_ban_center_active():
    from core.handlers.ban_center import render_ban_center
    from core.db import execute_write
    import datetime
    
    await execute_write("DELETE FROM temp_bans")
    
    # Добавляем будущий бан и прошедший бан
    future_time = (datetime.datetime.now() + datetime.timedelta(minutes=30)).isoformat()
    past_time = (datetime.datetime.now() - datetime.timedelta(minutes=10)).isoformat()
    
    await execute_write(
        "INSERT INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
        ("local", "1.1.1.1", future_time)
    )
    await execute_write(
        "INSERT INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
        ("router", "2.2.2.2", past_time)
    )
    
    text, reply_markup = await render_ban_center(None)
    
    # 1.1.1.1 должен быть активен
    assert "1.1.1.1" in text
    assert "Proxmox Host" in text
    
    # 2.2.2.2 должен быть удален, так как он истек
    assert "2.2.2.2" not in text
    
    # Должна быть кнопка разблокировки 1.1.1.1 и кнопка Назад
    assert len(reply_markup.inline_keyboard) == 2
    assert reply_markup.inline_keyboard[0][0].callback_data == "ban_center_unban:local:1.1.1.1"
    assert reply_markup.inline_keyboard[1][0].callback_data == "main_menu"

def teardown_module(module):
    try:
        os.close(temp_db_fd)
        os.remove(temp_db_path)
    except Exception:
        pass
    core.db.DB_FILE = ORIGINAL_DB_FILE
    core.db.init_db()
