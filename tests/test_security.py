import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from modules.proxmox.monitor.traffic.killer import get_and_kill_local_or_lxc_process
from modules.proxmox.monitor.traffic.firewall import block_local_ip
from modules.proxmox.monitor.remote.hysteria import handle_remote_hysteria_line
from modules.proxmox.monitor.remote.hysteria.alerts.state import recent_hysteria_violations

@pytest.mark.asyncio
async def test_get_and_kill_local_process():
    # Временно очищаем белый список процессов для теста
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    try:
        # Сценарий 1: Локальный процесс на хосте (vmid == 0)
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b'tcp ESTAB 0 0 127.0.0.1:22 192.0.2.42:22 users:(("sshd",pid=12345,fd=3))', b"")
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            assert proc_name == "sshd"
            assert pid == "12345"
            
            # Проверяем, что был выполнен ss и соответствующий kill -9
            mock_exec.assert_any_call("ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            mock_exec.assert_any_call("kill", "-9", "12345", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    finally:
        settings.ips_process_whitelist = original_whitelist
        
@pytest.mark.asyncio
async def test_get_and_kill_lxc_process():
    # Временно очищаем белый список процессов для теста
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    try:
        # Сценарий 2: Процесс внутри LXC контейнера (vmid == 101)
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b'tcp ESTAB 0 0 127.0.0.1:80 192.0.2.42:80 users:(("nginx",pid=9876,fd=4))', b"")
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=101, spt=80)
            assert proc_name == "nginx"
            assert pid == "9876"
            
            # Проверяем pct exec для получения сокетов и pct exec для kill -9
            mock_exec.assert_any_call("pct", "exec", "101", "--", "ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            mock_exec.assert_any_call("pct", "exec", "101", "--", "kill", "-9", "9876", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    finally:
        settings.ips_process_whitelist = original_whitelist

@pytest.mark.asyncio
async def test_get_and_kill_whitelisted_process():
    # Сценарий 3: Попытка убить защищенный процесс из белого списка
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b'tcp ESTAB 0 0 127.0.0.1:22 192.0.2.42:22 users:(("systemd",pid=1,fd=5))', b"")
    
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    # Временно добавляем systemd в белый список
    settings.ips_process_whitelist = ["systemd"]
    
    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            assert proc_name == "systemd"
            assert pid == "WHITELISTED"
            
            # Проверяем, что ss выполнился, а kill -9 НЕ вызывался
            mock_exec.assert_any_call("ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            # Убеждаемся, что kill не вызывался
            for call in mock_exec.call_args_list:
                assert call[0][0] != "kill"
    finally:
        settings.ips_process_whitelist = original_whitelist

@pytest.mark.asyncio
async def test_block_local_ip():
    mock_proc = AsyncMock()
    mock_proc.wait.return_value = 0
    
    with patch("asyncio.create_subprocess_shell", return_value=mock_proc) as mock_shell:
        success = await block_local_ip("198.51.100.42", delay=1)
        assert success is True
        
        # Проверяем, что были выполнены команды iptables на блокировку
        mock_shell.assert_any_call(
            "iptables -I OUTPUT -d 198.51.100.42 -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        mock_shell.assert_any_call(
            "iptables -I FORWARD -d 198.51.100.42 -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

@pytest.mark.asyncio
async def test_hysteria_warning_accumulation_and_ban():
    # Очищаем историю нарушений для чистоты теста
    recent_hysteria_violations.clear()
    
    server = {
        'ip': '192.168.1.99',
        'user': 'root',
        'key': 'config/dummy_key'
    }
    
    # 1. Формируем тестовые TCP лог-линии на sensitive порты
    tcp_error_line = (
        "May 25 03:00:00 server hysteria-server[100]: "
        "TCP error {\"id\": \"hacker_user\", \"addr\": \"203.0.113.5:54321\", "
        "\"reqAddr\": \"10.0.0.5:22\", \"error\": \"connection timed out\"}"
    )
    
    # Мокаем отправку алертов и функцию бана
    with patch("modules.proxmox.monitor.remote.hysteria.send_alert_to_admins", AsyncMock()) as mock_alert, \
         patch("modules.proxmox.monitor.remote.hysteria.block_remote_hysteria_user", AsyncMock(return_value=True)) as mock_block:
         
        # Попытка 1: Должен добавиться 1 варн
        await handle_remote_hysteria_line(tcp_error_line, server=server)
        assert len(recent_hysteria_violations.get("hacker_user", [])) == 1
        mock_alert.assert_called_once()
        mock_block.assert_not_called()
        
        mock_alert.reset_mock()
        
        # Попытка 2: Должен добавиться 2-й варн (но оповещение задросселировано)
        await handle_remote_hysteria_line(tcp_error_line, server=server)
        assert len(recent_hysteria_violations.get("hacker_user", [])) == 2
        mock_alert.assert_not_called()  # Оповещение задросселировано
        mock_block.assert_not_called()
        
        mock_alert.reset_mock()
        
        # Попытка 3: Должен сработать автоматический бан (3+ попытки)
        await handle_remote_hysteria_line(tcp_error_line, server=server)
        
        # Проверяем, что была вызвана блокировка пользователя
        mock_block.assert_called_once_with(server, "hacker_user")
        # Проверяем, что админы получили уведомление о бане (не дросселируется)
        mock_alert.assert_called_once()
        # Проверяем, что после бана счетчик нарушений сброшен
        assert len(recent_hysteria_violations.get("hacker_user", [])) == 0

@pytest.mark.asyncio
async def test_get_and_kill_self_defense_bot_itself():
    import os
    my_pid = os.getpid()
    
    # Сценарий: Процесс имеет PID самого бота
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (f'tcp ESTAB 0 0 127.0.0.1:22 192.0.2.42:22 users:(("python3",pid={my_pid},fd=3))'.encode(), b"")
    
    # Временно очищаем белый список процессов
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            
            # Проверяем, что процесс распознан как WHITELISTED (самозащита сработала)
            assert proc_name == "python3"
            assert pid == "WHITELISTED"
            
            # Проверяем, что ss выполнился, а kill -9 НЕ вызывался
            mock_exec.assert_any_call("ss", "-atnup", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            for call in mock_exec.call_args_list:
                assert call[0][0] != "kill"
    finally:
        settings.ips_process_whitelist = original_whitelist

@pytest.mark.asyncio
async def test_get_and_kill_self_defense_child_process():
    import os
    my_pid = os.getpid()
    child_pid = 99999
    
    # Сценарий: Процесс имеет другой PID, но его родитель - наш бот
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (f'tcp ESTAB 0 0 127.0.0.1:22 192.0.2.42:22 users:(("python3",pid={child_pid},fd=3))'.encode(), b"")
    
    # Временно очищаем белый список процессов
    from core.config import settings
    original_whitelist = settings.ips_process_whitelist
    settings.ips_process_whitelist = []
    
    # Мокаем проверку PPid в файле /proc/99999/status с правильной поддержкой контекстного менеджера с-команды
    mock_open = patch("builtins.open", MagicMock(side_effect=lambda path, *args, **kwargs: 
        MagicMock(__enter__=lambda s: s, __exit__=lambda s, *a: None, __iter__=lambda s: iter([f"Name: python3\n", f"PPid: {my_pid}\n"])) if "99999" in str(path) else open(path, *args, **kwargs)
    ))
    
    try:
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec, \
             patch("os.path.exists", return_value=True), \
             mock_open:
             
            proc_name, pid = await get_and_kill_local_or_lxc_process(vmid=0, spt=22)
            
            # Проверяем, что процесс распознан как дочерний (WHITELISTED)
            assert proc_name == "python3"
            assert pid == "WHITELISTED"
            
            # Проверяем, что kill -9 НЕ вызывался
            for call in mock_exec.call_args_list:
                assert call[0][0] != "kill"
    finally:
        settings.ips_process_whitelist = original_whitelist


@pytest.mark.asyncio
async def test_get_bot_public_ip():
    from modules.proxmox.monitor.remote.helpers import get_bot_public_ip
    import modules.proxmox.monitor.remote.helpers as remote_helpers
    
    # Сбросим кэш перед тестом
    remote_helpers.bot_public_ip = None
    
    # Мокаем aiohttp.ClientSession
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="203.0.113.88")
    
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    
    # get должен быть обычным MagicMock, чтобы возвращать контекст напрямую
    mock_session.get = MagicMock()
    
    mock_get_context = AsyncMock()
    mock_get_context.__aenter__.return_value = mock_response
    mock_session.get.return_value = mock_get_context
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        ip = await get_bot_public_ip()
        assert ip == "203.0.113.88"


@pytest.mark.asyncio
async def test_get_bot_public_ip_fallback():
    from modules.proxmox.monitor.remote.helpers import get_bot_public_ip
    import modules.proxmox.monitor.remote.helpers as remote_helpers
    
    remote_helpers.bot_public_ip = None
    
    # Первая попытка фейлится, вторая проходит
    mock_response_ok = AsyncMock()
    mock_response_ok.status = 200
    mock_response_ok.text = AsyncMock(return_value="203.0.113.99")
    
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    
    # get должен быть обычным MagicMock, чтобы возвращать контекст напрямую
    mock_session.get = MagicMock()
    
    mock_get_fail_context = AsyncMock()
    mock_get_fail_context.__aenter__.side_effect = Exception("ipify failed")
    
    mock_get_ok_context = AsyncMock()
    mock_get_ok_context.__aenter__.return_value = mock_response_ok
    
    mock_session.get.side_effect = [mock_get_fail_context, mock_get_ok_context]
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        ip = await get_bot_public_ip()
        assert ip == "203.0.113.99"



def test_parse_tcp_file():
    from modules.proxmox.monitor.remote.helpers import parse_tcp_file
    
    tcp_content = (
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 0100007F:0016 0100007F:0400 01 00000000:00000000 00:00000000 00000000  1000        0 12345 1 0000000000000000\n"
        "   1: 326433C6:3039 326433C6:0016 01 00000000:00000000 00:00000000 00000000     0        0 23456 1 0000000000000000\n"
    )
    
    mock_open = patch("builtins.open", MagicMock(side_effect=lambda path, *args, **kwargs: 
        MagicMock(__enter__=lambda s: s, __exit__=lambda s, *a: None, readlines=lambda: tcp_content.splitlines())
    ))
    
    with patch("os.path.exists", return_value=True), mock_open:
        conns = parse_tcp_file("/proc/999/net/tcp")
        assert len(conns) == 2
        assert conns[1] == (12345, "198.51.100.50", 22, 23456)


def test_get_active_ssh_ports_for_vps():
    from modules.proxmox.monitor.remote.helpers import get_active_ssh_ports_for_vps
    
    with patch("os.getpid", return_value=1000), \
         patch("modules.proxmox.monitor.remote.helpers.get_child_pids", return_value=[1001, 1002]), \
         patch("os.path.exists", side_effect=lambda path: True if "/proc/" in str(path) else False), \
         patch("builtins.open", MagicMock(side_effect=lambda path, *args, **kwargs:
             MagicMock(__enter__=lambda s: s, __exit__=lambda s, *a: None, read=lambda: "ssh" if "1001/comm" in str(path) else "bash")
         )), \
         patch("modules.proxmox.monitor.remote.helpers.get_process_socket_inodes", return_value={99999}), \
         patch("modules.proxmox.monitor.remote.helpers.parse_tcp_file", side_effect=lambda path: 
             [(43210, "198.51.100.50", 22, 99999)] if "1001" in str(path) else []
         ):
        ports = get_active_ssh_ports_for_vps("198.51.100.50")
        assert ports == [43210]


@pytest.mark.asyncio
async def test_handle_remote_ssh_auth_line_trusted_bot():
    from modules.proxmox.monitor.remote.auth import handle_remote_ssh_auth_line
    import modules.proxmox.monitor.remote.auth as remote_auth
    from core.config import settings
    
    server = {
        'ip': '198.51.100.50',
        'user': 'root',
        'key': 'config/dummy_key'
    }
    
    original_keys = settings.remote_monitor_ignore_keys
    original_ips = settings.remote_monitor_ignore_ips
    settings.remote_monitor_ignore_keys = ["bot@bot"]
    settings.remote_monitor_ignore_ips = ["203.0.113.88"]
    
    line = "May 27 21:00:00 server sshd[123]: Accepted publickey for root from 203.0.113.88 port 43210 ssh2: RSA SHA256:fingerprint_xyz"
    
    try:
        remote_auth.remote_key_caches[server['ip']] = {"SHA256:fingerprint_xyz": "bot@bot"}
        import modules.proxmox.monitor.remote.helpers as remote_helpers
        remote_helpers.bot_public_ip = "203.0.113.88"
        
        with patch("modules.proxmox.monitor.remote.auth.get_active_ssh_ports_for_vps", return_value=[43210]), \
             patch("modules.proxmox.monitor.remote.auth.refresh_remote_key_cache", AsyncMock()) as mock_refresh, \
             patch("modules.proxmox.monitor.remote.auth.send_alert_to_admins", AsyncMock()) as mock_send:
            await handle_remote_ssh_auth_line(line, server=server)
            mock_send.assert_not_called()
            mock_refresh.assert_not_called()
    finally:
        settings.remote_monitor_ignore_keys = original_keys
        settings.remote_monitor_ignore_ips = original_ips


@pytest.mark.asyncio
async def test_handle_remote_ssh_auth_line_unauthorized_ip():
    from modules.proxmox.monitor.remote.auth import handle_remote_ssh_auth_line
    import modules.proxmox.monitor.remote.auth as remote_auth
    from core.config import settings
    
    server = {
        'ip': '198.51.100.50',
        'user': 'root',
        'key': 'config/dummy_key'
    }
    
    original_keys = settings.remote_monitor_ignore_keys
    original_ips = settings.remote_monitor_ignore_ips
    settings.remote_monitor_ignore_keys = ["bot@bot"]
    settings.remote_monitor_ignore_ips = ["203.0.113.88"]
    
    line = "May 27 21:00:00 server sshd[123]: Accepted publickey for root from 99.99.99.99 port 54321 ssh2: RSA SHA256:fingerprint_xyz"
    
    try:
        remote_auth.remote_key_caches[server['ip']] = {"SHA256:fingerprint_xyz": "bot@bot"}
        import modules.proxmox.monitor.remote.helpers as remote_helpers
        remote_helpers.bot_public_ip = "203.0.113.88"
        
        with patch("modules.proxmox.monitor.remote.auth.get_active_ssh_ports_for_vps", return_value=[]), \
             patch("modules.proxmox.monitor.remote.auth.refresh_remote_key_cache", AsyncMock()) as mock_refresh, \
             patch("modules.proxmox.monitor.remote.auth.send_alert_to_admins", AsyncMock()) as mock_send:
            await handle_remote_ssh_auth_line(line, server=server)
            
            mock_send.assert_called_once()
            alert_text = mock_send.call_args[0][0]
            assert "КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ БЕЗОПАСНОСТИ" in alert_text
            assert "Возможна утечка и компрометация приватного ключа" in alert_text
            mock_refresh.assert_not_called()
    finally:
        settings.remote_monitor_ignore_keys = original_keys
        settings.remote_monitor_ignore_ips = original_ips


@pytest.mark.asyncio
async def test_handle_remote_ssh_auth_line_compromised_container():
    from modules.proxmox.monitor.remote.auth import handle_remote_ssh_auth_line
    import modules.proxmox.monitor.remote.auth as remote_auth
    from core.config import settings
    
    server = {
        'ip': '198.51.100.50',
        'user': 'root',
        'key': 'config/dummy_key'
    }
    
    original_keys = settings.remote_monitor_ignore_keys
    original_ips = settings.remote_monitor_ignore_ips
    settings.remote_monitor_ignore_keys = ["bot@bot"]
    settings.remote_monitor_ignore_ips = ["203.0.113.88"]
    
    line = "May 27 21:00:00 server sshd[123]: Accepted publickey for root from 203.0.113.88 port 9999 ssh2: RSA SHA256:fingerprint_xyz"
    
    try:
        remote_auth.remote_key_caches[server['ip']] = {"SHA256:fingerprint_xyz": "bot@bot"}
        import modules.proxmox.monitor.remote.helpers as remote_helpers
        remote_helpers.bot_public_ip = "203.0.113.88"
        
        with patch("modules.proxmox.monitor.remote.auth.get_active_ssh_ports_for_vps", return_value=[43210]), \
             patch("modules.proxmox.monitor.remote.auth.refresh_remote_key_cache", AsyncMock()) as mock_refresh, \
             patch("modules.proxmox.monitor.remote.auth.send_alert_to_admins", AsyncMock()) as mock_send:
            await handle_remote_ssh_auth_line(line, server=server)
            
            mock_send.assert_called_once()
            alert_text = mock_send.call_args[0][0]
            assert "КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ БЕЗОПАСНОСТИ" in alert_text
            assert "Крайне высокий риск компрометации контейнера/хоста бота" in alert_text
            mock_refresh.assert_not_called()
    finally:
        settings.remote_monitor_ignore_keys = original_keys
        settings.remote_monitor_ignore_ips = original_ips


@pytest.mark.asyncio
async def test_hysteria_disconnect_silent_no_ssh():
    from modules.proxmox.monitor.remote.hysteria.alerts.disconnect import handle_hysteria_disconnect
    from modules.proxmox.monitor.remote.hysteria.alerts.state import active_activity_cards
    import time as pytime
    import datetime
    
    server = {'ip': '198.51.100.50'}
    username = 'test_user'
    client_ip = '198.51.100.99'
    key = (server['ip'], username)
    
    # Создаем активную карточку в памяти
    now = pytime.time()
    active_activity_cards[key] = {
        'admin_messages': [],
        'started_at': now,
        'last_activity_at': now,
        'lines': [],
        'connections': {client_ip: [datetime.datetime.now()]}
    }
    
    with patch("modules.proxmox.monitor.remote.hysteria.alerts.disconnect.get_remote_hysteria_traffic", AsyncMock()) as mock_get_traffic, \
         patch("modules.proxmox.monitor.remote.hysteria.alerts.disconnect.update_disconnection", AsyncMock()) as mock_db:
         
        # Запускаем в бесшумном режиме (silent=True)
        await handle_hysteria_disconnect(server, username, client_ip, silent=True)
        
        # Убеждаемся, что запрос трафика к удаленному API Hysteria по SSH/curl НЕ вызывался
        mock_get_traffic.assert_not_called()
        # Но сессия в базе данных все равно закрылась
        mock_db.assert_called_once()






