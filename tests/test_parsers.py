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
            'dst': '194.87.29.14',
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
            'dst': '194.87.29.14',
            'spt': 45678,
            'dpt': 22
        }
        risk_level_trusted, label_trusted, desc_trusted = classify_connection(event_trusted)
        assert risk_level_trusted == 'INFO'
        assert 'Доверенный исходящий трафик' in label_trusted
    finally:
        settings.ips_lxc_whitelist = original_whitelist


def test_generate_ansible_hosts_ini(tmp_path):
    from modules.ansible.keyboards import get_existing_ip_mappings, generate_ansible_hosts_ini
    from core.config import settings
    
    # Создаем фиктивный hosts.ini во временной папке для проверки парсинга старого
    hosts_ini_content = """
# Existing
master ansible_host=192.168.1.77
frankfurt ansible_host=194.87.29.14

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
    assert ip_to_name["194.87.29.14"] == "frankfurt"
    assert global_vars["ansible_user"] == "my_test_user"
    assert global_vars["ansible_ssh_private_key_file"] == "/path/to/key"
    
    # Мокаем remote_servers в settings
    original_remote = settings.remote_servers
    settings.remote_servers = [{"ip": "194.87.29.14", "user": "root", "key": "dummy"}]
    
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
            assert "frankfurt ansible_host=194.87.29.14" in new_content
            assert "ansible_user=my_test_user" in new_content
            assert "[vpn]" in new_content
            assert "frankfurt" in new_content
        finally:
            proxmox.proxmox = original_pve
    finally:
        settings.remote_servers = original_remote


