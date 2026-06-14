import pytest
from modules.proxmox.monitor.hysteria_alerts import check_new_ip_and_get_history

def test_check_new_ip_and_get_history_normal():
    mock_logs = [
        {"timestamp": 100, "username": "system", "action": "xray_connect", "target": "192.168.1.1", "details": '{"username": "test_user", "tx": 100, "rx": 100}'},
        {"timestamp": 90, "username": "system", "action": "xray_disconnect", "target": "192.168.1.2", "details": '{"username": "test_user", "duration": "50 сек"}'},
        {"timestamp": 50, "username": "system", "action": "xray_connect", "target": "192.168.1.2", "details": '{"username": "test_user"}'},
        {"timestamp": 40, "username": "system", "action": "xray_connect", "target": "10.0.0.1", "details": '{"username": "other_user"}'},
    ]

    # Case 1: New IP connection
    is_new, history = check_new_ip_and_get_history("test_user", "192.168.1.5", 110, mock_logs)
    assert is_new is True
    assert len(history) == 2

    # Case 2: Existing IP connection (no new IP warning)
    is_new, history = check_new_ip_and_get_history("test_user", "192.168.1.2", 110, mock_logs)
    assert is_new is False
    assert len(history) == 2


def test_check_new_ip_and_get_history_loopback():
    mock_logs = [
        {"timestamp": 100, "username": "system", "action": "xray_connect", "target": "192.168.1.1", "details": '{"username": "test_user", "tx": 100, "rx": 100}'},
    ]
    # Local loopbacks must not report as new IP
    is_new, history = check_new_ip_and_get_history("test_user", "127.0.0.1", 110, mock_logs)
    assert is_new is False
    assert len(history) == 0
    
    is_new, history = check_new_ip_and_get_history("test_user", "::1", 110, mock_logs)
    assert is_new is False
    assert len(history) == 0
