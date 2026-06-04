import pytest
from unittest.mock import AsyncMock, patch
import datetime

def test_parse_router_iptables_line():
    from modules.router.monitor.parser import parse_router_iptables_line
    
    line = "May 29 23:25:35 router kernel: [12345.678] ROUTER-IPS: IN=br-lan OUT= SRC=192.168.1.150 DST=203.0.113.100 PROTO=TCP SPT=54321 DPT=22"
    event = parse_router_iptables_line(line)
    
    assert event is not None
    assert event['src_ip'] == "192.168.1.150"
    assert event['dst_host'] == "203.0.113.100"
    assert event['proto'] == "TCP"
    assert event['src_port'] == 54321
    assert event['dst_port'] == 22


@pytest.mark.asyncio
async def test_handle_router_iptables_log_line_sensitive():
    from modules.router.monitor.router_handlers import handle_router_iptables_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    line = "ROUTER-IPS: IN=br-lan OUT= SRC=192.168.1.150 DST=203.0.113.100 PROTO=TCP SPT=54321 DPT=22"
    
    with patch("modules.router.monitor.router_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_router_iptables_log_line(line)
        
        # Проверяем, что алерт безопасности БЫЛ вызван
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: IPTables" in alert_text
        assert "192.168.1.150:54321" in alert_text
        assert "203.0.113.100:22" in alert_text


@pytest.mark.asyncio
async def test_setup_router_logging_rules():
    from modules.router.monitor.rules import setup_router_logging_rules
    from core.config import settings
    
    original_ssh = settings.router_monitor_enable
    original_type = settings.router_type
    
    settings.router_monitor_enable = True
    settings.router_type = 'openwrt'
    
    try:
        with patch("modules.router.monitor.rules.run_router_ssh_cmd", AsyncMock(return_value=(True, "", ""))) as mock_cmd, \
             patch("modules.router.monitor.rules.remove_router_logging_rules", AsyncMock()) as mock_remove:
            
            success = await setup_router_logging_rules()
            assert success is True
            
            mock_remove.assert_called_once()
            mock_cmd.assert_called_once()
            cmd_arg = mock_cmd.call_args[0][0]
            assert "nft add rule inet fw4 forward tcp dport" in cmd_arg
            assert "log prefix \"ROUTER-IPS: \"" in cmd_arg
    finally:
        settings.router_monitor_enable = original_ssh
        settings.router_type = original_type


@pytest.mark.asyncio
async def test_remove_router_logging_rules():
    from modules.router.monitor.rules import remove_router_logging_rules
    from core.config import settings
    
    original_ssh = settings.router_monitor_enable
    original_type = settings.router_type
    
    settings.router_monitor_enable = True
    settings.router_type = 'openwrt'
    
    try:
        with patch("modules.router.monitor.rules.run_router_ssh_cmd", AsyncMock(return_value=(True, "", ""))) as mock_cmd:
            await remove_router_logging_rules()
            
            assert mock_cmd.call_count > 0
            calls = [c[0][0] for c in mock_cmd.call_args_list]
            assert any("/etc/init.d/firewall reload" in cmd for cmd in calls)
    finally:
        settings.router_monitor_enable = original_ssh
        settings.router_type = original_type


@pytest.mark.asyncio
async def test_monitor_router_syslog_execution():
    import asyncio
    from modules.router.monitor.core import monitor_router_syslog
    from core.config import settings
    from unittest.mock import MagicMock
    
    original_ssh = settings.router_monitor_enable
    original_type = settings.router_type
    
    settings.router_monitor_enable = True
    settings.router_type = 'openwrt'
    
    try:
        mock_conn = MagicMock()
        mock_process = AsyncMock()
        
        async def mock_stdout_iter(*args, **kwargs):
            yield "May 29 23:25:35 router kernel: ROUTER-IPS: IN=br-lan OUT= SRC=192.168.1.150 DST=203.0.113.100 PROTO=TCP SPT=54321 DPT=22"
            await asyncio.sleep(3600)
            
        mock_process.stdout.__aiter__ = mock_stdout_iter
        
        # Моки для отслеживания вызовов
        connect_called = []
        create_process_called = []
        
        class MockCreateProcess:
            def __init__(self, cmd):
                create_process_called.append(cmd)
            async def __aenter__(self):
                return mock_process
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        mock_conn.create_process = MockCreateProcess
        
        class MockSSHConnect:
            def __init__(self, **kwargs):
                connect_called.append(kwargs)
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        with patch("asyncssh.connect", MockSSHConnect), \
             patch("modules.router.monitor.ssh_workers.setup_router_logging_rules", AsyncMock()) as mock_setup, \
             patch("modules.router.monitor.ssh_workers.remove_router_logging_rules", AsyncMock()) as mock_remove, \
             patch("modules.router.monitor.ssh_workers.handle_router_iptables_log_line", AsyncMock()) as mock_handler:
             
            # Запускаем как задачу, чтобы можно было прервать бесконечный цикл переподключений
            task = asyncio.create_task(monitor_router_syslog())
            
            # Даем воркеру время прочитать первую строчку
            await asyncio.sleep(0.1)
            
            # Отменяем задачу
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
            mock_setup.assert_called_once()
            assert len(connect_called) == 1
            assert len(create_process_called) == 1
            assert "logread -f" in create_process_called[0]
            mock_handler.assert_called_once()
            mock_remove.assert_called_once()
            
    finally:
        settings.router_monitor_enable = original_ssh
        settings.router_type = original_type


@pytest.mark.asyncio
async def test_parse_router_conntrack_line():
    from modules.router.monitor.parser import parse_router_conntrack_line
    
    # Realistic conntrack -E output line (IPv4)
    line = "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=5.255.255.242 sport=33296 dport=22 [UNREPLIED] src=5.255.255.242 dst=1.2.3.4 sport=443 dport=33296"
    event = parse_router_conntrack_line(line)
    
    assert event is not None
    assert event['src_ip'] == "192.168.1.69"
    assert event['dst_host'] == "5.255.255.242"
    assert event['proto'] == "TCP"
    assert event['src_port'] == 33296
    assert event['dst_port'] == 22

    # Non-matching line
    bad_line = "[UPDATE] tcp      6 120 src=192.168.1.69"
    assert parse_router_conntrack_line(bad_line) is None


@pytest.mark.asyncio
async def test_handle_router_conntrack_log_line():
    from modules.router.monitor.router_handlers import handle_router_conntrack_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    from core.config import settings
    
    lxc_alert_throttle.clear()
    
    # Sensitive port 22
    line = "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=192.168.1.1 sport=33296 dport=22 [UNREPLIED]"
    
    with patch("modules.router.monitor.router_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_router_conntrack_log_line(line)
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: Conntrack" in alert_text
        assert "192.168.1.69" in alert_text
        assert "192.168.1.1:22" in alert_text

    # Safe port 443
    lxc_alert_throttle.clear()
    safe_line = "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=8.8.8.8 sport=33296 dport=443 [UNREPLIED]"
    
    with patch("modules.router.monitor.router_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_router_conntrack_log_line(safe_line)
        mock_alert.assert_not_called()


@pytest.mark.asyncio
async def test_monitor_router_conntrack_execution():
    import asyncio
    from modules.router.monitor.core import monitor_router_conntrack
    from core.config import settings
    from unittest.mock import MagicMock
    
    original_ssh = settings.router_monitor_enable
    settings.router_monitor_enable = True
    
    try:
        mock_conn = MagicMock()
        mock_process = AsyncMock()
        
        async def mock_stdout_iter(*args, **kwargs):
            yield "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=192.168.1.1 sport=33296 dport=22"
            await asyncio.sleep(3600)
            
        mock_process.stdout.__aiter__ = mock_stdout_iter
        
        connect_called = []
        create_process_called = []
        
        class MockCreateProcess:
            def __init__(self, cmd):
                create_process_called.append(cmd)
            async def __aenter__(self):
                return mock_process
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        mock_conn.create_process = MockCreateProcess
        
        class MockSSHConnect:
            def __init__(self, **kwargs):
                connect_called.append(kwargs)
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        with patch("asyncssh.connect", MockSSHConnect), \
             patch("modules.router.monitor.ssh_workers.handle_router_conntrack_log_line", AsyncMock()) as mock_handler:
             
            task = asyncio.create_task(monitor_router_conntrack())
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
            assert len(connect_called) == 1
            assert len(create_process_called) == 1
            assert "conntrack -E -p tcp -e NEW" in create_process_called[0]
            mock_handler.assert_called_once()
            
    finally:
        settings.router_monitor_enable = original_ssh



@pytest.mark.asyncio
async def test_check_is_bot_or_admin():
    from modules.router.monitor.helpers import check_is_bot_or_admin
    from core.config import settings
    
    original_trusted = settings.trusted_admin_ips
    original_router = settings.router_ssh_host
    original_proxmox = settings.proxmox_host
    
    settings.trusted_admin_ips = "192.168.1.92, 192.168.1.93"
    settings.router_ssh_host = "192.168.1.1"
    settings.proxmox_host = "192.168.1.120:8006"
    
    try:
        # Whitelisted admin IPs
        assert await check_is_bot_or_admin("192.168.1.92", 12345) is True
        assert await check_is_bot_or_admin("192.168.1.93", 12345) is True
        
        # Router IP
        assert await check_is_bot_or_admin("192.168.1.1", 12345) is True
        
        # Proxmox host IP with mocked local process check
        with patch("modules.router.monitor.helpers.is_local_bot_process", AsyncMock(return_value=True)) as mock_local:
            assert await check_is_bot_or_admin("192.168.1.120", 47278) is True
            mock_local.assert_called_once_with(47278)
            
        with patch("modules.router.monitor.helpers.is_local_bot_process", AsyncMock(return_value=False)) as mock_local:
            assert await check_is_bot_or_admin("192.168.1.120", 47278) is False
            mock_local.assert_called_once_with(47278)
            
        # Proactive SSH connection bypass check
        settings.router_ssh_port = 22
        original_remote_servers = settings.remote_servers
        settings.remote_servers = [{"ip": "198.51.100.42", "user": "root", "key": "key"}]
        try:
            # Proxmox host connecting to router SSH port (192.168.1.1:22)
            assert await check_is_bot_or_admin("192.168.1.120", 47278, "192.168.1.1", 22) is True
            # Proxmox host connecting to remote VPS SSH port (198.51.100.42:22)
            assert await check_is_bot_or_admin("192.168.1.120", 47278, "198.51.100.42", 22) is True
            # Proxmox host connecting to some random IP on port 22 (should fall back to is_local_bot_process, returning False)
            with patch("modules.router.monitor.helpers.is_local_bot_process", AsyncMock(return_value=False)):
                assert await check_is_bot_or_admin("192.168.1.120", 47278, "8.8.8.8", 22) is False
        finally:
            settings.remote_servers = original_remote_servers

        # Bot's own public IP bypass check
        with patch("modules.proxmox.monitor.remote.helpers.get_bot_public_ip", AsyncMock(return_value="1.2.3.4")):
            assert await check_is_bot_or_admin("1.2.3.4", 12345) is True

        # Normal client IP
        assert await check_is_bot_or_admin("192.168.1.50", 12345) is False
    finally:
        settings.trusted_admin_ips = original_trusted
        settings.router_ssh_host = original_router
        settings.proxmox_host = original_proxmox


@pytest.mark.asyncio
async def test_monitor_expired_bans_router():
    from modules.proxmox.monitor.traffic.garbage import monitor_expired_bans
    from core.db import execute_write, execute_read_one
    import datetime
    import asyncio
    
    # Clear temp_bans first for isolation
    await execute_write("DELETE FROM temp_bans")
    
    # Insert expired router ban
    dst_ip = "192.168.1.199"
    expire_time = (datetime.datetime.now() - datetime.timedelta(seconds=60)).isoformat()
    await execute_write(
        "INSERT OR REPLACE INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
        ("router", dst_ip, expire_time)
    )
    
    # Mock unban_router_ip to return True and mock reconcile_router_bans to do nothing
    with patch("modules.proxmox.monitor.traffic.garbage.unban_router_ip", AsyncMock(return_value=(True, "OK"))) as mock_unban, \
         patch("modules.proxmox.monitor.traffic.garbage.reconcile_router_bans", AsyncMock()) as mock_reconcile:
         
        task = asyncio.create_task(monitor_expired_bans())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
            
        mock_unban.assert_called_once_with(dst_ip)
        
        # Verify the ban is deleted from the DB
        ban_in_db = await execute_read_one("SELECT * FROM temp_bans WHERE dst_ip = ?", (dst_ip,))
        assert ban_in_db is None


@pytest.mark.asyncio
async def test_reconcile_router_bans():
    from modules.proxmox.monitor.traffic.garbage import reconcile_router_bans
    from core.db import execute_write, execute_read_all
    from core.config import settings
    
    # 1. Setup clean state
    await execute_write("DELETE FROM temp_bans WHERE server_ip = 'router'")
    
    # 2. Add one "known" ban to the SQLite DB
    known_ip = "192.168.1.55"
    await execute_write(
        "INSERT INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
        ("router", known_ip, "2026-05-29T12:00:00")
    )
    
    # 3. Define simulated stdout from router containing:
    # - A known ban rule (should NOT be removed)
    # - An unknown iptables ban rule (should be automatically removed)
    # - An unknown nftables ban rule (should be automatically removed)
    # - A blocked trusted admin IP rule (should be rescued and trigger critical alert)
    # - A safe/whitelisted technical IP rule (should NOT be touched)
    # - A generic non-DROP rule (should NOT be touched)
    simulated_stdout = (
        f"-A FORWARD -s {known_ip}/32 -j DROP\n"
        f"-A INPUT -s 192.168.1.99/32 -j DROP\n"
        f"ip saddr 192.168.1.150 drop\n"
        f"-A FORWARD -s 192.168.1.50/32 -j DROP\n"
        f"-A FORWARD -s 127.0.0.1 -j DROP\n"
        f"-A FORWARD -p tcp --dport 80 -j ACCEPT\n"
    )
    
    # Mock settings
    original_ssh_host = settings.router_ssh_host
    original_trusted = settings.trusted_admin_ips
    settings.router_ssh_host = "192.168.1.1"
    settings.trusted_admin_ips = ["192.168.1.50"]
    
    try:
        with patch("modules.proxmox.monitor.traffic.garbage.run_router_ssh_cmd", AsyncMock(return_value=(True, simulated_stdout, ""))) as mock_run:
            # Mock unban_router_ip and send_alert_to_admins
            with patch("modules.proxmox.monitor.traffic.garbage.unban_router_ip", AsyncMock(return_value=(True, "OK"))) as mock_unban, \
                 patch("modules.proxmox.monitor.traffic.garbage.send_alert_to_admins", AsyncMock()) as mock_alert:
                 
                await reconcile_router_bans()
                
                # Check that run_router_ssh_cmd was called once
                mock_run.assert_called_once()
                
                # Check that unban_router_ip was called for unknown and trusted blocked IPs:
                # 192.168.1.99 (iptables DROP), 192.168.1.150 (nftables drop), and 192.168.1.50 (trusted IP)
                # But NOT for known_ip (192.168.1.55) or loopback/technical ones.
                assert mock_unban.call_count == 3
                unbanned_ips = {call.args[0] for call in mock_unban.call_args_list}
                assert unbanned_ips == {"192.168.1.99", "192.168.1.150", "192.168.1.50"}
                
                # Check that Telegram alerts were sent for all 3 unbans
                assert mock_alert.call_count == 3
                alert_texts = [call.args[0] for call in mock_alert.call_args_list]
                assert any("192.168.1.99" in txt for txt in alert_texts)
                assert any("192.168.1.150" in txt for txt in alert_texts)
                # Verify the trusted rescue alert triggered correctly
                assert any("КРИТИЧЕСКАЯ УГРОЗА: Восстановлен доступ для доверенного узла!" in txt for txt in alert_texts)
                assert any("192.168.1.50" in txt for txt in alert_texts)
    finally:
        settings.router_ssh_host = original_ssh_host
        settings.trusted_admin_ips = original_trusted









