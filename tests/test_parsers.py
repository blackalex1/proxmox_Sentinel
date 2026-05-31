import pytest

def test_parse_remote_iptables_line():
    from modules.proxmox.monitor.remote.traffic import parse_remote_iptables_line
    
    # 1. Проверяем правильный разбор исходящего соединения на sensitive порт
    log_line = (
        "May 25 02:29:00 vps kernel: [123.456] REMOTE_CONN_OUT: "
        "IN= OUT=eth0 SRC=198.51.100.50 DST=203.0.113.100 LEN=60 "
        "TOS=0x00 PREC=0x00 TTL=64 ID=21151 DF PROTO=TCP SPT=43210 DPT=22"
    )
    
    event = parse_remote_iptables_line(log_line)
    assert event is not None
    assert event['direction'] == 'OUT'
    assert event['proto'] == 'TCP'
    assert event['src'] == '198.51.100.50'
    assert event['dst'] == '203.0.113.100'
    assert event['spt'] == 43210
    assert event['dpt'] == 22

    # 2. Игнорируем нерелевантные строки логов
    invalid_line = "May 25 02:29:00 vps sshd[12345]: Accepted password for root from 1.1.1.1"
    assert parse_remote_iptables_line(invalid_line) is None


def test_classify_connection_lxc_whitelist():
    from modules.proxmox.monitor.traffic.parser import classify_connection
    from core.config import settings
    
    # Мокаем ips_lxc_whitelist, добавив туда контейнер 100
    original_whitelist = settings.ips_lxc_whitelist
    settings.ips_lxc_whitelist = [100]
    
    try:
        # 1. Исходящее соединение от обычного контейнера (не в белом списке) на sensitive порт
        event_normal = {
            'vmid': 102,
            'direction': 'OUT',
            'proto': 'TCP',
            'src': '192.168.1.102',
            'dst': '198.51.100.42',
            'spt': 45678,
            'dpt': 22
        }
        risk_level, label, desc = classify_connection(event_normal)
        assert risk_level == 'WARNING'
        assert 'Исходящий SSH/DB запрос' in label
        
        # 2. Исходящее соединение от доверенного контейнера (в белом списке) на sensitive порт
        event_trusted = {
            'vmid': 100,
            'direction': 'OUT',
            'proto': 'TCP',
            'src': '192.168.1.100',
            'dst': '198.51.100.42',
            'spt': 45678,
            'dpt': 22
        }
        risk_level_trusted, label_trusted, desc_trusted = classify_connection(event_trusted)
        assert risk_level_trusted == 'INFO'
        assert 'Доверенный исходящий трафик' in label_trusted
    finally:
        settings.ips_lxc_whitelist = original_whitelist


def test_generate_ansible_hosts_ini(tmp_path):
    from modules.ansible.inventory import get_existing_ip_mappings, generate_ansible_hosts_ini
    from core.config import settings
    
    # Создаем фиктивный hosts.ini во временной папке для проверки парсинга старого
    hosts_ini_content = """
# Existing
master ansible_host=192.168.1.77
my_vps ansible_host=198.51.100.42

[all:vars]
ansible_user=my_test_user
ansible_ssh_private_key_file=/path/to/key
"""
    playbooks_dir = str(tmp_path)
    existing_file = tmp_path / "hosts.ini"
    existing_file.write_text(hosts_ini_content, encoding="utf-8")
    
    # Проверяем парсинг существующего инвентаря
    ip_to_name, global_vars = get_existing_ip_mappings(playbooks_dir)
    assert ip_to_name["192.168.1.77"] == "master"
    assert ip_to_name["198.51.100.42"] == "my_vps"
    assert global_vars["ansible_user"] == "my_test_user"
    assert global_vars["ansible_ssh_private_key_file"] == "/path/to/key"
    
    # Мокаем remote_servers в settings
    original_remote = settings.remote_servers
    settings.remote_servers = [{"ip": "198.51.100.42", "user": "root", "key": "dummy"}]
    
    try:
        # Генерируем новый hosts.ini
        # Для чистоты теста мокаем proxmox клиента, чтобы он не делал сетевых запросов
        from modules.proxmox.api import proxmox
        original_pve = proxmox.proxmox
        proxmox.proxmox = None # Отключаем обращение к API
        
        try:
            success = generate_ansible_hosts_ini(playbooks_dir)
            assert success is True
            
            # Читаем новый файл и проверяем содержимое
            new_content = existing_file.read_text(encoding="utf-8")
            assert "my_vps ansible_host=198.51.100.42" in new_content
            assert "ansible_user=my_test_user" in new_content
            assert "[vpn]" in new_content
            assert "my_vps" in new_content
        finally:
            proxmox.proxmox = original_pve
    finally:
        settings.remote_servers = original_remote


