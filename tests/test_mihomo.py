import pytest
from unittest.mock import AsyncMock, patch
import datetime

@pytest.mark.asyncio
async def test_handle_mihomo_log_line_sensitive_ipv4():
    from modules.mihomo.monitor.mihomo_handlers import handle_mihomo_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    # TCP-соединение на sensitive порт 22
    payload = "[TCP] 192.168.1.150:54321 --> 203.0.113.100:22 match Direct"
    
    with patch("modules.mihomo.monitor.mihomo_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_mihomo_log_line(payload)
        
        # Проверяем, что алерт безопасности БЫЛ вызван
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: Mihomo" in alert_text
        assert "192.168.1.150:54321" in alert_text
        assert "203.0.113.100:22" in alert_text

@pytest.mark.asyncio
async def test_handle_mihomo_log_line_sensitive_ipv6():
    from modules.mihomo.monitor.mihomo_handlers import handle_mihomo_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    # UDP-соединение на sensitive порт 8006 (Proxmox VE)
    payload = "[UDP] [2001:db8::1]:12345 --> [2001:db8::2]:8006 match Rule"
    
    with patch("modules.mihomo.monitor.mihomo_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_mihomo_log_line(payload)
        
        # Проверяем, что IPv6 адрес корректно распарсен и алерт отправлен
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: Mihomo" in alert_text
        assert "2001:db8::1:12345" in alert_text
        assert "2001:db8::2:8006" in alert_text

@pytest.mark.asyncio
async def test_handle_mihomo_log_line_safe_port():
    from modules.mihomo.monitor.mihomo_handlers import handle_mihomo_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    # Соединение на безопасный порт 443
    payload = "[TCP] 192.168.1.150:54321 --> 1.1.1.1:443 match Proxy"
    
    with patch("modules.mihomo.monitor.mihomo_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_mihomo_log_line(payload)
        
        # Проверяем, что алерт не отправлялся для безопасных портов
        mock_alert.assert_not_called()
    
@pytest.mark.asyncio
async def test_handle_mihomo_kill_connection_success():
    from modules.mihomo.handlers import handle_mihomo_kill_connection
    from unittest.mock import MagicMock
    
    # Мокаем CallbackQuery
    mock_callback = AsyncMock()
    mock_callback.data = "mihomo_kill:dummy-uuid-12345"
    
    mock_msg = MagicMock()
    mock_msg.text = "🚨 [Router Security: Mihomo] Обнаружен доступ к чувствительному порту!"
    mock_msg.edit_text = AsyncMock()
    mock_callback.message = mock_msg
    
    # Мокаем close_mihomo_connection, возвращающий True
    with patch("modules.mihomo.handlers.close_mihomo_connection", AsyncMock(return_value=True)) as mock_close:
        await handle_mihomo_kill_connection(mock_callback)
        
        # Проверяем успешный вызов разрыва
        mock_close.assert_called_once_with("dummy-uuid-12345")
        # Проверяем, что callback-запрос был успешно отвечен
        mock_callback.answer.assert_called_once_with("✅ Соединение успешно разорвано!", show_alert=True)
        # Проверяем, что текст сообщения был обновлен
        mock_msg.edit_text.assert_called_once()
        new_text = mock_msg.edit_text.call_args[0][0]
        assert "СОЕДИНЕНИЕ РАЗОРВАНО АДМИНИСТРАТОРОМ" in new_text


@pytest.mark.asyncio
async def test_handle_mihomo_block_ip_success():
    from modules.mihomo.handlers import handle_mihomo_block_ip
    from unittest.mock import MagicMock
    
    mock_callback = AsyncMock()
    mock_callback.data = "mihomo_block:192.0.2.99"
    
    mock_msg = MagicMock()
    mock_msg.text = "🚨 [Router Security: Mihomo] Обнаружен доступ к чувствительному порту!"
    mock_msg.edit_text = AsyncMock()
    mock_callback.message = mock_msg
    
    with patch("modules.mihomo.handlers.ban_router_ip", AsyncMock(return_value=(True, "Success"))) as mock_ban:
        await handle_mihomo_block_ip(mock_callback)
        
        mock_ban.assert_called_once_with("192.0.2.99")
        mock_callback.answer.assert_called_once_with("🛑 IP 192.0.2.99 успешно заблокирован на роутере!", show_alert=True)
        mock_msg.edit_text.assert_called_once()
        new_text = mock_msg.edit_text.call_args[0][0]
        assert "УСТРОЙСТВО 192.0.2.99 ЗАБЛОКИРОВАНО НА РОУТЕРЕ" in new_text
 
 
@pytest.mark.asyncio
async def test_handle_mihomo_unblock_ip_success():
    from modules.mihomo.handlers import handle_mihomo_unblock_ip
    from unittest.mock import MagicMock
    
    mock_callback = AsyncMock()
    mock_callback.data = "mihomo_unblock:192.0.2.99"
    
    mock_msg = MagicMock()
    mock_msg.text = "🚨 [Router Security: Mihomo] Обнаружен доступ к чувствительному порту!\n\n🛑 <b>УСТРОЙСТВО 192.0.2.99 ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>"
    mock_msg.edit_text = AsyncMock()
    mock_callback.message = mock_msg
    
    with patch("modules.mihomo.handlers.unban_router_ip", AsyncMock(return_value=(True, "Success"))) as mock_unban:
        await handle_mihomo_unblock_ip(mock_callback)
        
        mock_unban.assert_called_once_with("192.0.2.99")
        mock_callback.answer.assert_called_once_with("🟢 Блокировка с IP 192.0.2.99 снята!", show_alert=True)
        mock_msg.edit_text.assert_called_once()
        new_text = mock_msg.edit_text.call_args[0][0]
        assert "ЗАБЛОКИРОВАНО" not in new_text


@pytest.mark.asyncio
async def test_handle_mihomo_log_line_auto_ban():
    from modules.mihomo.monitor.mihomo_handlers import handle_mihomo_log_line, recent_mihomo_violations
    from core.config import settings
    
    # Включаем auto-ban и SSH в моке настроек
    original_ssh = settings.router_ssh_enable
    original_auto = settings.mihomo_auto_ban
    original_max = settings.mihomo_max_violations
    
    settings.router_ssh_enable = True
    settings.mihomo_auto_ban = True
    settings.mihomo_max_violations = 3
    
    recent_mihomo_violations.clear()
    
    payload = "[TCP] 192.168.1.150:54321 --> 203.0.113.100:22 match Direct"
    
    try:
        with patch("modules.mihomo.monitor.mihomo_handlers.ban_router_ip", AsyncMock(return_value=(True, "Blocked"))) as mock_ban, \
             patch("modules.mihomo.monitor.mihomo_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
             
            # Попытка 1: Просто предупреждение
            await handle_mihomo_log_line(payload)
            assert len(recent_mihomo_violations["192.168.1.150"]) == 1
            mock_ban.assert_not_called()
            
            # Попытка 2: Предупреждение (но троттлинг алертов сработает на повторные вызовы одного хоста, счетчик нарушений увеличится)
            # Вручную добавим в violations для симуляции
            import time
            recent_mihomo_violations["192.168.1.150"].append(time.time())
            
            # Попытка 3: Автобан срабатывает!
            await handle_mihomo_log_line(payload)
            
            # Проверяем, что бан был вызван автоматически для этого IP
            mock_ban.assert_called_once_with("192.168.1.150")
            assert mock_alert.call_count == 2
            alert_text = mock_alert.call_args[0][0]
            assert "Auto-Block" in alert_text
            assert "Устройство заблокировано автоматически" in alert_text
            
            # Нарушения сброшены после бана
            assert len(recent_mihomo_violations.get("192.168.1.150", [])) == 0
    finally:
        settings.router_ssh_enable = original_ssh
        settings.mihomo_auto_ban = original_auto
        settings.mihomo_max_violations = original_max


@pytest.mark.asyncio
async def test_handle_new_mihomo_connection_sensitive():
    from modules.mihomo.monitor.mihomo_handlers import handle_new_mihomo_connection
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    conn = {
        "id": "test-uuid-99999",
        "metadata": {
            "network": "tcp",
            "sourceIP": "192.168.1.150",
            "sourcePort": "54321",
            "host": "203.0.113.100",
            "destinationPort": "22"
        }
    }
    
    with patch("modules.mihomo.monitor.mihomo_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_new_mihomo_connection(conn)
        
        # Проверяем, что алерт безопасности БЫЛ вызван
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: Mihomo" in alert_text
        assert "192.168.1.150:54321" in alert_text
        assert "203.0.113.100:22" in alert_text


def test_parse_router_iptables_line():
    from modules.mihomo.monitor.parser import parse_router_iptables_line
    
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
    from modules.mihomo.monitor.router_handlers import handle_router_iptables_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    
    lxc_alert_throttle.clear()
    
    line = "ROUTER-IPS: IN=br-lan OUT= SRC=192.168.1.150 DST=203.0.113.100 PROTO=TCP SPT=54321 DPT=22"
    
    with patch("modules.mihomo.monitor.router_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_router_iptables_log_line(line)
        
        # Проверяем, что алерт безопасности БЫЛ вызван
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: IPTables" in alert_text
        assert "192.168.1.150:54321" in alert_text
        assert "203.0.113.100:22" in alert_text


@pytest.mark.asyncio
async def test_setup_router_logging_rules():
    from modules.mihomo.monitor.rules import setup_router_logging_rules
    from core.config import settings
    
    original_ssh = settings.router_ssh_enable
    original_type = settings.router_type
    
    settings.router_ssh_enable = True
    settings.router_type = 'openwrt'
    
    try:
        with patch("modules.mihomo.monitor.rules.run_router_ssh_cmd", AsyncMock(return_value=(True, "", ""))) as mock_cmd, \
             patch("modules.mihomo.monitor.rules.remove_router_logging_rules", AsyncMock()) as mock_remove:
            
            success = await setup_router_logging_rules()
            assert success is True
            
            mock_remove.assert_called_once()
            mock_cmd.assert_called_once()
            cmd_arg = mock_cmd.call_args[0][0]
            assert "nft add rule inet fw4 forward tcp dport" in cmd_arg
            assert "log prefix \"ROUTER-IPS: \"" in cmd_arg
    finally:
        settings.router_ssh_enable = original_ssh
        settings.router_type = original_type


@pytest.mark.asyncio
async def test_remove_router_logging_rules():
    from modules.mihomo.monitor.rules import remove_router_logging_rules
    from core.config import settings
    
    original_ssh = settings.router_ssh_enable
    original_type = settings.router_type
    
    settings.router_ssh_enable = True
    settings.router_type = 'openwrt'
    
    try:
        with patch("modules.mihomo.monitor.rules.run_router_ssh_cmd", AsyncMock(return_value=(True, "", ""))) as mock_cmd:
            await remove_router_logging_rules()
            
            assert mock_cmd.call_count > 0
            calls = [c[0][0] for c in mock_cmd.call_args_list]
            assert any("/etc/init.d/firewall reload" in cmd for cmd in calls)
    finally:
        settings.router_ssh_enable = original_ssh
        settings.router_type = original_type


@pytest.mark.asyncio
async def test_monitor_router_syslog_execution():
    import asyncio
    from modules.mihomo.monitor.core import monitor_router_syslog
    from core.config import settings
    from unittest.mock import MagicMock
    
    original_ssh = settings.router_ssh_enable
    original_type = settings.router_type
    
    settings.router_ssh_enable = True
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
             patch("modules.mihomo.monitor.ssh_workers.setup_router_logging_rules", AsyncMock()) as mock_setup, \
             patch("modules.mihomo.monitor.ssh_workers.remove_router_logging_rules", AsyncMock()) as mock_remove, \
             patch("modules.mihomo.monitor.ssh_workers.handle_router_iptables_log_line", AsyncMock()) as mock_handler:
             
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
        settings.router_ssh_enable = original_ssh
        settings.router_type = original_type


@pytest.mark.asyncio
async def test_parse_router_conntrack_line():
    from modules.mihomo.monitor.parser import parse_router_conntrack_line
    
    # Realistic conntrack -E output line (IPv4)
    line = "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=5.255.255.242 sport=33296 dport=22 [UNREPLIED] src=5.255.255.242 dst=89.110.53.137 sport=443 dport=33296"
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
    from modules.mihomo.monitor.router_handlers import handle_router_conntrack_log_line
    from modules.proxmox.monitor.state import lxc_alert_throttle
    from core.config import settings
    
    lxc_alert_throttle.clear()
    
    # Sensitive port 22
    line = "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=192.168.1.1 sport=33296 dport=22 [UNREPLIED]"
    
    with patch("modules.mihomo.monitor.router_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_router_conntrack_log_line(line)
        mock_alert.assert_called_once()
        alert_text = mock_alert.call_args[0][0]
        assert "Router Security: Conntrack" in alert_text
        assert "192.168.1.69" in alert_text
        assert "192.168.1.1:22" in alert_text

    # Safe port 443
    lxc_alert_throttle.clear()
    safe_line = "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=8.8.8.8 sport=33296 dport=443 [UNREPLIED]"
    
    with patch("modules.mihomo.monitor.router_handlers.send_alert_to_admins", AsyncMock()) as mock_alert:
        await handle_router_conntrack_log_line(safe_line)
        mock_alert.assert_not_called()


@pytest.mark.asyncio
async def test_monitor_router_conntrack_execution():
    import asyncio
    from modules.mihomo.monitor.core import monitor_router_conntrack
    from core.config import settings
    from unittest.mock import MagicMock
    
    original_ssh = settings.router_ssh_enable
    settings.router_ssh_enable = True
    
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
             patch("modules.mihomo.monitor.ssh_workers.handle_router_conntrack_log_line", AsyncMock()) as mock_handler:
             
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
        settings.router_ssh_enable = original_ssh


@pytest.mark.asyncio
async def test_monitor_router_mihomo_mode_alias():
    from modules.mihomo.monitor.core import monitor_mihomo_connections
    from core.config import settings
    from unittest.mock import MagicMock, AsyncMock
    import asyncio
    
    original_mode = settings.mihomo_monitor_mode
    original_enable = settings.mihomo_monitor_enable
    
    settings.mihomo_monitor_mode = 'mihomo'
    settings.mihomo_monitor_enable = True
    
    try:
        # Mock ClientSession.get as an async context manager to exit early
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=asyncio.CancelledError())
        mock_get = MagicMock(return_value=mock_ctx)
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        class MockClientSession:
            async def __aenter__(self):
                return mock_session
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
                
        with patch("aiohttp.ClientSession", MagicMock(return_value=MockClientSession())):
            task = asyncio.create_task(monitor_mihomo_connections())
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # If 'mihomo' mode was correctly mapped to polling, it should have initiated the HTTP request
            mock_get.assert_called()
    finally:
        settings.mihomo_monitor_mode = original_mode
        settings.mihomo_monitor_enable = original_enable


@pytest.mark.asyncio
async def test_check_is_bot_or_admin():
    from modules.mihomo.monitor.helpers import check_is_bot_or_admin
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
        with patch("modules.mihomo.monitor.helpers.is_local_bot_process", AsyncMock(return_value=True)) as mock_local:
            assert await check_is_bot_or_admin("192.168.1.120", 47278) is True
            mock_local.assert_called_once_with(47278)
            
        with patch("modules.mihomo.monitor.helpers.is_local_bot_process", AsyncMock(return_value=False)) as mock_local:
            assert await check_is_bot_or_admin("192.168.1.120", 47278) is False
            mock_local.assert_called_once_with(47278)
            
        # Proactive SSH connection bypass check
        settings.router_ssh_port = 22
        original_remote_servers = settings.remote_servers
        settings.remote_servers = [{"ip": "194.87.29.14", "user": "root", "key": "key"}]
        try:
            # Proxmox host connecting to router SSH port (192.168.1.1:22)
            assert await check_is_bot_or_admin("192.168.1.120", 47278, "192.168.1.1", 22) is True
            # Proxmox host connecting to remote VPS SSH port (194.87.29.14:22)
            assert await check_is_bot_or_admin("192.168.1.120", 47278, "194.87.29.14", 22) is True
            # Proxmox host connecting to some random IP on port 22 (should fall back to is_local_bot_process, returning False)
            with patch("modules.mihomo.monitor.helpers.is_local_bot_process", AsyncMock(return_value=False)):
                assert await check_is_bot_or_admin("192.168.1.120", 47278, "8.8.8.8", 22) is False
        finally:
            settings.remote_servers = original_remote_servers

        # Bot's own public IP bypass check
        with patch("modules.proxmox.monitor.remote.helpers.get_bot_public_ip", AsyncMock(return_value="89.110.53.137")):
            assert await check_is_bot_or_admin("89.110.53.137", 12345) is True

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









