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


@pytest.mark.asyncio
async def test_check_and_send_card_delayed_noise():
    from modules.proxmox.monitor.hysteria_alerts import check_and_send_card_delayed, active_activity_cards
    
    key = ("testPanel", "noise_user", "Hysteria")
    session_id = "session_noise"
    
    # Setup card in active_activity_cards
    active_activity_cards[key] = {
        'lines': [{'session_id': session_id, 'text': 'Connect event', 'type': 'connect'}],
        'pending_send': True,
        'admin_messages': []
    }
    
    # Mock database to return a noise session (disconnect_time is not None, duration <= 3, traffic = 0)
    mock_session = {
        "connect_time": "2026-06-15 12:00:00",
        "disconnect_time": "2026-06-15 12:00:02",
        "download_bytes": 0,
        "upload_bytes": 0
    }
    
    with patch("core.db.execute_read_one", AsyncMock(return_value=mock_session)), \
         patch("asyncio.sleep", AsyncMock()):
         
        await check_and_send_card_delayed(key, session_id)
        
        # Since it is noise and it was the only line, card should be deleted from active_activity_cards
        assert key not in active_activity_cards


@pytest.mark.asyncio
async def test_check_and_send_card_delayed_active():
    from modules.proxmox.monitor.hysteria_alerts import check_and_send_card_delayed, active_activity_cards
    
    key = ("testPanel", "active_user", "Hysteria")
    session_id = "session_active"
    
    # Setup card in active_activity_cards
    active_activity_cards[key] = {
        'lines': [{'session_id': session_id, 'text': 'Connect event', 'type': 'connect'}],
        'pending_send': True,
        'admin_messages': []
    }
    
    # Mock database to return an active session (disconnect_time is None)
    mock_session = {
        "connect_time": "2026-06-15 12:00:00",
        "disconnect_time": None,
        "download_bytes": 0,
        "upload_bytes": 0
    }
    
    mock_send = AsyncMock(return_value=AsyncMock(message_id=999))
    
    with patch("core.db.execute_read_one", AsyncMock(return_value=mock_session)), \
         patch("asyncio.sleep", AsyncMock()), \
         patch("modules.proxmox.monitor.hysteria_alerts.get_traffic_from_api", AsyncMock(return_value=(100, 200))), \
         patch("modules.proxmox.monitor.utils.send_rich_message", mock_send):
         
        await check_and_send_card_delayed(key, session_id)
        
        # Card should still exist, pending_send should be False, and it should have admin_messages
        assert key in active_activity_cards
        card = active_activity_cards[key]
        assert card['pending_send'] is False
        assert len(card['admin_messages']) > 0
        assert card['admin_messages'][0]['message_id'] == 999
        
        # Clean up
        active_activity_cards.pop(key, None)