@pytest.mark.asyncio
async def test_xray_log_parsing_correct_ip():
    from modules.proxmox.monitor.xui_connections import handle_xray_log_line, active_clients
    from unittest.mock import AsyncMock, patch
    
    active_clients.clear()
    
    log_line = "2026/05/28 00:13:56.440850 from 192.0.2.1:47640 accepted tcp:51.159.186.137:443 [inbound-31534 -> hysteria] email: test_user"
    
    with patch("modules.proxmox.monitor.xui_connections.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_xray_log_line(log_line)
        
        # Проверяем, что клиент успешно сохранен с правильным IP-адресом
        assert "test_user" in active_clients
        assert active_clients["test_user"]["ip"] == "192.0.2.1"
        
        # Проверяем, что было отправлено корректное сообщение с правильным IP
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "IP-адрес: <code>192.0.2.1</code>" in alert_text


@pytest.mark.asyncio
async def test_watcher_host_ssh_verification():
    from modules.proxmox.monitor.traffic.watcher import handle_traffic_log_line
    from modules.proxmox.monitor.state import recent_bot_ports, lxc_traffic_history
    from unittest.mock import AsyncMock, patch

    # 1. Clean state
    recent_bot_ports.clear()
    lxc_traffic_history[0].clear()

    # Log line where Host (vmid=0) connects to router SSH (192.168.1.1:22) from source port 56088
    log_line = (
        "May 30 02:47:54 proxmox kernel: [12345.67] HOST_CONN_OUT: "
        "IN= OUT=eth0 SRC=192.168.1.120 DST=192.168.1.1 LEN=60 "
        "TOS=0x00 PREC=0x00 TTL=64 ID=21151 DF PROTO=TCP SPT=56088 DPT=22"
    )

    # A) Simulate legitimate connection by the bot: port 56088 is registered in recent_bot_ports
    recent_bot_ports.append(56088)

    with patch("modules.proxmox.monitor.traffic.watcher.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_traffic_log_line(log_line)
        # Should be classified as INFO, no alerts sent
        mock_alert.assert_not_called()
        assert len(lxc_traffic_history[0]) == 1
        assert lxc_traffic_history[0][0]['risk_level'] == 'INFO'
        assert '🟢 Служебный SSH Хоста (Бот)' in lxc_traffic_history[0][0]['label']

    # B) Simulate malicious/unauthorized connection by someone else: port 56088 is NOT in recent_bot_ports
    recent_bot_ports.clear()
    lxc_traffic_history[0].clear()

    # Mock is_local_bot_process to return False
    with patch("modules.proxmox.monitor.traffic.watcher.send_alert_to_admins", AsyncMock()) as mock_alert, \
         patch("modules.mihomo.monitor.helpers.is_local_bot_process", AsyncMock(return_value=False)), \
         patch("modules.proxmox.monitor.traffic.watcher.get_and_kill_local_or_lxc_process", AsyncMock(return_value=("ssh", 9999))):
        await handle_traffic_log_line(log_line)
        # Must be classified as CRITICAL, alert sent immediately!
        mock_alert.assert_called_once()
        assert len(lxc_traffic_history[0]) == 1
        assert lxc_traffic_history[0][0]['risk_level'] == 'CRITICAL'
        assert '🚨 Исходящий запрос Хоста на sensitive порт' in lxc_traffic_history[0][0]['label']


@pytest.mark.asyncio
async def test_watcher_lxc_inbound_ssh_verification():
    from modules.proxmox.monitor.traffic.watcher import handle_traffic_log_line
    from modules.proxmox.monitor.state import recent_bot_ports, lxc_traffic_history
    from unittest.mock import AsyncMock, patch
    from core.config import settings

    # Clean state
    recent_bot_ports.clear()
    lxc_traffic_history[109].clear()

    # Log line where someone SSHs into LXC 109 from host IP
    log_line = (
        "May 30 16:45:10 proxmox kernel: [12345.67] LXC_CONN: "
        "IN=veth109i0 OUT= SRC=192.168.1.120 DST=192.168.1.53 LEN=60 "
        "TOS=0x00 PREC=0x00 TTL=64 ID=21151 DF PROTO=TCP SPT=48614 DPT=22"
    )

    # Mock settings.proxmox_host to make 192.168.1.120 the host IP
    original_host = settings.proxmox_host
    settings.proxmox_host = "192.168.1.120:8006"

    try:
        # A) Simulate legitimate connection by the bot / child process (e.g. Ansible):
        # is_local_bot_process returns True
        with patch("modules.proxmox.monitor.traffic.watcher.send_alert_to_admins", AsyncMock()) as mock_alert, \
             patch("modules.mihomo.monitor.helpers.is_local_bot_process", AsyncMock(return_value=True)):
            
            await handle_traffic_log_line(log_line)
            # Should be classified as INFO, no alerts sent
            mock_alert.assert_not_called()
            assert len(lxc_traffic_history[109]) == 1
            assert lxc_traffic_history[109][0]['risk_level'] == 'INFO'
            assert '🟢 Служебный SSH Хоста (Бот)' in lxc_traffic_history[109][0]['label']

        # B) Simulate malicious/unauthorized connection by someone else on the host (is_local_bot_process returns False)
        recent_bot_ports.clear()
        lxc_traffic_history[109].clear()

        with patch("modules.proxmox.monitor.traffic.watcher.send_alert_to_admins", AsyncMock()) as mock_alert, \
             patch("modules.mihomo.monitor.helpers.is_local_bot_process", AsyncMock(return_value=False)), \
             patch("modules.proxmox.monitor.traffic.watcher.get_and_kill_local_or_lxc_process", AsyncMock(return_value=(None, None))):
            
            await handle_traffic_log_line(log_line)
            # Must be classified as WARNING, alert sent!
            mock_alert.assert_called_once()
            assert len(lxc_traffic_history[109]) == 1
            assert lxc_traffic_history[109][0]['risk_level'] == 'WARNING'
            assert '⚠️ Локальный вход на порт' in lxc_traffic_history[109][0]['label']
    finally:
        settings.proxmox_host = original_host




