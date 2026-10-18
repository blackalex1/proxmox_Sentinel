import pytest
import os
import json
import time
from unittest.mock import AsyncMock, patch
from core.db import (
    init_db, approve_ip, is_ip_approved, save_vpn_connect,
    execute_write, execute_read_all, get_db_connection
)
from modules.proxmox.monitor.hysteria_alerts import (
    check_new_ip_and_get_history, process_hysteria_audit_event, _last_new_ip_alerts
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    _last_new_ip_alerts.clear()
    test_db = str(tmp_path / 'test_vpn_history.db')
    monkeypatch.setattr('core.db.DB_FILE', test_db)
    init_db()
    yield test_db
    _last_new_ip_alerts.clear()


@pytest.mark.asyncio
async def test_vpn_unapproved_ip_triggers_alert_and_approve_flow():
    # 1. Seed approved IP: only 192.168.1.50 is approved for 'client_test'
    await execute_write('DELETE FROM approved_ips')
    await execute_write('DELETE FROM vpn_sessions')
    await approve_ip('client_test', '192.168.1.50')

    assert await is_ip_approved('client_test', '192.168.1.50') is True
    assert await is_ip_approved('client_test', '198.51.100.230') is False

    # 2. Test connect from unapproved IP: 198.51.100.230
    mock_panel = AsyncMock()
    mock_panel.name = 'testPanel'
    mock_panel.get_user_traffic = AsyncMock(return_value=(1024, 2048))

    mock_send_alert = AsyncMock()

    with patch('modules.proxmox.monitor.utils.send_alert_to_admins', mock_send_alert), \
         patch('modules.proxmox.monitor.utils.get_geoip_info', AsyncMock(return_value={'country': 'US', 'city': 'Dallas'})):

        details_json = json.dumps({'username': 'client_test', 'tx': 1024, 'rx': 2048})
        log_ts = int(time.time())

        await process_hysteria_audit_event(
            panel=mock_panel,
            action='singbox_connect',
            client_ip='198.51.100.230',
            log_timestamp=log_ts,
            details_str=details_json
        )

        # Alert MUST be triggered for unapproved IP
        assert mock_send_alert.called is True
        call_args = mock_send_alert.call_args
        alert_text = call_args[0][0]
        reply_markup = call_args[1].get('reply_markup')

        assert '198.51.100.230' in alert_text
        assert 'client_test' in alert_text
        assert reply_markup is not None
        btn_callback = reply_markup.inline_keyboard[0][0].callback_data
        assert btn_callback == 'approve_ip:client_test:198.51.100.230'

    # 3. Test connect from approved IP: 192.168.1.50 (should NOT send alert)
    mock_send_alert.reset_mock()
    with patch('modules.proxmox.monitor.utils.send_alert_to_admins', mock_send_alert):

        details_json = json.dumps({'username': 'client_test', 'tx': 500, 'rx': 500})
        log_ts = int(time.time())

        await process_hysteria_audit_event(
            panel=mock_panel,
            action='singbox_connect',
            client_ip='192.168.1.50',
            log_timestamp=log_ts,
            details_str=details_json
        )

        # Alert MUST NOT be triggered for approved IP
        assert mock_send_alert.called is False

    # 4. Now admin approves 198.51.100.230
    await approve_ip('client_test', '198.51.100.230')
    assert await is_ip_approved('client_test', '198.51.100.230') is True

    # 5. Subsequent connect from 198.51.100.230 should now be silent
    mock_send_alert.reset_mock()
    with patch('modules.proxmox.monitor.utils.send_alert_to_admins', mock_send_alert):

        details_json = json.dumps({'username': 'client_test', 'tx': 100, 'rx': 100})
        log_ts = int(time.time())

        await process_hysteria_audit_event(
            panel=mock_panel,
            action='singbox_connect',
            client_ip='198.51.100.230',
            log_timestamp=log_ts,
            details_str=details_json
        )

        assert mock_send_alert.called is False


@pytest.mark.asyncio
async def test_vpn_new_ip_cooldown_suppresses_rapid_reconnects():
    """Verifies that an unapproved IP only triggers 1 alert, and repeated reconnects within cooldown are suppressed."""
    await execute_write('DELETE FROM approved_ips')
    await execute_write('DELETE FROM vpn_sessions')

    mock_panel = AsyncMock()
    mock_panel.name = 'testPanel'
    mock_send_alert = AsyncMock()

    unapproved_ip = '198.51.100.50'
    username = 'test_user_mobile'
    details_json = json.dumps({'username': username, 'tx': 1024, 'rx': 2048})
    now = time.time()

    with patch('modules.proxmox.monitor.utils.send_alert_to_admins', mock_send_alert), \
         patch('modules.proxmox.monitor.utils.get_geoip_info', AsyncMock(return_value={'country': 'RU', 'city': 'St Petersburg'})):

        # 1. First connection from 198.51.100.50 -> Alert MUST be dispatched
        await process_hysteria_audit_event(
            panel=mock_panel,
            action='singbox_connect',
            client_ip=unapproved_ip,
            log_timestamp=int(now),
            details_str=details_json
        )
        assert mock_send_alert.call_count == 1

        # 2. Second connection 2 seconds later (simulating mobile network reconnect) -> MUST be suppressed by cooldown
        await process_hysteria_audit_event(
            panel=mock_panel,
            action='singbox_connect',
            client_ip=unapproved_ip,
            log_timestamp=int(now + 2),
            details_str=details_json
        )
        assert mock_send_alert.call_count == 1  # Still 1, no duplicate alert!

        # 3. Third connection 10 seconds later -> Still suppressed
        await process_hysteria_audit_event(
            panel=mock_panel,
            action='singbox_connect',
            client_ip=unapproved_ip,
            log_timestamp=int(now + 10),
            details_str=details_json
        )
        assert mock_send_alert.call_count == 1

        # 4. Connection from a DIFFERENT unapproved IP -> Alert MUST be dispatched
        diff_ip = '198.51.100.99'
        await process_hysteria_audit_event(
            panel=mock_panel,
            action='singbox_connect',
            client_ip=diff_ip,
            log_timestamp=int(now + 15),
            details_str=json.dumps({'username': username, 'tx': 0, 'rx': 0})
        )
        assert mock_send_alert.call_count == 2
