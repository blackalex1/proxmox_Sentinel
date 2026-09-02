import sys
import os
import pytest
from unittest.mock import AsyncMock, patch

# Add bot to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot')))

from core.messages.i18n import set_current_locale, get_current_locale, _
import core.messages as msgs
from core.sender import send_rich_message, edit_rich_message, send_rich_message_draft, send_alert_to_admins

@pytest.fixture(autouse=True)
def restore_locale():
    orig = get_current_locale()
    yield
    set_current_locale(orig)

def test_all_templates_russian_locale():
    set_current_locale("ru")
    
    # Auth
    assert "SSH Access Report" in msgs.get_ssh_login_alert("SSH Login", "🟢", "PVE", "root", "1.2.3.4", "publickey", "fp123", "2026-08-30", "raw log line")
    assert "SSH Auth Alert" in msgs.get_ssh_fail_alert("SSH Fail", "🔴", "PVE", "admin", "1.2.3.4", "password", "2026-08-30", "raw log line")
    assert "Privileged Execution" in msgs.get_sudo_alert("SUDO", "⚡", "PVE", "root", "root", "apt update", "2026-08-30", "raw log line")
    
    # Nodes
    assert "Сервер недоступен" in msgs.get_node_offline_alert("pve-node", "offline")
    assert "Сервер снова в сети" in msgs.get_node_online_alert("pve-node")
    
    # Resources
    assert "Высокая нагрузка CPU" in msgs.get_vps_cpu_alert("VPS-1", 95.0)
    assert "Высокое потребление RAM" in msgs.get_vps_ram_alert("VPS-1", 92.0)
    
    # Traffic
    assert "Traffic Security Alert" in msgs.get_ips_sensitive_access_alert("1.2.3.4", "TCP", "10.0.0.1", "1234", "10.0.0.2", "22", "2026-08-30")
    
    # Router
    assert "Security Recovery" in msgs.get_router_recovery_alert("192.168.1.50", "Rule 1")
    assert "Клиенты вашего роутера" in msgs.get_router_clients_list_text(True)
    assert "Управление клиентом роутера" in msgs.get_router_client_details_card("Laptop", "192.168.1.10", "AA:BB", True, None, [])
    
    # Spectre
    assert "Пользователь" in msgs.get_session_activity_card("VLESS", "Panel1", "test@user", "10 MB", "2 MB", "🟢 Connect")
    disc_alert = msgs.get_client_disconnected_alert("Hysteria 2", "VPS 198.51.100.14", "test_client_alpha", "198.51.100.205", "22:57", {"country": "SampleCountry", "city": "SampleCity", "isp": "SampleISP"})
    assert "<table" in disc_alert
    assert "test_client_alpha" in disc_alert
    assert "SampleISP" in disc_alert

    new_ip = msgs.get_new_ip_alert("Hysteria 2", "VPS 198.51.100.14", "test_client_alpha", "198.51.100.205", "22:57", [], {"country": "SampleCountry", "city": "SampleCity"})
    assert "<table" in new_ip

    table_bans = msgs.get_ban_center_table([], [])
    assert "<table" in table_bans
    
    table_wl = msgs.get_whitelist_view_table("Node-1", ["192.168.1.1:80"], ["nginx"])
    assert "<table" in table_wl
    
    table_threats = msgs.get_threats_table([])
    assert "<table" in table_threats
    
    # Ansible
    assert "Папка" in msgs.get_ansible_missing_dir_text("/etc/ansible")
    assert "Управление Ansible" in msgs.get_ansible_playbooks_menu_text()
    # System Status Table with Panels
    status_tbl = msgs.get_system_status_table(
        pve_nodes=[{"node": "pve", "status": "online", "cpu": 0.05, "mem": 4*1024**3, "maxmem": 16*1024**3}],
        services={"resource_monitor": True, "auth_watcher": True, "ips_engine": True, "remote_monitor": True},
        panels=[{"name": "LXC 104 (testPanel)", "status": "online", "online": 5, "total": 10, "cpu": 3.5}]
    )
    assert "<table" in status_tbl
    assert "testPanel" in status_tbl
    assert "Панели Sentinel Panel" in status_tbl

    # Main Menu, Help & Welcome
    from core.handlers.keyboards import get_main_menu_text, get_help_text
    main_menu = get_main_menu_text()
    assert "<table" in main_menu
    assert "Proxmox Sentinel" in main_menu
    assert "Proxmox Sentinel" in _("keyboards", "welcome_message")
    help_msg = get_help_text()
    assert "<table" in help_msg
    assert "Proxmox Sentinel" in help_msg


