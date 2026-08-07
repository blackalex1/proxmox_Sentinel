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


@pytest.mark.asyncio
async def test_singbox_connect_new_ip_alert():
    from modules.proxmox.monitor.hysteria_alerts import process_hysteria_audit_event, active_activity_cards
    import json
    
    mock_panel = AsyncMock()
    mock_panel.name = "Proxmox-Singbox-Node"
    
    details_payload = json.dumps({
        "username": "test_user_alpha",
        "duration": "0 сек"
    })
    
    mock_send = AsyncMock(return_value=AsyncMock(message_id=777))
    mock_history = [{"ip": "198.51.100.10", "timestamp": 1234567, "duration": "10 мин"}]
    
    with patch("core.db.save_vpn_connect", AsyncMock(return_value="sess_sb_123")) as mock_save, \
         patch("modules.proxmox.monitor.hysteria_alerts.check_new_ip_and_get_history", AsyncMock(return_value=(True, mock_history))) as mock_chk, \
         patch("modules.proxmox.monitor.utils.get_geoip_info", AsyncMock(return_value="🇳🇱 Нидерланды, Амстердам")), \
         patch("modules.proxmox.monitor.utils.send_rich_message", mock_send), \
         patch("modules.proxmox.monitor.hysteria_alerts.get_traffic_from_api", AsyncMock(return_value=(500, 1000))), \
         patch("modules.proxmox.monitor.hysteria_alerts.check_and_send_card_delayed", AsyncMock()):
        
        import time
        await process_hysteria_audit_event(
            panel=mock_panel,
            action="singbox_connect",
            client_ip="203.0.113.88",
            log_timestamp=time.time(),
            details_str=details_payload
        )
        
        # Verify save_vpn_connect was called with Sing-box user and client IP
        mock_save.assert_called_once()
        args = mock_save.call_args[0]
        assert args[0] == "test_user_alpha"
        assert args[1] == "203.0.113.88"
        
        # Verify new IP check was invoked
        mock_chk.assert_called_once_with("test_user_alpha", "203.0.113.88", "sess_sb_123")
        
        # Verify admin alert message was sent with buttons
        assert mock_send.called
        call_kwargs = mock_send.call_args.kwargs
        call_args = mock_send.call_args[0]
        alert_text = call_args[1] if len(call_args) > 1 else call_kwargs.get("text", "")
        reply_markup = call_kwargs.get("reply_markup") or (call_args[2] if len(call_args) > 2 else None)
        
        assert "Sing-box" in alert_text or "singbox" in alert_text.lower()
        assert "test_user_alpha" in alert_text
        assert "203.0.113.88" in alert_text
        assert reply_markup is not None
        
        # Verify callback data buttons
        buttons_data = [btn.callback_data for row in reply_markup.inline_keyboard for btn in row]
        assert any("approve_ip:test_user_alpha:203.0.113.88" in b for b in buttons_data)
        assert any("block_ip:Proxmox-Singbox-Node:test_user_alpha:203.0.113.88" in b for b in buttons_data)
        
        # Clean up card state
        key = ("Proxmox-Singbox-Node", "test_user_alpha", "Sing-box")
        active_activity_cards.pop(key, None)

