import pytest
from unittest.mock import AsyncMock, patch
from modules.proxmox.monitor.hysteria_alerts import check_new_ip_and_get_history


@pytest.mark.asyncio
async def test_check_new_ip_and_get_history_database_flow():
    # 1. Test case when IP is new (is_new_ip = 1 in db)
    mock_row_new = {"is_new_ip": 1}
    mock_history_rows = [
        {"ip": "10.0.0.2", "connect_time": "2026-06-14 21:57:00", "duration": "50 сек"},
        {"ip": "192.168.1.15", "connect_time": "2026-06-14 20:00:00", "duration": None}
    ]
    
    with patch("core.db.execute_read_one", AsyncMock(return_value=mock_row_new)) as mock_one, \
         patch("core.db.execute_read_all", AsyncMock(return_value=mock_history_rows)) as mock_all:
         
        is_new, history = await check_new_ip_and_get_history("test_user", "192.168.1.5", "session_123")
        
        assert is_new is True
        assert len(history) == 2
        assert history[0]["ip"] == "10.0.0.2"
        assert history[0]["duration"] == "50 сек"
        assert history[1]["ip"] == "192.168.1.15"
        assert history[1]["duration"] == "неизвестно" # duration is None so defaults to неизвестно
        
        mock_one.assert_called_once_with(
            "SELECT is_new_ip FROM vpn_sessions WHERE username = ? AND session_id = ?",
            ("test_user", "session_123")
        )
        mock_all.assert_called_once_with(
            "SELECT ip, connect_time, duration FROM vpn_sessions WHERE username = ? AND ip != ? AND session_id != ? ORDER BY connect_time DESC LIMIT 5",
            ("test_user", "192.168.1.5", "session_123")
        )