def test_all_templates_english_locale():
    set_current_locale("en")



    
    # Auth
    assert "SSH Access Report" in msgs.get_ssh_login_alert("SSH Login", "🟢", "PVE", "root", "1.2.3.4", "publickey", "fp123", "2026-08-30", "raw log line")
    assert "SSH Auth Alert" in msgs.get_ssh_fail_alert("SSH Fail", "🔴", "PVE", "admin", "1.2.3.4", "password", "2026-08-30", "raw log line")
    assert "Privileged Execution" in msgs.get_sudo_alert("SUDO", "⚡", "PVE", "root", "root", "apt update", "2026-08-30", "raw log line")

    # Nodes
    assert "Server is offline" in msgs.get_node_offline_alert("pve-node", "offline")
    assert "Server is back online" in msgs.get_node_online_alert("pve-node")

    # Resources
    assert "High CPU load" in msgs.get_vps_cpu_alert("VPS-1", 95.0)
    assert "High RAM usage" in msgs.get_vps_ram_alert("VPS-1", 92.0)
    
    # Traffic
    assert "Traffic Security Alert" in msgs.get_ips_sensitive_access_alert("1.2.3.4", "TCP", "10.0.0.1", "1234", "10.0.0.2", "22", "2026-08-30")



    
    # Router
    assert "Router connected devices" in msgs.get_router_clients_list_text(True)
    assert "Router Client Management" in msgs.get_router_client_details_card("Laptop", "192.168.1.10", "AA:BB", True, None, [])
    
    # Ansible
    assert "Folder" in msgs.get_ansible_missing_dir_text("/etc/ansible")
    assert "Ansible Control" in msgs.get_ansible_playbooks_menu_text()
    assert "Which hosts" in msgs.get_ansible_ask_host_text("test.yml")
    assert "Ansible Setup" in msgs.get_ansible_setup_loading_text()

    # System Status Table with Panels
    status_tbl = msgs.get_system_status_table(
        pve_nodes=[{"node": "pve", "status": "online", "cpu": 0.05, "mem": 4*1024**3, "maxmem": 16*1024**3}],
        services={"resource_monitor": True, "auth_watcher": True, "ips_engine": True, "remote_monitor": True},
        panels=[{"name": "LXC 104 (testPanel)", "status": "online", "online": 5, "total": 10, "cpu": 3.5}]
    )
    assert "<table" in status_tbl
    assert "testPanel" in status_tbl
    assert "Sentinel Panels" in status_tbl

    # Main Menu, Help & Welcome
    from core.handlers.keyboards import get_main_menu_text, get_help_text
    main_menu = get_main_menu_text()
    assert "<table" in main_menu
    assert "Proxmox Sentinel" in main_menu
    assert "Proxmox Sentinel" in _("keyboards", "welcome_message")
    help_msg = get_help_text()
    assert "<table" in help_msg
    assert "Proxmox Sentinel" in help_msg





@pytest.mark.asyncio
async def test_sender_dispatch():
    with patch("core.sender.bot") as mock_bot:
        mock_bot.send_message = AsyncMock(return_value=AsyncMock())
        mock_bot.send_rich_message = AsyncMock(return_value=AsyncMock())
        mock_bot.edit_message_text = AsyncMock(return_value=AsyncMock())
        mock_bot.edit_rich_message = AsyncMock(return_value=AsyncMock())
        
        # Test send_rich_message with plain text / rich blocks
        await send_rich_message(12345, "Hello <b>World</b>")
        assert mock_bot.send_rich_message.called or mock_bot.send_message.called
        
        # Test edit_rich_message
        await edit_rich_message(12345, 67890, "Updated <b>Text</b>")
        assert mock_bot.edit_rich_message.called or mock_bot.edit_message_text.called


